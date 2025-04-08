import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { FaMusic, FaTrash, FaUpload } from 'react-icons/fa';

function AudioUploader({ onFileSelected, file, disabled }) {
  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles && acceptedFiles.length > 0) {
      onFileSelected(acceptedFiles[0]);
    }
  }, [onFileSelected]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'audio/*': ['.mp3', '.wav', '.ogg', '.flac']
    },
    maxFiles: 1,
    disabled
  });

  const removeFile = () => {
    onFileSelected(null);
  };

  return (
    <div className="w-full">
      {!file ? (
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-lg p-6 flex flex-col items-center justify-center cursor-pointer transition-colors ${
            isDragActive
              ? 'border-blue-500 bg-blue-50'
              : 'border-gray-300 hover:border-blue-400'
          } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          <input {...getInputProps()} />
          <FaUpload className="text-3xl text-gray-400 mb-2" />
          <p className="text-sm text-center text-gray-500">
            {isDragActive
              ? 'Drop the audio file here'
              : 'Drag & drop an audio file, or click to select'}
          </p>
          <p className="text-xs text-gray-400 mt-1">
            Supports MP3, WAV, OGG, and FLAC
          </p>
        </div>
      ) : (
        <div className="border rounded-lg p-4 bg-gray-50">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="bg-blue-100 p-2 rounded-full">
                <FaMusic className="text-blue-600" />
              </div>
              <div className="overflow-hidden">
                <p className="font-medium text-sm truncate" title={file.name}>
                  {file.name}
                </p>
                <p className="text-xs text-gray-500">
                  {(file.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
            </div>
            {!disabled && (
              <button
                onClick={removeFile}
                className="text-red-500 hover:text-red-700 focus:outline-none"
                type="button"
              >
                <FaTrash />
              </button>
            )}
          </div>
          
          {file.type.startsWith('audio/') && (
            <div className="mt-3">
              <audio controls className="w-full h-8">
                <source src={URL.createObjectURL(file)} type={file.type} />
                Your browser does not support the audio element.
              </audio>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default AudioUploader;