# Ncircle Resume Converter

A React-based web application that converts resumes to Ncircle format.

## Features

- Clean, professional UI with custom design system
- Three-page workflow: Upload → Processing → Download
- PDF file upload with validation
- Real-time processing status
- Automatic file download
- Responsive design for all devices

## Design Philosophy

This application features a distinctive, human-designed aesthetic with:
- Custom color palette inspired by nature (forest green, sage, mint)
- Sophisticated typography using Fraunces (display) and Archivo (body)
- Smooth animations and micro-interactions
- Clean, uncluttered layouts
- Professional yet approachable feel

## Setup Instructions

### Prerequisites

- Node.js 18+ installed
- FastAPI backend running on `http://localhost:8000`

### Installation

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm run dev
```

The application will open at `http://localhost:3000`

### Production Build

```bash
npm run build
npm run preview
```

## Backend Integration

The app connects to your FastAPI server at `http://localhost:8000/upload-resume`.

Make sure your backend is running and has CORS enabled:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Project Structure

```
ncircle-resume/
├── src/
│   ├── pages/
│   │   ├── UploadPage.jsx
│   │   ├── UploadPage.css
│   │   ├── ProcessingPage.jsx
│   │   ├── ProcessingPage.css
│   │   ├── DownloadPage.jsx
│   │   └── DownloadPage.css
│   ├── App.jsx
│   ├── App.css
│   ├── main.jsx
│   └── index.css
├── index.html
├── package.json
└── vite.config.js
```

## Technology Stack

- React 18
- React Router 6
- Vite
- CSS3 with custom properties
- Google Fonts (Fraunces, Archivo)

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)
