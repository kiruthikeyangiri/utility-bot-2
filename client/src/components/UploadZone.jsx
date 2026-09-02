import React, { useRef, useState } from 'react';
import { UploadCloud, Image as ImageIcon, X, FileCheck } from 'lucide-react';

export default function UploadZone({ onFileSelected, selectedFile, onClear, isLoading }) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [previewUrl, setPreviewUrl] = useState(null);
  const fileInputRef = useRef(null);

  const handleFile = (file) => {
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      alert('Please upload a valid image file (JPG, JPEG, PNG).');
      return;
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    onFileSelected(file);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleClear = (e) => {
    e.stopPropagation();
    setPreviewUrl(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
    onClear();
  };

  return (
    <div className="bg-white border border-slate-200/80 rounded-2xl p-6 shadow-sm relative overflow-hidden">
      
      {/* Hidden file input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
        accept="image/png,image/jpeg,image/jpg"
        className="hidden"
      />

      {!selectedFile ? (
        <div
          onClick={() => fileInputRef.current?.click()}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          className={`border-2 border-dashed rounded-xl p-8 sm:p-12 text-center cursor-pointer transition-all duration-200 flex flex-col items-center justify-center ${
            isDragOver
              ? 'border-sky-500 bg-sky-50/50 scale-[1.01]'
              : 'border-slate-300 hover:border-slate-400 bg-slate-50/50 hover:bg-slate-50'
          }`}
        >
          <div className="w-16 h-16 rounded-2xl bg-sky-50 border border-sky-100 flex items-center justify-center text-sky-600 mb-4 shadow-sm">
            <UploadCloud className="w-8 h-8" />
          </div>
          <h3 className="text-base font-semibold text-slate-800 mb-1">
            Drop your ID Document image here, or <span className="text-sky-600 underline">browse</span>
          </h3>
          <p className="text-xs text-slate-500 mb-4 max-w-sm">
            Supports Indian <strong>Aadhaar Card</strong>, <strong>PAN Card</strong>, and <strong>Driving Licence</strong> (JPG, JPEG, PNG).
          </p>
          <div className="flex items-center space-x-2 text-[11px] text-slate-500 bg-slate-100 px-3 py-1.5 rounded-full border border-slate-200">
            <span>🔒 Images are processed in-memory and never stored on disk.</span>
          </div>
        </div>
      ) : (
        <div className="flex flex-col sm:flex-row items-center justify-between p-4 bg-slate-50 border border-slate-200 rounded-xl gap-4">
          <div className="flex items-center space-x-4 w-full sm:w-auto">
            {previewUrl && (
              <img
                src={previewUrl}
                alt="Upload preview"
                className="w-16 h-16 object-cover rounded-lg border border-slate-200 shadow-sm flex-shrink-0"
              />
            )}
            <div className="overflow-hidden">
              <div className="flex items-center space-x-2">
                <FileCheck className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                <p className="text-sm font-semibold text-slate-800 truncate max-w-xs">{selectedFile.name}</p>
              </div>
              <p className="text-xs text-slate-500">{(selectedFile.size / 1024).toFixed(1)} KB • Ready for extraction</p>
            </div>
          </div>

          <div className="flex items-center space-x-2 w-full sm:w-auto justify-end">
            <button
              onClick={handleClear}
              disabled={isLoading}
              className="p-2 rounded-lg bg-white hover:bg-slate-100 text-slate-500 hover:text-slate-700 border border-slate-200 transition disabled:opacity-50"
              title="Remove image"
            >
              <X className="w-4 h-4" />
            </button>
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isLoading}
              className="px-4 py-2 rounded-lg bg-white hover:bg-slate-100 text-slate-700 hover:text-slate-900 border border-slate-200 text-xs font-medium transition shadow-sm disabled:opacity-50"
            >
              Change File
            </button>
          </div>
        </div>
      )}

      {/* Supported Documents Badges */}
      <div className="mt-4 pt-4 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
        <span className="font-medium text-slate-600">Supported Formats:</span>
        <div className="flex flex-wrap gap-2">
          <span className="px-2.5 py-1 rounded-md bg-blue-50 text-blue-700 border border-blue-200 font-medium text-[11px]">
            🆔 Aadhaar Card
          </span>
          <span className="px-2.5 py-1 rounded-md bg-amber-50 text-amber-800 border border-amber-200 font-medium text-[11px]">
            💳 PAN Card
          </span>
          <span className="px-2.5 py-1 rounded-md bg-emerald-50 text-emerald-700 border border-emerald-200 font-medium text-[11px]">
            🚗 Driving Licence
          </span>
        </div>
      </div>

    </div>
  );
}
