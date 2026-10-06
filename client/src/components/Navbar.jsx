import React from 'react';
import { Bot, History, Clock } from 'lucide-react';

export default function Navbar({ onToggleSidebar, onToggleHistory, isConnected, activePage = 'home', onNavigate }) {
  const getPageInfo = () => {
    switch (activePage) {
      case 'home':
        return {
          title: 'Home Dashboard',
          subtitle: 'Select ID Verification, Shipping Scanner, or QR Tools',
          badge: 'Home',
          badgeColor: 'bg-indigo-50 text-indigo-700 border-indigo-200'
        };
      case 'shipping_scanner':
        return {
          title: 'Shipping Scanner',
          subtitle: 'Multi-Label OCR • Barcode & QR Extraction',
          badge: 'Shipping',
          badgeColor: 'bg-emerald-50 text-emerald-700 border-emerald-200'
        };
      case 'qr_tools':
        return {
          title: 'QR & Barcode Tools',
          subtitle: '12 Format Generator & Standalone Matrix Scanner',
          badge: 'QR & Barcode',
          badgeColor: 'bg-violet-50 text-violet-700 border-violet-200'
        };
      case 'id_verification':
      default:
        return {
          title: 'Document Verification',
          subtitle: 'Aadhaar • PAN • Driving Licence Verification',
          badge: 'ID Verify',
          badgeColor: 'bg-sky-50 text-sky-700 border-sky-200'
        };
    }
  };

  const pageInfo = getPageInfo();

  return (
    <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b border-slate-200 shadow-sm">
      <div className="max-w-[1700px] w-full mx-auto px-4 sm:px-8 lg:px-12 h-16 flex items-center justify-between">
        
        {/* Left: Hamburger Button + Brand Logo & Title */}
        <div className="flex items-center space-x-3 sm:space-x-4">
          
          {/* Hamburger Menu Button */}
          <button
            onClick={onToggleSidebar}
            aria-label="Open Navigation Menu"
            className="w-10 h-10 rounded-xl text-slate-700 hover:text-slate-900 bg-slate-50 hover:bg-slate-100 border border-slate-200 hover:border-slate-300 transition flex items-center justify-center cursor-pointer shadow-sm active:scale-95"
            title="Open Navigation Menu"
          >
            <span className="text-xl font-bold leading-none select-none">☰</span>
          </button>

          <button
            onClick={() => onNavigate && onNavigate('home')}
            className="flex items-center space-x-3 text-left group cursor-pointer focus:outline-hidden"
            title="Return to Home Dashboard"
          >
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center shadow-md shadow-sky-500/20 text-white group-hover:scale-105 transition-transform">
              <Bot className="w-6 h-6" />
            </div>

            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-base font-bold text-slate-900 tracking-tight group-hover:text-indigo-600 transition-colors">
                  Utility Bot
                </h1>
                <span className={`text-[10px] font-bold tracking-wider uppercase px-2 py-0.5 rounded-full border ${pageInfo.badgeColor}`}>
                  {pageInfo.badge}
                </span>
              </div>
              <p className="text-xs text-slate-500">
                {pageInfo.subtitle}
              </p>
            </div>
          </button>
        </div>

        {/* Action Controls & Badges */}
        <div className="flex items-center space-x-3">
          {/* 30-Day Retention Policy Badge */}
          <div className="hidden md:flex items-center space-x-1.5 px-3 py-1 rounded-lg bg-slate-100 border border-slate-200 text-xs">
            <Clock className="w-3.5 h-3.5 text-indigo-600" />
            <span className="text-slate-600 font-medium">Policy:</span>
            <span className="text-indigo-700 font-semibold">30-Day Auto-Retention</span>
          </div>

          {/* History Button */}
          <button
            onClick={onToggleHistory}
            className="flex items-center space-x-2 px-3.5 py-1.5 rounded-lg bg-white hover:bg-slate-50 text-slate-700 hover:text-slate-900 border border-slate-200 hover:border-slate-300 transition text-xs font-medium shadow-sm"
          >
            <History className="w-4 h-4 text-sky-600" />
            <span className="hidden sm:inline">Applicant History</span>
            <span className="sm:hidden">History</span>
          </button>
        </div>

      </div>
    </header>
  );
}
