# simul

This project uses Demucs for audio separation and processing with a React (Vite) frontend and FastAPI backend.

## Project Structure

```
project/
├── frontend/                # Vite frontend
│   ├── src/
│   │   ├── components/
│   │   │   └── AudioUploader.jsx
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── public/
│   ├── package.json
│   └── vite.config.js
├── backend/                 # FastAPI backend
│   ├── app.py               # Main FastAPI app
│   ├── demucs_processor.py  # Demucs processing logic
│   └── requirements.txt
└── README.md
```

## Prerequisites

- Node.js 16+ and npm
- Python 3.8+
- ffmpeg installed on your system

## Setup Instructions

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Start the FastAPI server:
   ```bash
   uvicorn app:app --reload
   ```

The backend will be available at http://localhost:8000.

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

The frontend will be available at http://localhost:5173.

## Usage

1. Open the frontend in your browser (http://localhost:5173)
2. Upload two audio files:
   - Vocal track in the left upload area
   - Beat track in the right upload area
3. Click "Process Audio Files"
4. Wait for processing to complete
5. Download the processed file

## Notes

- Demucs processing might take some time depending on the file size and your hardware
- The backend creates temporary directories for processing and stores results in an "processed" directory
- Make sure you have enough disk space for the audio files and processing

## Troubleshooting

- If you encounter FFmpeg errors, make sure FFmpeg is properly installed and accessible in your PATH
- For large files, you may need to adjust the FastAPI upload limits
- Check the console logs for detailed error messages