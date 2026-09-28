import React, { useState, useEffect, useRef } from 'react';
import { 
  Fingerprint, 
  Camera, 
  RefreshCw, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  Scan, 
  X, 
  Sparkles, 
  Activity, 
  ShieldCheck, 
  Check 
} from 'lucide-react';
import { verifyBiometricApi } from '../services/api';

export default function BiometricScanModal({ 
  isOpen, 
  onClose, 
  applicantName, 
  idNumber,
  onVerificationComplete 
}) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  
  const [stream, setStream] = useState(null);
  const [cameraError, setCameraError] = useState(null);
  const [capturedImage, setCapturedImage] = useState(null);
  const [isCapturing, setIsCapturing] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const [step, setStep] = useState('camera'); // 'camera' | 'processing' | 'result'
  const [progressMsg, setProgressMsg] = useState('');

  useEffect(() => {
    if (isOpen) {
      setStep('camera');
      setCapturedImage(null);
      setResult(null);
      setCameraError(null);
      startCamera();
    } else {
      stopCamera();
    }

    return () => {
      stopCamera();
    };
  }, [isOpen]);

  const startCamera = async () => {
    setCameraError(null);
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('Camera access is not supported by your browser.');
      }
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: 'environment' // Prefers back camera if available (macro focus), or user camera
        },
        audio: false
      });
      setStream(mediaStream);
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
      }
    } catch (err) {
      console.warn('Environment camera failed, falling back to default:', err);
      try {
        const mediaStream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' },
          audio: false
        });
        setStream(mediaStream);
        if (videoRef.current) {
          videoRef.current.srcObject = mediaStream;
        }
      } catch (fallbackErr) {
        console.error('Webcam error:', fallbackErr);
        setCameraError(fallbackErr.message || 'Unable to access camera for biometric capture.');
      }
    }
  };

  const stopCamera = () => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      setStream(null);
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  };

  const captureFingerprint = () => {
    if (!videoRef.current || !canvasRef.current) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;

    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.95);
    setCapturedImage(dataUrl);
    stopCamera();
    runBiometricAnalysis(dataUrl);
  };

  const runBiometricAnalysis = async (imageData) => {
    setIsProcessing(true);
    setStep('processing');
    setProgressMsg('Extracting fingertip dermal region...');

    const timer1 = setTimeout(() => setProgressMsg('Applying Gabor multi-orientation ridge filters...'), 600);
    const timer2 = setTimeout(() => setProgressMsg('Calculating ISO minutiae endings & bifurcations...'), 1200);

    try {
      const response = await verifyBiometricApi({
        fingerprint_image: imageData,
        applicant_name: applicantName,
        id_number: idNumber
      });

      clearTimeout(timer1);
      clearTimeout(timer2);
      setResult(response);
      setStep('result');

      if (onVerificationComplete && response.verification_passed) {
        onVerificationComplete({
          method: 'biometric_fingerprint',
          status: response.status,
          isVerified: response.verification_passed,
          score: response.quality_score,
          tier: response.verification_passed ? 'STRONG_MATCH' : 'WEAK',
          details: response
        });
      }
    } catch (err) {
      console.error('Biometric processing error:', err);
      setResult({
        status: 'FAILED',
        verification_passed: false,
        quality_score: 0.0,
        minutiae_count: 0,
        summary: 'Error processing biometric scan. Please retry with better lighting.'
      });
      setStep('result');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleRetake = () => {
    setCapturedImage(null);
    setResult(null);
    setStep('camera');
    startCamera();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/65 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-xl bg-white border border-slate-200 rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[92vh]">
        
        {/* Header */}
        <div className="px-6 py-4.5 border-b border-slate-100 flex items-center justify-between bg-gradient-to-r from-slate-50 via-white to-slate-50">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-xl bg-teal-50 border border-teal-200 text-teal-700">
              <Fingerprint className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">Contactless Biometric Scan</h3>
              <p className="text-xs text-slate-500">
                Optical dermal ridge extraction & minutiae matching for {applicantName || 'Applicant'}
              </p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Hidden Canvas */}
        <canvas ref={canvasRef} className="hidden" />

        {/* Body */}
        <div className="p-6 overflow-y-auto space-y-5">
          
          {/* CAMERA VIEW */}
          {step === 'camera' && (
            <div className="space-y-4">
              <div className="p-3.5 bg-teal-50/80 border border-teal-200 rounded-2xl flex items-center space-x-3 text-teal-900 shadow-sm">
                <div className="p-2 bg-teal-600 text-white rounded-xl shadow-sm flex-shrink-0">
                  <Activity className="w-4 h-4" />
                </div>
                <div className="flex-1">
                  <span className="text-[10px] font-bold text-teal-700 uppercase tracking-wider block">Biometric Guide</span>
                  <p className="text-xs font-semibold">Hold your index fingertip steady inside the center oval guide</p>
                </div>
              </div>

              {cameraError ? (
                <div className="p-8 text-center bg-red-50 border border-red-200 rounded-2xl space-y-3">
                  <AlertTriangle className="w-10 h-10 text-red-500 mx-auto" />
                  <p className="text-sm font-semibold text-red-900">{cameraError}</p>
                  <button 
                    onClick={startCamera}
                    className="px-4 py-2 bg-red-600 text-white text-xs font-bold rounded-xl shadow hover:bg-red-700 transition"
                  >
                    Retry Camera
                  </button>
                </div>
              ) : (
                <div className="relative aspect-[4/3] bg-slate-950 rounded-2xl overflow-hidden shadow-inner flex items-center justify-center border border-slate-800">
                  <video 
                    ref={videoRef}
                    autoPlay
                    playsInline
                    muted
                    className="w-full h-full object-cover"
                  />

                  {/* FINGERPRINT OVAL TARGET RETICLE */}
                  <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                    <div className="relative w-44 h-56 border-2 border-dashed border-teal-400/90 rounded-[50%] shadow-[0_0_20px_rgba(20,184,166,0.35)] flex flex-col items-center justify-center bg-teal-500/10 backdrop-contrast-125">
                      <Fingerprint className="w-12 h-12 text-teal-300/40 animate-pulse" />
                      <span className="text-[11px] font-bold text-teal-200 bg-slate-900/80 px-2.5 py-0.5 rounded-full mt-2 border border-teal-400/40 shadow">
                        Place Fingertip Here
                      </span>
                    </div>
                  </div>

                  {/* Optical status indicator */}
                  <div className="absolute bottom-3 left-3 px-2.5 py-1 bg-slate-900/80 backdrop-blur border border-slate-700 rounded-lg text-[11px] text-teal-300 flex items-center space-x-1.5 font-mono">
                    <span className="w-2 h-2 rounded-full bg-teal-400 animate-ping" />
                    <span>Optical Ridge Sensor Active</span>
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex items-center justify-between pt-2">
                <button
                  onClick={onClose}
                  className="px-4 py-2.5 text-xs font-bold text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-xl transition cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  onClick={captureFingerprint}
                  disabled={!!cameraError}
                  className="px-6 py-3 bg-gradient-to-r from-teal-600 to-emerald-600 text-white text-xs font-bold rounded-2xl shadow-lg shadow-teal-600/25 hover:from-teal-700 hover:to-emerald-700 active:scale-98 transition flex items-center space-x-2 cursor-pointer disabled:opacity-50"
                >
                  <Fingerprint className="w-4 h-4" />
                  <span>Capture & Analyze Ridges</span>
                </button>
              </div>
            </div>
          )}

          {/* PROCESSING VIEW */}
          {step === 'processing' && (
            <div className="py-12 px-6 text-center space-y-6">
              <div className="relative w-24 h-24 mx-auto">
                <div className="absolute inset-0 rounded-full border-4 border-teal-100 border-t-teal-600 animate-spin" />
                <div className="absolute inset-2 rounded-full bg-teal-50 flex items-center justify-center text-teal-600">
                  <Fingerprint className="w-10 h-10 animate-pulse" />
                </div>
              </div>
              <div className="space-y-2">
                <h4 className="text-base font-bold text-slate-900">Processing Biometric Minutiae</h4>
                <p className="text-xs font-medium text-slate-500 animate-pulse">{progressMsg}</p>
              </div>
            </div>
          )}

          {/* RESULT VIEW */}
          {step === 'result' && result && (
            <div className="space-y-5 animate-in fade-in duration-300">
              
              {/* Status Header Banner */}
              <div className={`p-4 rounded-2xl border flex items-center space-x-3.5 ${
                result.verification_passed 
                  ? 'bg-emerald-50 border-emerald-200 text-emerald-900' 
                  : 'bg-amber-50 border-amber-200 text-amber-900'
              }`}>
                {result.verification_passed ? (
                  <CheckCircle2 className="w-7 h-7 text-emerald-600 flex-shrink-0" />
                ) : (
                  <XCircle className="w-7 h-7 text-amber-600 flex-shrink-0" />
                )}
                <div>
                  <h4 className="text-sm font-bold">
                    {result.verification_passed ? 'Biometric Scan Verified' : 'Scan Quality Insufficient'}
                  </h4>
                  <p className="text-xs opacity-90">{result.summary}</p>
                </div>
              </div>

              {/* Visualization Canvas Grid */}
              <div className="grid grid-cols-2 gap-3.5">
                {/* Minutiae Feature Map */}
                <div className="p-3 bg-slate-950 rounded-2xl border border-slate-800 text-center space-y-2">
                  <span className="text-[10px] font-bold tracking-wider uppercase text-teal-400 block">
                    Biometric Minutiae Map
                  </span>
                  {result.minutiae_visualization ? (
                    <img 
                      src={result.minutiae_visualization} 
                      alt="Minutiae Map" 
                      className="w-full h-36 object-contain rounded-xl bg-black border border-slate-800"
                    />
                  ) : (
                    <div className="w-full h-36 bg-slate-900 rounded-xl flex items-center justify-center text-xs text-slate-600">
                      No map available
                    </div>
                  )}
                  <div className="flex justify-center space-x-3 text-[10px] text-slate-400 font-medium">
                    <span className="flex items-center space-x-1">
                      <span className="w-2 h-2 rounded-full bg-red-500 inline-block" />
                      <span>Endings ({result.endings_count || 0})</span>
                    </span>
                    <span className="flex items-center space-x-1">
                      <span className="w-2 h-2 rounded-full bg-green-500 inline-block" />
                      <span>Bifurcations ({result.bifurcations_count || 0})</span>
                    </span>
                  </div>
                </div>

                {/* Enhanced Dermal Ridge Pattern */}
                <div className="p-3 bg-slate-900 rounded-2xl border border-slate-800 text-center space-y-2">
                  <span className="text-[10px] font-bold tracking-wider uppercase text-teal-400 block">
                    Dermal Ridge Flow (Gabor)
                  </span>
                  {result.enhanced_ridge_image ? (
                    <img 
                      src={result.enhanced_ridge_image} 
                      alt="Dermal Ridges" 
                      className="w-full h-36 object-contain rounded-xl bg-black border border-slate-800"
                    />
                  ) : (
                    <div className="w-full h-36 bg-slate-900 rounded-xl flex items-center justify-center text-xs text-slate-600">
                      No ridge image
                    </div>
                  )}
                  <div className="text-[10px] text-slate-400 font-medium">
                    Clarity Index: <strong className="text-slate-200">{result.ridge_clarity || 0}%</strong>
                  </div>
                </div>
              </div>

              {/* Metrics Row */}
              <div className="grid grid-cols-3 gap-3 p-3.5 bg-slate-50 border border-slate-200 rounded-2xl text-center">
                <div>
                  <span className="text-[10px] text-slate-500 font-bold uppercase block">Quality Score</span>
                  <span className="text-base font-extrabold text-slate-900">{result.quality_score || 0}%</span>
                </div>
                <div className="border-x border-slate-200">
                  <span className="text-[10px] text-slate-500 font-bold uppercase block">Minutiae Points</span>
                  <span className="text-base font-extrabold text-teal-700">{result.minutiae_count || 0}</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 font-bold uppercase block">Status</span>
                  <span className={`text-xs font-extrabold px-2 py-0.5 rounded-full inline-block mt-0.5 ${
                    result.verification_passed ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
                  }`}>
                    {result.status}
                  </span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-between pt-2">
                <button
                  onClick={handleRetake}
                  className="px-4 py-2.5 text-xs font-bold text-slate-700 hover:bg-slate-100 border border-slate-200 rounded-xl transition flex items-center space-x-1.5 cursor-pointer"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Scan Again</span>
                </button>

                {result.verification_passed ? (
                  <button
                    onClick={onClose}
                    className="px-6 py-2.5 bg-emerald-600 text-white text-xs font-bold rounded-xl shadow-lg shadow-emerald-600/25 hover:bg-emerald-700 transition flex items-center space-x-1.5 cursor-pointer"
                  >
                    <Check className="w-4 h-4" />
                    <span>Complete Verification</span>
                  </button>
                ) : (
                  <button
                    onClick={handleRetake}
                    className="px-6 py-2.5 bg-slate-900 text-white text-xs font-bold rounded-xl hover:bg-slate-800 transition cursor-pointer"
                  >
                    Retry Fingerprint Scan
                  </button>
                )}
              </div>

            </div>
          )}

        </div>

      </div>
    </div>
  );
}
