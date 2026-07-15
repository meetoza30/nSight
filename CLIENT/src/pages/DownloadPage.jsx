import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './DownloadPage.css';

function DownloadPage({ data, onReset }) {
  const navigate = useNavigate();
  const [downloadUrl, setDownloadUrl] = useState(null);

  useEffect(() => {
    if (data?.blob) {
      const url = URL.createObjectURL(data.blob);
      setDownloadUrl(url);

      return () => {
        URL.revokeObjectURL(url);
      };
    }
  }, [data]);

  const handleDownload = () => {
    if (downloadUrl && data?.filename) {
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = data.filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  const handleNewResume = () => {
    if (onReset) onReset();
    try {
      localStorage.removeItem('nsight_extracted_data');
    } catch (e) {
      console.error(e);
    }
    navigate('/');
  };

  return (
    <div className="download-page glass-card">
      <div className="success-icon-wrapper">
        <svg viewBox="0 0 100 100" className="animated-checkmark">
          <circle 
            cx="50" cy="50" r="45" 
            fill="none" 
            stroke="var(--accent-blue)" 
            strokeWidth="4" 
            className="checkmark-circle"
          />
          <path 
            fill="none" 
            stroke="var(--primary-navy)" 
            strokeWidth="5" 
            strokeLinecap="round" 
            strokeLinejoin="round" 
            d="M30 50 L43 63 L70 36" 
            className="checkmark-check"
          />
        </svg>
      </div>

      <h1 className="download-title">
        DONE!
      </h1>

      <p className="download-subtitle">
        Resume has been successfully generated in nCircle format.
      </p>
      
      {data?.filename && (
        <div className="filename-chip">
           {data.filename}
        </div>
      )}

      <div className="download-actions">
        <button className="primary-btn" onClick={handleDownload}>
          Click to download
        </button>
        <button className="outline-btn" onClick={handleNewResume}>
          Convert another resume
        </button>
      </div>
    </div>
  );
}

export default DownloadPage;
