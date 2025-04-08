import { useState } from 'react';
import AudioUploader from './components/AudioUploader';
import axios from 'axios';
import { FaSpinner, FaDownload, FaCheck, FaExclamationCircle } from 'react-icons/fa';

const API_URL = 'http://localhost:8000';

function App() {
  const [vocalFile, setVocalFile] = useState(null);
  const [beatFile, setBeatFile] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState('idle'); // idle, processing, completed, error
  const [downloadUrl, setDownloadUrl] = useState(null);
  const [error, setError] = useState('');

  const handleVocalUpload = (file) => {
    setVocalFile(file);
  };

  const handleBeatUpload = (file) => {
    setBeatFile(file);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!vocalFile || !beatFile) {
      setError('Please upload both vocal and beat files');
      return;
    }

    setProcessing(true);
    setStatus('processing');
    setError('');

    try {
      const formData = new FormData();
      formData.append('vocal_file', vocalFile);
      formData.append('beat_file', beatFile);

      const response = await axios.post(`${API_URL}/process`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setJobId(response.data.job_id);
      
      // Poll for status
      pollStatus(response.data.job_id);
    } catch (error) {
      console.error('Error processing files:', error);
      setError('Error processing files. Please try again.');
      setStatus('error');
      setProcessing(false);
    }
  };

  const pollStatus = async (id) => {
    try {
      const response = await axios.get(`${API_URL}/status/${id}`);
      
      if (response.data.status === 'completed') {
        setStatus('completed');
        setProcessing(false);
        setDownloadUrl(`${API_URL}/download/${id}`);
      } else if (response.data.status === 'processing') {
        // Continue polling
        setTimeout(() => pollStatus(id), 2000);
      } else {
        setStatus('error');
        setProcessing(false);
        setError('Processing failed');
      }
    } catch (error) {
      console.error('Error checking status:', error);
      setStatus('error');
      setProcessing(false);
      setError('Error checking processing status');
    }
  };

  const getStatusDisplay = () => {
    switch (status) {
      case 'processing':
        return (
          <div className="flex items-center space-x-2 text-blue-600">
            <FaSpinner className="animate-spin" />
            <span>Processing your audio files...</span>
          </div>
        );
      case 'completed':
        return (
          <div className="flex flex-col items-center space-y-4">
            <div className="flex items-center space-x-2 text-green-600">
              <FaCheck />
              <span>Processing complete!</span>
            </div>
            <a 
              href={downloadUrl} 
              className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded flex items-center space-x-2"
              download
            >
              <FaDownload />
              <span>Download Processed Audio</span>
            </a>
          </div>
        );
      case 'error':
        return (
          <div className="flex items-center space-x-2 text-red-600">
            <FaExclamationCircle />
            <span>{error || 'An error occurred'}</span>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto">
        <div className="bg-white shadow rounded-lg p-6">
          <h1 className="text-2xl font-bold text-center mb-8">Demucs Audio Processor</h1>
          
          <form onSubmit={handleSubmit}>
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              <div>
                <h2 className="text-lg font-medium mb-2">Vocal Track</h2>
                <AudioUploader 
                  onFileSelected={handleVocalUpload} 
                  file={vocalFile}
                  disabled={processing}
                />
              </div>
              
              <div>
                <h2 className="text-lg font-medium mb-2">Beat Track</h2>
                <AudioUploader 
                  onFileSelected={handleBeatUpload}
                  file={beatFile}
                  disabled={processing}
                />
              </div>
            </div>
            
            <div className="mt-6 flex justify-center">
              <button
                type="submit"
                disabled={processing || !vocalFile || !beatFile}
                className={`px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 ${
                  (processing || !vocalFile || !beatFile) ? 'opacity-50 cursor-not-allowed' : ''
                }`}
              >
                {processing ? 'Processing...' : 'Process Audio Files'}
              </button>
            </div>
          </form>
          
          <div className="mt-8 flex justify-center">
            {getStatusDisplay()}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;