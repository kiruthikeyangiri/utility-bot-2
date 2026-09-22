import React, { useState, useEffect } from 'react';
import { 
  AlertTriangle, 
  XCircle, 
  ShieldCheck, 
  User, 
  Calendar, 
  MapPin, 
  Hash, 
  Clock, 
  Image as ImageIcon,
  RotateCcw,
  Car, 
  Check, 
  RefreshCw, 
  Upload, 
  CheckCircle2, 
  Lock, 
  Cpu, 
  CalendarDays, 
  ThumbsUp, 
  ThumbsDown, 
  Camera, 
  FileCheck, 
  Scan, 
  UserCheck, 
  ArrowLeft, 
  Edit3 
} from 'lucide-react';
import { confirmVerificationApi } from '../services/api';
import IdentityReferenceCard from './IdentityReferenceCard';
import LiveFaceVerificationModal from './LiveFaceVerificationModal';
import SecondIdVerificationModal from './SecondIdVerificationModal';

export default function ResultsView({ result, onUploadAnother, onRetryScan, isRetrying }) {
  if (!result) return null;

  const { 
    document_type, 
    is_valid, 
    short_circuited, 
    is_duplicate_or_sample, 
    authenticity_status, 
    data, 
    warnings, 
    images, 
    portrait_photo, 
    status: initialStatus,
    sequential_id: initialSeqId,
    reference_card: initialRefCard
  } = result;

  const [formData, setFormData] = useState(data || {});
  const [confirmationStatus, setConfirmationStatus] = useState(initialStatus || 'Pending Confirmation');
  const [confirmedId, setConfirmedId] = useState(initialSeqId || null);
  const [referenceCardData, setReferenceCardData] = useState(initialRefCard || null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [confirmMessage, setConfirmMessage] = useState(null);
  
  // Navigation Screens: 'ocr_review' | 'customer_verify' | 'rejected_review' | 'reference_card'
  const [currentScreen, setCurrentScreen] = useState('ocr_review');
  
  // Customer Identity Verification State
  const [identityStatus, setIdentityStatus] = useState('NOT_VERIFIED'); // 'NOT_VERIFIED' | 'VERIFIED' | 'UNCERTAIN' | 'FAILED'
  const [verificationMethod, setVerificationMethod] = useState(null); // 'live_face' | 'second_id'
  const [verificationScore, setVerificationScore] = useState(null);
  const [verificationDetails, setVerificationDetails] = useState(null);
  const [isLiveFaceModalOpen, setIsLiveFaceModalOpen] = useState(false);
  const [isSecondIdModalOpen, setIsSecondIdModalOpen] = useState(false);

  useEffect(() => {
    setFormData(data || {});
    setConfirmationStatus(result.status || 'Pending Confirmation');
    setConfirmedId(result.sequential_id || result.id || null);
    setReferenceCardData(result.reference_card || null);
    setConfirmMessage(null);
    setCurrentScreen(result.status === 'Success' ? 'customer_verify' : 'ocr_review');
    setIdentityStatus('NOT_VERIFIED');
    setVerificationMethod(null);
    setVerificationScore(null);
    setVerificationDetails(null);
  }, [result]);

  const handleFieldChange = (field, val) => {
    setFormData(prev => ({ ...prev, [field]: val }));
  };

  // STEP 1: User confirms OCR fields are Correct
  const handleCorrectClick = async () => {
    setIsSubmitting(true);
    try {
      const payload = {
        action: 'correct',
        data: formData,
        document_type: document_type,
        is_valid: is_valid,
        authenticity_status: authenticity_status,
        raw_ocr_text: result.raw_ocr_text || '',
        ocr_confidence: result.ocr_confidence || 0.0,
        original_filename: result.originalFileName || 'document.jpg',
        thumbnail_image: images?.original || null,
        portrait_photo: portrait_photo || null,
        quality_report: result.quality_report || {},
        warnings: warnings || []
      };

      const response = await confirmVerificationApi(payload);
      setConfirmedId(response.sequential_id || response.id);
      setConfirmationStatus('Success');
      if (response.reference_card) {
        setReferenceCardData(response.reference_card);
      }
      
      // Move to Customer Identity Verification stage
      setCurrentScreen('customer_verify');
      setConfirmMessage({
        type: 'success',
        text: `Document details confirmed (${response.sequential_id || response.id}). Please complete Customer Identity Verification.`
      });
    } catch (err) {
      console.error('Confirmation error:', err);
      setConfirmMessage({
        type: 'error',
        text: 'Failed to record confirmation. Please try again.'
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  // User marks OCR fields as Wrong (keeps document visible, allows retry or replacement)
  const handleWrongClick = async () => {
    setIsSubmitting(true);
    try {
      const payload = {
        action: 'wrong',
        data: formData,
        document_type: document_type,
        is_valid: is_valid,
        authenticity_status: authenticity_status,
        raw_ocr_text: result.raw_ocr_text || '',
        ocr_confidence: result.ocr_confidence || 0.0,
        original_filename: result.originalFileName || 'document.jpg',
        thumbnail_image: images?.original || null,
        portrait_photo: portrait_photo || null,
        quality_report: result.quality_report || {},
        warnings: warnings || []
      };

      const response = await confirmVerificationApi(payload);
      setConfirmedId(response.sequential_id || response.id);
      setConfirmationStatus('Failed');
      setReferenceCardData(null);
      setCurrentScreen('rejected_review');
      setConfirmMessage({
        type: 'failed',
        text: `Document marked as incorrect (Audit ID: ${response.sequential_id || response.id}). Choose next action below.`
      });
    } catch (err) {
      console.error('Wrong action error:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  // STEP 2: Customer Identity Verification Completed Callback
  const handleVerificationComplete = (res) => {
    setVerificationMethod(res.method);
    setVerificationScore(res.score);
    setVerificationDetails(res.details);

    if (res.isVerified) {
      setIdentityStatus('VERIFIED');
      setConfirmMessage({
        type: 'success',
        text: res.method === 'live_face' 
          ? `Customer Identity Verified! Live Face Match: ${res.score}%.` 
          : `Customer Identity Verified! Multi-Document Consistency: ${res.score}%.`
      });
    } else if (res.status === 'UNCERTAIN') {
      setIdentityStatus('UNCERTAIN');
      setConfirmMessage({
        type: 'warning',
        text: `Face match uncertain (${res.score}%). Please complete Second ID Verification to verify customer.`
      });
    } else {
      setIdentityStatus('FAILED');
      setConfirmMessage({
        type: 'failed',
        text: `Customer Verification Failed (${res.score || 0}%). Biometric mismatch.`
      });
    }
  };

  const currentDateTime = new Date().toLocaleString('en-IN', {
    weekday: 'short', year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true
  });

  const applicantName = formData?.name || formData?.cardholder_name || formData?.holder_name || 'Applicant';

  // Document Badge
  const getBadge = () => {
    if (is_duplicate_or_sample || authenticity_status === "DUPLICATE_COPY") {
      return (
        <div className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-rose-100 border border-rose-300 text-rose-800 text-[11px] font-bold">
          <AlertTriangle className="w-3 h-3 text-rose-600" />
          <span>DUPLICATE / SAMPLE</span>
        </div>
      );
    }
    if (short_circuited) {
      return (
        <div className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-rose-50 border border-rose-200 text-rose-700 text-[11px] font-bold">
          <XCircle className="w-3 h-3 text-rose-600" />
          <span>NON-ID DOCUMENT</span>
        </div>
      );
    }
    const configs = {
      aadhaar: { label: 'AADHAAR FRONT', colors: 'bg-blue-50 border-blue-200 text-blue-700' },
      aadhaar_back: { label: 'AADHAAR BACK', colors: 'bg-indigo-50 border-indigo-200 text-indigo-700' },
      pan: { label: 'PAN CARD', colors: 'bg-amber-50 border-amber-200 text-amber-800' },
      pan_back: { label: 'PAN BACK', colors: 'bg-amber-50 border-amber-300 text-amber-900' },
      driving_licence: { label: 'DRIVING LICENCE', colors: 'bg-emerald-50 border-emerald-200 text-emerald-800' },
      driving_licence_back: { label: 'DL BACK', colors: 'bg-emerald-50 border-emerald-200 text-emerald-800' },
    };
    const config = configs[document_type] || { label: 'UNSUPPORTED', colors: 'bg-red-50 border-red-200 text-red-700' };
    const Icon = document_type === 'pan_back' ? RotateCcw : ShieldCheck;
    return (
      <div className={`inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full border text-[11px] font-bold ${config.colors}`}>
        <Icon className="w-3 h-3" />
        <span>{config.label}</span>
      </div>
    );
  };

  // Identity Status Badge Renderer
  const renderIdentityStatusBadge = () => {
    if (identityStatus === 'VERIFIED') {
      return (
        <div className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-emerald-50 border border-emerald-300 text-emerald-800 text-xs font-bold shadow-sm animate-in fade-in">
          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          <span>Customer Verified {verificationScore ? `(${verificationScore}%)` : ''}</span>
        </div>
      );
    }
    if (identityStatus === 'UNCERTAIN') {
      return (
        <div className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-amber-50 border border-amber-300 text-amber-900 text-xs font-bold shadow-sm animate-in fade-in">
          <AlertTriangle className="w-4 h-4 text-amber-600" />
          <span>Identity Uncertain ({verificationScore}%) — 2nd ID Needed</span>
        </div>
      );
    }
    if (identityStatus === 'FAILED') {
      return (
        <div className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-rose-50 border border-rose-300 text-rose-800 text-xs font-bold shadow-sm animate-in fade-in">
          <XCircle className="w-4 h-4 text-rose-600" />
          <span>Verification Failed</span>
        </div>
      );
    }
    // Default Initial State: Not Verified
    return (
      <div className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-slate-100 border border-slate-200 text-slate-700 text-xs font-bold shadow-sm">
        <div className="w-2 h-2 rounded-full bg-slate-400" />
        <span>Identity: Not Verified</span>
      </div>
    );
  };

  // Editable field card
  const FieldCard = ({ icon: Icon, label, field, placeholder, iconBg, mono = false, type = 'input' }) => (
    <div className="group bg-white border border-slate-200 rounded-xl p-3.5 flex items-start space-x-3 hover:shadow-sm hover:border-slate-300 transition-all duration-200">
      <div className={`p-1.5 rounded-lg ${iconBg} flex-shrink-0`}>
        <Icon className="w-3.5 h-3.5" />
      </div>
      <div className="flex-1 overflow-hidden">
        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-0.5">{label}</span>
        {type === 'textarea' ? (
          <textarea
            rows="2"
            value={formData?.[field] || ''}
            onChange={(e) => handleFieldChange(field, e.target.value)}
            placeholder={placeholder}
            className="w-full text-xs font-medium text-slate-800 bg-transparent border border-transparent hover:border-slate-300 focus:border-blue-500 focus:bg-blue-50/30 p-1 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500/20 transition resize-none"
          />
        ) : (
          <input
            type="text"
            value={formData?.[field] || ''}
            onChange={(e) => handleFieldChange(field, e.target.value)}
            placeholder={placeholder}
            className={`w-full text-[13px] font-semibold text-slate-900 bg-transparent border-b border-dashed border-transparent hover:border-slate-300 focus:border-blue-500 focus:bg-blue-50/30 px-0.5 py-0.5 rounded focus:outline-none transition ${mono ? 'font-mono tracking-wider' : ''}`}
          />
        )}
      </div>
    </div>
  );

  const iconBg = {
    aadhaar: 'bg-blue-100 text-blue-600',
    aadhaar_back: 'bg-indigo-100 text-indigo-600',
    pan: 'bg-amber-100 text-amber-600',
    driving_licence: 'bg-emerald-100 text-emerald-600',
    driving_licence_back: 'bg-emerald-100 text-emerald-600',
  }[document_type] || 'bg-slate-100 text-slate-600';

  const handleRetryClick = (e) => {
    e.preventDefault();
    if (onRetryScan) {
      onRetryScan();
    }
  };

  return (
    <div className="space-y-6">

      {/* Deep Scan Loading Indicator Banner */}
      {isRetrying && (
        <div className="p-4 bg-gradient-to-r from-indigo-900 to-slate-900 text-white rounded-xl shadow-lg border border-indigo-500/40 flex items-center space-x-3 animate-pulse">
          <RefreshCw className="w-5 h-5 text-indigo-400 animate-spin flex-shrink-0" />
          <div>
            <h4 className="text-xs font-bold text-indigo-200">Deep Multi-Pass OCR Scan in Progress...</h4>
            <p className="text-[11px] text-slate-300">Applying multi-scale CLAHE, bilateral noise reduction, and re-evaluating text bounding boxes.</p>
          </div>
        </div>
      )}

      {/* Status Toast Alert */}
      {confirmMessage && (
        <div className={`p-4 rounded-2xl text-xs font-semibold flex items-center justify-between shadow-sm animate-in fade-in slide-in-from-bottom-1 duration-300 ${
          confirmMessage.type === 'success' 
            ? 'bg-emerald-50 text-emerald-900 border border-emerald-200' 
            : confirmMessage.type === 'failed'
              ? 'bg-rose-50 text-rose-900 border border-rose-200'
              : confirmMessage.type === 'warning'
                ? 'bg-amber-50 text-amber-900 border border-amber-200'
                : 'bg-orange-50 text-orange-900 border border-orange-200'
        }`}>
          <div className="flex items-center space-x-2.5">
            {confirmMessage.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-rose-600 flex-shrink-0" />
            )}
            <span>{confirmMessage.text}</span>
          </div>

          {referenceCardData && identityStatus === 'VERIFIED' && currentScreen !== 'reference_card' && (
            <button
              onClick={() => setCurrentScreen('reference_card')}
              className="px-3 py-1 bg-white hover:bg-slate-50 text-slate-700 rounded-lg border border-slate-200 text-[11px] font-bold transition shadow-sm cursor-pointer ml-3 flex-shrink-0"
            >
              View Reference Card →
            </button>
          )}
        </div>
      )}

      {/* ===================================================================== */}
      {/* SCREEN A: PRIVACY-SAFE REFERENCE CARD (Shown after full verification) */}
      {/* ===================================================================== */}
      {currentScreen === 'reference_card' && referenceCardData ? (
        <div className="space-y-4">
          <IdentityReferenceCard
            referenceData={referenceCardData}
            onProcessNew={onUploadAnother}
            onRevoked={(refId) => {
              setReferenceCardData(prev => prev ? ({ ...prev, revoked: true, verification_status: 'REVOKED' }) : null);
            }}
          />

          <div className="text-center pt-2">
            <button
              onClick={() => setCurrentScreen('customer_verify')}
              className="text-xs text-indigo-600 font-bold hover:underline cursor-pointer"
            >
              ← Back to Customer Verification Dashboard
            </button>
          </div>
        </div>
      ) : currentScreen === 'customer_verify' ? (

        /* ===================================================================== */
        /* SCREEN B: DEDICATED CUSTOMER IDENTITY VERIFICATION PAGE                */
        /* (Opened ONLY after user clicks "Correct" to confirm OCR details)       */
        /* ===================================================================== */
        <div className="bg-white border border-slate-200 rounded-3xl shadow-sm overflow-hidden space-y-6 p-6 sm:p-8 animate-in fade-in slide-in-from-right-2 duration-300">
          
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-5 border-b border-slate-100">
            <div>
              <div className="flex items-center space-x-2 text-indigo-600 font-bold text-xs uppercase tracking-wider mb-1">
                <UserCheck className="w-4 h-4" />
                <span>Stage 2 of 2</span>
              </div>
              <h2 className="text-xl font-bold text-slate-900 tracking-tight">
                Customer Identity Verification
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Verify applicant presence for <strong>{applicantName}</strong> ({confirmedId || 'Verified Record'})
              </p>
            </div>

            <div>
              {renderIdentityStatusBadge()}
            </div>
          </div>

          {/* Applicant Summary Banner */}
          <div className="p-4 bg-slate-50/80 rounded-2xl border border-slate-200/80 flex items-center justify-between">
            <div className="flex items-center space-x-3.5">
              {portrait_photo ? (
                <div className="relative">
                  <img src={portrait_photo} alt="Portrait" className="w-12 h-14 object-cover rounded-xl border border-slate-200 shadow-sm" />
                  {/* Verified Tick appears ONLY after verification is successful */}
                  {identityStatus === 'VERIFIED' && (
                    <div className="absolute -bottom-1 -right-1 p-0.5 rounded-full bg-emerald-600 text-white shadow">
                      <Check className="w-3 h-3" />
                    </div>
                  )}
                </div>
              ) : (
                <div className="w-12 h-14 bg-slate-200 rounded-xl flex items-center justify-center text-slate-400">
                  <User className="w-5 h-5" />
                </div>
              )}
              <div>
                <h4 className="text-sm font-bold text-slate-900">{applicantName}</h4>
                <div className="flex items-center space-x-2 text-xs text-slate-500 mt-0.5">
                  <span className="font-semibold text-slate-700">{document_type.replace(/_/g, ' ').toUpperCase()}</span>
                  <span>•</span>
                  <span>DOB: {formData?.date_of_birth || 'N/A'}</span>
                </div>
              </div>
            </div>

            <button
              onClick={() => setCurrentScreen('ocr_review')}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-white hover:bg-slate-100 text-slate-700 rounded-xl border border-slate-200 text-xs font-bold transition shadow-sm cursor-pointer"
            >
              <Edit3 className="w-3.5 h-3.5" />
              <span>Review OCR Data</span>
            </button>
          </div>

          {/* TWO MAIN VERIFICATION OPTIONS */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 pt-1">
            
            {/* OPTION 1: LIVE FACE VERIFICATION */}
            <div className="p-6 rounded-3xl border border-indigo-100 bg-gradient-to-b from-indigo-50/40 via-white to-white shadow-sm hover:shadow-md transition flex flex-col justify-between space-y-4">
              <div className="space-y-3">
                <div className="w-10 h-10 rounded-2xl bg-indigo-600 text-white flex items-center justify-center shadow-md shadow-indigo-600/20">
                  <Camera className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900">
                    Option 1: Live Face Verification
                  </h3>
                  <p className="text-xs text-slate-600 leading-relaxed mt-1">
                    Live camera capture with active anti-spoofing liveness check & Deep SFace cosine similarity match against ID portrait.
                  </p>
                </div>
              </div>

              <button
                onClick={() => setIsLiveFaceModalOpen(true)}
                className="w-full inline-flex items-center justify-center space-x-2 py-3 px-5 bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white rounded-2xl text-xs font-bold shadow-md shadow-indigo-600/25 transition cursor-pointer hover:scale-[1.01] active:scale-[0.99]"
              >
                <Scan className="w-4 h-4" />
                <span>
                  {identityStatus === 'VERIFIED' && verificationMethod === 'live_face' 
                    ? 'Re-verify Live Face' 
                    : 'Start Live Face Verification'}
                </span>
              </button>
            </div>

            {/* OPTION 2: UPLOAD ANOTHER ID DOCUMENT */}
            <div className="p-6 rounded-3xl border border-emerald-100 bg-gradient-to-b from-emerald-50/40 via-white to-white shadow-sm hover:shadow-md transition flex flex-col justify-between space-y-4">
              <div className="space-y-3">
                <div className="w-10 h-10 rounded-2xl bg-emerald-600 text-white flex items-center justify-center shadow-md shadow-emerald-600/20">
                  <FileCheck className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900">
                    Option 2: Upload Another ID Document
                  </h3>
                  <p className="text-xs text-slate-600 leading-relaxed mt-1">
                    Upload a complementary ID (Aadhaar / PAN / DL) for fuzzy name, normalized DOB, and biometric portrait cross-verification.
                  </p>
                </div>
              </div>

              <button
                onClick={() => setIsSecondIdModalOpen(true)}
                className="w-full inline-flex items-center justify-center space-x-2 py-3 px-5 bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white rounded-2xl text-xs font-bold shadow-md shadow-emerald-600/25 transition cursor-pointer hover:scale-[1.01] active:scale-[0.99]"
              >
                <FileCheck className="w-4 h-4" />
                <span>
                  {identityStatus === 'VERIFIED' && verificationMethod === 'second_id' 
                    ? 'Re-cross-check Second ID' 
                    : 'Upload Another ID Document'}
                </span>
              </button>
            </div>

          </div>

          {/* Footer Actions */}
          <div className="flex items-center justify-between pt-4 border-t border-slate-100">
            <button
              onClick={() => setCurrentScreen('ocr_review')}
              className="inline-flex items-center space-x-1.5 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-bold transition cursor-pointer"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back to Document Details</span>
            </button>

            {referenceCardData && identityStatus === 'VERIFIED' && (
              <button
                onClick={() => setCurrentScreen('reference_card')}
                className="inline-flex items-center space-x-2 px-6 py-2.5 bg-gradient-to-r from-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600 text-white rounded-xl text-xs font-bold shadow-md shadow-indigo-600/25 transition cursor-pointer hover:scale-[1.02] active:scale-[0.98]"
              >
                <ShieldCheck className="w-4 h-4" />
                <span>View Privacy Reference Card →</span>
              </button>
            )}
          </div>

        </div>

      ) : (

        /* ===================================================================== */
        /* SCREEN C: INITIAL OCR DOCUMENT DETAILS REVIEW                         */
        /* (Shown immediately after document extraction)                         */
        /* ===================================================================== */
        <div className="space-y-6">

          {/* Rejected Alert Banner (Shown when user clicked Wrong) */}
          {currentScreen === 'rejected_review' && (
            <div className="p-4 bg-rose-50 border border-rose-300 rounded-2xl flex items-start justify-between space-x-3 text-xs text-rose-950 shadow-sm animate-in fade-in">
              <div className="flex items-start space-x-2.5">
                <AlertTriangle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-xs font-bold">Document Marked as Incorrect</h4>
                  <p className="text-[11px] text-rose-800 mt-0.5">
                    Extracted details were marked wrong. You can retry with a deep enhancement scan or upload a replacement file.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setCurrentScreen('ocr_review')}
                className="px-2.5 py-1 bg-white hover:bg-slate-50 text-rose-900 border border-rose-200 rounded-lg text-[11px] font-bold cursor-pointer transition shadow-sm flex-shrink-0"
              >
                Edit & Retry
              </button>
            </div>
          )}

          {/* Main Extracted Details Card */}
          <div className="bg-white border border-slate-200/90 rounded-2xl shadow-sm overflow-hidden transition-all duration-200">
            
            {/* Card Header with Integrated Status Badges */}
            <div className="px-6 py-4.5 border-b border-slate-100 bg-gradient-to-r from-slate-50/90 via-slate-50/40 to-white flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-3">
                <div>{getBadge()}</div>
                <h2 className="text-base sm:text-lg font-bold text-slate-900 tracking-tight">
                  {document_type === 'unsupported' 
                    ? 'Verification Declined' 
                    : `${document_type.replace(/_/g, ' ').toUpperCase()} Extracted Details`}
                </h2>
              </div>

              <div className="flex flex-wrap items-center gap-2.5">
                {/* Status Indicator */}
                {confirmationStatus === 'Success' ? (
                  <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-lg text-xs font-mono font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                    <span>{confirmedId || 'OCR Confirmed'}</span>
                  </div>
                ) : confirmationStatus === 'Failed' ? (
                  <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-lg text-xs font-mono font-bold bg-rose-50 text-rose-700 border border-rose-200">
                    <XCircle className="w-3.5 h-3.5 text-rose-600" />
                    <span>{confirmedId || 'Marked Wrong'}</span>
                  </div>
                ) : (
                  <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-lg bg-amber-50 text-amber-800 border border-amber-200 text-xs font-bold shadow-sm">
                    <Clock className="w-3.5 h-3.5 text-amber-600 animate-pulse" />
                    <span>Step 1: Review Details</span>
                  </div>
                )}

                <div className="flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-slate-100 border border-slate-200 text-slate-600 text-[11px] font-semibold">
                  <Lock className="w-3 h-3 text-slate-500" />
                  <span>30-Day Retention</span>
                </div>
              </div>
            </div>

            {/* Card Body */}
            <div className="p-6 space-y-5">

              {/* SECURITY ALERT */}
              {(is_duplicate_or_sample || authenticity_status === "DUPLICATE_COPY") && (
                <div className="p-4 bg-rose-50 border border-rose-300 rounded-xl flex items-start space-x-3 text-xs text-rose-900 shadow-sm">
                  <AlertTriangle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <strong className="block text-xs font-bold text-rose-950 mb-0.5">Duplicate / Sample Detected</strong>
                    <p className="text-[11px] text-rose-800 leading-relaxed">
                      This document contains a watermark and should be rejected for KYC.
                    </p>
                  </div>
                </div>
              )}

              {/* PORTRAIT + FIELDS GRID */}
              {document_type !== 'unsupported' && document_type !== 'pan_back' && (
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">

                  {/* LEFT: Portrait Photo (Clean crop, NO verification tick during OCR review) */}
                  <div className="lg:col-span-4 xl:col-span-3 flex flex-col items-center justify-start p-5 bg-slate-50/80 border border-slate-200/90 rounded-2xl space-y-3 shadow-inner">
                    <div className="w-full flex items-center justify-between text-slate-500">
                      <span className="text-[11px] font-bold uppercase tracking-wider text-slate-600">Extracted Portrait</span>
                      <ImageIcon className="w-3.5 h-3.5 text-slate-400" />
                    </div>
                    {portrait_photo ? (
                      <div className="relative group">
                        <img src={portrait_photo} alt="Portrait"
                          className="w-32 h-40 object-cover rounded-xl border border-slate-200 shadow-sm" />
                        
                        {/* Verified Tick appears ONLY after customer verification is successful */}
                        {identityStatus === 'VERIFIED' ? (
                          <div className="absolute bottom-1.5 right-1.5 px-2 py-0.5 rounded bg-emerald-600 text-[10px] text-white font-bold shadow">
                            ✓ Verified Face
                          </div>
                        ) : null}
                      </div>
                    ) : (
                      <div className="w-32 h-40 bg-slate-100 rounded-xl border-2 border-dashed border-slate-300 flex flex-col items-center justify-center text-slate-400 p-2 text-center">
                        <User className="w-8 h-8 mb-1 opacity-50" />
                        <span className="text-[10px] font-medium">No Face Photo</span>
                      </div>
                    )}
                    <div className="text-[11px] text-center text-slate-500 font-medium">
                      {portrait_photo ? 'Cardholder Photo' : 'Document Details Only'}
                    </div>
                  </div>

                  {/* RIGHT: Editable Fields (Spans 8 cols on lg, 9 on xl) */}
                  <div className="lg:col-span-8 xl:col-span-9 grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-2 2xl:grid-cols-2 gap-3.5">
                    
                    {document_type === 'aadhaar' && (
                      <>
                        <FieldCard icon={User} label="Applicant Name" field="name" placeholder="Name" iconBg={iconBg} />
                        <FieldCard icon={Calendar} label="Date of Birth" field="date_of_birth" placeholder="DD/MM/YYYY" iconBg={iconBg} />
                        <FieldCard icon={User} label="Gender" field="gender" placeholder="Male / Female" iconBg={iconBg} />
                        <FieldCard icon={Hash} label="Aadhaar Number" field="aadhaar_number" placeholder="XXXX XXXX XXXX" iconBg={iconBg} mono />
                      </>
                    )}

                    {document_type === 'aadhaar_back' && (
                      <>
                        <FieldCard icon={User} label="Care Of" field="care_of" placeholder="Guardian Name" iconBg={iconBg} />
                        <FieldCard icon={MapPin} label="Pincode" field="pincode" placeholder="6-Digit" iconBg={iconBg} mono />
                        <div className="sm:col-span-2">
                          <FieldCard icon={MapPin} label="Full Address" field="address" placeholder="Complete Address" iconBg={iconBg} type="textarea" />
                        </div>
                      </>
                    )}

                    {document_type === 'pan' && (
                      <>
                        <FieldCard icon={User} label="Cardholder Name" field="name" placeholder="Name" iconBg={iconBg} />
                        <FieldCard icon={User} label="Father's Name" field="father_name" placeholder="Father's Name" iconBg={iconBg} />
                        <FieldCard icon={Calendar} label="Date of Birth" field="date_of_birth" placeholder="DD/MM/YYYY" iconBg={iconBg} />
                        <FieldCard icon={Hash} label="PAN Number" field="pan_number" placeholder="ABCDE1234F" iconBg={iconBg} mono />
                      </>
                    )}

                    {document_type === 'driving_licence' && (
                      <>
                        <FieldCard icon={Hash} label="DL Number" field="dl_number" placeholder="DL Number" iconBg={iconBg} mono />
                        <FieldCard icon={User} label="Holder Name" field="name" placeholder="Name" iconBg={iconBg} />
                        <FieldCard icon={Calendar} label="Date of Birth" field="date_of_birth" placeholder="DD/MM/YYYY" iconBg={iconBg} />
                        <FieldCard icon={Clock} label="Valid Until" field="valid_until" placeholder="DD/MM/YYYY" iconBg={iconBg} />
                      </>
                    )}

                    {document_type === 'driving_licence_back' && (
                      <>
                        <div className="sm:col-span-2">
                          <div className="group bg-white border border-slate-200 rounded-xl p-3.5 flex items-start space-x-3 hover:shadow-sm transition-all">
                            <div className={`p-1.5 rounded-lg ${iconBg} flex-shrink-0`}><Car className="w-3.5 h-3.5" /></div>
                            <div className="flex-1">
                              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">Vehicle Categories</span>
                              <div className="flex flex-wrap gap-1.5">
                                {data?.vehicle_classes?.length > 0 ? (
                                  data.vehicle_classes.map((vc, i) => (
                                    <span key={i} className="px-2 py-0.5 rounded-md bg-emerald-100 text-emerald-800 font-bold text-[11px] border border-emerald-200">{vc}</span>
                                  ))
                                ) : (
                                  <span className="text-[11px] text-slate-500">LMV / MCWG</span>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                        {data?.address && (
                          <div className="sm:col-span-2">
                            <div className="group bg-white border border-slate-200 rounded-xl p-3.5 flex items-start space-x-3 hover:shadow-sm transition-all">
                              <div className="p-1.5 rounded-lg bg-sky-100 text-sky-600 flex-shrink-0"><MapPin className="w-3.5 h-3.5" /></div>
                              <div className="flex-1">
                                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-0.5">Address</span>
                                <p className="text-[11px] text-slate-800 leading-relaxed font-medium">{data.address}</p>
                              </div>
                            </div>
                          </div>
                        )}
                      </>
                    )}

                  </div>
                </div>
              )}
            </div>

            {/* DATE FOOTER */}
            <div className="px-5 py-3 bg-slate-50/80 border-t border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-1.5">
              <div className="flex items-center space-x-1.5 text-slate-500">
                <CalendarDays className="w-3 h-3" />
                <span className="text-[11px] font-medium">
                  Scanned: <span className="text-slate-700 font-semibold">{currentDateTime}</span>
                </span>
              </div>
              <div className="flex items-center space-x-2.5 text-[10px] text-slate-400">
                <span className="flex items-center space-x-1">
                  <Cpu className="w-2.5 h-2.5" />
                  <span>RapidOCR</span>
                </span>
                {result.ocr_confidence > 0 && (
                  <span className="px-1.5 py-0.5 rounded-full bg-slate-200/80 text-slate-600 font-bold text-[10px]">
                    {result.ocr_confidence.toFixed(1)}%
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* ================================================================= */}
          {/* PRIMARY ACTION BUTTONS (Correct vs Wrong)                         */}
          {/* ================================================================= */}
          
          {/* Flow 1: When reviewing (Not yet marked Wrong) */}
          {currentScreen === 'ocr_review' && (
            <div className="bg-slate-50 border border-slate-200 rounded-2xl p-6 text-center space-y-3">
              <div className="max-w-md mx-auto">
                <h4 className="text-sm font-bold text-slate-900">Are the extracted document details correct?</h4>
                <p className="text-xs text-slate-500 mt-0.5">
                  Confirm accuracy to proceed to Customer Identity Verification.
                </p>
              </div>

              <div className="flex items-center justify-center gap-4 pt-2">
                <button
                  onClick={handleCorrectClick}
                  disabled={isSubmitting}
                  className="group inline-flex items-center space-x-2 py-3 px-8 rounded-2xl bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white font-bold text-xs shadow-md shadow-emerald-600/25 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer hover:scale-[1.02] active:scale-[0.98]"
                >
                  <ThumbsUp className="w-4 h-4" />
                  <span>Correct (Proceed to Verification)</span>
                </button>

                <button
                  onClick={handleWrongClick}
                  disabled={isSubmitting}
                  className="group inline-flex items-center space-x-2 py-3 px-8 rounded-2xl bg-rose-600 hover:bg-rose-500 active:bg-rose-700 text-white font-bold text-xs shadow-md shadow-rose-600/25 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer hover:scale-[1.02] active:scale-[0.98]"
                >
                  <ThumbsDown className="w-4 h-4" />
                  <span>Wrong</span>
                </button>
              </div>
            </div>
          )}

          {/* Flow 2: When user clicked Wrong (Shows 2 clear actions without removing document) */}
          {currentScreen === 'rejected_review' && (
            <div className="bg-white border border-rose-200 rounded-2xl p-6 space-y-4 shadow-sm animate-in slide-in-from-bottom-2 fade-in">
              <div className="text-center">
                <h4 className="text-sm font-bold text-slate-900">Choose Action for Incorrect Document</h4>
                <p className="text-xs text-slate-500 mt-0.5">
                  You can retry scanning with deep visual enhancement or upload a replacement file.
                </p>
              </div>

              <div className="flex items-center justify-center gap-4 pt-1">
                <button
                  onClick={handleRetryClick}
                  disabled={isRetrying || isSubmitting}
                  className="inline-flex items-center space-x-2 py-3 px-6 rounded-2xl bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white font-bold text-xs shadow-md shadow-indigo-600/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer hover:scale-[1.02] active:scale-[0.98]"
                >
                  <RefreshCw className={`w-4 h-4 ${isRetrying ? 'animate-spin' : ''}`} />
                  <span>{isRetrying ? 'Deep Scanning...' : 'Retry Deep Scan'}</span>
                </button>

                <button
                  onClick={onUploadAnother}
                  disabled={isSubmitting}
                  className="inline-flex items-center space-x-2 py-3 px-6 rounded-2xl bg-slate-800 hover:bg-slate-700 active:bg-slate-900 text-white font-bold text-xs shadow-md transition-all cursor-pointer hover:scale-[1.02] active:scale-[0.98]"
                >
                  <Upload className="w-4 h-4" />
                  <span>Upload Replacement Document</span>
                </button>
              </div>
            </div>
          )}

        </div>
      )}

      {/* Live Face Verification Modal */}
      <LiveFaceVerificationModal
        isOpen={isLiveFaceModalOpen}
        onClose={() => setIsLiveFaceModalOpen(false)}
        idPortraitPhoto={portrait_photo}
        applicantName={applicantName}
        onVerificationComplete={handleVerificationComplete}
      />

      {/* Second ID Verification Modal */}
      <SecondIdVerificationModal
        isOpen={isSecondIdModalOpen}
        onClose={() => setIsSecondIdModalOpen(false)}
        primaryDocumentType={document_type}
        primaryData={formData}
        primaryPortrait={portrait_photo}
        onVerificationComplete={handleVerificationComplete}
      />

    </div>
  );
}
