import { useNavigate } from 'react-router-dom';
import './JDResultsPage.css';
import { API_BASE } from '../utils/api';

/* Grade config */
const GRADE_CONFIG = {
  'Strong Match': { color: '#16A34A', bg: '#F0FDF4', border: '#BBF7D0', ring: '#22C55E', label: 'Strong', icon: '🟢' },
  'Good Match':   { color: '#2563EB', bg: '#EFF6FF', border: '#BFDBFE', ring: '#3B82F6', label: 'Good',   icon: '🔵' },
  'Moderate Match': { color: '#D97706', bg: '#FFFBEB', border: '#FDE68A', ring: '#F59E0B', label: 'Moderate', icon: '🟡' },
  'Weak Match':   { color: '#DC2626', bg: '#FEF2F2', border: '#FECACA', ring: '#EF4444', label: 'Weak',   icon: '🔴' },
};

function scoreToGrade(score) {
  if (score <= 25) return 'Weak Match';
  if (score <= 50) return 'Moderate Match';
  if (score <= 75) return 'Good Match';
  return 'Strong Match';
}

function getGradeConfig(grade) {
  return GRADE_CONFIG[grade] || { color: '#64748B', bg: '#F8FAFC', border: '#E2E8F0', ring: '#94A3B8', label: grade, icon: '⚪' };
}

/* Circular score ring */
function ScoreRing({ score, color, ring }) {
  const radius = 28;
  const circumference = 2 * Math.PI * radius;
  const filled = (score / 100) * circumference;
  const dash = `${filled} ${circumference - filled}`;

  return (
    <div className="score-ring-wrap">
      <svg width="76" height="76" viewBox="0 0 76 76">
        <circle cx="38" cy="38" r={radius} fill="none" stroke="#E2E8F0" strokeWidth="7" />
        <circle
          cx="38" cy="38" r={radius}
          fill="none"
          stroke={ring}
          strokeWidth="7"
          strokeDasharray={dash}
          strokeLinecap="round"
          transform="rotate(-90 38 38)"
          style={{ transition: 'stroke-dasharray 1s ease' }}
        />
      </svg>
      <div className="score-ring-label" style={{ color }}>
        <span className="score-ring-pct">{score}</span>
        <span className="score-ring-sym">%</span>
      </div>
    </div>
  );
}

function CandidateCard({ result, index }) {
  const cfg = getGradeConfig(result.grade);

  return (
    <div
      className="candidate-card glass-card"
      id={`candidate-${index + 1}`}
      style={{ '--card-border': cfg.border, '--card-ring': cfg.ring }}
    >
      {/* Left: score ring */}
      <div className="card-score-col">
        <ScoreRing score={result.overall_score} color={cfg.color} ring={cfg.ring} />
      </div>

      {/* Middle: info */}
      <div className="card-info-col">
        <div className="card-top-row">
          <h3 className="candidate-name">{result.candidate_name || result.filename.replace('.pdf', '')}</h3>
          <span
            className="grade-badge"
            style={{ background: cfg.bg, color: cfg.color, borderColor: cfg.border }}
          >
            {cfg.icon} {cfg.label}
          </span>
        </div>
        <p className="candidate-filename">{result.filename}</p>
        <p className="candidate-summary">{result.summary}</p>
      </div>
    </div>
  );
}

function JDResultsPage({ matchData, onReset }) {
  const navigate = useNavigate();

  if (!matchData) {
    navigate('/jd-matcher', { replace: true });
    return null;
  }

  const { results = [], report_download_url } = matchData;

  const mappedResults = results.map(r => ({
    ...r,
    grade: scoreToGrade(r.overall_score)
  }));

  // Sort: Strong → Good → Moderate → Weak
  const gradeOrder = { 'Strong Match': 0, 'Good Match': 1, 'Moderate Match': 2, 'Weak Match': 3 };
  const sorted = [...mappedResults].sort((a, b) => {
    const ao = gradeOrder[a.grade] ?? 99;
    const bo = gradeOrder[b.grade] ?? 99;
    if (ao !== bo) return ao - bo;
    return b.overall_score - a.overall_score;
  });

  const handleDownloadReport = () => {
    if (!report_download_url) return;
    const url = report_download_url.startsWith('http') ? report_download_url : `${API_BASE}${report_download_url}`;
    window.open(url, '_blank');
  };

  const handleNewMatch = () => {
    onReset?.();
    navigate('/jd-matcher');
  };

  /* Grade summary counts */
  const grades = { 'Strong Match': 0, 'Good Match': 0, 'Moderate Match': 0, 'Weak Match': 0 };
  mappedResults.forEach(r => { if (grades[r.grade] !== undefined) grades[r.grade]++; });

  return (
    <div className="jd-results-page">
      {/* ---- Top bar ---- */}
      <div className="jdr-topbar">
        <div className="jdr-topbar-left">
          <div className="jdr-icon-wrap">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="9 11 12 14 22 4" /><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
            </svg>
          </div>
          <div>
            <h2 className="jdr-main-title">Match Analysis Complete</h2>
            <p className="jdr-main-sub">{mappedResults.length} candidate{mappedResults.length !== 1 ? 's' : ''} analyzed and ranked by fit</p>
          </div>
        </div>

        <div className="jdr-topbar-actions">
          {report_download_url && (
            <button id="download-report-btn" className="primary-btn jdr-download-btn" onClick={handleDownloadReport}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              Download Match Report (PDF)
            </button>
          )}
          <button className="outline-btn jdr-new-btn" onClick={handleNewMatch}>
            New Match
          </button>
        </div>
      </div>

      {/* ---- Grade summary strip ---- */}
      <div className="jdr-grade-strip">
        {Object.entries(grades).map(([grade, count]) => {
          const cfg = getGradeConfig(grade);
          return (
            <div className="jdr-grade-chip" key={grade} style={{ background: cfg.bg, borderColor: cfg.border }}>
              <span className="jdr-grade-count" style={{ color: cfg.color }}>{count}</span>
              <span className="jdr-grade-label" style={{ color: cfg.color }}>{cfg.label}</span>
            </div>
          );
        })}
      </div>

      {/* ---- Candidate cards ---- */}
      <div className="jdr-cards">
        {sorted.length === 0 && (
          <div className="jdr-empty glass-card">
            <p>No results returned from the API.</p>
          </div>
        )}
        {sorted.map((result, i) => (
          <CandidateCard key={result.filename} result={result} index={i} />
        ))}
      </div>

      {/* Removed bottom CTA as per request */}
    </div>
  );
}

export default JDResultsPage;
