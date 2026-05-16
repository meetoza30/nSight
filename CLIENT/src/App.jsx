import { useState } from 'react';
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

function AppHeader() {
  const navigate = useNavigate();
  return (
    <header className="app-header" style={{ cursor: 'pointer' }} onClick={() => navigate('/')}>
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
  const [extractedData, setExtractedData] = useState(null);
  const [processedData, setProcessedData] = useState(null);

  // JD Matcher state
  const [matchData, setMatchData] = useState(null);

  const resetMatchData = () => setMatchData(null);

  return (
    <Router>
      <div className="app">
        <img src={logo} alt="" className="watermark-bg" />

        <AppHeader />

        <main className="main-container">
          <Routes>
            {/* ---- Home ---- */}
            <Route path="/" element={<HomePage />} />

            {/* ---- Resume Parser flow ---- */}
            <Route
              path="/upload"
              element={
                <UploadPage
                  onFileUpload={setUploadedFile}
                  uploadedFile={uploadedFile}
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
                  <Navigate to="/upload" replace />
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
                  />
                ) : (
                  <Navigate to="/upload" replace />
                )
              }
            />
            <Route
              path="/download"
              element={
                processedData ? (
                  <DownloadPage data={processedData} />
                ) : (
                  <Navigate to="/upload" replace />
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
