import React, { useState } from 'react';
import axios from 'axios';

const PDFUpload = ({ apiClient, isAuthenticated, onAnalysisComplete }) => {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      if (selectedFile.type !== 'application/pdf') {
        setError('Please select a PDF file');
        return;
      }
      if (selectedFile.size > 10 * 1024 * 1024) { // 10MB limit
        setError('File size must be less than 10MB');
        return;
      }
      setFile(selectedFile);
      setError(null);
      setSuccess(null);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a PDF file');
      return;
    }

    setUploading(true);
    setError(null);
    setSuccess(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await apiClient.post('/api/pdf/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setSuccess('PDF uploaded and analyzed successfully!');
      if (onAnalysisComplete) {
        onAnalysisComplete(response.data);
      }
      
      // Reset form
      setFile(null);
      document.getElementById('pdf-file').value = '';
    } catch (err) {
      if (err.response?.status === 401) {
        setError('Please log in to upload PDFs');
      } else {
        setError(err.response?.data?.detail || err.message || 'Upload failed');
      }
      console.error('PDF upload error:', err);
    } finally {
      setUploading(false);
    }
  };

  const handleClear = () => {
    setFile(null);
    setError(null);
    setSuccess(null);
    document.getElementById('pdf-file').value = '';
  };

  return (
    <div className="card mb-8">
      <h2 className="text-2xl font-bold text-gray-900 mb-4">
        <i className="fas fa-file-pdf mr-2 text-red-600"></i>
        PDF Document Analysis
      </h2>

      {!isAuthenticated ? (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
          <div className="flex items-center">
            <i className="fas fa-exclamation-triangle text-yellow-400 mr-3"></i>
            <div>
              <h3 className="text-sm font-medium text-yellow-800">Authentication Required</h3>
              <p className="text-sm text-yellow-700 mt-1">
                Please log in with Google to upload and analyze PDF documents.
              </p>
            </div>
          </div>
        </div>
      ) : null}

      <div className="space-y-4">
        <div>
          <label htmlFor="pdf-file" className="block text-sm font-medium text-gray-700 mb-2">
            Select PDF Document:
          </label>
          <div className="flex items-center space-x-4">
            <input
              id="pdf-file"
              type="file"
              accept=".pdf"
              onChange={handleFileChange}
              disabled={uploading || !isAuthenticated}
              className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
            />
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Maximum file size: 10MB. Supported format: PDF only.
          </p>
        </div>

        {file && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <i className="fas fa-file-pdf text-red-600 mr-2"></i>
                <div>
                  <p className="text-sm font-medium text-blue-800">{file.name}</p>
                  <p className="text-xs text-blue-600">
                    {(file.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
              </div>
              <button
                onClick={handleClear}
                className="text-red-600 hover:text-red-800"
                disabled={uploading}
              >
                <i className="fas fa-times"></i>
              </button>
            </div>
          </div>
        )}

        <div className="flex flex-wrap gap-2">
          <button
            onClick={handleUpload}
            disabled={!file || uploading || !isAuthenticated}
            className="btn-primary"
          >
            {uploading ? (
              <>
                <i className="fas fa-spinner fa-spin mr-2"></i>
                Analyzing PDF...
              </>
            ) : (
              <>
                <i className="fas fa-upload mr-2"></i>
                Upload & Analyze PDF
              </>
            )}
          </button>

          <button
            onClick={handleClear}
            disabled={uploading || !file}
            className="btn-secondary"
          >
            <i className="fas fa-times mr-2"></i>
            Clear
          </button>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex">
              <i className="fas fa-exclamation-triangle text-red-400 mt-1 mr-3"></i>
              <div>
                <h3 className="text-sm font-medium text-red-800">Upload Error</h3>
                <p className="text-sm text-red-700 mt-1">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Success Display */}
        {success && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <div className="flex">
              <i className="fas fa-check-circle text-green-400 mt-1 mr-3"></i>
              <div>
                <h3 className="text-sm font-medium text-green-800">Success</h3>
                <p className="text-sm text-green-700 mt-1">{success}</p>
              </div>
            </div>
          </div>
        )}

        {/* Instructions */}
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-800 mb-2">
            <i className="fas fa-info-circle mr-2"></i>
            PDF Analysis Features
          </h3>
          <ul className="text-sm text-gray-600 space-y-1">
            <li>• Extract text content from legal PDF documents</li>
            <li>• Identify key legal issues and arguments</li>
            <li>• Extract and verify legal citations</li>
            <li>• Generate comprehensive case summaries</li>
            <li>• Analyze legal patterns and precedents</li>
            <li>• Provide confidence scores for analysis quality</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default PDFUpload;