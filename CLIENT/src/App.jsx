import { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import HomePage from './pages/HomePage';
import UploadPage from './pages/UploadPage';
import ProcessingPage from './pages/ProcessingPage';
import ReviewPage from './pages/ReviewPage';
import DownloadPage from './pages/DownloadPage';
import JDMatcherPage from './pages/JDMatcherPage';
import JDResultsPage from './pages/JDResultsPage';
import logo from './icon/ncircle_tech_logo.jpg';
import './App.css';

function AppHeader({ onReset }) {
  const navigate = useNavigate();
  return (
    <header className="app-header" style={{ cursor: 'pointer' }} onClick={() => {
      if (onReset) onReset();
      navigate('/');
    }}>
      <img src={logo} alt="nCircle Logo" className="app-logo-small" />
      <h1 className="app-title">
        nSight
        <span className="app-subtitle">by nCircle Tech</span>
      </h1>
    </header>
  );
}

function App() {
  // Resume parser state
  const [uploadedFile, setUploadedFile] = useState(null);
  const [extractedData, setExtractedData] = useState(() => {
    try {
      const saved = localStorage.getItem('nsight_extracted_data');
      return saved ? JSON.parse(saved) : null;
    } catch (e) {
      return null;
    }
  });
  const [processedData, setProcessedData] = useState(null);

  useEffect(() => {
    try {
      if (extractedData) {
        localStorage.setItem('nsight_extracted_data', JSON.stringify(extractedData));
      } else {
        localStorage.removeItem('nsight_extracted_data');
      }
    } catch (e) {
      console.error('Failed to sync to localStorage', e);
    }
  }, [extractedData]);

  const resetResumeFlow = () => {
    setUploadedFile(null);
    setExtractedData(null);
    setProcessedData(null);
    try {
      localStorage.removeItem('nsight_extracted_data');
    } catch (e) {
      console.error(e);
    }
  };

  // JD Matcher state
  const [matchData, setMatchData] = useState(null);

  const resetMatchData = () => setMatchData(null);

  return (
    <Router>
      <div className="app">
        <img src={logo} alt="" className="watermark-bg" />

        <AppHeader onReset={resetResumeFlow} />

        <main className="main-container">
          <Routes>
            {/* ---- Home ---- */}
            <Route path="/" element={<UploadPage
                  onFileUpload={setUploadedFile}
                  uploadedFile={uploadedFile}
                  onReset={resetResumeFlow}
                />} />

            {/* ---- Resume Parser flow ---- */}
            <Route
              path="/upload"
              element={
                <UploadPage
                  onFileUpload={setUploadedFile}
                  uploadedFile={uploadedFile}
                  onReset={resetResumeFlow}
                />
              }
            />
            <Route
              path="/processing"
              element={
                uploadedFile ? (
                  <ProcessingPage
                    file={uploadedFile}
                    onExtractComplete={setExtractedData}
                  />
                ) : (
                  <Navigate to="/" replace />
                )
              }
            />
            <Route
              path="/review"
              element={
                extractedData ? (
                  <ReviewPage
                    extractedData={extractedData}
                    onGenerateComplete={setProcessedData}
                    onDataChange={setExtractedData}
                  />
                ) : (
                  <Navigate to="/" replace />
                )
              }
            />
            <Route
              path="/download"
              element={
                processedData ? (
                  <DownloadPage data={processedData} onReset={resetResumeFlow} />
                ) : (
                  <Navigate to="/" replace />
                )
              }
            />

            {/* ---- JD Matcher flow ---- */}
            <Route
              path="/jd-matcher"
              element={
                <JDMatcherPage onMatchComplete={setMatchData} />
              }
            />
            <Route
              path="/jd-results"
              element={
                matchData ? (
                  <JDResultsPage matchData={matchData} onReset={resetMatchData} />
                ) : (
                  <Navigate to="/jd-matcher" replace />
                )
              }
            />

            {/* ---- Fallback ---- */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
