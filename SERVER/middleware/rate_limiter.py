import time
import threading
from fastapi import Request, HTTPException


# ── Configuration ────────────────────────────────────────────────────────────
MAX_REQUESTS_PER_WINDOW = 2
WINDOW_SECONDS = 60
COOLDOWN_SECONDS = 30

MAX_REQUESTS_PER_DAY = 100
DAY_SECONDS = 24 * 60 * 60

LOAD_TIER_1_THRESHOLD = 3
LOAD_TIER_2_THRESHOLD = 6


# ── Global State ─────────────────────────────────────────────────────────────
_lock = threading.Lock()

# Per-minute requests
_request_log: dict[str, list[float]] = {}

# Per-day requests
_daily_request_log: dict[str, list[float]] = {}

# Cooldowns
_cooldowns: dict[str, float] = {}

# Active requests
_active_requests = 0


# ── Helpers ──────────────────────────────────────────────────────────────────
def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _effective_limit() -> int:
    if _active_requests > LOAD_TIER_2_THRESHOLD:
        return 1
    if _active_requests > LOAD_TIER_1_THRESHOLD:
        return max(1, MAX_REQUESTS_PER_WINDOW // 2)
    return MAX_REQUESTS_PER_WINDOW


def _prune(ip: str, now: float) -> None:
    cutoff = now - WINDOW_SECONDS
    if ip in _request_log:
        _request_log[ip] = [t for t in _request_log[ip] if t > cutoff]
        if not _request_log[ip]:
            del _request_log[ip]


def _prune_daily(ip: str, now: float) -> None:
    cutoff = now - DAY_SECONDS
    if ip in _daily_request_log:
        _daily_request_log[ip] = [
            t for t in _daily_request_log[ip]
            if t > cutoff
        ]
        if not _daily_request_log[ip]:
            del _daily_request_log[ip]


# ── Public API ───────────────────────────────────────────────────────────────
def increment_active() -> None:
    global _active_requests
    with _lock:
        _active_requests += 1


def decrement_active() -> None:
    global _active_requests
    with _lock:
        _active_requests = max(0, _active_requests - 1)


def check_rate_limit(request: Request, cost: int = 1) -> dict:
    now = time.time()
    ip = _get_client_ip(request)

    with _lock:
        # ── Cooldown check ──────────────────────────────────────────────
        if ip in _cooldowns:
            expires = _cooldowns[ip]

            if now < expires:
                retry_after = int(expires - now) + 1

                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "Rate limit exceeded",
                        "message": (
                            f"Please wait {retry_after} seconds before "
                            f"trying again."
                        ),
                        "retry_after": retry_after,
                    },
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(_effective_limit()),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(expires)),
                    },
                )

            del _cooldowns[ip]

        # ── Daily limit check ───────────────────────────────────────────
        _prune_daily(ip, now)
        daily_used = len(_daily_request_log.get(ip, []))

        if daily_used + cost > MAX_REQUESTS_PER_DAY:
            oldest = _daily_request_log[ip][0]
            retry_after = int(oldest + DAY_SECONDS - now) + 1

            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Daily rate limit exceeded",
                    "message": (
                        f"You've reached the daily limit of "
                        f"{MAX_REQUESTS_PER_DAY} requests."
                    ),
                    "retry_after": retry_after,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Daily-Limit": str(MAX_REQUESTS_PER_DAY),
                    "X-RateLimit-Daily-Remaining": "0",
                },
            )

        # ── Per-minute limit check ──────────────────────────────────────
        _prune(ip, now)

        limit = _effective_limit()
        used = len(_request_log.get(ip, []))

        if used + cost > limit:
            cooldown_until = now + COOLDOWN_SECONDS
            _cooldowns[ip] = cooldown_until

            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "message": (
                        f"You've hit the upload limit "
                        f"({limit} requests per {WINDOW_SECONDS}s). "
                        f"Please wait {COOLDOWN_SECONDS} seconds."
                    ),
                    "retry_after": COOLDOWN_SECONDS,
                },
                headers={
                    "Retry-After": str(COOLDOWN_SECONDS),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(cooldown_until)),
                },
            )

        # ── Record request in minute log ────────────────────────────────
        if ip not in _request_log:
            _request_log[ip] = []

        for _ in range(cost):
            _request_log[ip].append(now)

        # ── Record request in daily log ─────────────────────────────────
        if ip not in _daily_request_log:
            _daily_request_log[ip] = []

        for _ in range(cost):
            _daily_request_log[ip].append(now)

        remaining = max(0, limit - len(_request_log[ip]))
        daily_remaining = max(
            0,
            MAX_REQUESTS_PER_DAY - len(_daily_request_log[ip])
        )

        window_reset = now + WINDOW_SECONDS

    return {
        "X-RateLimit-Limit": str(limit),
        "X-RateLimit-Remaining": str(remaining),
        "X-RateLimit-Reset": str(int(window_reset)),
        "X-RateLimit-Daily-Limit": str(MAX_REQUESTS_PER_DAY),
        "X-RateLimit-Daily-Remaining": str(daily_remaining),
    }


def get_load_info() -> dict:
    with _lock:
        return {
            "active_requests": _active_requests,
            "effective_limit": _effective_limit(),
            "tracked_ips": len(_request_log),
            "tracked_daily_ips": len(_daily_request_log),
        }