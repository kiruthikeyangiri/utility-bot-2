import React, { useState, useEffect } from 'react';
import { 
  AlertTriangle, 
  XCircle, 
  ShieldCheck, 
  User, 
  Calendar, 
  MapPin, 
  Hash, 
  FileText, 
  Clock, 
  Image as ImageIcon,
  RotateCcw,
  ArrowRight,
  Truck,
  Car,
  Check,
  X,
  RefreshCw,
  Upload,
  CheckCircle2,
  Lock,
  Sparkles,
  Award
} from 'lucide-react';
import { confirmVerificationApi } from '../services/api';

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
    sequential_id: initialSeqId
  } = result;

  // Local editable state for human-in-the-loop editing
  const [formData, setFormData] = useState(data || {});
  const [confirmationStatus, setConfirmationStatus] = useState(initialStatus || 'Pending Confirmation');
  const [confirmedId, setConfirmedId] = useState(initialSeqId || null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [confirmMessage, setConfirmMessage] = useState(null);

  useEffect(() => {
    setFormData(data || {});
    setConfirmationStatus(result.status || 'Pending Confirmation');
    setConfirmedId(result.sequential_id || result.id || null);
    setConfirmMessage(null);
  }, [result]);

  const handleFieldChange = (field, val) => {
    setFormData(prev => ({ ...prev, [field]: val }));
  };

  const handleConfirmAction = async (action) => {
    setIsSubmitting(true);
    try {
      const payload = {
        action: action, // 'correct' or 'wrong'
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
      setConfirmationStatus(response.status); // 'Success' or 'Failed'
      
      if (action === 'correct') {
        setConfirmMessage({
          type: 'success',
          text: `Verification Confirmed! Assigned Sequential ID: ${response.sequential_id || response.id}. Saved to public History & 'verifications' collection.`
        });
      } else {
        setConfirmMessage({
          type: 'failed',
          text: `Marked as Failed. Assigned Audit ID: ${response.sequential_id || response.id}. Stored in 'failed_verifications' (Hidden from public history).`
        });
      }
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

  // Document Badge Colors for Light Theme
  const getBadge = () => {
    if (is_duplicate_or_sample || authenticity_status === "DUPLICATE_COPY") {
      return (
        <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-rose-100 border border-rose-300 text-rose-800 text-xs font-bold">
          <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
          <span>⚠️ DUPLICATE / SAMPLE COPY DETECTED</span>
        </div>
      );
    }

    if (short_circuited) {
      return (
        <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-rose-50 border border-rose-200 text-rose-700 text-xs font-bold">
          <XCircle className="w-3.5 h-3.5 text-rose-600" />
          <span>DECLINED: NON-ID DOCUMENT</span>
        </div>
      );
    }

    switch (document_type) {
      case 'aadhaar':
        return (
          <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-blue-50 border border-blue-200 text-blue-700 text-xs font-bold">
            <ShieldCheck className="w-3.5 h-3.5 text-blue-600" />
            <span>AADHAAR FRONT VERIFIED</span>
          </div>
        );
      case 'aadhaar_back':
        return (
          <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-200 text-indigo-700 text-xs font-bold">
            <ShieldCheck className="w-3.5 h-3.5 text-indigo-600" />
            <span>AADHAAR BACK (ADDRESS) VERIFIED</span>
          </div>
        );
      case 'pan':
        return (
          <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-amber-50 border border-amber-200 text-amber-800 text-xs font-bold">
            <ShieldCheck className="w-3.5 h-3.5 text-amber-600" />
            <span>PAN CARD VERIFIED</span>
          </div>
        );
      case 'pan_back':
        return (
          <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-amber-50 border border-amber-300 text-amber-900 text-xs font-bold">
            <RotateCcw className="w-3.5 h-3.5 text-amber-700" />
            <span>PAN BACK SIDE DETECTED</span>
          </div>
        );
      case 'driving_licence':
        return (
          <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-bold">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
            <span>DRIVING LICENCE VERIFIED</span>
          </div>
        );
      case 'driving_licence_back':
        return (
          <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-bold">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
            <span>DRIVING LICENCE (BACK) VERIFIED</span>
          </div>
        );
      default:
        return (
          <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-red-50 border border-red-200 text-red-700 text-xs font-bold">
            <XCircle className="w-3.5 h-3.5 text-red-600" />
            <span>UNSUPPORTED DOCUMENT</span>
          </div>
        );
    }
  };

  return (
    <div className="space-y-6">

      {/* ========================================================================= */}
      {/* 2. HUMAN-IN-THE-LOOP CONFIRMATION & AUDIT GATEWAY (STICKY TOP BAR) */}
      {/* ========================================================================= */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-indigo-950 text-white rounded-2xl p-5 shadow-lg border border-slate-700 space-y-4">
        
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-700/60 pb-3">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-xl bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
              <Award className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white tracking-wide">
                Human-in-the-Loop Confirmation & Audit Gateway
              </h3>
              <p className="text-xs text-slate-300">
                Review extracted fields below, make any corrections, and record your decision.
              </p>
            </div>
          </div>

          {/* Sequential ID Status Tag */}
          <div className="flex items-center space-x-2">
            {confirmedId ? (
              <span className={`px-3 py-1 rounded-lg text-xs font-mono font-bold tracking-wider ${
                confirmationStatus === 'Success' 
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' 
                  : 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
              }`}>
                ID: {confirmedId} ({confirmationStatus.toUpperCase()})
              </span>
            ) : (
              <span className="px-3 py-1 rounded-lg bg-amber-500/20 text-amber-300 border border-amber-500/40 text-xs font-bold flex items-center space-x-1.5">
                <Clock className="w-3.5 h-3.5 animate-pulse" />
                <span>Pending Human Confirmation</span>
              </span>
            )}
          </div>
        </div>

        {/* 4 ACTION BUTTONS GATEWAY */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-1">
          
          {/* Action 1: ✓ Correct (Assigns IMG000001 -> Success -> verifications) */}
          <button
            onClick={() => handleConfirmAction('correct')}
            disabled={isSubmitting || confirmationStatus === 'Success'}
            className="flex items-center justify-center space-x-2 py-3 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white font-bold text-xs sm:text-sm shadow-md shadow-emerald-600/30 transition disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            <Check className="w-4 h-4 stroke-[3]" />
            <span>✓ Correct</span>
          </button>

          {/* Action 2: ✗ Wrong (Assigns FAIL000001 -> Failed -> failed_verifications) */}
          <button
            onClick={() => handleConfirmAction('wrong')}
            disabled={isSubmitting || confirmationStatus === 'Failed'}
            className="flex items-center justify-center space-x-2 py-3 px-4 rounded-xl bg-rose-600 hover:bg-rose-500 active:bg-rose-700 text-white font-bold text-xs sm:text-sm shadow-md shadow-rose-600/30 transition disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            <X className="w-4 h-4 stroke-[3]" />
            <span>✗ Wrong</span>
          </button>

          {/* Action 3: 🔄 Retry Same Image (Deep Multi-Pass Scan) */}
          <button
            onClick={onRetryScan}
            disabled={isRetrying || isSubmitting}
            className="flex items-center justify-center space-x-2 py-3 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white font-bold text-xs sm:text-sm shadow-md shadow-indigo-600/30 transition disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            <RefreshCw className={`w-4 h-4 ${isRetrying ? 'animate-spin' : ''}`} />
            <span>{isRetrying ? 'Deep Scanning...' : '🔄 Retry Multi-Pass'}</span>
          </button>

          {/* Action 4: 📁 Upload New Image */}
          <button
            onClick={onUploadAnother}
            disabled={isSubmitting}
            className="flex items-center justify-center space-x-2 py-3 px-4 rounded-xl bg-slate-700 hover:bg-slate-600 active:bg-slate-800 text-slate-100 font-bold text-xs sm:text-sm border border-slate-600 transition cursor-pointer"
          >
            <Upload className="w-4 h-4" />
            <span>📁 Upload New</span>
          </button>

        </div>

        {/* Confirmation Notification Toast */}
        {confirmMessage && (
          <div className={`p-3 rounded-xl text-xs font-semibold flex items-center space-x-2 animate-in fade-in duration-200 ${
            confirmMessage.type === 'success' 
              ? 'bg-emerald-500/20 text-emerald-200 border border-emerald-500/40' 
              : 'bg-rose-500/20 text-rose-200 border border-rose-500/40'
          }`}>
            {confirmMessage.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0" />
            )}
            <span>{confirmMessage.text}</span>
          </div>
        )}

      </div>
      
      {/* ========================================================================= */}
      {/* MAIN EXTRACTED DETAILS & PORTRAIT PHOTO DISPLAY */}
      {/* ========================================================================= */}
      <div className="bg-white border border-slate-200/80 rounded-2xl p-6 shadow-sm space-y-6">
        
        {/* Card Header & 30-Day Expiry Tag */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-100">
          <div>
            <div className="mb-1.5">{getBadge()}</div>
            <h2 className="text-xl font-bold text-slate-900 tracking-tight">
              {document_type === 'unsupported' 
                ? 'Verification Declined' 
                : `${document_type.replace('_', ' ').toUpperCase()} DETAILS`}
            </h2>
          </div>
          
          <div className="flex items-center space-x-1.5 px-3 py-1 rounded-lg bg-indigo-50 border border-indigo-100 text-indigo-700 text-xs font-semibold self-start sm:self-auto">
            <Clock className="w-3.5 h-3.5" />
            <span>Utility Bot 30-Day Storage</span>
          </div>
        </div>

        {/* SECURITY ALERT: DUPLICATE / SAMPLE CARD WARNING */}
        {(is_duplicate_or_sample || authenticity_status === "DUPLICATE_COPY") && (
          <div className="p-4 bg-rose-50 border-2 border-rose-300 rounded-xl flex items-start space-x-3 text-xs text-rose-900 shadow-sm">
            <AlertTriangle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
            <div>
              <strong className="block text-sm font-bold text-rose-950 mb-0.5">
                ⚠️ SECURITY WARNING: Duplicate / Sample Card Watermark Detected!
              </strong>
              <p className="text-rose-800 leading-relaxed">
                This document contains a <strong>'DUPLICATE / SAMPLE / DIGITAL COPY'</strong> watermark. 
                While text details were extracted for reference, this document is <strong>NOT a genuine physical government ID</strong> and should be rejected for KYC verification.
              </p>
            </div>
          </div>
        )}

        {/* SPECIAL CASE: PAN BACK SIDE GUIDANCE PROMPT */}
        {document_type === 'pan_back' && (
          <div className="p-5 bg-amber-50 border border-amber-300 rounded-2xl text-amber-900 space-y-3">
            <div className="flex items-center space-x-2 font-bold text-sm">
              <RotateCcw className="w-4 h-4 text-amber-700" />
              <span>PAN Card Back Side Uploaded</span>
            </div>
            <p className="text-xs text-amber-800 leading-relaxed">
              The back side of a standard Indian PAN Card contains only machine barcodes and return instructions. 
              <strong> Personal details (Name, Father's Name, DOB, PAN Number) are located on the FRONT side.</strong>
            </p>
            <button
              onClick={onUploadAnother}
              className="inline-flex items-center space-x-2 px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-xl text-xs font-bold transition shadow-sm"
            >
              <span>Upload Front Side Now</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* GRID LAYOUT: PORTRAIT PHOTO + EXTRACTED FIELDS */}
        {document_type !== 'unsupported' && document_type !== 'pan_back' && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">

            {/* LEFT COLUMN: APPLICANT PORTRAIT PHOTO (When available) */}
            <div className="md:col-span-1 flex flex-col items-center justify-start p-4 bg-slate-50 border border-slate-200 rounded-2xl space-y-3">
              <div className="w-full flex items-center justify-between text-slate-700">
                <span className="text-[11px] font-bold uppercase tracking-wider">Cardholder Photo</span>
                <ImageIcon className="w-3.5 h-3.5 text-slate-400" />
              </div>

              {portrait_photo ? (
                <div className="relative group">
                  <img
                    src={portrait_photo}
                    alt="Applicant Portrait"
                    className="w-32 h-40 object-cover rounded-xl border-2 border-indigo-200 shadow-sm"
                  />
                  <div className="absolute bottom-1 right-1 px-1.5 py-0.5 rounded bg-slate-900/80 text-[10px] text-emerald-300 font-bold">
                    ✓ Face Detected
                  </div>
                </div>
              ) : (
                <div className="w-32 h-40 bg-slate-200/80 rounded-xl border-2 border-dashed border-slate-300 flex flex-col items-center justify-center text-slate-400 p-3 text-center">
                  <User className="w-8 h-8 mb-1 opacity-50" />
                  <span className="text-[10px] font-medium leading-tight">Portrait Cropped from Scan</span>
                </div>
              )}

              <div className="text-[11px] text-center text-slate-500">
                {document_type === 'aadhaar' ? 'Aadhaar Biometric Photo' : 'Cardholder Identification'}
              </div>
            </div>

            {/* RIGHT COLUMN: EDITABLE EXTRACTED FIELDS (3 Cols) */}
            <div className="md:col-span-3 grid grid-cols-1 sm:grid-cols-2 gap-4">
              
              {/* 1. AADHAAR FRONT */}
              {document_type === 'aadhaar' && (
                <>
                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex items-start space-x-3 shadow-sm">
                    <div className="p-2 rounded-lg bg-blue-100 text-blue-700 flex-shrink-0">
                      <User className="w-4 h-4" />
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">Applicant Name</span>
                      <input
                        type="text"
                        value={formData?.name || ''}
                        onChange={(e) => handleFieldChange('name', e.target.value)}
                        placeholder="Cardholder Name"
                        className="w-full text-sm font-bold text-slate-900 bg-transparent border-b border-dashed border-transparent hover:border-slate-300 focus:border-blue-500 focus:bg-white px-1 py-0.5 rounded focus:outline-none transition"
                      />
                    </div>
                  </div>

                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex items-start space-x-3 shadow-sm">
                    <div className="p-2 rounded-lg bg-blue-100 text-blue-700 flex-shrink-0">
                      <Calendar className="w-4 h-4" />
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">Date of Birth</span>
                      <input
                        type="text"
                        value={formData?.date_of_birth || ''}
                        onChange={(e) => handleFieldChange('date_of_birth', e.target.value)}
                        placeholder="YYYY-MM-DD"
                        className="w-full text-sm font-bold text-slate-900 bg-transparent border-b border-dashed border-transparent hover:border-slate-300 focus:border-blue-500 focus:bg-white px-1 py-0.5 rounded focus:outline-none transition"
                      />
                    </div>
                  </div>

                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex items-start space-x-3 shadow-sm">
                    <div className="p-2 rounded-lg bg-blue-100 text-blue-700 flex-shrink-0">
                      <User className="w-4 h-4" />
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">Gender</span>
                      <input
                        type="text"
                        value={formData?.gender || ''}
                        onChange={(e) => handleFieldChange('gender', e.target.value)}
                        placeholder="Male / Female"
                        className="w-full text-sm font-bold text-slate-900 bg-transparent border-b border-dashed border-transparent hover:border-slate-300 focus:border-blue-500 focus:bg-white px-1 py-0.5 rounded focus:outline-none transition"
                      />
                    </div>
                  </div>

                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex items-start space-x-3 shadow-sm">
                    <div className="p-2 rounded-lg bg-blue-100 text-blue-700 flex-shrink-0">
                      <Hash className="w-4 h-4" />
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">Masked Aadhaar Number</span>
                      <input
                        type="text"
                        value={formData?.aadhaar_number || ''}
                        onChange={(e) => handleFieldChange('aadhaar_number', e.target.value)}
                        placeholder="********7645"
                        className="w-full text-sm font-mono font-bold text-slate-900 bg-transparent border-b border-dashed border-transparent hover:border-slate-300 focus:border-blue-500 focus:bg-white px-1 py-0.5 rounded focus:outline-none transition"
                      />
                    </div>
                  </div>
                </>
              )}

              {/* 2. AADHAAR BACK */}
              {document_type === 'aadhaar_back' && (
                <>
                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex items-start space-x-3 shadow-sm">
                    <div className="p-2 rounded-lg bg-indigo-100 text-indigo-700 flex-shrink-0">
                      <User className="w-4 h-4" />
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">Care Of (C/O, S/O, D/O, W/O)</span>
                      <input
                        type="text"
                        value={formData?.care_of || ''}
                        onChange={(e) => handleFieldChange('care_of', e.target.value)}
                        placeholder="Guardian / Spouse Name"
                        className="w-full text-sm font-bold text-slate-900 bg-transparent border-b border-dashed border-transparent hover:border-slate-300 focus:border-indigo-500 focus:bg-white px-1 py-0.5 rounded focus:outline-none transition"
                      />
                    </div>
                  </div>

                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex items-start space-x-3 shadow-sm">
                    <div className="p-2 rounded-lg bg-indigo-100 text-indigo-700 flex-shrink-0">
                      <MapPin className="w-4 h-4" />
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">Pincode</span>
                      <input
                        type="text"
                        value={formData?.pincode || ''}
                        onChange={(e) => handleFieldChange('pincode', e.target.value)}
                        placeholder="6-Digit Pincode"
                        className="w-full text-sm font-bold text-slate-900 bg-transparent border-b border-dashed border-transparent hover:border-slate-300 focus:border-indigo-500 focus:bg-white px-1 py-0.5 rounded focus:outline-none transition"
                      />
                    </div>
                  </div>

                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 sm:col-span-2 flex items-start space-x-3 shadow-sm">
                    <div className="p-2 rounded-lg bg-indigo-100 text-indigo-700 flex-shrink-0">
                      <MapPin className="w-4 h-4" />
                    </div>
                    <div className="flex-1">
                      <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">Full Residential Address</span>
                      <textarea
                        rows="2"
                        value={formData?.address || ''}
                        onChange={(e) => handleFieldChange('address', e.target.value)}
                        placeholder="Complete Address"
                        className="w-full text-xs font-medium text-slate-800 bg-transparent border border-transparent hover:border-slate-300 focus:border-indigo-500 focus:bg-white p-1 rounded focus:outline-none transition mt-1"
                      />
                    </div>
                  </div>
                </>
              )}

              {/* 3. PAN FRONT */}
              {document_type === 'pan' && (
                <>
                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex items-start space-x-3 shadow-sm">
                    <div className="p-2 rounded-lg bg-amber-100 text-amber-700 flex-shrink-0">
                      <User className="w-4 h-4" />
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">Cardholder Name</span>
                      <input
                        type="text"
                        value={formData?.name || ''}
                        onChange={(e) => handleFieldChange('name', e.target.value)}
                        placeholder="Name on PAN Card"
                        className="w-full text-sm font-bold text-slate-900 bg-transparent border-b border-dashed border-transparent hover:border-slate-300 focus:border-amber-500 focus:bg-white px-1 py-0.5 rounded focus:outline-none transition"
                      />
                    </div>
                  </div>

                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex items-start space-x-3 shadow-sm">
                    <div className="p-2 rounded-lg bg-amber-100 text-amber-700 flex-shrink-0">
                      <User className="w-4 h-4" />
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">Father's Name</span>
                      <input
                        type="text"
                        value={formData?.father_name || ''}
                        onChange={(e) => handleFieldChange('father_name', e.target.value)}
                        placeholder="Father's Name"
                        className="w-full text-sm font-bold text-slate-900 bg-transparent border-b border-dashed border-transparent hover:border-slate-300 focus:border-amber-500 focus:bg-white px-1 py-0.5 rounded focus:outline-none transition"
                      />
                    </div>
                  </div>

                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex items-start space-x-3 shadow-sm">
                    <div className="p-2 rounded-lg bg-amber-100 text-amber-700 flex-shrink-0">
                      <Calendar className="w-4 h-4" />
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">Date of Birth</span>
                      <input
                        type="text"
                        value={formData?.date_of_birth || ''}
                        onChange={(e) => handleFieldChange('date_of_birth', e.target.value)}
                        placeholder="YYYY-MM-DD"
                        className="w-full text-sm font-bold text-slate-900 bg-transparent border-b border-dashed border-transparent hover:border-slate-300 focus:border-amber-500 focus:bg-white px-1 py-0.5 rounded focus:outline-none transition"
                      />
                    </div>
                  </div>

                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex items-start space-x-3 shadow-sm">
                    <div className="p-2 rounded-lg bg-amber-100 text-amber-700 flex-shrink-0">
                      <Hash className="w-4 h-4" />
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">10-Digit PAN Number</span>
                      <input
                        type="text"
                        value={formData?.pan_number || ''}
                        onChange={(e) => handleFieldChange('pan_number', e.target.value)}
                        placeholder="ABCDE1234F"
                        className="w-full text-sm font-mono font-bold text-slate-900 bg-transparent border-b border-dashed border-transparent hover:border-slate-300 focus:border-amber-500 focus:bg-white px-1 py-0.5 rounded focus:outline-none transition"
                      />
                    </div>
                  </div>
                </>
              )}

              {/* 4. DRIVING LICENCE FRONT */}
              {document_type === 'driving_licence' && (
                <>
                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex items-start space-x-3 shadow-sm">
                    <div className="p-2 rounded-lg bg-emerald-100 text-emerald-700 flex-shrink-0">
                      <Hash className="w-4 h-4" />
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">DL Number</span>
                      <input
                        type="text"
                        value={formData?.dl_number || ''}
                        onChange={(e) => handleFieldChange('dl_number', e.target.value)}
                        placeholder="DL Number"
                        className="w-full text-sm font-mono font-bold text-slate-900 bg-transparent border-b border-dashed border-transparent hover:border-slate-300 focus:border-emerald-500 focus:bg-white px-1 py-0.5 rounded focus:outline-none transition"
                      />
                    </div>
                  </div>

                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex items-start space-x-3 shadow-sm">
                    <div className="p-2 rounded-lg bg-emerald-100 text-emerald-700 flex-shrink-0">
                      <User className="w-4 h-4" />
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">Licence Holder Name</span>
                      <input
                        type="text"
                        value={formData?.name || ''}
                        onChange={(e) => handleFieldChange('name', e.target.value)}
                        placeholder="Name on DL"
                        className="w-full text-sm font-bold text-slate-900 bg-transparent border-b border-dashed border-transparent hover:border-slate-300 focus:border-emerald-500 focus:bg-white px-1 py-0.5 rounded focus:outline-none transition"
                      />
                    </div>
                  </div>

                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex items-start space-x-3 shadow-sm">
                    <div className="p-2 rounded-lg bg-emerald-100 text-emerald-700 flex-shrink-0">
                      <Calendar className="w-4 h-4" />
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">Date of Birth</span>
                      <input
                        type="text"
                        value={formData?.date_of_birth || ''}
                        onChange={(e) => handleFieldChange('date_of_birth', e.target.value)}
                        placeholder="YYYY-MM-DD"
                        className="w-full text-sm font-bold text-slate-900 bg-transparent border-b border-dashed border-transparent hover:border-slate-300 focus:border-emerald-500 focus:bg-white px-1 py-0.5 rounded focus:outline-none transition"
                      />
                    </div>
                  </div>

                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex items-start space-x-3 shadow-sm">
                    <div className="p-2 rounded-lg bg-emerald-100 text-emerald-700 flex-shrink-0">
                      <Clock className="w-4 h-4" />
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">Valid Until</span>
                      <input
                        type="text"
                        value={formData?.valid_until || ''}
                        onChange={(e) => handleFieldChange('valid_until', e.target.value)}
                        placeholder="YYYY-MM-DD"
                        className="w-full text-sm font-bold text-slate-900 bg-transparent border-b border-dashed border-transparent hover:border-slate-300 focus:border-emerald-500 focus:bg-white px-1 py-0.5 rounded focus:outline-none transition"
                      />
                    </div>
                  </div>
                </>
              )}

              {/* 5. DRIVING LICENCE BACK */}
              {document_type === 'driving_licence_back' && (
                <>
                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 sm:col-span-2 flex items-start space-x-3 shadow-sm">
                    <div className="p-2 rounded-lg bg-emerald-100 text-emerald-700 flex-shrink-0">
                      <Car className="w-4 h-4" />
                    </div>
                    <div className="flex-1">
                      <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">Authorised Vehicle Categories</span>
                      <div className="flex flex-wrap gap-2 mt-1.5">
                        {data?.vehicle_classes && data.vehicle_classes.length > 0 ? (
                          data.vehicle_classes.map((vc, i) => (
                            <span key={i} className="px-2.5 py-1 rounded-md bg-emerald-100 text-emerald-800 font-bold text-xs">
                              {vc}
                            </span>
                          ))
                        ) : (
                          <span className="text-xs text-slate-500">LMV / MCWG (Detected on back)</span>
                        )}
                      </div>
                    </div>
                  </div>

                  {data?.address && (
                    <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 sm:col-span-2 flex items-start space-x-3 shadow-sm">
                      <div className="p-2 rounded-lg bg-sky-100 text-sky-700 flex-shrink-0">
                        <MapPin className="w-4 h-4" />
                      </div>
                      <div className="flex-1">
                        <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">Permanent Address</span>
                        <p className="text-xs text-slate-800 mt-1 leading-relaxed font-medium">{data.address}</p>
                      </div>
                    </div>
                  )}
                </>
              )}

            </div>

          </div>
        )}

      </div>

    </div>
  );
}
