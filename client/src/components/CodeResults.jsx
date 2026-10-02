import React, { useState } from 'react';
import { 
  Barcode, 
  QrCode, 
  Copy, 
  Check, 
  ExternalLink, 
  AlertCircle,
  Hash
} from 'lucide-react';

export default function CodeResults({ barcodes = [], qr_codes = [] }) {
  const [copiedKey, setCopiedKey] = useState(null);

  const handleCopy = (key, text) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => {
      setCopiedKey(null);
    }, 2000);
  };

  const isUrl = (val) => {
    try {
      return val && (val.startsWith('http://') || val.startsWith('https://'));
    } catch {
      return false;
    }
  };

  const totalCodes = (barcodes?.length || 0) + (qr_codes?.length || 0);

  return (
    <div className="space-y-6">
      
      {/* Top Banner Summary */}
      <div className="bg-slate-50 border border-slate-200/80 rounded-2xl p-4 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-1.5 font-semibold text-slate-700">
            <Barcode className="w-4 h-4 text-sky-600" />
            <span>Barcodes:</span>
            <span className="px-2 py-0.5 rounded-full bg-sky-100 text-sky-800 text-[11px] font-bold">
              {barcodes?.length || 0}
            </span>
          </div>

          <div className="flex items-center space-x-1.5 font-semibold text-slate-700">
            <QrCode className="w-4 h-4 text-indigo-600" />
            <span>QR Codes:</span>
            <span className="px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-800 text-[11px] font-bold">
              {qr_codes?.length || 0}
            </span>
          </div>
        </div>

        <span className="text-slate-500 text-[11px]">
          Multi-pass ZXing-CPP + OpenCV Barcode & 2D Matrix Engine
        </span>
      </div>

      {totalCodes === 0 && (
        <div className="p-8 text-center bg-white border border-slate-200/80 rounded-2xl space-y-2">
          <AlertCircle className="w-8 h-8 text-slate-400 mx-auto" />
          <h4 className="text-sm font-semibold text-slate-700">No Optical Codes Detected</h4>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            Neither 1D linear barcodes nor 2D QR codes were recognized on this image label.
          </p>
        </div>
      )}

      {/* 1. BARCODES SECTION */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="p-1.5 rounded-lg bg-sky-50 text-sky-600 border border-sky-100">
              <Barcode className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
              Barcodes ({barcodes?.length || 0})
            </h3>
          </div>
        </div>

        {(!barcodes || barcodes.length === 0) ? (
          <div className="p-4 bg-white border border-dashed border-slate-200 rounded-xl text-center text-xs text-slate-500">
            No 1D barcodes found
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3">
            {barcodes.map((item, idx) => {
              const itemKey = `barcode-${idx}-${item.value}`;
              const isCopied = copiedKey === itemKey;

              return (
                <div 
                  key={itemKey}
                  className="bg-white border border-slate-200/90 rounded-xl p-4 shadow-sm hover:border-slate-300 transition flex items-center justify-between gap-3"
                >
                  <div className="flex items-start space-x-3 min-w-0 flex-1">
                    <div className="p-2 rounded-lg bg-slate-100 text-slate-700 flex-shrink-0 mt-0.5">
                      <Barcode className="w-5 h-5" />
                    </div>
                    <div className="min-w-0 flex-1 space-y-1">
                      <div className="flex items-center space-x-2">
                        <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
                          {item.format || 'Barcode'}
                        </span>
                        <span className="text-[11px] text-slate-400 font-mono">
                          #{idx + 1}
                        </span>
                      </div>
                      <div className="text-sm font-mono font-bold text-slate-900 break-all select-all">
                        {item.value}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center space-x-2 flex-shrink-0">
                    <button
                      onClick={() => handleCopy(itemKey, item.value)}
                      className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 transition text-xs font-medium"
                      title="Copy code value"
                    >
                      {isCopied ? (
                        <>
                          <Check className="w-3.5 h-3.5 text-emerald-600" />
                          <span className="text-emerald-700 font-semibold">Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3.5 h-3.5 text-slate-500" />
                          <span>Copy</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* 2. QR CODES SECTION */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="p-1.5 rounded-lg bg-indigo-50 text-indigo-600 border border-indigo-100">
              <QrCode className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
              QR Codes ({qr_codes?.length || 0})
            </h3>
          </div>
        </div>

        {(!qr_codes || qr_codes.length === 0) ? (
          <div className="p-4 bg-white border border-dashed border-slate-200 rounded-xl text-center text-xs text-slate-500">
            No QR codes found
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3">
            {qr_codes.map((item, idx) => {
              const itemKey = `qr-${idx}-${item.value}`;
              const isCopied = copiedKey === itemKey;
              const hasUrl = isUrl(item.value);

              return (
                <div 
                  key={itemKey}
                  className="bg-white border border-slate-200/90 rounded-xl p-4 shadow-sm hover:border-slate-300 transition flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                >
                  <div className="flex items-start space-x-3 min-w-0 flex-1">
                    <div className="p-2 rounded-lg bg-indigo-50 text-indigo-700 flex-shrink-0 mt-0.5">
                      <QrCode className="w-5 h-5" />
                    </div>
                    <div className="min-w-0 flex-1 space-y-1">
                      <div className="flex items-center space-x-2">
                        <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-800 border border-indigo-200">
                          {item.format || 'QRCode'}
                        </span>
                        <span className="text-[11px] text-slate-400 font-mono">
                          #{idx + 1}
                        </span>
                      </div>
                      <div className="text-xs font-mono font-medium text-slate-800 break-all select-all leading-relaxed">
                        {item.value}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center space-x-2 flex-shrink-0 self-end sm:self-center">
                    {hasUrl && (
                      <a
                        href={item.value}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-700 transition text-xs font-semibold border border-indigo-200"
                        title="Open URL in new tab"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                        <span>Open Link</span>
                      </a>
                    )}

                    <button
                      onClick={() => handleCopy(itemKey, item.value)}
                      className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 transition text-xs font-medium"
                      title="Copy QR value"
                    >
                      {isCopied ? (
                        <>
                          <Check className="w-3.5 h-3.5 text-emerald-600" />
                          <span className="text-emerald-700 font-semibold">Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3.5 h-3.5 text-slate-500" />
                          <span>Copy</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

    </div>
  );
}
