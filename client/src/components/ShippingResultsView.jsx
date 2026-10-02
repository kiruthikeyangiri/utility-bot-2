import React, { useState } from 'react';
import { 
  FileText, 
  MapPin, 
  User, 
  Phone, 
  Mail, 
  Building, 
  Truck, 
  Package, 
  ShoppingBag, 
  Calendar, 
  CreditCard, 
  Hash, 
  Barcode, 
  Code, 
  AlertTriangle,
  Copy,
  Check,
  CheckCircle2,
  DollarSign,
  Scale,
  Maximize2
} from 'lucide-react';
import CodeResults from './CodeResults';
import JsonViewer from './JsonViewer';

function SingleLabelCard({ label, index }) {
  const [activeTab, setActiveTab] = useState('details');
  const [copiedOcr, setCopiedOcr] = useState(false);

  const handleCopyOcr = () => {
    if (!label.raw_ocr_text) return;
    navigator.clipboard.writeText(label.raw_ocr_text);
    setCopiedOcr(true);
    setTimeout(() => setCopiedOcr(false), 2000);
  };

  const shipTo = label.ship_to || {};
  const shipFrom = label.ship_from || {};
  const order = label.order || {};
  const pkg = label.package || {};
  const items = label.items || [];
  const barcodes = label.barcodes || [];
  const qrCodes = label.qr_codes || [];

  return (
    <div className="bg-white border border-slate-200/90 rounded-2xl shadow-sm overflow-hidden space-y-0 transition-all hover:shadow-md">
      
      {/* Label Header */}
      <div className="p-5 bg-gradient-to-r from-slate-50 via-slate-50/80 to-white border-b border-slate-200 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center space-x-3.5">
          <div className="w-10 h-10 rounded-xl bg-sky-600 text-white flex items-center justify-center font-bold text-sm shadow-md shadow-sky-600/20">
            #{label.image_index || index + 1}
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-base font-bold text-slate-900">
                Shipping Label #{label.image_index || index + 1}
              </h3>
              {label.courier && (
                <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200">
                  {label.courier}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 font-mono mt-0.5">
              {label.image_name || `Image_${index + 1}.jpg`}
            </p>
          </div>
        </div>

        {/* Confidence & Badges */}
        <div className="flex items-center space-x-3">
          {label.ocr_confidence > 0 && (
            <div className="flex items-center space-x-1.5 px-3 py-1 rounded-lg bg-emerald-50 border border-emerald-200 text-xs text-emerald-800">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
              <span className="font-semibold">{Math.round(label.ocr_confidence)}% OCR Confidence</span>
            </div>
          )}

          {barcodes.length > 0 && (
            <div className="hidden sm:flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-slate-100 text-slate-700 text-xs font-medium border border-slate-200">
              <Barcode className="w-3.5 h-3.5" />
              <span>{barcodes.length} Barcode{barcodes.length > 1 ? 's' : ''}</span>
            </div>
          )}
        </div>
      </div>

      {/* Warnings Banner if present */}
      {label.warnings && label.warnings.length > 0 && (
        <div className="mx-5 mt-4 p-3 bg-amber-50 border border-amber-200 rounded-xl flex items-start space-x-2 text-xs text-amber-800">
          <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            {label.warnings.map((w, wIdx) => (
              <p key={wIdx}>{w}</p>
            ))}
          </div>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="px-5 pt-3 border-b border-slate-200 flex space-x-1 sm:space-x-2 bg-slate-50/40">
        <button
          onClick={() => setActiveTab('details')}
          className={`flex items-center space-x-2 py-2.5 px-3.5 rounded-t-xl text-xs font-bold transition border-b-2 ${
            activeTab === 'details'
              ? 'border-sky-600 text-sky-700 bg-white shadow-sm'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <FileText className="w-4 h-4" />
          <span>Details</span>
        </button>

        <button
          onClick={() => setActiveTab('ocr')}
          className={`flex items-center space-x-2 py-2.5 px-3.5 rounded-t-xl text-xs font-bold transition border-b-2 ${
            activeTab === 'ocr'
              ? 'border-sky-600 text-sky-700 bg-white shadow-sm'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <FileText className="w-4 h-4" />
          <span>OCR Text</span>
        </button>

        <button
          onClick={() => setActiveTab('codes')}
          className={`flex items-center space-x-2 py-2.5 px-3.5 rounded-t-xl text-xs font-bold transition border-b-2 ${
            activeTab === 'codes'
              ? 'border-sky-600 text-sky-700 bg-white shadow-sm'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Barcode className="w-4 h-4" />
          <span>Barcode / QR ({barcodes.length + qrCodes.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('json')}
          className={`flex items-center space-x-2 py-2.5 px-3.5 rounded-t-xl text-xs font-bold transition border-b-2 ${
            activeTab === 'json'
              ? 'border-sky-600 text-sky-700 bg-white shadow-sm'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Code className="w-4 h-4" />
          <span>JSON</span>
        </button>
      </div>

      {/* Tab Contents */}
      <div className="p-5">
        
        {/* TAB 1: DETAILS */}
        {activeTab === 'details' && (
          <div className="space-y-6">
            
            {/* 1. Address Blocks: SHIP TO & SHIP FROM */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              
              {/* SHIP TO (Receiver) */}
              <div className="bg-sky-50/40 border border-sky-100 rounded-2xl p-4 space-y-3">
                <div className="flex items-center space-x-2 pb-2 border-b border-sky-100 text-sky-900">
                  <div className="p-1.5 rounded-lg bg-sky-600 text-white">
                    <MapPin className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-xs font-bold uppercase tracking-wider">SHIP TO (Receiver)</h4>
                    <p className="text-[11px] text-sky-700">Delivery destination</p>
                  </div>
                </div>

                <div className="space-y-2 text-xs">
                  <div>
                    <span className="text-slate-500 text-[11px] block">Name</span>
                    <span className="font-bold text-slate-900 text-sm">
                      {shipTo.name || <span className="text-slate-400 font-normal italic">Not specified</span>}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <span className="text-slate-500 text-[11px] block">Phone</span>
                      <span className="font-semibold text-slate-800">
                        {shipTo.phone || <span className="text-slate-400 font-normal italic">None</span>}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500 text-[11px] block">Postal Code</span>
                      <span className="font-mono font-bold text-slate-900">
                        {shipTo.postal_code || <span className="text-slate-400 font-normal italic">None</span>}
                      </span>
                    </div>
                  </div>

                  {shipTo.email && (
                    <div>
                      <span className="text-slate-500 text-[11px] block">Email</span>
                      <span className="text-slate-700 font-medium">{shipTo.email}</span>
                    </div>
                  )}

                  <div>
                    <span className="text-slate-500 text-[11px] block">Address</span>
                    <p className="text-slate-800 font-medium whitespace-pre-line leading-relaxed bg-white/70 p-2.5 rounded-lg border border-sky-100">
                      {shipTo.address || <span className="text-slate-400 font-normal italic">No address detected</span>}
                    </p>
                  </div>

                  <div className="grid grid-cols-3 gap-2 pt-1 text-[11px]">
                    <div>
                      <span className="text-slate-500 block">City</span>
                      <span className="font-semibold text-slate-700">{shipTo.city || '—'}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">State</span>
                      <span className="font-semibold text-slate-700">{shipTo.state || '—'}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Country</span>
                      <span className="font-semibold text-slate-700">{shipTo.country || 'India'}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* SHIP FROM (Sender) */}
              <div className="bg-slate-50/60 border border-slate-200 rounded-2xl p-4 space-y-3">
                <div className="flex items-center space-x-2 pb-2 border-b border-slate-200 text-slate-800">
                  <div className="p-1.5 rounded-lg bg-slate-700 text-white">
                    <Building className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-xs font-bold uppercase tracking-wider">SHIP FROM (Sender)</h4>
                    <p className="text-[11px] text-slate-500">Origin / Return address</p>
                  </div>
                </div>

                <div className="space-y-2 text-xs">
                  <div>
                    <span className="text-slate-500 text-[11px] block">Company / Name</span>
                    <span className="font-bold text-slate-900 text-sm">
                      {shipFrom.company || shipFrom.name || <span className="text-slate-400 font-normal italic">Not specified</span>}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <span className="text-slate-500 text-[11px] block">Phone</span>
                      <span className="font-semibold text-slate-800">
                        {shipFrom.phone || <span className="text-slate-400 font-normal italic">None</span>}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500 text-[11px] block">Postal Code</span>
                      <span className="font-mono font-bold text-slate-900">
                        {shipFrom.postal_code || <span className="text-slate-400 font-normal italic">None</span>}
                      </span>
                    </div>
                  </div>

                  {shipFrom.email && (
                    <div>
                      <span className="text-slate-500 text-[11px] block">Email</span>
                      <span className="text-slate-700 font-medium">{shipFrom.email}</span>
                    </div>
                  )}

                  <div>
                    <span className="text-slate-500 text-[11px] block">Address</span>
                    <p className="text-slate-800 font-medium whitespace-pre-line leading-relaxed bg-white/70 p-2.5 rounded-lg border border-slate-200">
                      {shipFrom.address || <span className="text-slate-400 font-normal italic">No address detected</span>}
                    </p>
                  </div>

                  <div className="grid grid-cols-3 gap-2 pt-1 text-[11px]">
                    <div>
                      <span className="text-slate-500 block">City</span>
                      <span className="font-semibold text-slate-700">{shipFrom.city || '—'}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">State</span>
                      <span className="font-semibold text-slate-700">{shipFrom.state || '—'}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Country</span>
                      <span className="font-semibold text-slate-700">{shipFrom.country || 'India'}</span>
                    </div>
                  </div>
                </div>
              </div>

            </div>

            {/* 2. ORDER & PACKAGE INFORMATION */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              
              {/* ORDER DETAILS */}
              <div className="bg-white border border-slate-200 rounded-2xl p-4 space-y-3">
                <div className="flex items-center space-x-2 pb-2 border-b border-slate-100 text-slate-800">
                  <div className="p-1.5 rounded-lg bg-indigo-50 text-indigo-700">
                    <Truck className="w-4 h-4" />
                  </div>
                  <h4 className="text-xs font-bold uppercase tracking-wider">ORDER DETAILS</h4>
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <span className="text-slate-500 text-[11px] block">AWB Number</span>
                    <span className="font-mono font-bold text-slate-900 select-all">
                      {order.awb_number || <span className="text-slate-400 font-normal italic">—</span>}
                    </span>
                  </div>

                  <div>
                    <span className="text-slate-500 text-[11px] block">Tracking Number</span>
                    <span className="font-mono font-bold text-slate-900 select-all">
                      {order.tracking_number || <span className="text-slate-400 font-normal italic">—</span>}
                    </span>
                  </div>

                  <div>
                    <span className="text-slate-500 text-[11px] block">Order ID</span>
                    <span className="font-mono font-semibold text-slate-800 select-all">
                      {order.order_id || <span className="text-slate-400 font-normal italic">—</span>}
                    </span>
                  </div>

                  <div>
                    <span className="text-slate-500 text-[11px] block">Payment Type</span>
                    {order.payment_type ? (
                      <span className={`inline-block px-2 py-0.5 rounded-full text-[11px] font-bold border ${
                        order.payment_type.includes('COD') 
                          ? 'bg-amber-50 text-amber-800 border-amber-200' 
                          : 'bg-emerald-50 text-emerald-800 border-emerald-200'
                      }`}>
                        {order.payment_type}
                      </span>
                    ) : (
                      <span className="text-slate-400 italic">—</span>
                    )}
                  </div>

                  <div>
                    <span className="text-slate-500 text-[11px] block">Shipping Date</span>
                    <span className="font-medium text-slate-700">
                      {order.shipping_date || <span className="text-slate-400 italic">—</span>}
                    </span>
                  </div>

                  <div>
                    <span className="text-slate-500 text-[11px] block">Remarks</span>
                    <span className="font-medium text-slate-700 truncate block">
                      {order.remarks || <span className="text-slate-400 italic">—</span>}
                    </span>
                  </div>
                </div>
              </div>

              {/* PACKAGE INFORMATION */}
              <div className="bg-white border border-slate-200 rounded-2xl p-4 space-y-3">
                <div className="flex items-center space-x-2 pb-2 border-b border-slate-100 text-slate-800">
                  <div className="p-1.5 rounded-lg bg-teal-50 text-teal-700">
                    <Package className="w-4 h-4" />
                  </div>
                  <h4 className="text-xs font-bold uppercase tracking-wider">PACKAGE INFORMATION</h4>
                </div>

                <div className="grid grid-cols-2 gap-4 text-xs">
                  <div className="bg-slate-50/70 p-3 rounded-xl border border-slate-100">
                    <div className="flex items-center space-x-1.5 text-slate-500 text-[11px] mb-1">
                      <Scale className="w-3.5 h-3.5 text-teal-600" />
                      <span>Weight</span>
                    </div>
                    <span className="text-sm font-bold text-slate-900">
                      {pkg.weight || <span className="text-slate-400 font-normal italic">Not specified</span>}
                    </span>
                  </div>

                  <div className="bg-slate-50/70 p-3 rounded-xl border border-slate-100">
                    <div className="flex items-center space-x-1.5 text-slate-500 text-[11px] mb-1">
                      <Maximize2 className="w-3.5 h-3.5 text-teal-600" />
                      <span>Dimensions</span>
                    </div>
                    <span className="text-sm font-bold text-slate-900">
                      {pkg.dimensions || <span className="text-slate-400 font-normal italic">Not specified</span>}
                    </span>
                  </div>
                </div>
              </div>

            </div>

            {/* 3. PRODUCT / ITEM TABLE */}
            <div className="bg-white border border-slate-200 rounded-2xl p-4 space-y-3">
              <div className="flex items-center space-x-2 pb-2 border-b border-slate-100 text-slate-800">
                <div className="p-1.5 rounded-lg bg-emerald-50 text-emerald-700">
                  <ShoppingBag className="w-4 h-4" />
                </div>
                <h4 className="text-xs font-bold uppercase tracking-wider">
                  ITEMS / PRODUCT MANIFEST ({items.length})
                </h4>
              </div>

              {items.length === 0 ? (
                <div className="p-4 bg-slate-50 border border-dashed border-slate-200 rounded-xl text-center text-xs text-slate-500">
                  No line items or SKU table detected on this label.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-200 bg-slate-50/70 text-slate-600">
                        <th className="py-2.5 px-3 font-semibold rounded-l-lg">#</th>
                        <th className="py-2.5 px-3 font-semibold">Product Description</th>
                        <th className="py-2.5 px-3 font-semibold text-center">Qty</th>
                        <th className="py-2.5 px-3 font-semibold text-right">Price</th>
                        <th className="py-2.5 px-3 font-semibold text-center">Curr</th>
                        <th className="py-2.5 px-3 font-semibold text-right rounded-r-lg">Total</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {items.map((it, itIdx) => (
                        <tr key={itIdx} className="hover:bg-slate-50/60 transition">
                          <td className="py-2.5 px-3 text-slate-400 font-mono">{itIdx + 1}</td>
                          <td className="py-2.5 px-3 font-semibold text-slate-900">
                            {it.product || 'Item'}
                          </td>
                          <td className="py-2.5 px-3 text-center font-mono text-slate-700">
                            {it.quantity != null ? it.quantity : '—'}
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono text-slate-700">
                            {it.price != null ? it.price.toLocaleString() : '—'}
                          </td>
                          <td className="py-2.5 px-3 text-center text-slate-500 font-mono text-[11px]">
                            {it.currency || 'INR'}
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono font-bold text-slate-900">
                            {it.total != null ? it.total.toLocaleString() : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

          </div>
        )}

        {/* TAB 2: OCR TEXT */}
        {activeTab === 'ocr' && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wide">
                  Raw RapidOCR Text Lines
                </h4>
                <p className="text-[11px] text-slate-500">
                  Full text detected with bounding coordinate engine
                </p>
              </div>
              <button
                onClick={handleCopyOcr}
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-medium transition shadow-sm"
              >
                {copiedOcr ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-600" />
                    <span className="text-emerald-700 font-semibold">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5 text-slate-500" />
                    <span>Copy Text</span>
                  </>
                )}
              </button>
            </div>

            <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 max-h-[450px] overflow-auto">
              <pre className="text-xs text-slate-800 font-mono whitespace-pre-wrap leading-relaxed select-all">
                {label.raw_ocr_text || 'No text detected on this label.'}
              </pre>
            </div>
          </div>
        )}

        {/* TAB 3: BARCODE / QR */}
        {activeTab === 'codes' && (
          <CodeResults 
            barcodes={label.barcodes || []} 
            qr_codes={label.qr_codes || []} 
          />
        )}

        {/* TAB 4: JSON PAYLOAD */}
        {activeTab === 'json' && (
          <JsonViewer 
            data={label} 
          />
        )}

      </div>

    </div>
  );
}

export default function ShippingResultsView({ results = [], onScanMore }) {
  if (!results || results.length === 0) return null;

  return (
    <div className="space-y-6 animate-in fade-in-50 duration-300">
      
      {/* Top Results Overview Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 bg-sky-50/50 border border-sky-100 rounded-2xl">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-xl bg-sky-600 text-white shadow-sm">
            <Package className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              Extraction Completed ({results.length} Label{results.length > 1 ? 's' : ''})
            </h3>
            <p className="text-xs text-slate-600">
              Every shipping label was analyzed independently with zero cross-contamination.
            </p>
          </div>
        </div>

        {onScanMore && (
          <button
            onClick={onScanMore}
            className="px-4 py-2 rounded-xl bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs border border-slate-200 hover:border-slate-300 transition shadow-sm"
          >
            Scan More Labels
          </button>
        )}
      </div>

      {/* Separate Result Card for each uploaded image */}
      <div className="space-y-6">
        {results.map((item, idx) => (
          <SingleLabelCard key={idx} label={item} index={idx} />
        ))}
      </div>

    </div>
  );
}
