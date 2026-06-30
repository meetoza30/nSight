import { useEffect, useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import './ProcessingPage.css';
import { API_BASE } from '../utils/api';

function ProcessingPage({ file, onExtractComplete }) {
  const navigate = useNavigate();
  const [progress, setProgress] = useState(0);
  const [rateLimited, setRateLimited] = useState(false);
  const [cooldown, setCooldown] = useState(0);

  const hasUploaded = useRef(false);
  const cooldownRef = useRef(null);

  // Countdown timer for rate-limit cooldown
  const startCooldown = useCallback((seconds) => {
    setRateLimited(true);
    setCooldown(seconds);
    if (cooldownRef.current) clearInterval(cooldownRef.current);

    cooldownRef.current = setInterval(() => {
      setCooldown(prev => {
        if (prev <= 1) {
          clearInterval(cooldownRef.current);
          cooldownRef.current = null;
          // Redirect back to upload after cooldown
          navigate('/upload');
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  }, [navigate]);

  useEffect(() => {
    return () => {
      if (cooldownRef.current) clearInterval(cooldownRef.current);
    };
  }, []);

  useEffect(() => {
    if (hasUploaded.current) return;
    hasUploaded.current = true;

    const uploadResume = async () => {
      try {
        const formData = new FormData();
        formData.append('file', file);

        const progressInterval = setInterval(() => {
          setProgress(prev => {
            if (prev < 95) return prev + 5;
            return prev;
          });
        }, 400);

        const response = await fetch(`${API_BASE}/extract-resume`, {
          method: 'POST',
          body: formData,
        });

        clearInterval(progressInterval);

        // ── Handle 429 Rate Limited ──────────────────────────────────
        if (response.status === 429) {
          const errData = await response.json().catch(() => ({}));
          const detail = errData.detail || {};
          const retryAfter =
            detail.retry_after ||
            parseInt(response.headers.get('Retry-After') || '30', 10);

          startCooldown(retryAfter);
          return;
        }

        if (!response.ok) {
          throw new Error('Failed to process resume');
        }

        const result = await response.json();

        setProgress(100);

        onExtractComplete(result.data);

        setTimeout(() => {
          navigate('/review');
        }, 500);

      } catch (error) {
        console.error('Error uploading resume:', error);
        setTimeout(() => {
          navigate('/upload');
        }, 2000);
      }
    };

    uploadResume();
  }, [file, navigate, onExtractComplete, startCooldown]);

  // ── Rate-limited state ───────────────────────────────────────────────
  if (rateLimited) {
    return (
      <div className="processing-page glass-card rate-limit-card">
        <div className="rate-limit-icon">
          <svg width="52" height="52" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <polyline points="12 6 12 12 16 14" />
          </svg>
        </div>
        <h2 className="processing-title rate-limit-title">
          Slow down — server is busy
        </h2>
        <p className="processing-subtitle rate-limit-sub">
          You've uploaded too many resumes in a short time. Please wait before trying again.
        </p>
        <div className="cooldown-timer">
          <span className="cooldown-number">{cooldown}</span>
          <span className="cooldown-label">seconds remaining</span>
        </div>
        <div className="cooldown-bar-track">
          <div className="cooldown-bar-fill" style={{ animationDuration: `${cooldown}s` }} />
        </div>
        <p className="rate-limit-hint">You'll be redirected automatically.</p>
      </div>
    );
  }

  // ── Normal processing state ──────────────────────────────────────────
  return (
    <div className="processing-page glass-card">
      <h2 className="processing-title">Extracting details from your resume...</h2>
      <p className="processing-subtitle">This will only take a moment.</p>
      <div className="res-scanner-icon">
            <svg width="52" height="52" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="res-scan-svg">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            <div className="res-scan-ring" />
          </div>
    </div>
  );
}

export default ProcessingPage;
