import { useNavigate } from 'react-router-dom';
import './HomePage.css';

function HomePage() {
  const navigate = useNavigate();

  return (
    <div className="home-page">
      <div className="home-headline">
        <h2 className="home-title">What would you like to do?</h2>
        <p className="home-sub">Choose a tool to get started with AI-powered resume intelligence.</p>
      </div>

      <div className="feature-cards">
        {/* Feature 1: Resume Parser */}
        <div className="feature-card glass-card" onClick={() => navigate('/upload')} id="feature-resume-parser">
          <div className="feature-icon-wrap feature-icon-blue">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <polyline points="10 9 9 9 8 9" />
            </svg>
          </div>
          <div className="feature-content">
            <h3 className="feature-title">Resume to nCircle Format</h3>
            {/* <div className="feature-tags">
              <span className="tag">PDF Upload</span>
              <span className="tag">AI Extraction</span>
              <span className="tag">Auto Format</span>
            </div> */}
          </div>
          <div className="feature-cta">
            <span>Get Started</span>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="9 18 15 12 9 6" />
            </svg>
          </div>
        </div>

        {/* Feature 2: JD Score Matcher */}
        <div className="feature-card glass-card" onClick={() => navigate('/jd-matcher')} id="feature-jd-matcher">
          <div className="feature-icon-wrap feature-icon-purple">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
              <line x1="11" y1="8" x2="11" y2="14" />
              <line x1="8" y1="11" x2="14" y2="11" />
            </svg>
          </div>
          <div className="feature-content">
            <h3 className="feature-title">Resume analyzer</h3>
            {/* <div className="feature-tags">
              <span className="tag tag--purple">Bulk Upload</span>
              <span className="tag tag--purple">AI Scoring</span>
              <span className="tag tag--purple">PDF Report</span>
            </div> */}
          </div>
          <div className="feature-cta feature-cta--purple">
            <span>Start Matching</span>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="9 18 15 12 9 6" />
            </svg>
          </div>
        </div>
      </div>
    </div>
  );
}

export default HomePage;
