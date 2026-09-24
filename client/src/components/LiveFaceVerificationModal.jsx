import React, { useState, useEffect, useRef } from 'react';
import { 
  Camera, 
  RefreshCw, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  Scan, 
  X, 
  Eye, 
  Check 
} from 'lucide-react';
import { getLivenessChallengeApi, verifyLiveFaceApi } from '../services/api';

export default function LiveFaceVerificationModal({ 
  isOpen, 
  onClose, 
  idPortraitPhoto, 
  applicantName, 
  onVerificationComplete 
}) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  
  const [stream, setStream] = useState(null);
  const [cameraError, setCameraError] = useState(null);
  const [capturedImage, setCapturedImage] = useState(null);
  const [isCapturing, setIsCapturing] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [verificationResult, setVerificationResult] = useState(null);
  const [activeChallenge, setActiveChallenge] = useState(null);
  const [step, setStep] = useState('prepare'); // 'prepare' | 'camera' | 'analyzing' | 'result'
  const [progressStep, setProgressStep] = useState(0);

  // Initialize camera when modal opens
  useEffect(() => {
    if (isOpen) {
      setStep('camera');
      setCapturedImage(null);
      setVerificationResult(null);
      setCameraError(null);
      startCamera();
      fetchChallenge();
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
          width: { ideal: 640 },
          height: { ideal: 480 },
          facingMode: 'user'
        },
        audio: false
      });
      setStream(mediaStream);
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
      }
    } catch (err) {
      console.error('Webcam error:', err);
      setCameraError(err.message || 'Unable to access live webcam. Please ensure camera permissions are granted.');
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

  const fetchChallenge = async () => {
    try {
      const challenge = await getLivenessChallengeApi();
      setActiveChallenge(challenge);
    } catch (err) {
      console.warn('Challenge fetch notice:', err);
      setActiveChallenge({
        challenge_id: 'chal_default',
        challenge_type: 'blink',
        instruction: 'Look straight into the camera and blink naturally'
      });
    }
  };

  const captureFrame = () => {
    if (!videoRef.current || !canvasRef.current) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;

    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.90);
    setCapturedImage(dataUrl);
    stopCamera();
    runVerification(dataUrl);
  };

  const runVerification = async (liveImageData) => {
    setIsVerifying(true);
    setStep('analyzing');
    setProgressStep(1);

    const timer1 = setTimeout(() => setProgressStep(2), 500);
    const timer2 = setTimeout(() => setProgressStep(3), 1100);

    try {
      const payload = {
        id_portrait_photo: idPortraitPhoto,
        live_selfie_image: liveImageData,
        challenge_id: activeChallenge?.challenge_id || null
      };

      const response = await verifyLiveFaceApi(payload);
      
      clearTimeout(timer1);
      clearTimeout(timer2);
      setProgressStep(3);

      setVerificationResult(response);
      setStep('result');

      if (onVerificationComplete) {
        onVerificationComplete({
          method: 'live_face',
          status: response.status,
          isVerified: response.verification_passed,
          score: response.face_matching?.match_score || 0,
          tier: response.overall_tier,
          details: response
        });
      }
    } catch (err) {
      console.error('Verification error:', err);
      setVerificationResult({
        status: 'FAILED',
        verification_passed: false,
        overall_tier: 'WEAK',
        summary: 'Error communicating with face verification engine. Please try again.'
      });
      setStep('result');
    } finally {
      setIsVerifying(false);
    }
  };

  const handleRetake = () => {
    setCapturedImage(null);
    setVerificationResult(null);
    setStep('camera');
    startCamera();
    fetchChallenge();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-xl bg-white border border-slate-200 rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        
        {/* Header */}
        <div className="px-6 py-4.5 border-b border-slate-100 flex items-center justify-between bg-gradient-to-r from-slate-50 via-white to-slate-50">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-xl bg-indigo-50 border border-indigo-200 text-indigo-700">
              <Camera className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">Live Face Verification</h3>
              <p className="text-xs text-slate-500">
                Match applicant face against extracted ID portrait ({applicantName || 'Applicant'})
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

        {/* Hidden Canvas for frame snapshot */}
        <canvas ref={canvasRef} className="hidden" />

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-5">
          
          {/* CAMERA FEED VIEW */}
          {step === 'camera' && (
            <div className="space-y-4">
              {/* Liveness Challenge Instruction Banner */}
              {activeChallenge && (
                <div className="p-3.5 bg-blue-50 border border-blue-200 rounded-2xl flex items-center space-x-3 text-blue-900 shadow-sm animate-in slide-in-from-top-1 duration-200">
                  <div className="p-2 bg-blue-600 text-white rounded-xl shadow-sm flex-shrink-0">
                    <Eye className="w-4 h-4" />
                  </div>
                  <div className="flex-1">
                    <span className="text-[10px] font-bold text-blue-600 uppercase tracking-wider block">Liveness Prompt</span>
                    <p className="text-xs font-semibold">{activeChallenge.instruction}</p>
                  </div>
                </div>
              )}

              {/* Video Stream Container with Oval Alignment Guide */}
              <div className="relative aspect-[4/3] bg-slate-950 rounded-2xl overflow-hidden shadow-inner flex items-center justify-center">
                {cameraError ? (
                  <div className="p-6 text-center space-y-3">
                    <AlertTriangle className="w-10 h-10 text-amber-400 mx-auto" />
                    <p className="text-xs text-slate-300 max-w-xs">{cameraError}</p>
                    <button
                      onClick={startCamera}
                      className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold transition shadow"
                    >
                      Retry Camera
                    </button>
                  </div>
                ) : (
                  <>
                    <video
                      ref={videoRef}
                      autoPlay
                      playsInline
                      muted
                      className="w-full h-full object-cover transform -scale-x-100"
                    />

                    {/* Face Alignment Oval Guide */}
                    <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
                      <div className="w-52 h-64 border-2 border-dashed border-indigo-400/80 rounded-[50%] shadow-[0_0_0_9999px_rgba(15,23,42,0.45)] relative flex items-center justify-center">
                        <div className="absolute top-3 text-[10px] font-bold text-indigo-200 uppercase tracking-wider bg-slate-900/70 px-2 py-0.5 rounded-full backdrop-blur-sm">
                          Align Face Here
                        </div>
                      </div>
                    </div>

                    {/* ID Portrait Comparison Overlay Thumbnail */}
                    {idPortraitPhoto && (
                      <div className="absolute bottom-3 left-3 p-1.5 bg-slate-900/80 backdrop-blur-md rounded-xl border border-white/20 flex items-center space-x-2 shadow-lg">
                        <img 
                          src={idPortraitPhoto} 
                          alt="ID Portrait" 
                          className="w-10 h-12 object-cover rounded-lg border border-white/30" 
                        />
                        <div className="pr-1 text-left">
                          <span className="text-[9px] font-bold uppercase text-slate-300 block">ID Portrait</span>
                          <span className="text-[10px] text-emerald-400 font-semibold">Ready to match</span>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>

              {/* Action Controls */}
              {!cameraError && (
                <div className="flex items-center justify-center gap-3 pt-2">
                  <button
                    onClick={captureFrame}
                    className="inline-flex items-center space-x-2 px-8 py-3 bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white rounded-2xl text-xs font-bold shadow-lg shadow-indigo-600/25 transition cursor-pointer hover:scale-[1.02] active:scale-[0.98]"
                  >
                    <Camera className="w-4 h-4" />
                    <span>Capture & Verify Face</span>
                  </button>
                </div>
              )}
            </div>
          )}

          {/* ANALYZING VIEW */}
          {step === 'analyzing' && (
            <div className="py-12 px-6 flex flex-col items-center justify-center space-y-6 text-center">
              <div className="relative">
                <div className="w-20 h-20 rounded-full border-4 border-indigo-100 border-t-indigo-600 animate-spin" />
                <Scan className="w-8 h-8 text-indigo-600 absolute inset-0 m-auto animate-pulse" />
              </div>

              <div className="space-y-2 max-w-sm">
                <h4 className="text-sm font-bold text-slate-900">Comparing Biometric Embeddings...</h4>
                <p className="text-xs text-slate-500">
                  Running multi-scale anti-spoofing tests and ArcFace cosine similarity against ID card portrait.
                </p>
              </div>

              {/* Step Checklist */}
              <div className="w-full max-w-xs space-y-2 text-left bg-slate-50 p-4 rounded-2xl border border-slate-200/80">
                <div className="flex items-center space-x-2.5 text-xs">
                  {progressStep >= 1 ? <CheckCircle2 className="w-4 h-4 text-emerald-600" /> : <div className="w-4 h-4 rounded-full border border-slate-300" />}
                  <span className={progressStep >= 1 ? "font-semibold text-slate-800" : "text-slate-400"}>Face Detection & Alignment</span>
                </div>
                <div className="flex items-center space-x-2.5 text-xs">
                  {progressStep >= 2 ? <CheckCircle2 className="w-4 h-4 text-emerald-600" /> : <div className="w-4 h-4 rounded-full border border-slate-300" />}
                  <span className={progressStep >= 2 ? "font-semibold text-slate-800" : "text-slate-400"}>FFT Moiré & Anti-Spoofing</span>
                </div>
                <div className="flex items-center space-x-2.5 text-xs">
                  {progressStep >= 3 ? <CheckCircle2 className="w-4 h-4 text-emerald-600" /> : <div className="w-4 h-4 rounded-full border border-slate-300" />}
                  <span className={progressStep >= 3 ? "font-semibold text-slate-800" : "text-slate-400"}>Deep Cosine Similarity Matching</span>
                </div>
              </div>
            </div>
          )}

          {/* RESULT VIEW */}
          {step === 'result' && verificationResult && (
            <div className="space-y-5 animate-in fade-in slide-in-from-bottom-2 duration-300">
              
              {/* Top Summary Banner */}
              <div className={`p-4 rounded-2xl border flex items-start space-x-3.5 ${
                verificationResult.status === 'VERIFIED'
                  ? 'bg-emerald-50 border-emerald-200 text-emerald-950'
                  : verificationResult.status === 'UNCERTAIN'
                    ? 'bg-amber-50 border-amber-200 text-amber-950'
                    : 'bg-rose-50 border-rose-200 text-rose-950'
              }`}>
                {verificationResult.status === 'VERIFIED' ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
                ) : verificationResult.status === 'UNCERTAIN' ? (
                  <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                ) : (
                  <XCircle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
                )}
                <div>
                  <div className="flex items-center space-x-2">
                    <h4 className="text-sm font-bold">
                      {verificationResult.status === 'VERIFIED' 
                        ? '✅ Identity Verified (Strong Match)' 
                        : verificationResult.status === 'UNCERTAIN'
                          ? '🟡 Uncertain Match (Second ID Recommended)'
                          : '❌ Identity Verification Failed'}
                    </h4>
                  </div>
                  <p className="text-xs mt-1 leading-relaxed opacity-90">
                    {verificationResult.summary || verificationResult.face_matching?.explanation}
                  </p>
                </div>
              </div>

              {/* Side-by-Side Face Comparison Cards */}
              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 bg-slate-50 border border-slate-200 rounded-2xl text-center space-y-2">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">1. ID Card Portrait</span>
                  {idPortraitPhoto ? (
                    <img src={idPortraitPhoto} alt="ID" className="w-24 h-32 object-cover rounded-xl mx-auto border border-slate-200 shadow-sm" />
                  ) : (
                    <div className="w-24 h-32 bg-slate-200 rounded-xl mx-auto flex items-center justify-center text-xs text-slate-400">No Image</div>
                  )}
                  <span className="text-[11px] font-medium text-slate-600 block">Extracted from ID</span>
                </div>

                <div className="p-3 bg-slate-50 border border-slate-200 rounded-2xl text-center space-y-2">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">2. Live Selfie Capture</span>
                  {capturedImage ? (
                    <img src={capturedImage} alt="Live" className="w-24 h-32 object-cover rounded-xl mx-auto border border-slate-200 shadow-sm" />
                  ) : (
                    <div className="w-24 h-32 bg-slate-200 rounded-xl mx-auto flex items-center justify-center text-xs text-slate-400">No Image</div>
                  )}
                  <span className="text-[11px] font-medium text-slate-600 block">Live Webcam Feed</span>
                </div>
              </div>

              {/* Detailed Metrics */}
              <div className="p-4 bg-white border border-slate-200 rounded-2xl space-y-3 shadow-sm">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-500 font-semibold">Face Cosine Similarity Match:</span>
                  <span className="font-bold text-slate-900 font-mono text-sm">
                    {verificationResult.face_matching?.match_score || 0}%
                  </span>
                </div>

                {/* Progress Meter */}
                <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
                  <div 
                    className={`h-full rounded-full transition-all duration-500 ${
                      verificationResult.status === 'VERIFIED'
                        ? 'bg-emerald-500'
                        : verificationResult.status === 'UNCERTAIN'
                          ? 'bg-amber-500'
                          : 'bg-rose-500'
                    }`}
                    style={{ width: `${Math.min(100, Math.max(5, verificationResult.face_matching?.match_score || 0))}%` }}
                  />
                </div>

                <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1">
                  <span>Weak (&lt;50%)</span>
                  <span>Uncertain (50-74%)</span>
                  <span>Strong (≥75%)</span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  onClick={handleRetake}
                  className="inline-flex items-center space-x-1.5 px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-bold transition cursor-pointer"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Retake Selfie</span>
                </button>

                <button
                  onClick={onClose}
                  className={`inline-flex items-center space-x-1.5 px-6 py-2.5 rounded-xl text-xs font-bold text-white shadow-md transition cursor-pointer ${
                    verificationResult.status === 'VERIFIED'
                      ? 'bg-emerald-600 hover:bg-emerald-500 shadow-emerald-600/20'
                      : 'bg-slate-800 hover:bg-slate-700'
                  }`}
                >
                  <Check className="w-4 h-4" />
                  <span>Apply & Done</span>
                </button>
              </div>

            </div>
          )}

        </div>

      </div>
    </div>
  );
}
