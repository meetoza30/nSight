import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './UploadPage.css';

function UploadPage({ onFileUpload, uploadedFile }) {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFile = (file) => {
    if (file && file.type === 'application/pdf') {
      onFileUpload(file);
      navigate('/processing');
    } else if (file) {
      alert('Please select a PDF file');
    }
  };

  const handleFileSelect = (event) => {
    handleFile(event.target.files[0]);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleButtonClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="upload-page glass-card">
      <h2 className="upload-title">Generate your resume in nCircle Format</h2>
      <p className="upload-subtitle">Upload your existing resume to extract and format it automatically.</p>
      
      <div 
        className={`drag-drop-zone ${isDragging ? 'dragging' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleButtonClick}
      >
        <p className="zone-text-main">
          <span className="upload-highlight">Click to upload</span> or drag and drop
        </p>
        <p className="zone-text-sub">PDF files only (max 5MB)</p>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf"
        onChange={handleFileSelect}
        style={{ display: 'none' }}
      />
      <div className='upload-footer'>
      {/* <button 
        className="primary-btn upload-btn"
        onClick={handleButtonClick}
      >
        Upload Resume
      </button> */}
      <button className="outline-btn" onClick={() => navigate('/')}>Back</button>
      </div>
    </div>
  );
}

export default UploadPage;
