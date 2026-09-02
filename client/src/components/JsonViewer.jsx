import React, { useState } from 'react';
import { Copy, Check, Download, Code2 } from 'lucide-react';

export default function JsonViewer({ data }) {
  const [copied, setCopied] = useState(false);

  if (!data) return null;

  // Clean payload for clean presentation (omit heavy base64 image dict if present)
  const displayData = { ...data };
  if (displayData.images) {
    delete displayData.images;
  }

  const jsonString = JSON.stringify(displayData, null, 2);

  const handleCopy = () => {
    navigator.clipboard.writeText(jsonString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `extraction_${data.document_type || 'document'}_${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="bg-white border border-slate-200/80 rounded-2xl overflow-hidden shadow-sm">
      {/* Header with actions */}
      <div className="p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
        <div className="flex items-center space-x-2 text-slate-800">
          <Code2 className="w-4 h-4 text-sky-600" />
          <span className="text-xs font-bold">Structured JSON Output</span>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={handleCopy}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 text-xs font-medium transition shadow-sm"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? 'Copied!' : 'Copy JSON'}</span>
          </button>
          <button
            onClick={handleDownload}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-700 text-white text-xs font-semibold transition shadow-sm"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download .json</span>
          </button>
        </div>
      </div>

      {/* Formatted Code Box in Clean Light Theme */}
      <div className="bg-slate-50/80 p-5 overflow-auto max-h-[500px]">
        <pre className="text-xs text-slate-800 font-mono leading-relaxed whitespace-pre-wrap selection:bg-sky-200 selection:text-slate-900">
          <code>{jsonString}</code>
        </pre>
      </div>
    </div>
  );
}
