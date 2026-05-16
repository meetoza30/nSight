import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './JDMatcherPage.css';
import { API_BASE } from '../utils/api';

function JDMatcherPage({ onMatchComplete }) {
  const navigate = useNavigate();

  const [jdMode, setJdMode] = useState('text');
  const [jdText, setJdText] = useState('');
  const [jdFile, setJdFile] = useState(null);
  const jdFileRef = useRef(null);
  const [resumeFiles, setResumeFiles] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const resumeInputRef = useRef(null);


  const [isLoading, setIsLoading] = useState(false);
  // const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);

  /* ---- JD FILE HANDLERS ---- */
  const handleJdFileSelect = (e) => {
    const f = e.target.files[0];
    if (f && f.type === 'application/pdf') setJdFile(f);
    else if (f) setError('JD PDF must be a PDF file.');
  };

  /* ---- RESUME FILE HANDLERS ---- */
  const addResumes = (files) => {
    const pdfs = Array.from(files).filter(f => f.type === 'application/pdf');
    if (pdfs.length !== files.length) setError('Only PDF files accepted. Non-PDFs were skipped.');
    setResumeFiles(prev => {
      const names = new Set(prev.map(f => f.name));
      return [...prev, ...pdfs.filter(f => !names.has(f.name))];
    });
  };

  const handleDragOver = (e) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave = (e) => { e.preventDefault(); setIsDragging(false); };
  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files.length) addResumes(e.dataTransfer.files);
  };

  const removeResume = (name) => setResumeFiles(prev => prev.filter(f => f.name !== name));

  /* ---- SUBMIT ---- */
  const handleSubmit = async () => {
    setError(null);

    // Validation
    if (jdMode === 'text' && !jdText.trim()) return setError('Please paste the Job Description text.');
    if (jdMode === 'file' && !jdFile) return setError('Please upload a JD PDF file.');
    if (resumeFiles.length === 0) return setError('Please upload at least one resume PDF.');

    const formData = new FormData();
    if (jdMode === 'text') {
      formData.append('jd_text', jdText.trim());
    } else {
      formData.append('jd_file', jdFile);
    }
    resumeFiles.forEach(f => formData.append('resume_files', f));

    setIsLoading(true);
    // setProgress(0);

    // Animate progress bar (fake progress during API call)
    // const progressInterval = setInterval(() => {
    //   setProgress(p => {
    //     if (p >= 88) { clearInterval(progressInterval); return p; }
    //     return p + Math.random() * 6;
    //   });
    // }, 600);

    try {
      const res = await fetch(`${API_BASE}/match-bulk`, {
        method: 'POST',
        body: formData,
      });

      // clearInterval(progressInterval);
      // setProgress(100);

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Server error ${res.status}`);
      }

      const data = await res.json();
      onMatchComplete(data);

      setTimeout(() => navigate('/jd-results'), 300);
    } catch (err) {
      // clearInterval(progressInterval);
      setIsLoading(false);
      // setProgress(0);
      setError(err.message || 'Something went wrong. Please try again.');
    }
  };

  /* ---- RENDER ---- */
  if (isLoading) {
    return (
      <div className="jd-matcher-page-container">
        <div className="jdm-header-top">
        <div className="jdm-header-left">
        <div className="jdm-icon-wrap">
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
        </div>
        <div>
          <h2 className="jdm-title">Resume analyzer</h2>
          <p className="jdm-subtitle">Match multiple resumes against a single Job Description</p>
        </div>
        </div>
        {/* ---- Submit ---- */}
        <div className="jdm-footer">
          <button
            id="jdm-submit-btn"
            className="primary-btn jdm-submit-btn"
            onClick={handleSubmit}
            disabled={isLoading}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            Run analysis
          </button>
          <button className="outline-btn" onClick={() => navigate('/')}>Back</button>
        </div>
      </div>

        <div className="jdm-section glass-card jd-loading-state">
          <div className="jd-scanner-icon">
            <svg width="52" height="52" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="jd-scan-svg">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            <div className="jd-scan-ring" />
          </div>
          <h3 className="jd-loading-title">Deep Scanning Resumes…</h3>
          <p className="jd-loading-sub">
            Analyzing {resumeFiles.length} resume{resumeFiles.length > 1 ? 's' : ''} against the JD. This may take a while.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="jd-matcher-page-container">
      {/* Header top */}
      <div className="jdm-header-top">
        <div className="jdm-header-left">
        <div className="jdm-icon-wrap">
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
        </div>
        <div>
          <h2 className="jdm-title">Resume analyzer</h2>
          <p className="jdm-subtitle">Match multiple resumes against a single Job Description</p>
        </div>
        </div>
        {/* ---- Submit ---- */}
        <div className="jdm-footer">
          <button
            id="jdm-submit-btn"
            className="primary-btn jdm-submit-btn"
            onClick={handleSubmit}
            disabled={isLoading}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            Run analysis
          </button>
          <button className="outline-btn" onClick={() => navigate('/')}>Back</button>
        </div>
      </div>

      {error && (
        <div className="jdm-error" role="alert">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          {error}
        </div>
      )}

      <div className="jdm-sections-row">
        {/* ---- Section 1: Job Description ---- */}
        <section className="jdm-section glass-card">
          <div className="jdm-section-label">
            <span className="jdm-step">1</span>
            <h3 className="jdm-section-title">Job Description</h3>
          </div>

          {/* Toggle tabs */}
          <div className="jdm-toggle-tabs" role="tablist">
            <button
              id="tab-paste"
              role="tab"
              aria-selected={jdMode === 'text'}
              className={`jdm-tab ${jdMode === 'text' ? 'active' : ''}`}
              onClick={() => setJdMode('text')}
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="17" y1="10" x2="3" y2="10" /><line x1="21" y1="6" x2="3" y2="6" /><line x1="21" y1="14" x2="3" y2="14" /><line x1="17" y1="18" x2="3" y2="18" />
              </svg>
              Paste Text
            </button>
            <button
              id="tab-pdf"
              role="tab"
              aria-selected={jdMode === 'file'}
              className={`jdm-tab ${jdMode === 'file' ? 'active' : ''}`}
              onClick={() => setJdMode('file')}
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" />
              </svg>
              Upload PDF
            </button>
          </div>

          {/* Panel: Paste text */}
          {jdMode === 'text' && (
            <div className="jdm-panel" role="tabpanel" aria-labelledby="tab-paste">
              <textarea
                id="jd_text"
                name="jd_text"
                className="jdm-textarea"
                placeholder="Paste the full Job Description here…"
                value={jdText}
                onChange={e => setJdText(e.target.value)}
                rows={10}
              />
              <div className="jdm-char-count">{jdText.length} chars</div>
            </div>
          )}

          {/* Panel: Upload JD PDF */}
          {jdMode === 'file' && (
            <div className="jdm-panel" role="tabpanel" aria-labelledby="tab-pdf">
              {jdFile ? (
                <div className="jdm-file-chip">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" />
                  </svg>
                  <span>{jdFile.name}</span>
                  <button className="jdm-chip-remove" onClick={() => setJdFile(null)} aria-label="Remove JD file">×</button>
                </div>
              ) : (
                <button className="jdm-upload-jd-btn" onClick={() => jdFileRef.current?.click()}>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" />
                  </svg>
                  Click to upload JD PDF
                </button>
              )}
              <input ref={jdFileRef} type="file" name="jd_file" accept=".pdf" onChange={handleJdFileSelect} style={{ display: 'none' }} />
            </div>
          )}
        </section>

        {/* ---- Section 2: Resume Upload ---- */}
        <section className="jdm-section glass-card">
          <div className="jdm-section-label">
            <span className="jdm-step">2</span>
            <h3 className="jdm-section-title">Upload Resumes</h3>
          </div>

          <div
            id="resume-dropzone"
            className={`jdm-dropzone ${isDragging ? 'dragging' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => resumeInputRef.current?.click()}
          >
            <div className="jdm-dz-icon">
              <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" />
              </svg>
            </div>
            <p className="jdm-dz-main"><span className="jdm-dz-highlight">Click to upload</span> or drag & drop</p>
            <p className="jdm-dz-sub">Multiple PDF resumes supported</p>
          </div>
          <input
            ref={resumeInputRef}
            type="file"
            name="resume_files"
            accept=".pdf"
            multiple
            onChange={e => addResumes(e.target.files)}
            style={{ display: 'none' }}
          />

          {/* File list */}
          {resumeFiles.length > 0 && (
            <div className="jdm-file-list">
              <div className="jdm-file-list-header">
                <span>{resumeFiles.length} resume{resumeFiles.length > 1 ? 's' : ''} selected</span>
                <button className="jdm-clear-all" onClick={() => setResumeFiles([])}>Clear all</button>
              </div>
              {resumeFiles.map(f => (
                <div key={f.name} className="jdm-file-row">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" />
                  </svg>
                  <span className="jdm-file-name">{f.name}</span>
                  <span className="jdm-file-size">{(f.size / 1024).toFixed(0)} KB</span>
                  <button className="jdm-remove-file" onClick={() => removeResume(f.name)} aria-label={`Remove ${f.name}`}>×</button>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      
    </div>
  );
}

export default JDMatcherPage;
