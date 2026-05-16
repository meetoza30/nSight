import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './ProcessingPage.css';
import { API_BASE } from '../utils/api';

function ProcessingPage({ file, onExtractComplete }) {
  const navigate = useNavigate();
  const [progress, setProgress] = useState(0);

  useEffect(() => {
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
  }, [file, navigate, onExtractComplete]);

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
