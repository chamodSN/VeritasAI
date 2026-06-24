// src/components/shared/ExportMenu.jsx
import React, { useState, useRef, useEffect } from 'react';
import { Download, Copy, Check, FileDown } from 'lucide-react';
import { saveAs } from 'file-saver';
import copy from 'copy-to-clipboard';

export default function ExportMenu({ contentRef, result }) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const menuRef = useRef(null);

  // Close on outside click
  useEffect(() => {
    const handler = (e) => { if (menuRef.current && !menuRef.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const handleCopy = () => {
    if (!result) return;
    const text = [
      `Query: ${result.query}`,
      `\nSUMMARY\n${result.summary}`,
      `\nISSUES\n${result.issues?.join('\n')}`,
      `\nARGUMENTS\n${result.arguments}`,
      `\nCASES ANALYSED: ${result.cases_analyzed}`,
    ].join('\n');
    copy(text);
    setCopied(true);
    setTimeout(() => { setCopied(false); setOpen(false); }, 1500);
  };

  const handleDownload = () => {
    if (!contentRef?.current) return;
    const html = `<!DOCTYPE html><html><head><meta charset="utf-8">
      <style>body{font-family:Georgia,serif;max-width:800px;margin:40px auto;padding:0 20px;color:#1C1917}</style>
      </head><body>${contentRef.current.innerHTML}</body></html>`;
    saveAs(new Blob([html], { type: 'application/msword' }), `veritasai-${Date.now()}.doc`);
    setOpen(false);
  };

  return (
    <div className="relative" ref={menuRef}>
      <button onClick={() => setOpen(v => !v)} className="btn-secondary text-xs">
        <Download size={12} />
        Export
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1.5 w-44 bg-white border border-stone rounded-card shadow-elevated z-20">
          <button
            onClick={handleCopy}
            className="w-full flex items-center gap-2.5 px-3 py-2.5 text-sm text-ink hover:bg-stone transition-colors rounded-t-card"
          >
            {copied ? <Check size={13} className="text-sage" /> : <Copy size={13} className="text-mist" />}
            {copied ? 'Copied!' : 'Copy as text'}
          </button>
          <div className="h-px bg-stone" />
          <button
            onClick={handleDownload}
            className="w-full flex items-center gap-2.5 px-3 py-2.5 text-sm text-ink hover:bg-stone transition-colors rounded-b-card"
          >
            <FileDown size={13} className="text-mist" />
            Download as Word
          </button>
        </div>
      )}
    </div>
  );
}