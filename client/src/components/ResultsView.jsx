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
  Edit2,
  Check
} from 'lucide-react';

export default function ResultsView({ result, onUploadAnother }) {
  if (!result) return null;

  const { document_type, is_valid, short_circuited, is_duplicate_or_sample, authenticity_status, data, warnings, images } = result;

  // Local editable state for human-in-the-loop editing
  const [formData, setFormData] = useState(data || {});
  const [editingField, setEditingField] = useState(null);

  useEffect(() => {
    setFormData(data || {});
  }, [data]);

  const handleFieldChange = (field, val) => {
    setFormData(prev => ({ ...prev, [field]: val }));
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
      
      {/* Main Extracted Card */}
      <div className="bg-white border border-slate-200/80 rounded-2xl p-6 shadow-sm">
        
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
          <div className="mt-4 p-4 bg-rose-50 border-2 border-rose-300 rounded-xl flex items-start space-x-3 text-xs text-rose-900 shadow-sm">
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
          <div className="mt-6 p-6 bg-amber-50/80 border border-amber-200 rounded-2xl">
            <div className="flex items-start space-x-4">
              <div className="p-3 bg-amber-100 text-amber-800 rounded-xl flex-shrink-0">
                <RotateCcw className="w-6 h-6" />
              </div>
              <div className="flex-1">
                <h3 className="text-base font-bold text-amber-900 mb-1">
                  PAN Card Back Side Detected
                </h3>
                <p className="text-xs text-amber-800 leading-relaxed max-w-2xl">
                  The back side of an Indian PAN Card contains only barcodes and instructions. It does not have your Name, Father's Name, DOB, or PAN Number.
                </p>
                <div className="mt-4 p-3 bg-white/90 border border-amber-200 rounded-xl text-xs text-slate-700 flex items-center justify-between">
                  <span>👉 <strong>Action Required:</strong> Please flip the card and upload the <strong>FRONT SIDE</strong> to complete verification.</span>
                  {onUploadAnother && (
                    <button
                      onClick={onUploadAnother}
                      className="ml-3 px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-700 text-white font-bold text-xs shadow-sm transition flex items-center space-x-1.5 flex-shrink-0"
                    >
                      <span>Upload Front Side</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* BACK-SIDE PROMPT FOR AADHAAR & DRIVING LICENCE */}
        {(document_type === 'aadhaar_back' || document_type === 'driving_licence_back') && (
          <div className="mt-4 p-4 bg-sky-50 border border-sky-200 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-sky-900">
            <div className="flex items-start space-x-2.5">
              <ShieldCheck className="w-4 h-4 text-sky-600 flex-shrink-0 mt-0.5" />
              <div>
                <strong className="block text-sky-950 font-bold">Back Side Verified (Address & Details Extracted)!</strong>
                <span>To link with your full name and cardholder photo, please also upload the <strong>FRONT SIDE</strong>.</span>
              </div>
            </div>
            {onUploadAnother && (
              <button
                onClick={onUploadAnother}
                className="px-3.5 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-700 text-white font-bold text-xs shadow-sm transition flex items-center space-x-1 self-start sm:self-auto flex-shrink-0"
              >
                <span>Upload Front Side</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        )}

        {/* Validation Warnings Alert */}
        {warnings && warnings.length > 0 && document_type !== 'pan_back' && (
          <div className="mt-4 p-3.5 bg-amber-50 border border-amber-200 rounded-xl flex items-start space-x-3 text-xs text-amber-800">
            <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold block mb-0.5">Verification Notices:</span>
              <ul className="list-disc list-inside space-y-0.5 text-amber-900/90">
                {warnings.map((w, idx) => (
                  <li key={idx}>{w}</li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {/* Extracted Fields Content with Photo Attachment */}
        {document_type === 'unsupported' ? (
          <div className="mt-6 p-8 bg-slate-50 border border-slate-200 rounded-xl text-center">
            <XCircle className="w-10 h-10 text-rose-500 mx-auto mb-2" />
            <h3 className="text-base font-semibold text-slate-800 mb-1">Non-Supported Document</h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto">
              {data?.error || 'Only Indian Aadhaar Card, PAN Card, and Driving Licence are supported by Utility Bot.'}
            </p>
          </div>
        ) : document_type !== 'pan_back' && (
          <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            {/* Left Column: Attached Document Photo */}
            {images?.original && (
              <div className="lg:col-span-1 bg-slate-50 border border-slate-200 rounded-xl p-4 flex flex-col items-center justify-center text-center shadow-sm">
                <div className="flex items-center space-x-1.5 text-xs font-bold text-slate-700 mb-3 self-start">
                  <ImageIcon className="w-4 h-4 text-sky-600" />
                  <span>Applicant Document Photo</span>
                </div>
                <img
                  src={images.original}
                  alt="Verified Document Scan"
                  className="max-h-48 w-full object-contain rounded-lg border border-slate-200 shadow-sm bg-white p-1"
                />
                <span className="text-[11px] text-slate-400 mt-2">Stored with 30-day retention</span>
              </div>
            )}

            {/* Right Columns: Extracted Data Cards */}
            <div className={`grid grid-cols-1 sm:grid-cols-2 gap-4 ${images?.original ? 'lg:col-span-2' : 'lg:col-span-3'}`}>
              
              {/* 1. AADHAAR FRONT FIELDS */}
              {document_type === 'aadhaar' && (
                <>
                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex items-start space-x-3 shadow-sm group">
                    <div className="p-2 rounded-lg bg-sky-100 text-sky-700 flex-shrink-0">
                      <User className="w-4 h-4" />
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">Applicant Name</span>
                      <input
                        type="text"
                        value={formData?.name || ''}
                        onChange={(e) => handleFieldChange('name', e.target.value)}
                        placeholder="Applicant Name"
                        className="w-full text-sm font-bold text-slate-900 bg-transparent border-b border-dashed border-transparent hover:border-slate-300 focus:border-sky-500 focus:bg-white px-1 py-0.5 rounded focus:outline-none transition"
                      />
                    </div>
                  </div>

                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex items-start space-x-3 shadow-sm">
                    <div className="p-2 rounded-lg bg-indigo-100 text-indigo-700 flex-shrink-0">
                      <Hash className="w-4 h-4" />
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">Aadhaar Number (Masked)</span>
                      <input
                        type="text"
                        value={formData?.aadhaar_number || ''}
                        onChange={(e) => handleFieldChange('aadhaar_number', e.target.value)}
                        placeholder="********1234"
                        className="w-full text-sm font-bold text-sky-700 font-mono bg-transparent border-b border-dashed border-transparent hover:border-slate-300 focus:border-sky-500 focus:bg-white px-1 py-0.5 rounded focus:outline-none transition"
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
                        value={formData?.date_of_birth || formData?.year_of_birth || ''}
                        onChange={(e) => handleFieldChange('date_of_birth', e.target.value)}
                        placeholder="YYYY-MM-DD"
                        className="w-full text-sm font-bold text-slate-900 bg-transparent border-b border-dashed border-transparent hover:border-slate-300 focus:border-emerald-500 focus:bg-white px-1 py-0.5 rounded focus:outline-none transition"
                      />
                    </div>
                  </div>

                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex items-start space-x-3 shadow-sm">
                    <div className="p-2 rounded-lg bg-purple-100 text-purple-700 flex-shrink-0">
                      <FileText className="w-4 h-4" />
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">Gender</span>
                      <input
                        type="text"
                        value={formData?.gender || ''}
                        onChange={(e) => handleFieldChange('gender', e.target.value)}
                        placeholder="Male / Female"
                        className="w-full text-sm font-bold text-slate-900 bg-transparent border-b border-dashed border-transparent hover:border-slate-300 focus:border-purple-500 focus:bg-white px-1 py-0.5 rounded focus:outline-none transition"
                      />
                    </div>
                  </div>
                </>
              )}

              {/* 2. AADHAAR BACK FIELDS (Address & Care of) */}
              {document_type === 'aadhaar_back' && (
                <>
                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex items-start space-x-3 shadow-sm">
                    <div className="p-2 rounded-lg bg-purple-100 text-purple-700 flex-shrink-0">
                      <User className="w-4 h-4" />
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">Guardian / Spouse (C/O)</span>
                      <input
                        type="text"
                        value={formData?.care_of || ''}
                        onChange={(e) => handleFieldChange('care_of', e.target.value)}
                        placeholder="Father / Husband Name"
                        className="w-full text-sm font-bold text-slate-900 bg-transparent border-b border-dashed border-transparent hover:border-slate-300 focus:border-purple-500 focus:bg-white px-1 py-0.5 rounded focus:outline-none transition"
                      />
                    </div>
                  </div>

                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex items-start space-x-3 shadow-sm">
                    <div className="p-2 rounded-lg bg-indigo-100 text-indigo-700 flex-shrink-0">
                      <Hash className="w-4 h-4" />
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">Postal Pincode</span>
                      <input
                        type="text"
                        value={formData?.pincode || ''}
                        onChange={(e) => handleFieldChange('pincode', e.target.value)}
                        placeholder="6-digit PIN"
                        className="w-full text-sm font-bold text-sky-700 font-mono bg-transparent border-b border-dashed border-transparent hover:border-slate-300 focus:border-sky-500 focus:bg-white px-1 py-0.5 rounded focus:outline-none transition"
                      />
                    </div>
                  </div>

                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 sm:col-span-2 flex items-start space-x-3 shadow-sm">
                    <div className="p-2 rounded-lg bg-sky-100 text-sky-700 flex-shrink-0">
                      <MapPin className="w-4 h-4" />
                    </div>
                    <div className="flex-1">
                      <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">Full Residential Address</span>
                      <textarea
                        rows={2}
                        value={formData?.address || ''}
                        onChange={(e) => handleFieldChange('address', e.target.value)}
                        placeholder="Full Residential Address"
                        className="w-full text-xs text-slate-800 font-medium bg-transparent border-b border-dashed border-transparent hover:border-slate-300 focus:border-sky-500 focus:bg-white px-1 py-1 rounded focus:outline-none transition mt-1"
                      />
                    </div>
                  </div>
                </>
              )}

              {/* 3. PAN FRONT FIELDS */}
              {document_type === 'pan' && (
                <>
                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex items-start space-x-3 shadow-sm">
                    <div className="p-2 rounded-lg bg-sky-100 text-sky-700 flex-shrink-0">
                      <User className="w-4 h-4" />
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">Cardholder Name</span>
                      <input
                        type="text"
                        value={formData?.name || ''}
                        onChange={(e) => handleFieldChange('name', e.target.value)}
                        placeholder="Cardholder Name"
                        className="w-full text-sm font-bold text-slate-900 bg-transparent border-b border-dashed border-transparent hover:border-slate-300 focus:border-sky-500 focus:bg-white px-1 py-0.5 rounded focus:outline-none transition"
                      />
                    </div>
                  </div>

                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex items-start space-x-3 shadow-sm">
                    <div className="p-2 rounded-lg bg-indigo-100 text-indigo-700 flex-shrink-0">
                      <Hash className="w-4 h-4" />
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">PAN Number</span>
                      <input
                        type="text"
                        value={formData?.pan_number || ''}
                        onChange={(e) => handleFieldChange('pan_number', e.target.value.toUpperCase())}
                        placeholder="ABCDE1234F"
                        className="w-full text-sm font-bold text-sky-700 font-mono uppercase bg-transparent border-b border-dashed border-transparent hover:border-slate-300 focus:border-sky-500 focus:bg-white px-1 py-0.5 rounded focus:outline-none transition"
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
                </>
              )}

              {/* 4. DRIVING LICENCE FRONT FIELDS */}
              {document_type === 'driving_licence' && (
                <>
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
                        placeholder="Licence Holder Name"
                        className="w-full text-sm font-bold text-slate-900 bg-transparent border-b border-dashed border-transparent hover:border-slate-300 focus:border-emerald-500 focus:bg-white px-1 py-0.5 rounded focus:outline-none transition"
                      />
                    </div>
                  </div>

                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex items-start space-x-3 shadow-sm">
                    <div className="p-2 rounded-lg bg-sky-100 text-sky-700 flex-shrink-0">
                      <Hash className="w-4 h-4" />
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">Licence Number</span>
                      <input
                        type="text"
                        value={formData?.dl_number || ''}
                        onChange={(e) => handleFieldChange('dl_number', e.target.value.toUpperCase())}
                        placeholder="DL Number"
                        className="w-full text-sm font-bold text-sky-700 font-mono uppercase bg-transparent border-b border-dashed border-transparent hover:border-slate-300 focus:border-sky-500 focus:bg-white px-1 py-0.5 rounded focus:outline-none transition"
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
                    <div className="p-2 rounded-lg bg-indigo-100 text-indigo-700 flex-shrink-0">
                      <Clock className="w-4 h-4" />
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">Valid Until</span>
                      <input
                        type="text"
                        value={formData?.valid_until || ''}
                        onChange={(e) => handleFieldChange('valid_until', e.target.value)}
                        placeholder="YYYY-MM-DD"
                        className="w-full text-sm font-bold text-slate-900 bg-transparent border-b border-dashed border-transparent hover:border-slate-300 focus:border-indigo-500 focus:bg-white px-1 py-0.5 rounded focus:outline-none transition"
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
