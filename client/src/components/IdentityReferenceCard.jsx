import React, { useState } from 'react';
import { 
  ShieldCheck, 
  QrCode, 
  Lock, 
  Printer, 
  Ban, 
  RotateCcw, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  ExternalLink,
  User,
  Fingerprint,
  Calendar,
  Eye,
  Check
} from 'lucide-react';
import { revokeReferenceApi } from '../services/api';

export default function IdentityReferenceCard({ referenceData, onProcessNew, onRevoked }) {
  const [isRevoking, setIsRevoking] = useState(false);
  const [isRevoked, setIsRevoked] = useState(referenceData?.revoked || false);
  const [showQrModal, setShowQrModal] = useState(false);
  const [showVerifyModal, setShowVerifyModal] = useState(false);
  const [revokeSuccess, setRevokeSuccess] = useState(false);

  if (!referenceData) return null;

  const {
    reference_id,
    verification_id,
    document_type_display,
    name,
    masked_number,
    photo,
    verification_status,
    created_at,
    qr_code_image
  } = referenceData;

  const handleRevoke = async () => {
    if (!window.confirm(`Are you sure you want to REVOKE Reference ID ${reference_id}? This reference will immediately become invalid and can no longer be used for verification.`)) {
      return;
    }

    setIsRevoking(true);
    try {
      await revokeReferenceApi(reference_id);
      setIsRevoked(true);
      setRevokeSuccess(true);
      if (onRevoked) onRevoked(reference_id);
    } catch (err) {
      console.error('Revocation failed:', err);
      alert('Failed to revoke reference. Please try again.');
    } finally {
      setIsRevoking(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const formattedDate = created_at ? new Date(created_at).toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric'
  }) : 'Today';

  return (
    <div className="space-y-6 animate-in fade-in-50 duration-300">

      {/* Revocation Alert Banner */}
      {isRevoked && (
        <div className="p-4 bg-rose-50 border-2 border-rose-300 rounded-2xl flex items-center space-x-3 text-rose-900 shadow-sm">
          <AlertTriangle className="w-5 h-5 text-rose-600 flex-shrink-0" />
          <div className="flex-1">
            <h4 className="text-sm font-bold text-rose-950">REFERENCE CARD REVOKED</h4>
            <p className="text-xs text-rose-800">
              Reference ID <strong>{reference_id}</strong> is marked invalid. Scans will be rejected.
            </p>
          </div>
          <span className="px-2.5 py-1 rounded-md bg-rose-600 text-white font-bold text-xs uppercase tracking-wider">
            Revoked
          </span>
        </div>
      )}

      {/* ================================================================= */}
      {/* 1. PHYSICAL / DIGITAL IDENTITY REFERENCE CARD (LIGHT THEME)        */}
      {/* ================================================================= */}
      <div className="max-w-xl mx-auto bg-white text-slate-900 rounded-3xl p-6 sm:p-8 shadow-xl shadow-slate-200/60 border border-slate-200/90 relative overflow-hidden transition-all">
        
        {/* Subtle background ambient gradients */}
        <div className="absolute top-0 right-0 w-72 h-72 bg-gradient-to-br from-indigo-50/60 to-transparent rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-0 w-72 h-72 bg-gradient-to-tr from-sky-50/60 to-transparent rounded-full blur-3xl pointer-events-none" />

        {/* Card Content */}
        <div className="space-y-6 relative">

          {/* Card Header */}
          <div className="flex items-center justify-between border-b border-slate-100 pb-4">
            <div className="flex items-center space-x-2.5">
              <div className="p-2 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-100 shadow-sm">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-xs font-black tracking-widest uppercase text-slate-900">IDENTITY REFERENCE</h3>
                <p className="text-[10px] text-slate-500 font-medium">Privacy-Safe Verification Token</p>
              </div>
            </div>

            {/* Verification Status Badge */}
            <div className={`inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-full text-[11px] font-bold tracking-wide border shadow-sm ${
              isRevoked 
                ? 'bg-rose-50 text-rose-700 border-rose-200' 
                : 'bg-emerald-50 text-emerald-800 border border-emerald-200'
            }`}>
              {isRevoked ? <XCircle className="w-3.5 h-3.5 text-rose-600" /> : <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />}
              <span>{isRevoked ? 'REVOKED' : '✓ DETAILS CONFIRMED'}</span>
            </div>
          </div>

          {/* Card Middle: Photo + Essential Details */}
          <div className="grid grid-cols-1 sm:grid-cols-12 gap-5 items-center">

            {/* Left: Protected Photo Frame */}
            <div className="sm:col-span-4 flex flex-col items-center justify-center">
              <div className="relative group">
                {photo ? (
                  <img
                    src={photo}
                    alt="Applicant"
                    className="w-28 h-36 object-cover rounded-2xl border-2 border-indigo-100 shadow-md group-hover:shadow-lg transition-shadow"
                  />
                ) : (
                  <div className="w-28 h-36 bg-slate-100 rounded-2xl border-2 border-dashed border-slate-200 flex flex-col items-center justify-center text-slate-400">
                    <User className="w-8 h-8 opacity-40 mb-1" />
                    <span className="text-[10px] font-medium">Photo Verified</span>
                  </div>
                )}
                <div className="absolute -bottom-2 inset-x-0 flex justify-center">
                  <span className="px-2.5 py-0.5 rounded-full bg-indigo-600 text-white text-[9px] font-bold tracking-wider uppercase shadow-md shadow-indigo-600/20">
                    Verified Face
                  </span>
                </div>
              </div>
            </div>

            {/* Right: Key Confirmed Identity Details */}
            <div className="sm:col-span-8 space-y-3 pl-0 sm:pl-2">
              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-0.5">Full Name</span>
                <p className="text-base font-extrabold text-slate-900 tracking-tight truncate">{name}</p>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-0.5">ID Type</span>
                  <p className="text-xs font-bold text-indigo-700 bg-indigo-50/80 px-2 py-0.5 rounded-md border border-indigo-100 inline-block">{document_type_display}</p>
                </div>
                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-0.5">Confirmed On</span>
                  <p className="text-xs font-semibold text-slate-700">{formattedDate}</p>
                </div>
              </div>

              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                  {document_type_display} Number (Masked)
                </span>
                <p className="text-xs font-mono font-bold tracking-widest text-emerald-800 bg-emerald-50/90 px-3 py-1.5 rounded-xl border border-emerald-200 shadow-sm inline-block">
                  {masked_number}
                </p>
              </div>
            </div>

          </div>

          {/* Card Lower Section: Reference ID & QR Code Box */}
          <div className="bg-gradient-to-r from-slate-50 via-indigo-50/30 to-slate-50 border border-slate-200/90 rounded-2xl p-4.5 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-sm">
            
            <div className="space-y-1 text-center sm:text-left">
              <span className="text-[10px] font-bold text-indigo-700 uppercase tracking-wider block">Privacy Reference ID</span>
              <p className="text-sm sm:text-base font-mono font-black tracking-wider text-slate-900 select-all">
                {reference_id}
              </p>
              <div className="flex items-center space-x-2 text-[10px] text-slate-500 justify-center sm:justify-start pt-0.5">
                <Lock className="w-3 h-3 text-slate-400" />
                <span>Internal Ref: <strong className="text-slate-700 font-semibold">{verification_id}</strong></span>
              </div>
            </div>

            {/* QR Code Trigger Thumbnail */}
            {qr_code_image && (
              <button
                onClick={() => setShowQrModal(true)}
                className="group relative p-2 rounded-2xl bg-white hover:bg-slate-50 transition-all border border-slate-200/90 shadow-sm hover:shadow-md flex-shrink-0 cursor-pointer"
                title="Click to expand QR code"
              >
                <img
                  src={qr_code_image}
                  alt="Reference QR Token"
                  className="w-16 h-16 object-contain"
                />
                <div className="absolute inset-0 bg-slate-900/60 opacity-0 group-hover:opacity-100 transition rounded-2xl flex items-center justify-center text-white text-[10px] font-bold">
                  <Eye className="w-3.5 h-3.5 mr-1" /> View
                </div>
              </button>
            )}

          </div>

          {/* Privacy Guarantee Footer Note */}
          <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[10px] text-slate-500">
            <span className="flex items-center space-x-1.5">
              <Lock className="w-3 h-3 text-emerald-600" />
              <span>Original ID Document: <strong className="text-slate-700 font-semibold">NOT DISPLAYED</strong></span>
            </span>
            <span className="font-semibold text-slate-400">Tamper-Protected</span>
          </div>

        </div>
      </div>

      {/* ================================================================= */}
      {/* 2. CARD ACTION CONTROLS                                           */}
      {/* ================================================================= */}
      <div className="max-w-xl mx-auto flex flex-wrap items-center justify-center gap-3 pt-2">
        
        {/* Verify QR / Preview Verification Button */}
        <button
          onClick={() => setShowVerifyModal(true)}
          className="inline-flex items-center space-x-2 py-2.5 px-4 rounded-xl bg-white hover:bg-slate-100 text-slate-800 font-bold text-xs border border-slate-200 shadow-sm transition cursor-pointer hover:shadow-md"
        >
          <QrCode className="w-3.5 h-3.5 text-indigo-600" />
          <span>Simulate QR Scan</span>
        </button>

        {/* Print / Download Button */}
        <button
          onClick={handlePrint}
          className="inline-flex items-center space-x-2 py-2.5 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-bold text-xs shadow-sm transition cursor-pointer"
        >
          <Printer className="w-3.5 h-3.5 text-slate-300" />
          <span>Print / Save Card</span>
        </button>

        {/* Revoke Button */}
        {!isRevoked && (
          <button
            onClick={handleRevoke}
            disabled={isRevoking}
            className="inline-flex items-center space-x-2 py-2.5 px-4 rounded-xl bg-rose-50 hover:bg-rose-100 text-rose-700 font-bold text-xs border border-rose-200 transition cursor-pointer disabled:opacity-50"
          >
            <Ban className="w-3.5 h-3.5 text-rose-600" />
            <span>{isRevoking ? 'Revoking...' : 'Revoke Reference'}</span>
          </button>
        )}

        {/* Process New Document */}
        <button
          onClick={onProcessNew}
          className="inline-flex items-center space-x-2 py-2.5 px-5 rounded-xl bg-gradient-to-r from-sky-600 to-indigo-600 hover:from-sky-500 hover:to-indigo-500 text-white font-bold text-xs shadow-md transition cursor-pointer"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Process New Document</span>
        </button>

      </div>

      {/* ================================================================= */}
      {/* 3. MODAL: LARGE QR CODE PREVIEW                                   */}
      {/* ================================================================= */}
      {showQrModal && qr_code_image && (
        <div 
          onClick={() => setShowQrModal(false)}
          className="fixed inset-0 z-50 bg-slate-900/80 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-200"
        >
          <div 
            onClick={(e) => e.stopPropagation()}
            className="bg-white rounded-3xl p-6 sm:p-8 max-w-sm w-full text-center space-y-4 shadow-2xl border border-slate-100"
          >
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <h3 className="text-sm font-bold text-slate-900">Scannable Reference QR Token</h3>
              <button onClick={() => setShowQrModal(false)} className="text-slate-400 hover:text-slate-700 text-lg font-bold">✕</button>
            </div>
            
            <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200 flex items-center justify-center">
              <img src={qr_code_image} alt="QR Code" className="w-56 h-56 object-contain" />
            </div>

            <div className="space-y-1">
              <p className="text-xs font-mono font-bold text-slate-800">{reference_id}</p>
              <p className="text-[11px] text-slate-500">Encodes privacy reference token only. No raw sensitive data.</p>
            </div>

            <button
              onClick={() => setShowQrModal(false)}
              className="w-full py-2.5 bg-slate-900 hover:bg-slate-800 text-white font-semibold text-xs rounded-xl transition"
            >
              Done
            </button>
          </div>
        </div>
      )}

      {/* ================================================================= */}
      {/* 4. MODAL: QR VERIFICATION SCREEN (SIMULATED SCAN RESULT)         */}
      {/* ================================================================= */}
      {showVerifyModal && (
        <div 
          onClick={() => setShowVerifyModal(false)}
          className="fixed inset-0 z-50 bg-slate-900/80 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-200"
        >
          <div 
            onClick={(e) => e.stopPropagation()}
            className="bg-white rounded-3xl p-6 sm:p-8 max-w-md w-full space-y-5 shadow-2xl border border-slate-100"
          >
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center space-x-2">
                <ShieldCheck className="w-5 h-5 text-indigo-600" />
                <h3 className="text-sm font-bold text-slate-900">IDENTITY VERIFICATION SCREEN</h3>
              </div>
              <button onClick={() => setShowVerifyModal(false)} className="text-slate-400 hover:text-slate-700 text-lg font-bold">✕</button>
            </div>

            {isRevoked ? (
              <div className="p-6 bg-rose-50 border border-rose-200 rounded-2xl text-center space-y-3">
                <XCircle className="w-12 h-12 text-rose-600 mx-auto" />
                <h4 className="text-base font-bold text-rose-950">REFERENCE INVALID / REVOKED</h4>
                <p className="text-xs text-rose-800">
                  This Reference ID has been revoked by the holder or authority and cannot be used.
                </p>
              </div>
            ) : (
              <div className="p-6 bg-slate-50 border border-slate-200 rounded-2xl space-y-4">
                <div className="flex items-center space-x-4">
                  {photo ? (
                    <img src={photo} alt="Photo" className="w-16 h-20 object-cover rounded-lg border border-slate-300 shadow-sm" />
                  ) : (
                    <div className="w-16 h-20 bg-slate-200 rounded-lg flex items-center justify-center text-slate-400">
                      <User className="w-6 h-6" />
                    </div>
                  )}
                  <div className="space-y-1">
                    <h4 className="text-base font-bold text-slate-900">{name}</h4>
                    <p className="text-xs text-indigo-700 font-semibold">{document_type_display}</p>
                    <p className="text-xs font-mono font-bold text-slate-700">{masked_number}</p>
                  </div>
                </div>

                <div className="p-3 bg-emerald-100/70 border border-emerald-300 rounded-xl flex items-center space-x-2 text-emerald-900 text-xs font-bold">
                  <CheckCircle2 className="w-4 h-4 text-emerald-700 flex-shrink-0" />
                  <span>✓ DETAILS CONFIRMED</span>
                </div>

                <div className="text-[11px] text-slate-500 font-mono text-center">
                  Ref: <strong className="text-slate-800">{reference_id}</strong>
                </div>
              </div>
            )}

            <button
              onClick={() => setShowVerifyModal(false)}
              className="w-full py-3 bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs rounded-xl transition cursor-pointer"
            >
              Close Verification
            </button>
          </div>
        </div>
      )}

    </div>
  );
}
