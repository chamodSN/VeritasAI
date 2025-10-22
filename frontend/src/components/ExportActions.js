import React, { useState } from 'react';
import { saveAs } from 'file-saver';
import copy from 'copy-to-clipboard';

const ExportActions = ({ targetRef, plainText }) => {
  const [copySuccess, setCopySuccess] = useState(false);
  const [downloadSuccess, setDownloadSuccess] = useState(false);

  const handleCopy = () => {
    if (plainText) {
      copy(plainText);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    }
  };

  const handleDownloadDoc = () => {
    if (!targetRef?.current) return;
    const html = targetRef.current.innerHTML;
    const blob = new Blob([
      `<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>${html}</body></html>`
    ], { type: 'application/msword' });
    saveAs(blob, 'veritasai-result.doc');
    setDownloadSuccess(true);
    setTimeout(() => setDownloadSuccess(false), 2000);
  };

  return (
    <div className="flex gap-2">
      <button 
        onClick={handleCopy} 
        className={`btn-secondary transition-all duration-300 ${copySuccess ? 'bg-green-600 hover:bg-green-700' : ''}`}
      >
        <i className={`fas ${copySuccess ? 'fa-check' : 'fa-copy'} mr-2 transition-transform duration-300 ${copySuccess ? 'animate-bounce' : ''}`}/>
        {copySuccess ? 'Copied!' : 'Copy'}
      </button>
      <button 
        onClick={handleDownloadDoc} 
        className={`btn-secondary transition-all duration-300 ${downloadSuccess ? 'bg-green-600 hover:bg-green-700' : ''}`}
      >
        <i className={`fas ${downloadSuccess ? 'fa-check' : 'fa-file-word'} mr-2 transition-transform duration-300 ${downloadSuccess ? 'animate-bounce' : ''}`}/>
        {downloadSuccess ? 'Downloaded!' : 'Word'}
      </button>
    </div>
  );
};

export default ExportActions;


