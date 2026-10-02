import React, { useState, useRef } from 'react';
import { 
  Package, 
  Upload, 
  Image as ImageIcon, 
  X, 
  Plus, 
  Loader2, 
  AlertCircle, 
  CheckCircle2, 
  ArrowRight,
  Sliders,
  FileCheck,
  Cpu,
  Key,
  Eye,
  EyeOff
} from 'lucide-react';
import { extractShippingApi } from '../services/api';
import ShippingResultsView from './ShippingResultsView';

export default function ShippingScanner({ settings = {} }) {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [previews, setPreviews] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);
  
  // OCR, LLM & enhancement options
  const [apiKey, setApiKey] = useState(() => localStorage.getItem('groq_api_key') || settings.groq_api_key || '');
  const [showApiKey, setShowApiKey] = useState(false);
  const [minConfidence, setMinConfidence] = useState(20);
  const [enableClahe, setEnableClahe] = useState(true);
  const [enableDenoise, setEnableDenoise] = useState(true);
  const [selectedModel, setSelectedModel] = useState(settings.model_name || 'llama-3.3-70b-versatile');
  const [showOptions, setShowOptions] = useState(false);

  const fileInputRef = useRef(null);

  const handleFiles = (incomingFiles) => {
    setErrorMessage(null);
    const validExtensions = ['image/jpeg', 'image/jpg', 'image/png'];
    const filtered = [];

    for (let i = 0; i < incomingFiles.length; i++) {
      const file = incomingFiles[i];
      const ext = file.name.split('.').pop().toLowerCase();
      const isImage = validExtensions.includes(file.type) || ['jpg', 'jpeg', 'png'].includes(ext);

      if (!isImage) {
        setErrorMessage(`File "${file.name}" is not supported. Please upload JPG, JPEG, or PNG images only.`);
        return;
      }
      filtered.push(file);
    }

    const combined = [...selectedFiles, ...filtered];
    if (combined.length > 3) {
      setErrorMessage('Maximum 3 shipping label images allowed. Please select up to 3 images.');
      return;
    }

    setSelectedFiles(combined);

    // Generate previews
    const newPreviews = combined.map((file) => ({
      file,
      url: URL.createObjectURL(file),
      name: file.name,
      size: (file.size / 1024).toFixed(1) + ' KB'
    }));
    setPreviews(newPreviews);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    if (isLoading) return;
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(Array.from(e.target.files));
    }
    // Reset file input so re-selecting same file works
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const removeFile = (indexToRemove) => {
    const updated = selectedFiles.filter((_, idx) => idx !== indexToRemove);
    setSelectedFiles(updated);

    // Revoke old URL to prevent memory leaks
    if (previews[indexToRemove]?.url) {
      URL.revokeObjectURL(previews[indexToRemove].url);
    }

    const updatedPreviews = updated.map((file) => ({
      file,
      url: URL.createObjectURL(file),
      name: file.name,
      size: (file.size / 1024).toFixed(1) + ' KB'
    }));
    setPreviews(updatedPreviews);
    setErrorMessage(null);
  };

  const handleReset = () => {
    previews.forEach((p) => URL.revokeObjectURL(p.url));
    setSelectedFiles([]);
    setPreviews([]);
    setResults(null);
    setErrorMessage(null);
  };

  const handleScan = async () => {
    if (selectedFiles.length === 0) {
      setErrorMessage('Please upload at least 1 shipping label image.');
      return;
    }
    if (selectedFiles.length > 3) {
      setErrorMessage('Maximum 3 shipping label images allowed.');
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);
    setResults(null);

    try {
      const data = await extractShippingApi(selectedFiles, {
        min_confidence: minConfidence,
        enable_clahe: enableClahe,
        enable_denoise: enableDenoise,
        model_name: selectedModel,
        groq_api_key: apiKey.trim() || settings.groq_api_key,
      });
      setResults(data);
    } catch (err) {
      console.error('Shipping extraction failed:', err);
      const msg = err.response?.data?.detail || err.response?.data?.error || err.message || 'Failed to extract shipping labels.';
      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full space-y-6">
      
      {/* Page Title & Instructions Header */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 text-white shadow-md shadow-sky-500/20">
              <Package className="w-5 h-5" />
            </div>
            <h2 className="text-xl font-bold text-slate-900 tracking-tight">
              Shipping Label Scanner
            </h2>
          </div>
          <p className="text-xs text-slate-500 max-w-2xl">
            Upload 1, 2, or up to 3 shipping label images. RapidOCR reads the label text, which is sent to the LLM to understand and separate into FROM, TO, Order, Package, and Item lines alongside multi-pass Barcode & QR code scanning.
          </p>
        </div>

        <div className="flex items-center space-x-2 text-xs">
          <button
            onClick={() => setShowOptions(!showOptions)}
            className="flex items-center space-x-1.5 px-3 py-2 rounded-xl bg-slate-50 hover:bg-slate-100 text-slate-700 font-semibold border border-slate-200 transition"
          >
            <Sliders className="w-4 h-4 text-slate-500" />
            <span>Options</span>
          </button>
          {results && (
            <button
              onClick={handleReset}
              className="px-3.5 py-2 rounded-xl bg-white hover:bg-slate-50 text-slate-700 font-semibold border border-slate-200 transition shadow-sm"
            >
              Reset
            </button>
          )}
        </div>
      </div>

      {/* Advanced Scan Settings (Collapsible) */}
      {showOptions && (
        <div className="bg-white border border-slate-200/80 rounded-2xl p-5 shadow-sm space-y-4 animate-in fade-in">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wide">
              Scanner, LLM & Preprocessing Options
            </h4>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
            {/* Groq API Key */}
            <div className="space-y-1 md:col-span-2">
              <div className="flex justify-between items-center">
                <label className="text-slate-700 font-medium flex items-center space-x-1.5">
                  <Key className="w-3.5 h-3.5 text-amber-600" />
                  <span>Groq API Key:</span>
                </label>
                {apiKey.trim() ? (
                  <span className="text-[10px] font-semibold text-emerald-600">✓ Connected</span>
                ) : (
                  <span className="text-[10px] text-slate-400">Optional (for LLM reasoning)</span>
                )}
              </div>
              <div className="relative">
                <input
                  type={showApiKey ? 'text' : 'password'}
                  value={apiKey}
                  onChange={(e) => {
                    const val = e.target.value.trim();
                    setApiKey(val);
                    localStorage.setItem('groq_api_key', val);
                  }}
                  placeholder="gsk_..."
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-2.5 pr-8 py-1.5 text-xs font-mono text-slate-800 placeholder-slate-400 focus:outline-none focus:border-sky-500 transition"
                />
                <button
                  type="button"
                  onClick={() => setShowApiKey(!showApiKey)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 cursor-pointer"
                  title={showApiKey ? "Hide key" : "Show key"}
                >
                  {showApiKey ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                </button>
              </div>
            </div>

            {/* AI Model selection */}
            <div className="space-y-1">
              <label className="text-slate-700 font-medium flex items-center space-x-1.5">
                <Cpu className="w-3.5 h-3.5 text-sky-600" />
                <span>Extraction LLM Model:</span>
              </label>
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs text-slate-800 focus:outline-none focus:border-sky-500 transition"
              >
                <option value="llama-3.3-70b-versatile">llama-3.3-70b-versatile (Recommended)</option>
                <option value="openai/gpt-oss-120b">openai/gpt-oss-120b</option>
                <option value="qwen/qwen3.6-27b">qwen/qwen3.6-27b</option>
                <option value="llama-3.1-8b-instant">llama-3.1-8b-instant</option>
              </select>
            </div>

            {/* Min OCR Confidence */}
            <div className="space-y-1">
              <div className="flex justify-between font-medium text-slate-700">
                <span>Min OCR Confidence:</span>
                <span className="font-bold text-sky-600">{minConfidence}%</span>
              </div>
              <input
                type="range"
                min="10"
                max="80"
                step="5"
                value={minConfidence}
                onChange={(e) => setMinConfidence(parseFloat(e.target.value))}
                className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-sky-600 mt-2"
              />
            </div>

            {/* Preprocessing Toggles */}
            <div className="flex items-center space-x-2 pt-2">
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={enableClahe}
                  onChange={(e) => setEnableClahe(e.target.checked)}
                  className="rounded text-sky-600 focus:ring-0"
                />
                <span className="font-medium text-slate-700">CLAHE Contrast Enhancement</span>
              </label>
            </div>

            <div className="flex items-center space-x-2 pt-2">
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={enableDenoise}
                  onChange={(e) => setEnableDenoise(e.target.checked)}
                  className="rounded text-sky-600 focus:ring-0"
                />
                <span className="font-medium text-slate-700">Bilateral Noise Reduction</span>
              </label>
            </div>
          </div>
        </div>
      )}

      {/* Uploader / Upload Zone */}
      {!results && (
        <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-sm space-y-5">
          
          {/* Drag & Drop Area */}
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onClick={() => {
              if (selectedFiles.length < 3 && fileInputRef.current) {
                fileInputRef.current.click();
              }
            }}
            className={`border-2 border-dashed rounded-2xl p-8 text-center transition cursor-pointer flex flex-col items-center justify-center space-y-3 ${
              selectedFiles.length >= 3 
                ? 'border-slate-200 bg-slate-50/50 cursor-not-allowed opacity-80' 
                : 'border-slate-300 hover:border-sky-500 hover:bg-sky-50/30'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept="image/jpeg,image/jpg,image/png"
              onChange={handleFileChange}
              disabled={selectedFiles.length >= 3 || isLoading}
              className="hidden"
            />

            <div className="w-14 h-14 rounded-2xl bg-sky-50 border border-sky-100 text-sky-600 flex items-center justify-center shadow-inner">
              <Upload className="w-7 h-7" />
            </div>

            <div className="space-y-1">
              <h3 className="text-sm font-bold text-slate-800">
                {selectedFiles.length >= 3 
                  ? 'Maximum 3 Images Reached' 
                  : 'Drag & Drop Shipping Label Images, or Click to Browse'}
              </h3>
              <p className="text-xs text-slate-500">
                Upload 1, 2, or 3 images (JPG, JPEG, PNG). Every label is analyzed independently.
              </p>
            </div>

            <div className="flex items-center space-x-2 pt-2">
              <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                {selectedFiles.length} / 3 Uploaded
              </span>
            </div>
          </div>

          {/* Selected Images Grid */}
          {selectedFiles.length > 0 && (
            <div className="space-y-3 pt-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-slate-700">
                  Ready to Scan ({selectedFiles.length} Image{selectedFiles.length > 1 ? 's' : ''}):
                </span>
                {selectedFiles.length < 3 && (
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isLoading}
                    className="flex items-center space-x-1 text-sky-600 hover:text-sky-700 font-semibold"
                  >
                    <Plus className="w-4 h-4" />
                    <span>Add Another Image ({3 - selectedFiles.length} remaining)</span>
                  </button>
                )}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                {previews.map((item, idx) => (
                  <div
                    key={idx}
                    className="relative bg-slate-50 border border-slate-200 rounded-xl p-3 flex flex-col space-y-2 group shadow-sm hover:border-slate-300 transition"
                  >
                    {/* Index Badge */}
                    <div className="absolute top-2 left-2 z-10 px-2 py-0.5 rounded-md bg-slate-900/80 text-white font-bold text-[10px] backdrop-blur-sm">
                      Label #{idx + 1}
                    </div>

                    {/* Remove button */}
                    {!isLoading && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          removeFile(idx);
                        }}
                        className="absolute top-2 right-2 z-10 p-1 rounded-full bg-white/90 hover:bg-rose-500 hover:text-white text-slate-600 shadow transition"
                        title="Remove image"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    )}

                    {/* Image Preview Thumbnail */}
                    <div className="h-36 w-full rounded-lg overflow-hidden bg-white border border-slate-200 flex items-center justify-center">
                      <img
                        src={item.url}
                        alt={`Preview ${idx + 1}`}
                        className="h-full w-full object-contain"
                      />
                    </div>

                    {/* Filename & size */}
                    <div className="truncate text-xs">
                      <p className="font-semibold text-slate-800 truncate" title={item.name}>
                        {item.name}
                      </p>
                      <p className="text-[11px] text-slate-400 font-mono">
                        {item.size}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Action Button */}
          {selectedFiles.length > 0 && (
            <button
              onClick={handleScan}
              disabled={isLoading}
              className="w-full py-4 px-6 rounded-2xl bg-gradient-to-r from-sky-600 via-indigo-600 to-indigo-700 hover:from-sky-500 hover:to-indigo-600 text-white font-bold text-base shadow-lg shadow-indigo-600/25 transition-all duration-200 flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer hover:scale-[1.01] active:scale-[0.99]"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>
                    Scanning {selectedFiles.length} Label{selectedFiles.length > 1 ? 's' : ''} (RapidOCR → LLM Data Separation → Barcode & QR Engine)...
                  </span>
                </>
              ) : (
                <>
                  <Package className="w-5 h-5" />
                  <span>
                    Scan {selectedFiles.length} Shipping Label{selectedFiles.length > 1 ? 's' : ''}
                  </span>
                  <ArrowRight className="w-5 h-5" />
                </>
              )}
            </button>
          )}

        </div>
      )}


      {/* Error Alert Box */}
      {errorMessage && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-2xl flex items-start space-x-3 text-rose-800 shadow-sm animate-in fade-in">
          <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <h4 className="text-sm font-bold text-rose-900">Extraction Error</h4>
            <p className="text-xs text-rose-700">{errorMessage}</p>
          </div>
        </div>
      )}

      {/* Results View */}
      {results && (
        <ShippingResultsView 
          results={results} 
          onScanMore={handleReset} 
        />
      )}

    </div>
  );
}
