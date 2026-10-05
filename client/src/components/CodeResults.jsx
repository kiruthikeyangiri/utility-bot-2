import React, { useState, useMemo } from 'react';
import { 
  Barcode, 
  QrCode, 
  Copy, 
  Check, 
  ExternalLink, 
  AlertCircle,
  Info,
  ChevronDown,
  ChevronUp,
  Search,
  BookOpen,
  Layers,
  Sparkles
} from 'lucide-react';

export const OPTICAL_CODE_CATALOG = [
  {
    type: 'Code 128',
    aliases: ['CODE128', 'CODE_128'],
    category: '1D Linear Barcode',
    fullForm: 'Code 128',
    useFor: 'Shipping labels, courier tracking, warehouse labels, logistics',
    density: 'High density alphanumeric'
  },
  {
    type: 'Code 39',
    aliases: ['CODE39', 'CODE_39', '3OF9'],
    category: '1D Linear Barcode',
    fullForm: 'Code 39 (3 of 9)',
    useFor: 'Automotive, manufacturing, inventory, industrial labels',
    density: 'Variable length alphanumeric'
  },
  {
    type: 'EAN-13',
    aliases: ['EAN13', 'EAN_13', 'EAN'],
    category: '1D Linear Barcode',
    fullForm: 'European Article Number – 13 digit',
    useFor: 'Retail product barcodes, supermarkets, consumer packaging',
    density: '13 numeric digits'
  },
  {
    type: 'EAN-8',
    aliases: ['EAN8', 'EAN_8'],
    category: '1D Linear Barcode',
    fullForm: 'European Article Number – 8 digit',
    useFor: 'Small retail products with limited label space',
    density: '8 numeric digits'
  },
  {
    type: 'UPC-A',
    aliases: ['UPCA', 'UPC_A', 'UPC'],
    category: '1D Linear Barcode',
    fullForm: 'Universal Product Code – Version A',
    useFor: 'Retail products, mainly US & Canada retail supply chains',
    density: '12 numeric digits'
  },
  {
    type: 'UPC-E',
    aliases: ['UPCE', 'UPC_E'],
    category: '1D Linear Barcode',
    fullForm: 'Universal Product Code – Version E',
    useFor: 'Small packages where standard UPC-A is too large (zero-suppressed)',
    density: '6-8 numeric digits'
  },
  {
    type: 'ITF',
    aliases: ['ITF', 'INTERLEAVED2OF5', 'I2OF5'],
    category: '1D Linear Barcode',
    fullForm: 'Interleaved Two of Five',
    useFor: 'Cartons, warehouse boxes, logistics & corrugated cardboard',
    density: 'Continuous numeric pairs'
  },
  {
    type: 'ITF-14',
    aliases: ['ITF14', 'ITF_14'],
    category: '1D Linear Barcode',
    fullForm: 'Interleaved Two of Five – 14 digit',
    useFor: 'Shipping master cartons and product cases in wholesale logistics',
    density: '14 numeric digits'
  },
  {
    type: 'Codabar',
    aliases: ['CODABAR', 'NW7', 'USD4'],
    category: '1D Linear Barcode',
    fullForm: 'Codabar Barcode',
    useFor: 'Libraries, blood banks, older logistics systems, parcel tracking',
    density: 'Numeric with special start/stop'
  },
  {
    type: 'GS1-128',
    aliases: ['GS1128', 'GS1_128', 'EAN128', 'UCC128'],
    category: '1D Linear Barcode',
    fullForm: 'GS1 Code 128',
    useFor: 'Shipping, supply chain, batch numbers, expiry dates, serial numbers',
    density: 'High density with GS1 AI prefixes'
  },
  {
    type: 'PDF417',
    aliases: ['PDF417', 'PDF_417'],
    category: '2D Stacked Barcode',
    fullForm: 'Portable Data File 417',
    useFor: 'Driving licences, IDs, transport documents, airline boarding passes',
    density: 'High capacity multi-row 2D'
  },
  {
    type: 'Data Matrix',
    aliases: ['DATAMATRIX', 'DATA_MATRIX'],
    category: '2D Matrix Code',
    fullForm: 'Data Matrix 2D Code',
    useFor: 'Electronics, medicine, manufacturing, small industrial components',
    density: 'Ultra compact 2D square matrix'
  },
  {
    type: 'QR Code',
    aliases: ['QRCODE', 'QR_CODE', 'QR'],
    category: '2D Matrix Code',
    fullForm: 'Quick Response Code',
    useFor: 'URLs, payments, tracking links, IDs, product authentication',
    density: 'High-speed 2D matrix'
  },
  {
    type: 'Micro QR',
    aliases: ['MICROQR', 'MICRO_QR'],
    category: '2D Matrix Code',
    fullForm: 'Micro Quick Response Code',
    useFor: 'Very small labels with limited space (single position pattern)',
    density: 'Compact 2D mini matrix'
  },
  {
    type: 'Aztec Code',
    aliases: ['AZTEC', 'AZTECCODE', 'AZTEC_CODE'],
    category: '2D Matrix Code',
    fullForm: 'Aztec Code',
    useFor: 'Flight tickets, train tickets, mobile electronic boarding passes',
    density: 'Central bullseye square matrix'
  },
  {
    type: 'MaxiCode',
    aliases: ['MAXICODE', 'MAXI_CODE', 'UPSCODE'],
    category: '2D Matrix Code',
    fullForm: 'MaxiCode',
    useFor: 'High-speed parcel sorting and shipping (UPS & conveyor logistics)',
    density: 'Hexagonal honeycomb matrix'
  },
  {
    type: 'GS1 DataMatrix',
    aliases: ['GS1DATAMATRIX', 'GS1_DATAMATRIX', 'GS1_DATA_MATRIX'],
    category: '2D Matrix Code',
    fullForm: 'GS1 Data Matrix',
    useFor: 'Healthcare, medicines, serial numbers, expiry and batch data',
    density: 'Standardized healthcare 2D matrix'
  }
];

export function lookupCodeInfo(rawFormat) {
  if (!rawFormat) return null;
  const clean = String(rawFormat).toUpperCase().replace(/[\s\-_]/g, '');
  return OPTICAL_CODE_CATALOG.find(item => {
    const cleanType = item.type.toUpperCase().replace(/[\s\-_]/g, '');
    if (clean === cleanType) return true;
    return item.aliases.some(a => clean === a.replace(/[\s\-_]/g, ''));
  }) || null;
}

export default function CodeResults({ barcodes = [], qr_codes = [] }) {
  const [copiedKey, setCopiedKey] = useState(null);
  const [showCatalog, setShowCatalog] = useState(false);
  const [catalogSearch, setCatalogSearch] = useState('');
  const [catalogFilter, setCatalogFilter] = useState('ALL');

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

  const filteredCatalog = useMemo(() => {
    return OPTICAL_CODE_CATALOG.filter(item => {
      const matchCat = 
        catalogFilter === 'ALL' ||
        (catalogFilter === '1D' && item.category.includes('1D')) ||
        (catalogFilter === '2D' && (item.category.includes('2D') || item.category.includes('QR')));

      const matchSearch = 
        !catalogSearch.trim() ||
        item.type.toLowerCase().includes(catalogSearch.toLowerCase()) ||
        item.fullForm.toLowerCase().includes(catalogSearch.toLowerCase()) ||
        item.useFor.toLowerCase().includes(catalogSearch.toLowerCase());

      return matchCat && matchSearch;
    });
  }, [catalogSearch, catalogFilter]);

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

        <div className="flex items-center space-x-3">
          <button
            onClick={() => setShowCatalog(!showCatalog)}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-white border border-slate-200 hover:border-slate-300 text-slate-700 font-semibold text-[11px] shadow-sm transition hover:bg-slate-50"
          >
            <BookOpen className="w-3.5 h-3.5 text-sky-600" />
            <span>Format & Symbology Guide ({OPTICAL_CODE_CATALOG.length})</span>
            {showCatalog ? <ChevronUp className="w-3.5 h-3.5 text-slate-400" /> : <ChevronDown className="w-3.5 h-3.5 text-slate-400" />}
          </button>
        </div>
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
              const info = lookupCodeInfo(item.format);

              return (
                <div 
                  key={itemKey}
                  className="bg-white border border-slate-200/90 rounded-xl p-4 shadow-sm hover:border-slate-300 transition flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                >
                  <div className="flex items-start space-x-3 min-w-0 flex-1">
                    <div className="p-2.5 rounded-xl bg-sky-50 text-sky-700 border border-sky-100 flex-shrink-0 mt-0.5">
                      <Barcode className="w-5 h-5" />
                    </div>
                    <div className="min-w-0 flex-1 space-y-1.5">
                      <div className="flex items-center space-x-2 flex-wrap gap-y-1">
                        <span className="text-[10px] font-bold uppercase px-2.5 py-0.5 rounded-full bg-sky-50 text-sky-800 border border-sky-200">
                          {item.format || 'Barcode'}
                        </span>
                        {info && (
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
                            {info.fullForm}
                          </span>
                        )}
                        <span className="text-[11px] text-slate-400 font-mono">
                          #{idx + 1}
                        </span>
                      </div>

                      <div className="text-sm font-mono font-bold text-slate-900 break-all select-all tracking-wide">
                        {item.value}
                      </div>

                      {info && (
                        <div className="flex items-center space-x-1.5 text-[11px] text-slate-500">
                          <Info className="w-3 h-3 text-sky-500 flex-shrink-0" />
                          <span className="truncate"><strong className="text-slate-700 font-medium">Used for:</strong> {info.useFor}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center space-x-2 flex-shrink-0 self-end sm:self-center">
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
              const info = lookupCodeInfo(item.format);

              return (
                <div 
                  key={itemKey}
                  className="bg-white border border-slate-200/90 rounded-xl p-4 shadow-sm hover:border-slate-300 transition flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                >
                  <div className="flex items-start space-x-3 min-w-0 flex-1">
                    <div className="p-2.5 rounded-xl bg-indigo-50 text-indigo-700 border border-indigo-100 flex-shrink-0 mt-0.5">
                      <QrCode className="w-5 h-5" />
                    </div>
                    <div className="min-w-0 flex-1 space-y-1.5">
                      <div className="flex items-center space-x-2 flex-wrap gap-y-1">
                        <span className="text-[10px] font-bold uppercase px-2.5 py-0.5 rounded-full bg-indigo-50 text-indigo-800 border border-indigo-200">
                          {item.format || 'QRCode'}
                        </span>
                        {item.content_type && (
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200">
                            {item.content_type}
                          </span>
                        )}
                        {info && (
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
                            {info.fullForm}
                          </span>
                        )}
                        <span className="text-[11px] text-slate-400 font-mono">
                          #{idx + 1}
                        </span>
                      </div>

                      <div className="text-xs font-mono font-medium text-slate-800 break-all select-all leading-relaxed">
                        {item.value}
                      </div>

                      {info && (
                        <div className="flex items-center space-x-1.5 text-[11px] text-slate-500">
                          <Info className="w-3 h-3 text-indigo-500 flex-shrink-0" />
                          <span className="truncate"><strong className="text-slate-700 font-medium">Used for:</strong> {info.useFor}</span>
                        </div>
                      )}
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

      {/* 3. OPTICAL CODE & SYMBOLOGY REFERENCE GUIDE (COLLAPSIBLE) */}
      {showCatalog && (
        <div className="mt-8 border border-slate-200 bg-white rounded-2xl p-5 shadow-sm space-y-4 animate-in fade-in duration-200">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
            <div className="flex items-center space-x-2.5">
              <div className="p-2 rounded-xl bg-sky-50 text-sky-600 border border-sky-100">
                <BookOpen className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-slate-900">
                  Barcode & QR Symbology Reference Guide
                </h4>
                <p className="text-xs text-slate-500">
                  Comprehensive standard full forms and real-world logistics applications
                </p>
              </div>
            </div>

            {/* Filter Tabs */}
            <div className="flex items-center space-x-1 bg-slate-100 p-1 rounded-xl text-xs font-semibold">
              <button
                onClick={() => setCatalogFilter('ALL')}
                className={`px-3 py-1 rounded-lg transition ${catalogFilter === 'ALL' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}
              >
                All ({OPTICAL_CODE_CATALOG.length})
              </button>
              <button
                onClick={() => setCatalogFilter('1D')}
                className={`px-3 py-1 rounded-lg transition ${catalogFilter === '1D' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}
              >
                1D Barcodes
              </button>
              <button
                onClick={() => setCatalogFilter('2D')}
                className={`px-3 py-1 rounded-lg transition ${catalogFilter === '2D' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}
              >
                2D Matrix & QR
              </button>
            </div>
          </div>

          {/* Search Box */}
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={catalogSearch}
              onChange={(e) => setCatalogSearch(e.target.value)}
              placeholder="Search by code type, full form, or industry use case..."
              className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:bg-white transition"
            />
          </div>

          {/* Catalog Table / Grid */}
          <div className="overflow-x-auto rounded-xl border border-slate-200/80">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-700 font-bold">
                  <th className="py-2.5 px-3.5 w-32">Type</th>
                  <th className="py-2.5 px-3.5 w-60">Full Form</th>
                  <th className="py-2.5 px-3.5">What It Is Used For</th>
                  <th className="py-2.5 px-3.5 w-36 hidden md:table-cell">Category</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredCatalog.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="py-6 text-center text-slate-400">
                      No matching symbology types found for &quot;{catalogSearch}&quot;
                    </td>
                  </tr>
                ) : (
                  filteredCatalog.map((item, idx) => (
                    <tr key={idx} className="hover:bg-slate-50/70 transition">
                      <td className="py-2.5 px-3.5 font-bold text-slate-900">
                        <span className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-800 border border-slate-200 text-[11px] font-mono">
                          {item.type}
                        </span>
                      </td>
                      <td className="py-2.5 px-3.5 font-medium text-slate-700">
                        {item.fullForm}
                      </td>
                      <td className="py-2.5 px-3.5 text-slate-600 leading-relaxed">
                        {item.useFor}
                      </td>
                      <td className="py-2.5 px-3.5 hidden md:table-cell">
                        <span className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                          item.category.includes('2D') || item.category.includes('QR')
                            ? 'bg-indigo-50 text-indigo-700 border border-indigo-200' 
                            : 'bg-sky-50 text-sky-700 border border-sky-200'
                        }`}>
                          {item.category}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

    </div>
  );
}
