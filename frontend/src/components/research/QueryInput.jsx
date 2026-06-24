
import React, { useState, useRef, useCallback } from 'react';
import { Search, Upload, X, FileText } from 'lucide-react';

export default function QueryInput({ onSubmit, onPDF, loading }) {
  const [mode, setMode] = useState('query');
  const [query, setQuery] = useState('');
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const fileRef = useRef(null);

  const handleSubmit = (e) => {
    e?.preventDefault();
    if (mode === 'query' && query.trim().length >= 3) onSubmit(query.trim());
    if (mode === 'pdf' && file) onPDF(file);
  };

  const handleKey = (e) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSubmit();
  };

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragging(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped?.type === 'application/pdf') setFile(dropped);
  }, []);

  const handleDragOver = (e) => { e.preventDefault(); setDragging(true); };
  const handleDragLeave = () => setDragging(false);

  return (
    <div className="card">
      {/* Mode tabs */}
      <div className="flex gap-1 mb-4 border-b border-stone -mx-5 -mt-5 px-5 pt-1">
        {[{ id: 'query', label: 'Query', icon: Search }, { id: 'pdf', label: 'Upload PDF', icon: Upload }].map(tab => (
          <button
            key={tab.id}
            onClick={() => setMode(tab.id)}
            className={`flex items-center gap-1.5 px-3 py-2.5 text-sm font-medium border-b-2 transition-colors duration-150 ${
              mode === tab.id
                ? 'border-sage text-sage'
                : 'border-transparent text-mist hover:text-ink'
            }`}
          >
            <tab.icon size={13} />
            {tab.label}
          </button>
        ))}
      </div>

      {mode === 'query' ? (
        <>
          <textarea
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Describe your legal research question — e.g. 'fourth amendment search and seizure automobile exception'"
            rows={3}
            disabled={loading}
            className="input-field mb-3"
          />
          <div className="flex items-center justify-between">
            <p className="text-xs text-mist">⌘ + Enter to submit</p>
            <button
              onClick={handleSubmit}
              disabled={loading || query.trim().length < 3}
              className="btn-primary"
            >
              <Search size={14} />
              {loading ? 'Analysing…' : 'Analyse'}
            </button>
          </div>
        </>
      ) : (
        <>
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onClick={() => !file && fileRef.current?.click()}
            className={`
              border-2 border-dashed rounded-card p-8 text-center cursor-pointer
              transition-colors duration-150
              ${dragging ? 'border-sage bg-sage-light' : 'border-stone hover:border-sage-dark hover:bg-stone'}
              ${file ? 'cursor-default' : ''}
            `}
          >
            {file ? (
              <div className="flex items-center justify-center gap-3">
                <FileText size={20} className="text-sage" />
                <span className="text-sm font-medium text-ink">{file.name}</span>
                <button
                  onClick={(e) => { e.stopPropagation(); setFile(null); }}
                  className="btn-ghost p-1"
                >
                  <X size={13} />
                </button>
              </div>
            ) : (
              <>
                <Upload size={20} className="text-mist mx-auto mb-2" />
                <p className="text-sm text-mist">Drop a PDF here or <span className="text-sage underline">browse</span></p>
                <p className="text-xs text-stone-dark mt-1">Max 10 MB</p>
              </>
            )}
          </div>
          <input ref={fileRef} type="file" accept="application/pdf" className="hidden" onChange={e => setFile(e.target.files[0])} />
          <div className="flex justify-end mt-3">
            <button onClick={handleSubmit} disabled={!file || loading} className="btn-primary">
              <Upload size={14} />
              {loading ? 'Analysing…' : 'Analyse PDF'}
            </button>
          </div>
        </>
      )}
    </div>
  );
}