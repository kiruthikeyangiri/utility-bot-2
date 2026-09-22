import React, { useState } from 'react';
import { 
  FileCheck, 
  Upload, 
  RefreshCw, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  X, 
  Check, 
  User, 
  Calendar, 
  Image as ImageIcon 
} from 'lucide-react';
import { extractDocumentApi, verifySecondIdApi } from '../services/api';

export default function SecondIdVerificationModal({
  isOpen,
  onClose,
  primaryDocumentType,
  primaryData,
  primaryPortrait,
  onVerificationComplete
}) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState(null);
  const [crosscheckResult, setCrosscheckResult] = useState(null);
  const [secondDocExtracted, setSecondDocExtracted] = useState(null);

  if (!isOpen) return null;

  const handleFileDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  };

  const handleFileInput = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelected(e.target.files[0]);
    }
  };

  const handleFileSelected = (selectedFile) => {
    setError(null);
    setFile(selectedFile);
    setCrosscheckResult(null);
    setSecondDocExtracted(null);

    const reader = new FileReader();
    reader.onload = (e) => {
      setPreview(e.target.result);
    };
    reader.readAsDataURL(selectedFile);
  };

  const getBaseDocType = (type) => {
    const t = (type || '').toLowerCase();
    if (t.includes('aadhaar')) return 'aadhaar';
    if (t.includes('pan')) return 'pan';
    if (t.includes('driving') || t.includes('dl') || t.includes('licence') || t.includes('license')) return 'driving_licence';
    return t;
  };

  const getDocLabel = (type) => {
    const base = getBaseDocType(type);
    const labels = {
      aadhaar: 'Aadhaar Card',
      pan: 'PAN Card',
      driving_licence: 'Driving Licence'
    };
    return labels[base] || (type ? type.toUpperCase() : 'ID Document');
  };

  const getAllowedSecondTypes = (primaryType) => {
    const base = getBaseDocType(primaryType);
    if (base === 'pan') return ['Aadhaar Card', 'Driving Licence'];
    if (base === 'aadhaar') return ['PAN Card', 'Driving Licence'];
    if (base === 'driving_licence') return ['Aadhaar Card', 'PAN Card'];
    return ['Aadhaar Card', 'PAN Card', 'Driving Licence'];
  };

  const runCrossVerification = async () => {
    if (!file) return;

    setIsProcessing(true);
    setError(null);

    try {
      // 1. Extract Second ID using standard pipeline
      const secondDocRes = await extractDocumentApi(file);
      setSecondDocExtracted(secondDocRes);

      if (!secondDocRes.is_valid || secondDocRes.document_type === 'unsupported') {
        throw new Error('The uploaded second document could not be recognized as a valid Indian ID card.');
      }

      // Check for same document type rejection (e.g. PAN + PAN, or Aadhaar + Aadhaar)
      const basePrimary = getBaseDocType(primaryDocumentType);
      const baseSecond = getBaseDocType(secondDocRes.document_type);

      if (basePrimary && baseSecond && basePrimary === baseSecond) {
        const allowedStr = getAllowedSecondTypes(basePrimary).join(' or ');
        throw new Error(
          `Invalid Document Pair: Primary document is already a ${getDocLabel(basePrimary)}. ` +
          `Cross-verification requires a complementary document. Please upload an ${allowedStr}.`
        );
      }

      // 2. Perform Cross-Verification against Primary ID
      const payload = {
        doc1_data: primaryData || {},
        doc1_portrait: primaryPortrait || null,
        doc1_type: primaryDocumentType || 'primary_id',
        doc2_data: secondDocRes.data || {},
        doc2_portrait: secondDocRes.portrait_photo || null,
        doc2_type: secondDocRes.document_type || 'secondary_id'
      };

      const crossResult = await verifySecondIdApi(payload);
      
      if (crossResult.is_same_type_error) {
        throw new Error(crossResult.summary || 'Cannot compare duplicate document types.');
      }

      setCrosscheckResult(crossResult);

      if (onVerificationComplete) {
        onVerificationComplete({
          method: 'second_id',
          status: crossResult.consistency_status,
          isVerified: crossResult.is_consistent,
          score: crossResult.overall_consistency_score,
          details: crossResult,
          secondDoc: secondDocRes
        });
      }
    } catch (err) {
      console.error('Cross verification error:', err);
      const errMsg = err.response?.data?.detail || err.message || 'Failed to complete document cross-verification.';
      setError(errMsg);
    } finally {
      setIsProcessing(false);
    }
  };

  const allowedTypes = getAllowedSecondTypes(primaryDocumentType);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-2xl bg-white border border-slate-200 rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        
        {/* Header */}
        <div className="px-6 py-4.5 border-b border-slate-100 flex items-center justify-between bg-gradient-to-r from-slate-50 via-white to-slate-50">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-700">
              <FileCheck className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">Second ID Verification</h3>
              <p className="text-xs text-slate-500">
                Primary ID: <strong className="text-slate-700">{getDocLabel(primaryDocumentType)}</strong> • Required: <strong className="text-emerald-700">{allowedTypes.join(' or ')}</strong>
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

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-5">
          
          {/* UPLOAD DROPZONE */}
          {!crosscheckResult && (
            <div className="space-y-4">
              <div
                onDrop={handleFileDrop}
                onDragOver={(e) => e.preventDefault()}
                className={`border-2 border-dashed rounded-2xl p-8 text-center transition-all ${
                  preview ? 'border-emerald-300 bg-emerald-50/20' : 'border-slate-300 hover:border-indigo-400 bg-slate-50/50'
                }`}
              >
                {preview ? (
                  <div className="space-y-3">
                    <img 
                      src={preview} 
                      alt="Second ID Preview" 
                      className="max-h-48 rounded-xl mx-auto shadow-md border border-slate-200 object-contain" 
                    />
                    <p className="text-xs font-semibold text-slate-700">{file?.name}</p>
                    <label className="inline-flex items-center space-x-1.5 text-xs text-indigo-600 font-bold hover:underline cursor-pointer">
                      <span>Choose a different file</span>
                      <input type="file" accept="image/*" onChange={handleFileInput} className="hidden" />
                    </label>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div className="w-12 h-12 rounded-2xl bg-indigo-50 border border-indigo-100 text-indigo-600 flex items-center justify-center mx-auto shadow-sm">
                      <Upload className="w-6 h-6" />
                    </div>
                    <div>
                      <p className="text-xs font-bold text-slate-800">
                        Upload Complementary ID Document
                      </p>
                      <div className="mt-1.5 inline-flex items-center space-x-1.5 px-3 py-1 rounded-lg bg-indigo-50 border border-indigo-200 text-indigo-800 text-[11px] font-bold">
                        <span>Accepted: {allowedTypes.join(' or ')}</span>
                      </div>
                      <p className="text-[11px] text-slate-500 mt-1.5">
                        Cannot upload another {getDocLabel(primaryDocumentType)}. A different ID type is required.
                      </p>
                    </div>
                    <label className="inline-flex items-center space-x-2 px-4 py-2 bg-white border border-slate-300 hover:border-slate-400 text-slate-700 rounded-xl text-xs font-bold shadow-sm cursor-pointer transition">
                      <span>Browse Files</span>
                      <input type="file" accept="image/*" onChange={handleFileInput} className="hidden" />
                    </label>
                  </div>
                )}
              </div>

              {error && (
                <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl flex items-center space-x-2.5 text-rose-800 text-xs">
                  <AlertTriangle className="w-4 h-4 text-rose-600 flex-shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              {file && (
                <div className="flex items-center justify-end gap-3 pt-2">
                  <button
                    onClick={runCrossVerification}
                    disabled={isProcessing}
                    className="inline-flex items-center space-x-2 px-6 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-bold shadow-md shadow-emerald-600/20 transition disabled:opacity-50 cursor-pointer"
                  >
                    {isProcessing ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        <span>Cross-Checking Records...</span>
                      </>
                    ) : (
                      <>
                        <FileCheck className="w-4 h-4" />
                        <span>Run Cross-Check</span>
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>
          )}

          {/* CROSS-VERIFICATION RESULTS VIEW */}
          {crosscheckResult && (
            <div className="space-y-5 animate-in fade-in slide-in-from-bottom-2 duration-300">
              
              {/* Verdict Banner */}
              <div className={`p-4 rounded-2xl border flex items-start space-x-3.5 ${
                crosscheckResult.is_consistent
                  ? 'bg-emerald-50 border-emerald-200 text-emerald-950'
                  : 'bg-rose-50 border-rose-200 text-rose-950'
              }`}>
                {crosscheckResult.is_consistent ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
                ) : (
                  <XCircle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
                )}
                <div>
                  <h4 className="text-sm font-bold">
                    {crosscheckResult.is_consistent 
                      ? '✅ Multi-Document Verification Passed (Consistent)' 
                      : '❌ Multi-Document Mismatch Detected'}
                  </h4>
                  <p className="text-xs mt-1 leading-relaxed opacity-90">
                    {crosscheckResult.summary}
                  </p>
                </div>
              </div>

              {/* Side-by-Side Comparison Matrix Table */}
              <div className="border border-slate-200 rounded-2xl overflow-hidden shadow-sm bg-white">
                <div className="grid grid-cols-12 bg-slate-50 border-b border-slate-200 px-4 py-2.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <div className="col-span-3">Field</div>
                  <div className="col-span-4">Doc 1 ({getDocLabel(crosscheckResult.doc1_type)})</div>
                  <div className="col-span-4">Doc 2 ({getDocLabel(crosscheckResult.doc2_type)})</div>
                  <div className="col-span-1 text-right">Status</div>
                </div>

                {/* Name Row */}
                <div className="grid grid-cols-12 px-4 py-3.5 border-b border-slate-100 items-center text-xs">
                  <div className="col-span-3 flex items-center space-x-2 font-semibold text-slate-700">
                    <User className="w-3.5 h-3.5 text-slate-400" />
                    <span>Full Name</span>
                  </div>
                  <div className="col-span-4 font-medium text-slate-900 truncate">
                    {crosscheckResult.field_comparisons?.name?.doc1_value}
                  </div>
                  <div className="col-span-4 font-medium text-slate-900 truncate">
                    {crosscheckResult.field_comparisons?.name?.doc2_value}
                  </div>
                  <div className="col-span-1 text-right">
                    {crosscheckResult.field_comparisons?.name?.status === 'MATCH' ? (
                      <span className="inline-flex px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 text-[10px] font-bold">✓ Match</span>
                    ) : (
                      <span className="inline-flex px-1.5 py-0.5 rounded bg-rose-100 text-rose-800 text-[10px] font-bold">✗ Diff</span>
                    )}
                  </div>
                </div>

                {/* DOB Row */}
                <div className="grid grid-cols-12 px-4 py-3.5 border-b border-slate-100 items-center text-xs">
                  <div className="col-span-3 flex items-center space-x-2 font-semibold text-slate-700">
                    <Calendar className="w-3.5 h-3.5 text-slate-400" />
                    <span>Date of Birth</span>
                  </div>
                  <div className="col-span-4 font-medium text-slate-900 truncate">
                    {crosscheckResult.field_comparisons?.date_of_birth?.doc1_value}
                  </div>
                  <div className="col-span-4 font-medium text-slate-900 truncate">
                    {crosscheckResult.field_comparisons?.date_of_birth?.doc2_value}
                  </div>
                  <div className="col-span-1 text-right">
                    {['EXACT_MATCH', 'YEAR_MATCH'].includes(crosscheckResult.field_comparisons?.date_of_birth?.status) ? (
                      <span className="inline-flex px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 text-[10px] font-bold">✓ Match</span>
                    ) : (
                      <span className="inline-flex px-1.5 py-0.5 rounded bg-rose-100 text-rose-800 text-[10px] font-bold">✗ Diff</span>
                    )}
                  </div>
                </div>

                {/* Face Similarity Row (if available) */}
                {crosscheckResult.field_comparisons?.portrait_face?.has_portraits && (
                  <div className="grid grid-cols-12 px-4 py-3.5 items-center text-xs">
                    <div className="col-span-3 flex items-center space-x-2 font-semibold text-slate-700">
                      <ImageIcon className="w-3.5 h-3.5 text-slate-400" />
                      <span>Face Photo</span>
                    </div>
                    <div className="col-span-4 flex items-center space-x-2">
                      {primaryPortrait && (
                        <img src={primaryPortrait} alt="Doc1 Face" className="w-9 h-11 object-cover rounded-lg border border-slate-200 shadow-sm" />
                      )}
                    </div>
                    <div className="col-span-4 flex items-center space-x-2">
                      {secondDocExtracted?.portrait_photo && (
                        <img src={secondDocExtracted.portrait_photo} alt="Doc2 Face" className="w-9 h-11 object-cover rounded-lg border border-slate-200 shadow-sm" />
                      )}
                    </div>
                    <div className="col-span-1 text-right">
                      {crosscheckResult.field_comparisons?.portrait_face?.status === 'MATCH' ? (
                        <span className="inline-flex px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 text-[10px] font-bold">✓ {crosscheckResult.field_comparisons?.portrait_face?.similarity_score}%</span>
                      ) : (
                        <span className="inline-flex px-1.5 py-0.5 rounded bg-rose-100 text-rose-800 text-[10px] font-bold">✗ {crosscheckResult.field_comparisons?.portrait_face?.similarity_score}%</span>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Consistency Meter */}
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-2xl space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-600 font-semibold">Overall Document Consistency:</span>
                  <span className="font-bold text-slate-900 font-mono text-sm">
                    {crosscheckResult.overall_consistency_score}%
                  </span>
                </div>
                <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
                  <div 
                    className={`h-full rounded-full transition-all duration-500 ${
                      crosscheckResult.is_consistent ? 'bg-emerald-500' : 'bg-rose-500'
                    }`}
                    style={{ width: `${Math.min(100, Math.max(5, crosscheckResult.overall_consistency_score))}%` }}
                  />
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  onClick={() => {
                    setCrosscheckResult(null);
                    setFile(null);
                    setPreview(null);
                  }}
                  className="inline-flex items-center space-x-1.5 px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-bold transition cursor-pointer"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Test Another ID</span>
                </button>

                <button
                  onClick={onClose}
                  className="inline-flex items-center space-x-1.5 px-6 py-2.5 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-bold shadow-md transition cursor-pointer"
                >
                  <Check className="w-4 h-4" />
                  <span>Apply & Close</span>
                </button>
              </div>

            </div>
          )}

        </div>

      </div>
    </div>
  );
}
