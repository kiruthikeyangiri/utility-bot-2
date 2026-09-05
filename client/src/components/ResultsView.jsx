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
  Award,
  ChevronRight,
  CalendarDays,
  Fingerprint,
  ThumbsUp,
  ThumbsDown
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

  const [formData, setFormData] = useState(data || {});
  const [confirmationStatus, setConfirmationStatus] = useState(initialStatus || 'Pending Confirmation');
  const [confirmedId, setConfirmedId] = useState(initialSeqId || null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [confirmMessage, setConfirmMessage] = useState(null);
  const [showWrongActions, setShowWrongActions] = useState(false);

  useEffect(() => {
    setFormData(data || {});
    setConfirmationStatus(result.status || 'Pending Confirmation');
    setConfirmedId(result.sequential_id || result.id || null);
    setConfirmMessage(null);
    setShowWrongActions(false);
  }, [result]);

  const handleFieldChange = (field, val) => {
    setFormData(prev => ({ ...prev, [field]: val }));
  };

  const handleConfirmAction = async (action) => {
    setIsSubmitting(true);
    try {
      const payload = {
        action: action,
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
      setConfirmationStatus(response.status);
      
      if (action === 'correct') {
        setConfirmMessage({
          type: 'success',
          text: `Verified! ID: ${response.sequential_id || response.id} — Saved to verifications.`
        });
      } else {
        setConfirmMessage({
          type: 'failed',
          text: `Rejected. Audit ID: ${response.sequential_id || response.id} — Stored in failed_verifications.`
        });
      }
    } catch (err) {
      console.error('Confirmation error:', err);
      setConfirmMessage({
        type: 'error',
        text: 'Failed to record. Please try again.'
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleWrongClick = () => {
    handleConfirmAction('wrong');
    setShowWrongActions(true);
  };

  const isDecided = confirmationStatus === 'Success' || confirmationStatus === 'Failed';

  const currentDateTime = new Date().toLocaleString('en-IN', {
    weekday: 'short', year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true
  });

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
    <div className="space-y-4">

      {/* Deep Scan Loading Indicator Banner */}
      {isRetrying && (
        <div className="p-4 bg-gradient-to-r from-indigo-900 to-slate-900 text-white rounded-xl shadow-lg border border-indigo-500/40 flex items-center space-x-3 animate-pulse">
          <RefreshCw className="w-5 h-5 text-indigo-400 animate-spin flex-shrink-0" />
          <div>
            <h4 className="text-xs font-bold text-indigo-200">⚡ Deep Multi-Pass OCR Scan in Progress...</h4>
            <p className="text-[11px] text-slate-300">Applying multi-scale CLAHE, bilateral noise reduction, and re-evaluating text bounding boxes.</p>
          </div>
        </div>
      )}

      {/* ================================================================= */}
      {/* 1. COMPACT STATUS HEADER — No buttons, just status                */}
      {/* ================================================================= */}
      <div className="relative overflow-hidden bg-gradient-to-r from-slate-900 via-slate-800 to-indigo-950 text-white rounded-xl shadow-md border border-slate-700/50">
        <div className="absolute inset-0 opacity-5">
          <div className="absolute top-0 right-0 w-48 h-48 bg-indigo-500 rounded-full blur-3xl translate-x-16 -translate-y-16" />
        </div>
        <div className="relative px-5 py-3.5 flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-lg bg-indigo-500/20 text-indigo-300 border border-indigo-500/25">
              <Fingerprint className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-[13px] font-bold text-white">Audit Confirmation Gateway</h3>
              <p className="text-[10px] text-slate-400">Review details below, then confirm or reject</p>
            </div>
          </div>

          {confirmedId ? (
            <div className={`inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-[11px] font-mono font-bold tracking-wider ${
              confirmationStatus === 'Success' 
                ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30' 
                : 'bg-rose-500/15 text-rose-300 border border-rose-500/30'
            }`}>
              {confirmationStatus === 'Success' ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
              <span>{confirmedId}</span>
            </div>
          ) : (
            <div className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-amber-500/15 text-amber-300 border border-amber-500/25 text-[11px] font-bold">
              <Clock className="w-3 h-3 animate-pulse" />
              <span>Pending</span>
            </div>
          )}
        </div>
      </div>

      {/* ================================================================= */}
      {/* 2. EXTRACTED DETAILS CARD                                          */}
      {/* ================================================================= */}
      <div className="bg-white border border-slate-200/80 rounded-2xl shadow-sm overflow-hidden">
        
        {/* Card Header */}
        <div className="px-5 py-4 border-b border-slate-100 bg-gradient-to-r from-slate-50/80 to-white">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <div className="mb-1.5">{getBadge()}</div>
              <h2 className="text-base font-bold text-slate-900 tracking-tight">
                {document_type === 'unsupported' 
                  ? 'Verification Declined' 
                  : `${document_type.replace(/_/g, ' ').toUpperCase()} — Extracted Details`}
              </h2>
            </div>
            <div className="flex items-center space-x-1 px-2.5 py-1 rounded-md bg-indigo-50 border border-indigo-100 text-indigo-600 text-[10px] font-semibold self-start sm:self-auto">
              <Lock className="w-2.5 h-2.5" />
              <span>30-Day Retention</span>
            </div>
          </div>
        </div>

        {/* Card Body */}
        <div className="p-5 space-y-4">

          {/* SECURITY ALERT */}
          {(is_duplicate_or_sample || authenticity_status === "DUPLICATE_COPY") && (
            <div className="p-3.5 bg-rose-50 border border-rose-300 rounded-xl flex items-start space-x-2.5 text-xs text-rose-900">
              <AlertTriangle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
              <div>
                <strong className="block text-xs font-bold text-rose-950 mb-0.5">⚠️ Duplicate / Sample Detected</strong>
                <p className="text-[11px] text-rose-800 leading-relaxed">
                  This document contains a watermark and should be rejected for KYC.
                </p>
              </div>
            </div>
          )}

          {/* PAN BACK GUIDANCE */}
          {document_type === 'pan_back' && (
            <div className="p-4 bg-amber-50 border border-amber-300 rounded-xl text-amber-900 space-y-2">
              <div className="flex items-center space-x-2 font-bold text-xs">
                <RotateCcw className="w-3.5 h-3.5 text-amber-700" />
                <span>PAN Back Side — Upload Front Side</span>
              </div>
              <p className="text-[11px] text-amber-800">
                Personal details are on the <strong>FRONT side</strong>.
              </p>
              <button onClick={onUploadAnother}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-[11px] font-bold transition cursor-pointer">
                <span>Upload Front</span>
                <ArrowRight className="w-3 h-3" />
              </button>
            </div>
          )}

          {/* PORTRAIT + FIELDS GRID */}
          {document_type !== 'unsupported' && document_type !== 'pan_back' && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">

              {/* LEFT: Portrait Photo */}
              <div className="md:col-span-1 flex flex-col items-center justify-start p-4 bg-slate-50/80 border border-slate-200 rounded-xl space-y-2.5">
                <div className="w-full flex items-center justify-between text-slate-500">
                  <span className="text-[10px] font-bold uppercase tracking-wider">Photo ID</span>
                  <ImageIcon className="w-3 h-3 text-slate-400" />
                </div>
                {portrait_photo ? (
                  <div className="relative group">
                    <img src={portrait_photo} alt="Portrait"
                      className="w-28 h-36 object-cover rounded-lg border-2 border-indigo-200 shadow group-hover:shadow-md transition-shadow" />
                    <div className="absolute bottom-1 right-1 px-1.5 py-0.5 rounded bg-emerald-600/90 text-[9px] text-white font-bold">✓ Face</div>
                  </div>
                ) : images?.original ? (
                  <div className="relative group">
                    <img src={`data:image/jpeg;base64,${images.original}`} alt="Document"
                      className="w-28 h-36 object-cover rounded-lg border-2 border-slate-300 shadow group-hover:shadow-md transition-shadow" />
                    <div className="absolute bottom-1 right-1 px-1.5 py-0.5 rounded bg-slate-700/80 text-[9px] text-white font-bold">📄 Doc</div>
                  </div>
                ) : (
                  <div className="w-28 h-36 bg-slate-200/80 rounded-lg border-2 border-dashed border-slate-300 flex flex-col items-center justify-center text-slate-400 p-2 text-center">
                    <User className="w-7 h-7 mb-1 opacity-50" />
                    <span className="text-[9px] font-medium">No Image</span>
                  </div>
                )}
                <div className="text-[10px] text-center text-slate-500 font-medium">
                  {document_type === 'aadhaar' ? 'Biometric Photo' : document_type.includes('back') ? 'Document Scan' : 'Cardholder ID'}
                </div>
              </div>

              {/* RIGHT: Editable Fields */}
              <div className="md:col-span-3 grid grid-cols-1 sm:grid-cols-2 gap-3">
                
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

        {/* ============================================================= */}
        {/* 3. DATE FOOTER                                                  */}
        {/* ============================================================= */}
        <div className="px-5 py-3 bg-slate-50/80 border-t border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-1.5">
          <div className="flex items-center space-x-1.5 text-slate-500">
            <CalendarDays className="w-3 h-3" />
            <span className="text-[11px] font-medium">
              Scanned: <span className="text-slate-700 font-semibold">{currentDateTime}</span>
            </span>
          </div>
          <div className="flex items-center space-x-2.5 text-[10px] text-slate-400">
            <span className="flex items-center space-x-1">
              <Sparkles className="w-2.5 h-2.5" />
              <span>RapidOCR</span>
            </span>
            {result.ocr_confidence > 0 && (
              <span className="px-1.5 py-0.5 rounded-full bg-slate-200/80 text-slate-600 font-bold text-[10px]">
                {(result.ocr_confidence * 100).toFixed(1)}%
              </span>
            )}
          </div>
        </div>
      </div>

      {/* ================================================================= */}
      {/* 4. ACTION BUTTONS — BELOW THE DETAILS (small & clean)             */}
      {/* ================================================================= */}
      
      {/* Confirmation Toast — show above buttons if exists */}
      {confirmMessage && (
        <div className={`p-3 rounded-xl text-xs font-semibold flex items-center space-x-2 animate-in fade-in slide-in-from-bottom-1 duration-300 ${
          confirmMessage.type === 'success' 
            ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' 
            : confirmMessage.type === 'failed'
              ? 'bg-rose-50 text-rose-800 border border-rose-200'
              : 'bg-orange-50 text-orange-800 border border-orange-200'
        }`}>
          {confirmMessage.type === 'success' ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
          ) : (
            <AlertTriangle className="w-4 h-4 text-rose-600 flex-shrink-0" />
          )}
          <span>{confirmMessage.text}</span>
        </div>
      )}

      {/* 1. Primary Actions: ✓ Correct / ✗ Wrong (Shown before any decision is made) */}
      {confirmationStatus === 'Pending Confirmation' && !showWrongActions && (
        <div className="flex items-center justify-center gap-3 pt-1">
          <button
            onClick={() => handleConfirmAction('correct')}
            disabled={isSubmitting}
            className="group inline-flex items-center space-x-2 py-2.5 px-6 rounded-xl bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white font-semibold text-xs shadow-sm shadow-emerald-600/20 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer hover:shadow-md"
          >
            <ThumbsUp className="w-3.5 h-3.5" />
            <span>Correct</span>
          </button>

          <button
            onClick={handleWrongClick}
            disabled={isSubmitting}
            className="group inline-flex items-center space-x-2 py-2.5 px-6 rounded-xl bg-rose-600 hover:bg-rose-500 active:bg-rose-700 text-white font-semibold text-xs shadow-sm shadow-rose-600/20 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer hover:shadow-md"
          >
            <ThumbsDown className="w-3.5 h-3.5" />
            <span>Wrong</span>
          </button>
        </div>
      )}

      {/* 2. Secondary Actions: Shown when marked as Wrong or status is Failed */}
      {(showWrongActions || confirmationStatus === 'Failed') && (
        <div className="space-y-2.5 pt-1 animate-in slide-in-from-bottom-2 fade-in duration-300">
          <p className="text-[11px] text-slate-500 text-center font-medium">
            Document rejected. Choose next action:
          </p>
          <div className="flex items-center justify-center gap-3">
            <button
              onClick={handleRetryClick}
              disabled={isRetrying || isSubmitting}
              className="inline-flex items-center space-x-2 py-2.5 px-6 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 active:from-indigo-700 active:to-indigo-600 text-white font-bold text-xs shadow-md shadow-indigo-600/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer hover:shadow-lg hover:scale-[1.02] active:scale-[0.98]"
            >
              <RefreshCw className={`w-4 h-4 ${isRetrying ? 'animate-spin' : ''}`} />
              <span>{isRetrying ? 'Deep Scanning...' : 'Retry Scan'}</span>
            </button>

            <button
              onClick={onUploadAnother}
              disabled={isSubmitting}
              className="inline-flex items-center space-x-2 py-2.5 px-6 rounded-xl bg-slate-700 hover:bg-slate-600 active:bg-slate-800 text-white font-bold text-xs shadow-md transition-all cursor-pointer hover:shadow-lg hover:scale-[1.02] active:scale-[0.98]"
            >
              <Upload className="w-4 h-4" />
              <span>Upload New</span>
            </button>
          </div>
        </div>
      )}

      {/* 3. Post-Success Actions: Shown when status is Success */}
      {confirmationStatus === 'Success' && (
        <div className="flex items-center justify-center gap-3 pt-1">
          <button
            onClick={handleRetryClick}
            disabled={isRetrying}
            className="inline-flex items-center space-x-1.5 py-2 px-4 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-[11px] border border-slate-200 transition-all cursor-pointer"
          >
            <RefreshCw className={`w-3 h-3 ${isRetrying ? 'animate-spin' : ''}`} />
            <span>{isRetrying ? 'Scanning...' : 'Re-scan'}</span>
          </button>
          <button
            onClick={onUploadAnother}
            className="inline-flex items-center space-x-1.5 py-2 px-4 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-[11px] border border-slate-200 transition-all cursor-pointer"
          >
            <Upload className="w-3 h-3" />
            <span>New Document</span>
          </button>
        </div>
      )}

    </div>
  );
}
