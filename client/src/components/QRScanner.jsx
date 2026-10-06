import React, { useState, useRef } from 'react';
import { 
  Scan, 
  UploadCloud, 
  Barcode, 
  QrCode, 
  Copy, 
  Check, 
  ExternalLink, 
  AlertCircle, 
  RefreshCw, 
  FileText,
  Layers,
  Sparkles,
  Info,
  CheckCircle2
} from 'lucide-react';
import { scanCodeApi, scanDocumentCodesApi } from '../services/api';
import { lookupCodeInfo } from './CodeResults';

export default function QRScanner() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [scanMode, setScanMode] = useState('codes_only'); // 'codes_only' | 'combined_ocr'
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [results, setResults] = useState(null);
  const [copiedKey, setCopiedKey] = useState(null);

  const fileInputRef = useRef(null);

  const isUrl = (val) => {
    try {
      return val && (val.startsWith('http://') || val.startsWith('https://'));
    } catch {
      return false;
    }
  };

  const handleFileChange = (file) => {
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      setError('Please upload a valid image file (JPG, JPEG, PNG).');
      return;
    }
    setSelectedFile(file);
    setError(null);
    setResults(null);

    const reader = new FileReader();
    reader.onload = () => {
      setPreviewUrl(reader.result);
    };
    reader.readAsDataURL(file);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileChange(e.dataTransfer.files[0]);
    }
  };

  const handleScan = async () => {
    if (!selectedFile) {
      setError('Please upload an image before scanning.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      let res;
      if (scanMode === 'combined_ocr') {
        res = await scanDocumentCodesApi(selectedFile);
      } else {
        res = await scanCodeApi(selectedFile);
      }
      setResults(res);
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Failed to scan codes from image.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = (key, text) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const handleClear = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setResults(null);
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const qrCodes = results?.qr_codes || [];
  const barcodes = results?.barcodes || [];
  const ocrData = results?.ocr || null;
  const totalCodes = qrCodes.length + barcodes.length;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
      
      {/* LEFT COLUMN: UPLOAD & CONTROLS */}
      <div className="lg:col-span-5 bg-white border border-slate-200/90 rounded-2xl p-6 shadow-sm space-y-5">
        <div>
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-100">
              <Scan className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">QR &amp; Barcode Scanner</h3>
              <p className="text-xs text-slate-500">
                Multi-pass optical reader supporting QR, Code 128, EAN, UPC, Data Matrix, Aztec &amp; PDF417.
              </p>
            </div>
          </div>
        </div>

        {/* Scan Mode Toggle */}
        <div className="bg-slate-50 p-1.5 rounded-xl border border-slate-200 flex items-center space-x-1 text-xs font-semibold">
          <button
            type="button"
            onClick={() => setScanMode('codes_only')}
            className={`flex-1 py-1.5 px-2 rounded-lg transition flex items-center justify-center space-x-1.5 ${
              scanMode === 'codes_only'
                ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            <Barcode className="w-3.5 h-3.5 text-sky-600" />
            <span>Codes Only</span>
          </button>

          <button
            type="button"
            onClick={() => setScanMode('combined_ocr')}
            className={`flex-1 py-1.5 px-2 rounded-lg transition flex items-center justify-center space-x-1.5 ${
              scanMode === 'combined_ocr'
                ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            <FileText className="w-3.5 h-3.5 text-indigo-600" />
            <span>Combined OCR + Codes</span>
          </button>
        </div>

        {error && (
          <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl flex items-start space-x-2 text-xs text-rose-800">
            <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
            <div className="leading-relaxed">{error}</div>
          </div>
        )}

        {/* DRAG & DROP ZONE */}
        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition flex flex-col items-center justify-center space-y-3 ${
            selectedFile
              ? 'border-indigo-400 bg-indigo-50/20'
              : 'border-slate-300 hover:border-slate-400 bg-slate-50/50 hover:bg-slate-50'
          }`}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={(e) => handleFileChange(e.target.files?.[0])}
            accept="image/png,image/jpeg,image/jpg"
            className="hidden"
          />

          {previewUrl ? (
            <div className="space-y-2 w-full">
              <img
                src={previewUrl}
                alt="Selected preview"
                className="max-h-48 mx-auto object-contain rounded-lg border border-slate-200 shadow-sm"
              />
              <p className="text-xs font-mono text-slate-600 font-semibold truncate max-w-[220px] mx-auto">
                {selectedFile?.name}
              </p>
              <span className="text-[11px] text-indigo-600 font-semibold block">Click to change image</span>
            </div>
          ) : (
            <>
              <div className="p-3 rounded-full bg-indigo-50 text-indigo-600 border border-indigo-100">
                <UploadCloud className="w-6 h-6" />
              </div>
              <div>
                <p className="text-xs font-bold text-slate-800">Drag &amp; Drop Image Here</p>
                <p className="text-[11px] text-slate-400 mt-0.5">Supports JPG, JPEG, PNG (Single image)</p>
              </div>
            </>
          )}
        </div>

        {/* SCAN BUTTON */}
        <div className="flex items-center space-x-2">
          <button
            type="button"
            disabled={!selectedFile || loading}
            onClick={handleScan}
            className="flex-1 flex items-center justify-center space-x-2 py-3 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 active:scale-[0.99] text-white font-bold text-xs shadow-lg shadow-indigo-600/25 transition disabled:opacity-50"
          >
            {loading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Running Multi-Pass Optical Scanner...</span>
              </>
            ) : (
              <>
                <Scan className="w-4 h-4" />
                <span>Scan Image Now</span>
              </>
            )}
          </button>

          {selectedFile && (
            <button
              type="button"
              onClick={handleClear}
              className="py-3 px-3.5 rounded-xl border border-slate-200 hover:bg-slate-100 text-slate-600 text-xs font-semibold transition"
              title="Clear Image"
            >
              Reset
            </button>
          )}
        </div>

      </div>

      {/* RIGHT COLUMN: DETECTION RESULTS */}
      <div className="lg:col-span-7 space-y-4">
        
        {/* If no scan executed yet */}
        {!results && !loading && (
          <div className="p-12 text-center bg-white border border-slate-200/90 rounded-2xl space-y-3">
            <div className="w-12 h-12 rounded-2xl bg-slate-100 text-slate-400 flex items-center justify-center mx-auto">
              <Scan className="w-6 h-6" />
            </div>
            <h4 className="text-sm font-bold text-slate-700">Ready to Scan</h4>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              Upload any shipping label, invoice, product barcode, or QR code image to decode all optical symbologies.
            </p>
          </div>
        )}

        {/* SCAN RESULTS */}
        {results && (
          <div className="space-y-4">
            
            {/* Top Summary Banner */}
            <div className="bg-white border border-slate-200/90 rounded-2xl p-4 flex flex-wrap items-center justify-between gap-3 text-xs shadow-sm">
              <div className="flex items-center space-x-3">
                <span className="font-bold text-slate-800">Detected Optical Codes:</span>
                <span className="px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-800 text-[11px] font-bold">
                  {totalCodes} Total ({barcodes.length} 1D, {qrCodes.length} 2D)
                </span>
              </div>

              <span className="text-slate-400 text-[11px] font-mono">
                {results.filename}
              </span>
            </div>

            {totalCodes === 0 && (
              <div className="p-8 text-center bg-white border border-slate-200/90 rounded-2xl space-y-2">
                <AlertCircle className="w-8 h-8 text-slate-400 mx-auto" />
                <h4 className="text-sm font-semibold text-slate-700">No Optical Codes Detected</h4>
                <p className="text-xs text-slate-500 max-w-md mx-auto">
                  No QR codes or 1D barcodes could be recognized. Try uploading a clearer, higher-contrast image.
                </p>
              </div>
            )}

            {/* 1. QR CODES */}
            {qrCodes.length > 0 && (
              <div className="space-y-2.5">
                <div className="flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-slate-800">
                  <QrCode className="w-4 h-4 text-indigo-600" />
                  <span>QR Codes ({qrCodes.length})</span>
                </div>

                <div className="grid grid-cols-1 gap-2.5">
                  {qrCodes.map((item, idx) => {
                    const itemKey = `qr-scan-${idx}-${item.value}`;
                    const isCopied = copiedKey === itemKey;
                    const hasUrl = isUrl(item.value);
                    const info = lookupCodeInfo(item.format);

                    return (
                      <div
                        key={itemKey}
                        className="bg-white border border-slate-200/90 rounded-xl p-4 shadow-sm hover:border-slate-300 transition flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                      >
                        <div className="flex items-start space-x-3 min-w-0 flex-1">
                          <div className="p-2.5 rounded-xl bg-indigo-50 text-indigo-700 border border-indigo-100 flex-shrink-0 mt-0.5">
                            <QrCode className="w-5 h-5" />
                          </div>
                          <div className="min-w-0 flex-1 space-y-1.5">
                            <div className="flex items-center space-x-2 flex-wrap gap-y-1">
                              <span className="text-[10px] font-bold uppercase px-2.5 py-0.5 rounded-full bg-indigo-50 text-indigo-800 border border-indigo-200">
                                {item.format || 'QRCode'}
                              </span>
                              {item.content_type && (
                                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200">
                                  {item.content_type}
                                </span>
                              )}
                              {info && (
                                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
                                  {info.fullForm}
                                </span>
                              )}
                            </div>

                            <div className="text-xs font-mono font-medium text-slate-800 break-all select-all leading-relaxed">
                              {item.value}
                            </div>

                            {info && (
                              <div className="flex items-center space-x-1.5 text-[11px] text-slate-500">
                                <Info className="w-3 h-3 text-indigo-500 flex-shrink-0" />
                                <span className="truncate"><strong className="text-slate-700 font-medium">Used for:</strong> {info.useFor}</span>
                              </div>
                            )}
                          </div>
                        </div>

                        <div className="flex items-center space-x-2 flex-shrink-0 self-end sm:self-center">
                          {hasUrl && (
                            <a
                              href={item.value}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-700 transition text-xs font-semibold border border-indigo-200"
                              title="Open URL in new tab"
                            >
                              <ExternalLink className="w-3.5 h-3.5" />
                              <span>Open Link</span>
                            </a>
                          )}

                          <button
                            onClick={() => handleCopy(itemKey, item.value)}
                            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 transition text-xs font-medium"
                          >
                            {isCopied ? (
                              <>
                                <Check className="w-3.5 h-3.5 text-emerald-600" />
                                <span className="text-emerald-700">Copied</span>
                              </>
                            ) : (
                              <>
                                <Copy className="w-3.5 h-3.5 text-slate-500" />
                                <span>Copy</span>
                              </>
                            )}
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* 2. BARCODES */}
            {barcodes.length > 0 && (
              <div className="space-y-2.5">
                <div className="flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-slate-800">
                  <Barcode className="w-4 h-4 text-sky-600" />
                  <span>1D Linear Barcodes ({barcodes.length})</span>
                </div>

                <div className="grid grid-cols-1 gap-2.5">
                  {barcodes.map((item, idx) => {
                    const itemKey = `bar-scan-${idx}-${item.value}`;
                    const isCopied = copiedKey === itemKey;
                    const info = lookupCodeInfo(item.format);

                    return (
                      <div
                        key={itemKey}
                        className="bg-white border border-slate-200/90 rounded-xl p-4 shadow-sm hover:border-slate-300 transition flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                      >
                        <div className="flex items-start space-x-3 min-w-0 flex-1">
                          <div className="p-2.5 rounded-xl bg-sky-50 text-sky-700 border border-sky-100 flex-shrink-0 mt-0.5">
                            <Barcode className="w-5 h-5" />
                          </div>
                          <div className="min-w-0 flex-1 space-y-1.5">
                            <div className="flex items-center space-x-2 flex-wrap gap-y-1">
                              <span className="text-[10px] font-bold uppercase px-2.5 py-0.5 rounded-full bg-sky-50 text-sky-800 border border-sky-200">
                                {item.format || 'Barcode'}
                              </span>
                              {info && (
                                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
                                  {info.fullForm}
                                </span>
                              )}
                            </div>

                            <div className="text-sm font-mono font-bold text-slate-900 break-all select-all tracking-wide">
                              {item.value}
                            </div>

                            {info && (
                              <div className="flex items-center space-x-1.5 text-[11px] text-slate-500">
                                <Info className="w-3 h-3 text-sky-500 flex-shrink-0" />
                                <span className="truncate"><strong className="text-slate-700 font-medium">Used for:</strong> {info.useFor}</span>
                              </div>
                            )}
                          </div>
                        </div>

                        <div className="flex items-center space-x-2 flex-shrink-0 self-end sm:self-center">
                          <button
                            onClick={() => handleCopy(itemKey, item.value)}
                            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 transition text-xs font-medium"
                          >
                            {isCopied ? (
                              <>
                                <Check className="w-3.5 h-3.5 text-emerald-600" />
                                <span className="text-emerald-700">Copied</span>
                              </>
                            ) : (
                              <>
                                <Copy className="w-3.5 h-3.5 text-slate-500" />
                                <span>Copy</span>
                              </>
                            )}
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* 3. COMBINED OCR OUTPUT (If scanMode was 'combined_ocr') */}
            {ocrData && (
              <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-sm space-y-3">
                <div className="flex items-center justify-between pb-2 border-b border-slate-100 text-slate-800">
                  <div className="flex items-center space-x-2">
                    <div className="p-1.5 rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-100">
                      <FileText className="w-4 h-4" />
                    </div>
                    <h4 className="text-xs font-bold uppercase tracking-wider">Printed Document OCR Text</h4>
                  </div>
                  {ocrData.confidence > 0 && (
                    <span className="px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-800 text-[11px] font-bold border border-emerald-200">
                      {ocrData.confidence}% OCR Confidence
                    </span>
                  )}
                </div>

                <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 font-mono text-xs text-slate-800 whitespace-pre-wrap leading-relaxed max-h-56 overflow-y-auto">
                  {ocrData.raw_text || <span className="text-slate-400 italic">No printed text detected.</span>}
                </div>

                {ocrData.raw_text && (
                  <div className="flex justify-end">
                    <button
                      onClick={() => handleCopy('ocr-text-copy', ocrData.raw_text)}
                      className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-medium"
                    >
                      {copiedKey === 'ocr-text-copy' ? (
                        <>
                          <Check className="w-3.5 h-3.5 text-emerald-600" />
                          <span className="text-emerald-700">Copied Text</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3.5 h-3.5 text-slate-500" />
                          <span>Copy OCR Text</span>
                        </>
                      )}
                    </button>
                  </div>
                )}
              </div>
            )}

          </div>
        )}

      </div>

    </div>
  );
}
