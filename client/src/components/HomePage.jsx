import React from 'react';
import { 
  ShieldCheck, 
  Package, 
  QrCode, 
  ArrowRight, 
  Sparkles, 
  CheckCircle2, 
  ScanText, 
  Cpu, 
  Layers, 
  Zap,
  Shield,
  FileText
} from 'lucide-react';

export default function HomePage({ onNavigate }) {
  const features = [
    {
      id: 'id_verification',
      title: 'ID Verification',
      subtitle: 'KYC & Identity Document Intelligence',
      badge: 'Identity Suite',
      badgeColor: 'bg-sky-100 text-sky-800 border-sky-200',
      gradient: 'from-sky-600 to-indigo-600',
      borderHover: 'hover:border-indigo-400 group-hover:shadow-indigo-500/10',
      buttonGradient: 'bg-indigo-600 hover:bg-indigo-700 text-white',
      icon: ShieldCheck,
      iconColor: 'text-indigo-600',
      iconBg: 'bg-indigo-50 border-indigo-100',
      description: 'Automated verification and structured data extraction for national identity documents.',
      bullets: [
        'Aadhaar, PAN Card & Driving Licence parsing',
        'OpenCV glare suppression & bilateral denoising',
        'RapidOCR high-precision field extraction',
        'Visual image pipeline & raw OCR inspection'
      ],
      actionLabel: 'Launch ID Verification'
    },
    {
      id: 'shipping_scanner',
      title: 'Shipping Label Scanner',
      subtitle: 'Multi-Image Logistics & Waybill Parser',
      badge: 'Logistics AI',
      badgeColor: 'bg-emerald-100 text-emerald-800 border-emerald-200',
      gradient: 'from-emerald-600 to-teal-600',
      borderHover: 'hover:border-emerald-400 group-hover:shadow-emerald-500/10',
      buttonGradient: 'bg-emerald-600 hover:bg-emerald-700 text-white',
      icon: Package,
      iconColor: 'text-emerald-600',
      iconBg: 'bg-emerald-50 border-emerald-100',
      description: 'End-to-end shipping label intelligence with automated multi-angle image stitching.',
      bullets: [
        'Upload 1–3 label photos per shipment',
        'Deterministic tracking cross-check (High/Medium/Mismatch)',
        'Extracted Shipper, Consignee, Order & Items',
        'Multi-pass ZXing-CPP 1D/2D code decode'
      ],
      actionLabel: 'Launch Shipping Scanner'
    },
    {
      id: 'qr_tools',
      title: 'QR & Barcode Tools',
      subtitle: 'Generation & Standalone Matrix Scanner',
      badge: 'Code Engine',
      badgeColor: 'bg-violet-100 text-violet-800 border-violet-200',
      gradient: 'from-violet-600 to-purple-600',
      borderHover: 'hover:border-violet-400 group-hover:shadow-violet-500/10',
      buttonGradient: 'bg-violet-600 hover:bg-violet-700 text-white',
      icon: QrCode,
      iconColor: 'text-violet-600',
      iconBg: 'bg-violet-50 border-violet-100',
      description: 'Generate standard compliant QR codes and scan any 1D barcode or 2D matrix directly.',
      bullets: [
        '12 QR Payload types (URL, WiFi, vCard, Geo, SMS)',
        'Error correction (L, M, Q, H) & auto-verification',
        'Barcode scanner (Code 128, EAN, UPC, ITF, PDF417)',
        'High-resolution PNG & SVG base64 export'
      ],
      actionLabel: 'Launch QR & Barcode Tools'
    }
  ];

  return (
    <div className="space-y-10 py-4 animate-in fade-in duration-300">
      
      {/* Hero Section */}
      <div className="text-center space-y-3 max-w-3xl mx-auto pt-2">
        <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-indigo-50 border border-indigo-200 text-indigo-700 text-xs font-semibold shadow-xs">
          <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
          <span>Utility Bot 2.0 • AI-Powered Document & Vision Suite</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
          Select a Tool to Begin
        </h1>
        <p className="text-sm sm:text-base text-slate-600 leading-relaxed">
          Streamline ID validation, logistics waybill extraction, and QR/Barcode workflows with high-accuracy computer vision and AI.
        </p>
      </div>

      {/* 3 Core Workflow Cards (Matching User Sketch) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 sm:gap-8">
        {features.map((feat) => {
          const Icon = feat.icon;
          return (
            <div
              key={feat.id}
              onClick={() => onNavigate(feat.id)}
              className={`group relative bg-white border border-slate-200/90 rounded-3xl p-6 sm:p-7 shadow-sm hover:shadow-xl transition-all duration-300 flex flex-col justify-between cursor-pointer ${feat.borderHover} hover:-translate-y-1`}
            >
              {/* Card Header */}
              <div className="space-y-4">
                <div className="flex items-start justify-between">
                  <div className={`w-14 h-14 rounded-2xl ${feat.iconBg} border flex items-center justify-center shadow-sm group-hover:scale-110 transition-transform duration-300`}>
                    <Icon className={`w-7 h-7 ${feat.iconColor}`} />
                  </div>
                  <span className={`text-[11px] font-bold px-2.5 py-1 rounded-full border ${feat.badgeColor}`}>
                    {feat.badge}
                  </span>
                </div>

                <div>
                  <h2 className="text-xl font-bold text-slate-900 group-hover:text-indigo-600 transition-colors">
                    {feat.title}
                  </h2>
                  <p className="text-xs font-semibold text-slate-500 mt-0.5">
                    {feat.subtitle}
                  </p>
                  <p className="text-xs text-slate-600 mt-2.5 leading-relaxed">
                    {feat.description}
                  </p>
                </div>

                {/* Bullets */}
                <div className="pt-2 border-t border-slate-100 space-y-2">
                  {feat.bullets.map((bullet, idx) => (
                    <div key={idx} className="flex items-start space-x-2 text-xs text-slate-700">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0 mt-0.5" />
                      <span className="leading-tight">{bullet}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Action Button */}
              <div className="pt-6 mt-4">
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onNavigate(feat.id);
                  }}
                  className={`w-full py-3 px-4 rounded-xl font-semibold text-xs shadow-md transition-all duration-200 flex items-center justify-center space-x-2 cursor-pointer ${feat.buttonGradient} active:scale-[0.98]`}
                >
                  <span>{feat.actionLabel}</span>
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Capabilities & Specifications Footer Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 rounded-3xl p-6 sm:p-8 text-white shadow-lg space-y-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-6">
          <div>
            <h3 className="text-base font-bold tracking-tight">Enterprise Infrastructure & Pipeline Highlights</h3>
            <p className="text-xs text-slate-400 mt-1">Multi-modal AI pipeline optimized for zero data leakages and rapid processing</p>
          </div>
          <div className="flex items-center space-x-2 text-xs font-semibold px-3 py-1.5 rounded-xl bg-white/10 backdrop-blur border border-white/10">
            <Shield className="w-3.5 h-3.5 text-emerald-400" />
            <span>30-Day Auto Retention Active</span>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 sm:gap-6 text-xs">
          <div className="space-y-1.5 p-3 rounded-2xl bg-white/5 border border-white/5">
            <div className="flex items-center space-x-2 text-sky-400 font-semibold">
              <Cpu className="w-4 h-4" />
              <span>Vision OCR Engine</span>
            </div>
            <p className="text-slate-300 text-[11px] leading-relaxed">
              RapidOCR on ONNX runtime with automated image thresholding and deskew.
            </p>
          </div>

          <div className="space-y-1.5 p-3 rounded-2xl bg-white/5 border border-white/5">
            <div className="flex items-center space-x-2 text-emerald-400 font-semibold">
              <Zap className="w-4 h-4" />
              <span>Barcode Matrix</span>
            </div>
            <p className="text-slate-300 text-[11px] leading-relaxed">
              12 multi-pass filters with ZXing-CPP engine & fallback OpenCV detection.
            </p>
          </div>

          <div className="space-y-1.5 p-3 rounded-2xl bg-white/5 border border-white/5">
            <div className="flex items-center space-x-2 text-violet-400 font-semibold">
              <Layers className="w-4 h-4" />
              <span>Multi-Source Match</span>
            </div>
            <p className="text-slate-300 text-[11px] leading-relaxed">
              Deterministic cross-checking between OCR text and decoded barcode data.
            </p>
          </div>

          <div className="space-y-1.5 p-3 rounded-2xl bg-white/5 border border-white/5">
            <div className="flex items-center space-x-2 text-amber-400 font-semibold">
              <FileText className="w-4 h-4" />
              <span>Structured Export</span>
            </div>
            <p className="text-slate-300 text-[11px] leading-relaxed">
              Real-time JSON schema formatting, PNG/SVG QR export and applicant tracking.
            </p>
          </div>
        </div>
      </div>

    </div>
  );
}
