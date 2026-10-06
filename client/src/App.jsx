import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import UploadZone from './components/UploadZone';
import ResultsView from './components/ResultsView';
import VisualPipeline from './components/VisualPipeline';
import JsonViewer from './components/JsonViewer';
import HistoryDrawer from './components/HistoryDrawer';
import ShippingScanner from './components/ShippingScanner';
import QRTools from './components/QRTools';
import { extractDocumentApi, getHealthApi } from './services/api';
import { ScanText, Eye, FileText, Code, AlertCircle, Loader2, ArrowRight, X, Bot, ShieldCheck, Package } from 'lucide-react';

export default function App() {
  // Page Routing State: 'id_verification' | 'shipping_scanner'
  const [currentPage, setCurrentPage] = useState('id_verification');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isAboutOpen, setIsAboutOpen] = useState(false);

  // Existing ID Verification States
  const [selectedFile, setSelectedFile] = useState(null);
  const [settings, setSettings] = useState({
    model_name: 'openai/gpt-oss-120b',
    psm_mode: 11,
    min_confidence: 25,
    enable_glare: true,
    enable_clahe: true,
    enable_denoise: true,
    enable_threshold: false,
    threshold_method: 'otsu',
  });

  const [isLoading, setIsLoading] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);
  const [extractionResult, setExtractionResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);
  const [activeTab, setActiveTab] = useState('fields');
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [isDbConnected, setIsDbConnected] = useState(false);

  useEffect(() => {
    getHealthApi()
      .then((data) => {
        setIsDbConnected(!!data.database_connected);
      })
      .catch(() => {
        setIsDbConnected(false);
      });
  }, []);

  const handleExtract = async () => {
    if (!selectedFile) return;

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const result = await extractDocumentApi(selectedFile, settings);
      setExtractionResult(result);
      setActiveTab('fields');
    } catch (err) {
      console.error('Extraction failed:', err);
      const msg = err.response?.data?.detail || err.response?.data?.error || err.message || 'Failed to extract document.';
      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRetryScan = async () => {
    if (!selectedFile) {
      alert("No image file loaded in current session. Please upload an image file to perform a deep retry scan.");
      return;
    }

    setIsRetrying(true);
    setErrorMessage(null);

    try {
      // Deep Multi-Pass OCR scan with bilateral denoising & contrast enhancement
      const result = await extractDocumentApi(selectedFile, settings, true);
      setExtractionResult(result);
      setActiveTab('fields');
    } catch (err) {
      console.error('Retry scan failed:', err);
      const msg = err.response?.data?.error || err.message || 'Deep scan retry failed.';
      setErrorMessage(msg);
    } finally {
      setIsRetrying(false);
    }
  };

  const handleClear = () => {
    setSelectedFile(null);
    setExtractionResult(null);
    setErrorMessage(null);
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900">
      
      {/* Navigation Bar with Hamburger Menu ☰ */}
      <Navbar
        onToggleSidebar={() => setIsSidebarOpen(true)}
        onToggleHistory={() => setIsHistoryOpen(true)}
        isConnected={isDbConnected}
        activePage={currentPage}
      />

      {/* Slide-out Sidebar Drawer */}
      <Sidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        currentPage={currentPage}
        onNavigate={(page) => setCurrentPage(page)}
        onOpenHistory={() => setIsHistoryOpen(true)}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onOpenAbout={() => setIsAboutOpen(true)}
      />

      {/* PAGE 1: SHIPPING LABEL SCANNER */}
      {currentPage === 'shipping_scanner' && (
        <main className="flex-1 w-full max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
          <ShippingScanner settings={settings} />
        </main>
      )}

      {/* PAGE 2: QR & BARCODE TOOLS (Generator + Standalone Scanner) */}
      {currentPage === 'qr_tools' && (
        <main className="flex-1 w-full max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
          <QRTools />
        </main>
      )}

      {/* PAGE 3: ID DOCUMENT VERIFICATION (Existing Workflow 100% Preserved) */}
      {currentPage === 'id_verification' && (
        <main className="flex-1 w-full max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-6 flex flex-col justify-center">
          
          {/* Upload Zone (Centered Single Card) */}
          <div className="w-full space-y-4">
            <UploadZone
              onFileSelected={(file) => {
                setSelectedFile(file);
                setExtractionResult(null);
                setErrorMessage(null);
              }}
              selectedFile={selectedFile}
              onClear={handleClear}
              isLoading={isLoading}
            />

            {/* Run Extraction Button (Appears when image is uploaded) */}
            {selectedFile && !extractionResult && (
              <button
                onClick={handleExtract}
                disabled={isLoading}
                className="w-full py-4 px-6 rounded-2xl bg-gradient-to-r from-sky-600 via-indigo-600 to-indigo-700 hover:from-sky-500 hover:to-indigo-600 text-white font-bold text-base shadow-lg shadow-indigo-600/25 transition-all duration-200 flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer hover:scale-[1.01] active:scale-[0.99]"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span>Processing Document (OpenCV Enhancement → RapidOCR Detection)...</span>
                  </>
                ) : (
                  <>
                    <ScanText className="w-5 h-5" />
                    <span>Extract Document Information</span>
                    <ArrowRight className="w-5 h-5" />
                  </>
                )}
              </button>
            )}
          </div>

          {/* Error Alert Box */}
          {errorMessage && (
            <div className="p-4 bg-rose-50 border border-rose-200 rounded-2xl flex items-start space-x-3 text-rose-800 shadow-sm">
              <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
              <div>
                <h4 className="text-sm font-bold text-rose-900">Extraction Request Failed</h4>
                <p className="text-xs text-rose-700 mt-0.5">{errorMessage}</p>
              </div>
            </div>
          )}

          {/* Results Dashboard */}
          {extractionResult && (
            <div className="space-y-4 animate-in fade-in-50 duration-300">
              
              {/* Tab Navigation */}
              <div className="flex border-b border-slate-200 space-x-2">
                <button
                  onClick={() => setActiveTab('fields')}
                  className={`flex items-center space-x-2 py-2.5 px-4 rounded-t-xl text-xs font-bold transition border-b-2 ${
                    activeTab === 'fields'
                      ? 'border-sky-600 text-sky-700 bg-white shadow-sm'
                      : 'border-transparent text-slate-500 hover:text-slate-800'
                  }`}
                >
                  <FileText className="w-4 h-4" />
                  <span>Extracted Fields</span>
                </button>

                <button
                  onClick={() => setActiveTab('pipeline')}
                  className={`flex items-center space-x-2 py-2.5 px-4 rounded-t-xl text-xs font-bold transition border-b-2 ${
                    activeTab === 'pipeline'
                      ? 'border-sky-600 text-sky-700 bg-white shadow-sm'
                      : 'border-transparent text-slate-500 hover:text-slate-800'
                  }`}
                >
                  <Eye className="w-4 h-4" />
                  <span>Visual Pipeline</span>
                </button>

                <button
                  onClick={() => setActiveTab('ocr')}
                  className={`flex items-center space-x-2 py-2.5 px-4 rounded-t-xl text-xs font-bold transition border-b-2 ${
                    activeTab === 'ocr'
                      ? 'border-sky-600 text-sky-700 bg-white shadow-sm'
                      : 'border-transparent text-slate-500 hover:text-slate-800'
                  }`}
                >
                  <FileText className="w-4 h-4" />
                  <span>Raw OCR Text</span>
                </button>

                <button
                  onClick={() => setActiveTab('json')}
                  className={`flex items-center space-x-2 py-2.5 px-4 rounded-t-xl text-xs font-bold transition border-b-2 ${
                    activeTab === 'json'
                      ? 'border-sky-600 text-sky-700 bg-white shadow-sm'
                      : 'border-transparent text-slate-500 hover:text-slate-800'
                  }`}
                >
                  <Code className="w-4 h-4" />
                  <span>JSON Payload</span>
                </button>
              </div>

              {/* Tab 1: Extracted Fields Card */}
              {activeTab === 'fields' && (
                <ResultsView 
                  result={extractionResult} 
                  onUploadAnother={handleClear}
                  onRetryScan={handleRetryScan}
                  isRetrying={isRetrying}
                />
              )}

              {/* Tab 2: Visual Pipeline Gallery */}
              {activeTab === 'pipeline' && (
                <VisualPipeline images={extractionResult.images} />
              )}

              {/* Tab 3: Raw OCR & Spatial Text */}
              {activeTab === 'ocr' && (
                <div className="bg-white border border-slate-200/80 rounded-2xl p-6 shadow-sm space-y-4">
                  <div>
                    <h3 className="text-base font-bold text-slate-900">OCR Extracted Text & Line Sequences</h3>
                    <p className="text-xs text-slate-500">Text lines detected directly by RapidOCR Engine</p>
                  </div>
                  <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 max-h-[400px] overflow-auto">
                    <pre className="text-xs text-slate-800 font-mono whitespace-pre-wrap leading-relaxed">
                      {extractionResult.raw_ocr_text || 'No text detected.'}
                    </pre>
                  </div>
                </div>
              )}

              {/* Tab 4: JSON Viewer */}
              {activeTab === 'json' && (
                <JsonViewer
                  data={extractionResult}
                  fileName={`${extractionResult.document_type}_${selectedFile?.name.replace(/\.[^/.]+$/, '')}`}
                />
              )}

            </div>
          )}

        </main>
      )}

      {/* History Slide-out Drawer */}
      <HistoryDrawer
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        onSelectDocument={(doc) => {
          setCurrentPage('id_verification');
          setExtractionResult(doc);
          setActiveTab('fields');
        }}
      />

      {/* Settings Modal */}
      {isSettingsOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-in fade-in">
          <div className="relative w-full max-w-2xl bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden">
            <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <h3 className="text-sm font-bold text-slate-800">Extraction & Model Settings</h3>
              <button
                onClick={() => setIsSettingsOpen(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-5">
              <SettingsPanel 
                settings={settings} 
                onChange={(newSettings) => setSettings(newSettings)} 
              />
            </div>
            <div className="p-4 bg-slate-50 border-t border-slate-200 flex justify-end">
              <button
                onClick={() => setIsSettingsOpen(false)}
                className="px-4 py-2 rounded-xl bg-sky-600 hover:bg-sky-700 text-white text-xs font-semibold shadow-sm transition"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* About Modal */}
      {isAboutOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-in fade-in">
          <div className="relative w-full max-w-lg bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden">
            <div className="p-5 bg-gradient-to-r from-sky-600 to-indigo-600 text-white flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-xl bg-white/20 backdrop-blur flex items-center justify-center">
                  <Bot className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-base font-bold">Utility Bot</h3>
                  <p className="text-xs text-white/80">Version 2.5.0 Enterprise</p>
                </div>
              </div>
              <button
                onClick={() => setIsAboutOpen(false)}
                className="p-1.5 rounded-lg text-white/80 hover:text-white hover:bg-white/20 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4 text-xs text-slate-600 leading-relaxed">
              <div className="p-3 bg-sky-50 border border-sky-100 rounded-xl text-sky-900 flex items-center space-x-3">
                <ShieldCheck className="w-6 h-6 text-sky-600 flex-shrink-0" />
                <div>
                  <strong className="block text-slate-900">ID Document Verification:</strong>
                  Automated OCR extraction and validation for Aadhaar, PAN Card, and Driving Licence with OpenCV preprocessing.
                </div>
              </div>
              <div className="p-3 bg-emerald-50 border border-emerald-100 rounded-xl text-emerald-900 flex items-center space-x-3">
                <Package className="w-6 h-6 text-emerald-600 flex-shrink-0" />
                <div>
                  <strong className="block text-slate-900">Shipping Label Scanner:</strong>
                  Multi-image logistics parsing (1–3 images), field extraction (Ship To, Ship From, Order, Dimensions, Items), and ZXing-CPP Barcode / QR matrix detection.
                </div>
              </div>
              <div className="text-[11px] text-slate-400 pt-2 border-t border-slate-100">
                Privacy Policy: All processed documents are protected by strict local hardware fingerprint isolation and an automated 30-day retention schedule.
              </div>
            </div>
            <div className="p-4 bg-slate-50 border-t border-slate-200 flex justify-end">
              <button
                onClick={() => setIsAboutOpen(false)}
                className="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold shadow-sm transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
