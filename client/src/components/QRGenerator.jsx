import React, { useState } from 'react';
import { 
  QrCode, 
  Download, 
  Copy, 
  Check, 
  RefreshCw, 
  ShieldCheck, 
  AlertCircle, 
  Link as LinkIcon,
  Phone,
  Mail,
  MessageSquare,
  Wifi,
  User,
  MapPin,
  Tag,
  ShoppingBag,
  Truck,
  FileCode,
  Info
} from 'lucide-react';
import { generateQrApi } from '../services/api';

const QR_TYPES = [
  { id: 'url', label: 'Website URL', icon: LinkIcon, desc: 'Opens a link in mobile browser' },
  { id: 'text', label: 'Plain Text', icon: QrCode, desc: 'Freeform text and notes' },
  { id: 'phone', label: 'Phone Number', icon: Phone, desc: 'Direct dial phone call' },
  { id: 'email', label: 'Email Address', icon: Mail, desc: 'Pre-filled email compose' },
  { id: 'sms', label: 'SMS Message', icon: MessageSquare, desc: 'Pre-filled text message' },
  { id: 'wifi', label: 'Wi-Fi Network', icon: Wifi, desc: 'Instant 1-tap Wi-Fi connection' },
  { id: 'vcard', label: 'Contact / vCard', icon: User, desc: 'Standard vCard address book contact' },
  { id: 'location', label: 'Location (Geo)', icon: MapPin, desc: 'Map coordinates & navigation' },
  { id: 'product', label: 'Product / SKU', icon: Tag, desc: 'Inventory and catalog identifier' },
  { id: 'order', label: 'Order ID', icon: ShoppingBag, desc: 'E-commerce purchase identifier' },
  { id: 'shipping', label: 'Shipping / AWB', icon: Truck, desc: 'Logistics tracking or AWB number' },
  { id: 'json', label: 'Structured JSON', icon: FileCode, desc: 'API / ERP payload data' }
];

const ERROR_CORRECTION_OPTIONS = [
  { value: 'L', label: 'L — Low (~7%)', desc: 'Highest storage capacity, lowest damage recovery' },
  { value: 'M', label: 'M — Medium (~15%)', desc: 'Recommended standard for shipping & web use' },
  { value: 'Q', label: 'Q — Quartile (~25%)', desc: 'High recovery for scratched/damaged thermal labels' },
  { value: 'H', label: 'H — High (~30%)', desc: 'Maximum recovery, lower data capacity' }
];

const SIZE_OPTIONS = [
  { value: 200, label: '200 × 200 px (Thumbnail)' },
  { value: 300, label: '300 × 300 px (Compact)' },
  { value: 400, label: '400 × 400 px (Standard Default)' },
  { value: 600, label: '600 × 600 px (High Res)' },
  { value: 800, label: '800 × 800 px (Print Quality)' },
  { value: 1200, label: '1200 × 1200 px (Ultra HD)' }
];

export default function QRGenerator() {
  const [qrType, setQrType] = useState('url');
  const [errorCorrection, setErrorCorrection] = useState('M');
  const [size, setSize] = useState(400);
  const [format, setFormat] = useState('png');

  // Dynamic Form Fields
  const [textVal, setTextVal] = useState('');
  const [urlVal, setUrlVal] = useState('https://');
  const [phoneVal, setPhoneVal] = useState('');
  const [emailFields, setEmailFields] = useState({ email: '', subject: '', body: '' });
  const [smsFields, setSmsFields] = useState({ phone: '', message: '' });
  const [wifiFields, setWifiFields] = useState({ ssid: '', password: '', auth_type: 'WPA', hidden: false });
  const [vcardFields, setVcardFields] = useState({ name: '', phone: '', email: '', company: '', title: '', address: '', url: '' });
  const [locationFields, setLocationFields] = useState({ latitude: '', longitude: '' });
  const [productVal, setProductVal] = useState('');
  const [orderVal, setOrderVal] = useState('');
  const [shippingFields, setShippingFields] = useState({ shipping_id: '', tracking_url: '' });
  const [jsonVal, setJsonVal] = useState('{\n  "id": "ITEM-101",\n  "status": "ACTIVE"\n}');

  // UI States
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [copied, setCopied] = useState(false);

  const handleGenerate = async (e) => {
    if (e) e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      let payloadData = null;
      let payloadFields = {};

      switch (qrType) {
        case 'url':
          payloadData = urlVal;
          break;
        case 'text':
          payloadData = textVal;
          break;
        case 'phone':
          payloadData = phoneVal;
          break;
        case 'email':
          payloadFields = emailFields;
          break;
        case 'sms':
          payloadFields = smsFields;
          break;
        case 'wifi':
          payloadFields = wifiFields;
          break;
        case 'vcard':
          payloadFields = vcardFields;
          break;
        case 'location':
          payloadFields = locationFields;
          break;
        case 'product':
          payloadData = productVal;
          break;
        case 'order':
          payloadData = orderVal;
          break;
        case 'shipping':
          payloadFields = shippingFields;
          break;
        case 'json':
          payloadData = jsonVal;
          break;
        default:
          payloadData = textVal;
      }

      const res = await generateQrApi({
        type: qrType,
        data: payloadData,
        fields: payloadFields,
        size: Number(size),
        error_correction: errorCorrection,
        format: format
      });

      setResult(res);
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Failed to generate QR Code.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = (text) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    if (!result?.image_base64) return;
    const a = document.createElement('a');
    a.href = result.image_base64;
    a.download = `qrcode_${result.qr_type}_${Date.now()}.${result.format || 'png'}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const handleReset = () => {
    setResult(null);
    setError(null);
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
      
      {/* LEFT COLUMN: QR CONFIGURATION FORM */}
      <div className="lg:col-span-7 bg-white border border-slate-200/90 rounded-2xl p-6 shadow-sm space-y-6">
        <div>
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-xl bg-sky-50 text-sky-600 border border-sky-100">
              <QrCode className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">QR Code Generator</h3>
              <p className="text-xs text-slate-500">
                Create verified QR codes for websites, Wi-Fi, contacts, logistics, and structured data.
              </p>
            </div>
          </div>
        </div>

        {error && (
          <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl flex items-start space-x-2.5 text-xs text-rose-800">
            <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
            <div className="leading-relaxed">{error}</div>
          </div>
        )}

        <form onSubmit={handleGenerate} className="space-y-5">
          
          {/* 1. SELECT QR TYPE */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
              1. Select QR Payload Type
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
              {QR_TYPES.map((t) => {
                const Icon = t.icon;
                const isSelected = qrType === t.id;
                return (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => {
                      setQrType(t.id);
                      setError(null);
                    }}
                    className={`flex flex-col items-start p-2.5 rounded-xl border text-left transition ${
                      isSelected
                        ? 'border-sky-500 bg-sky-50/60 text-sky-900 shadow-sm ring-1 ring-sky-500/30'
                        : 'border-slate-200 bg-white hover:bg-slate-50 text-slate-700'
                    }`}
                  >
                    <Icon className={`w-4 h-4 mb-1 ${isSelected ? 'text-sky-600' : 'text-slate-500'}`} />
                    <span className="text-xs font-semibold leading-tight">{t.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* 2. DYNAMIC INPUT FIELDS */}
          <div className="p-4 bg-slate-50/70 border border-slate-200/80 rounded-xl space-y-3">
            <div className="flex items-center justify-between pb-1 border-b border-slate-200/60 text-xs font-bold text-slate-700 uppercase">
              <span>2. Fill Content ({QR_TYPES.find(t => t.id === qrType)?.label})</span>
              <span className="text-[11px] font-normal lowercase text-slate-500">
                {QR_TYPES.find(t => t.id === qrType)?.desc}
              </span>
            </div>

            {/* URL */}
            {qrType === 'url' && (
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Website URL</label>
                <input
                  type="url"
                  required
                  value={urlVal}
                  onChange={(e) => setUrlVal(e.target.value)}
                  placeholder="https://example.com/portal"
                  className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 font-mono text-slate-800"
                />
              </div>
            )}

            {/* TEXT */}
            {qrType === 'text' && (
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Plain Text Content</label>
                <textarea
                  required
                  rows={3}
                  value={textVal}
                  onChange={(e) => setTextVal(e.target.value)}
                  placeholder="Type any text, message, or notes..."
                  className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 text-slate-800"
                />
              </div>
            )}

            {/* PHONE */}
            {qrType === 'phone' && (
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Phone Number</label>
                <input
                  type="tel"
                  required
                  value={phoneVal}
                  onChange={(e) => setPhoneVal(e.target.value)}
                  placeholder="+91 98765 43210"
                  className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 font-mono text-slate-800"
                />
              </div>
            )}

            {/* EMAIL */}
            {qrType === 'email' && (
              <div className="space-y-2">
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">Recipient Email</label>
                  <input
                    type="email"
                    required
                    value={emailFields.email}
                    onChange={(e) => setEmailFields({ ...emailFields, email: e.target.value })}
                    placeholder="contact@company.com"
                    className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 text-slate-800"
                  />
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">Subject (Optional)</label>
                    <input
                      type="text"
                      value={emailFields.subject}
                      onChange={(e) => setEmailFields({ ...emailFields, subject: e.target.value })}
                      placeholder="Inquiry / Tracking Request"
                      className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 text-slate-800"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">Pre-filled Message</label>
                    <input
                      type="text"
                      value={emailFields.body}
                      onChange={(e) => setEmailFields({ ...emailFields, body: e.target.value })}
                      placeholder="Hello, please assist..."
                      className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 text-slate-800"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* SMS */}
            {qrType === 'sms' && (
              <div className="space-y-2">
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">Phone Number</label>
                  <input
                    type="tel"
                    required
                    value={smsFields.phone}
                    onChange={(e) => setSmsFields({ ...smsFields, phone: e.target.value })}
                    placeholder="+91 98765 43210"
                    className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 font-mono text-slate-800"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">SMS Text</label>
                  <textarea
                    rows={2}
                    value={smsFields.message}
                    onChange={(e) => setSmsFields({ ...smsFields, message: e.target.value })}
                    placeholder="Type SMS message..."
                    className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 text-slate-800"
                  />
                </div>
              </div>
            )}

            {/* WI-FI */}
            {qrType === 'wifi' && (
              <div className="space-y-2.5">
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">Network Name (SSID)</label>
                  <input
                    type="text"
                    required
                    value={wifiFields.ssid}
                    onChange={(e) => setWifiFields({ ...wifiFields, ssid: e.target.value })}
                    placeholder="Office_Guest_WiFi"
                    className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 font-medium text-slate-800"
                  />
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">Password</label>
                    <input
                      type="text"
                      value={wifiFields.password}
                      onChange={(e) => setWifiFields({ ...wifiFields, password: e.target.value })}
                      placeholder="Password123"
                      className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 font-mono text-slate-800"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">Encryption</label>
                    <select
                      value={wifiFields.auth_type}
                      onChange={(e) => setWifiFields({ ...wifiFields, auth_type: e.target.value })}
                      className="w-full px-3 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 text-slate-800"
                    >
                      <option value="WPA">WPA / WPA2 / WPA3 (Standard)</option>
                      <option value="WEP">WEP (Legacy)</option>
                      <option value="NOPASS">None (Open Network)</option>
                    </select>
                  </div>
                </div>
              </div>
            )}

            {/* VCARD */}
            {qrType === 'vcard' && (
              <div className="space-y-2">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">Full Name</label>
                    <input
                      type="text"
                      required
                      value={vcardFields.name}
                      onChange={(e) => setVcardFields({ ...vcardFields, name: e.target.value })}
                      placeholder="John Doe"
                      className="w-full px-3 py-1.5 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 text-slate-800"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">Phone</label>
                    <input
                      type="tel"
                      value={vcardFields.phone}
                      onChange={(e) => setVcardFields({ ...vcardFields, phone: e.target.value })}
                      placeholder="+1 (555) 019-2834"
                      className="w-full px-3 py-1.5 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 text-slate-800 font-mono"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">Email</label>
                    <input
                      type="email"
                      value={vcardFields.email}
                      onChange={(e) => setVcardFields({ ...vcardFields, email: e.target.value })}
                      placeholder="john@example.com"
                      className="w-full px-3 py-1.5 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 text-slate-800"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">Company / Organization</label>
                    <input
                      type="text"
                      value={vcardFields.company}
                      onChange={(e) => setVcardFields({ ...vcardFields, company: e.target.value })}
                      placeholder="ACME Corporation"
                      className="w-full px-3 py-1.5 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 text-slate-800"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* LOCATION */}
            {qrType === 'location' && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">Latitude</label>
                  <input
                    type="number"
                    step="any"
                    required
                    value={locationFields.latitude}
                    onChange={(e) => setLocationFields({ ...locationFields, latitude: e.target.value })}
                    placeholder="12.9716"
                    className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 font-mono text-slate-800"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">Longitude</label>
                  <input
                    type="number"
                    step="any"
                    required
                    value={locationFields.longitude}
                    onChange={(e) => setLocationFields({ ...locationFields, longitude: e.target.value })}
                    placeholder="77.5946"
                    className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 font-mono text-slate-800"
                  />
                </div>
              </div>
            )}

            {/* PRODUCT */}
            {qrType === 'product' && (
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Product SKU / Serial ID</label>
                <input
                  type="text"
                  required
                  value={productVal}
                  onChange={(e) => setProductVal(e.target.value)}
                  placeholder="SKU-8921-XL"
                  className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 font-mono text-slate-800"
                />
              </div>
            )}

            {/* ORDER */}
            {qrType === 'order' && (
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Purchase Order ID</label>
                <input
                  type="text"
                  required
                  value={orderVal}
                  onChange={(e) => setOrderVal(e.target.value)}
                  placeholder="ORD-2026-98124"
                  className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 font-mono text-slate-800"
                />
              </div>
            )}

            {/* SHIPPING */}
            {qrType === 'shipping' && (
              <div className="space-y-2">
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">Shipment / AWB ID</label>
                  <input
                    type="text"
                    required
                    value={shippingFields.shipping_id}
                    onChange={(e) => setShippingFields({ ...shippingFields, shipping_id: e.target.value })}
                    placeholder="SHIP-10025 or 9400111899562537689100"
                    className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 font-mono text-slate-800"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">Tracking Portal URL (Optional)</label>
                  <input
                    type="url"
                    value={shippingFields.tracking_url}
                    onChange={(e) => setShippingFields({ ...shippingFields, tracking_url: e.target.value })}
                    placeholder="https://utility.com/shipping/SHIP-10025"
                    className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 font-mono text-slate-800"
                  />
                </div>
              </div>
            )}

            {/* JSON */}
            {qrType === 'json' && (
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">JSON Payload String (Max ~2.8 KB)</label>
                <textarea
                  required
                  rows={4}
                  value={jsonVal}
                  onChange={(e) => setJsonVal(e.target.value)}
                  placeholder='{"awb": "12345", "status": "IN_TRANSIT"}'
                  className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 font-mono text-slate-800"
                />
              </div>
            )}

          </div>

          {/* 3. SETTINGS: ERROR CORRECTION, SIZE, FORMAT */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-[11px] font-bold uppercase tracking-wide text-slate-600 mb-1">
                Error Correction
              </label>
              <select
                value={errorCorrection}
                onChange={(e) => setErrorCorrection(e.target.value)}
                className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-sky-500 text-slate-800 font-medium"
              >
                {ERROR_CORRECTION_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-bold uppercase tracking-wide text-slate-600 mb-1">
                Output Dimension
              </label>
              <select
                value={size}
                onChange={(e) => setSize(Number(e.target.value))}
                className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-sky-500 text-slate-800 font-medium"
              >
                {SIZE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-bold uppercase tracking-wide text-slate-600 mb-1">
                Image Format
              </label>
              <select
                value={format}
                onChange={(e) => setFormat(e.target.value)}
                className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-sky-500 text-slate-800 font-medium"
              >
                <option value="png">PNG (Raster Bitmap - Default)</option>
                <option value="svg">SVG (Scalable Vector Graphic)</option>
              </select>
            </div>
          </div>

          {/* GENERATE BUTTON */}
          <button
            type="submit"
            disabled={loading}
            className="w-full flex items-center justify-center space-x-2 py-3 px-5 rounded-xl bg-sky-600 hover:bg-sky-700 active:scale-[0.99] text-white font-bold text-xs shadow-lg shadow-sky-600/25 transition disabled:opacity-50"
          >
            {loading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Generating & Verifying QR Code...</span>
              </>
            ) : (
              <>
                <QrCode className="w-4 h-4" />
                <span>Generate & Verify QR Code</span>
              </>
            )}
          </button>

        </form>
      </div>

      {/* RIGHT COLUMN: LIVE QR PREVIEW & ACTIONS */}
      <div className="lg:col-span-5 space-y-4">
        <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-sm flex flex-col items-center text-center space-y-4">
          
          <div className="w-full flex items-center justify-between pb-3 border-b border-slate-100">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-700">QR Code Preview</span>
            {result?.verified ? (
              <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 text-[11px] font-bold">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                <span>Verified Readable</span>
              </span>
            ) : result ? (
              <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full bg-amber-50 text-amber-800 border border-amber-200 text-[11px] font-bold">
                <AlertCircle className="w-3.5 h-3.5 text-amber-600" />
                <span>Pending Verification</span>
              </span>
            ) : null}
          </div>

          {/* QR Image Canvas / Preview */}
          <div className="w-full aspect-square max-w-[280px] bg-slate-50 border border-slate-200/80 rounded-2xl p-4 flex items-center justify-center shadow-inner">
            {result?.image_base64 ? (
              <img
                src={result.image_base64}
                alt="Generated QR Code"
                className="w-full h-full object-contain drop-shadow-sm rounded-lg"
              />
            ) : (
              <div className="text-center space-y-2 p-4">
                <QrCode className="w-12 h-12 text-slate-300 mx-auto" />
                <p className="text-xs text-slate-400 font-medium">
                  Fill in the details on the left and click &quot;Generate &amp; Verify QR Code&quot;
                </p>
              </div>
            )}
          </div>

          {/* METADATA & ACTIONS */}
          {result && (
            <div className="w-full space-y-3 pt-2">
              
              {/* Payload box */}
              <div className="text-left bg-slate-50 p-3 rounded-xl border border-slate-200/70 space-y-1">
                <div className="flex items-center justify-between text-[10px] font-bold uppercase text-slate-500">
                  <span>Encoded Payload ({result.byte_size} bytes)</span>
                  <span>EC: {result.error_correction}</span>
                </div>
                <div className="font-mono text-xs font-semibold text-slate-800 break-all select-all max-h-24 overflow-y-auto">
                  {result.payload}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={handleDownload}
                  className="flex items-center justify-center space-x-1.5 py-2.5 px-3 rounded-xl bg-sky-600 hover:bg-sky-700 text-white font-bold text-xs shadow-md shadow-sky-600/20 transition"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download {result.format?.toUpperCase()}</span>
                </button>

                <button
                  onClick={() => handleCopy(result.payload)}
                  className="flex items-center justify-center space-x-1.5 py-2.5 px-3 rounded-xl bg-slate-100 hover:bg-slate-200 border border-slate-200 text-slate-700 font-bold text-xs transition"
                >
                  {copied ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-emerald-600" />
                      <span className="text-emerald-700">Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5 text-slate-600" />
                      <span>Copy Payload</span>
                    </>
                  )}
                </button>
              </div>

              <button
                onClick={handleReset}
                className="w-full text-center text-xs text-slate-500 hover:text-slate-800 pt-1 font-medium transition"
              >
                Generate Another QR Code
              </button>

            </div>
          )}

        </div>
      </div>

    </div>
  );
}
