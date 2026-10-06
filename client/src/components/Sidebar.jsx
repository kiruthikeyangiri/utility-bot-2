import React, { useEffect } from 'react';
import { 
  Home, 
  ShieldCheck, 
  Package, 
  QrCode,
  History, 
  Settings, 
  Info, 
  X, 
  Bot,
  ExternalLink,
  ChevronRight
} from 'lucide-react';

export default function Sidebar({
  isOpen,
  onClose,
  currentPage,
  onNavigate,
  onOpenHistory,
  onOpenSettings,
  onOpenAbout
}) {
  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Prevent background scroll when sidebar is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const handleNav = (page) => {
    onNavigate(page);
    onClose();
  };

  const menuItems = [
    {
      id: 'home',
      label: 'Home',
      icon: Home,
      action: () => handleNav('home'),
      active: currentPage === 'home',
      description: 'Main suite & tool selector'
    },
    {
      id: 'id_verification',
      label: 'ID Verification',
      icon: ShieldCheck,
      action: () => handleNav('id_verification'),
      active: currentPage === 'id_verification',
      badge: 'Active',
      description: 'Aadhaar, PAN, DL documents'
    },
    {
      id: 'shipping_scanner',
      label: 'Shipping Label Scanner',
      icon: Package,
      action: () => handleNav('shipping_scanner'),
      active: currentPage === 'shipping_scanner',
      badge: 'Active',
      badgeColor: 'bg-emerald-100 text-emerald-800 border-emerald-200',
      description: 'Multi-image logistics & courier labels'
    },
    {
      id: 'qr_tools',
      label: 'QR & Barcode Tools',
      icon: QrCode,
      action: () => handleNav('qr_tools'),
      active: currentPage === 'qr_tools',
      badge: 'New',
      badgeColor: 'bg-sky-100 text-sky-800 border-sky-200',
      description: 'Generate and scan QR / Barcode'
    },
    {
      id: 'history',
      label: 'History',
      icon: History,
      action: () => {
        onClose();
        if (onOpenHistory) onOpenHistory();
      },
      description: 'Applicant & scan records'
    },
    {
      id: 'settings',
      label: 'Settings',
      icon: Settings,
      action: () => {
        onClose();
        if (onOpenSettings) onOpenSettings();
      },
      description: 'OCR & model preferences'
    },
    {
      id: 'about',
      label: 'About',
      icon: Info,
      action: () => {
        onClose();
        if (onOpenAbout) onOpenAbout();
      },
      description: 'Version, technology & legal'
    }
  ];

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm transition-opacity duration-300 animate-in fade-in"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer */}
      <div className="relative w-80 max-w-[85vw] bg-white h-full shadow-2xl flex flex-col z-10 transition-transform duration-300 animate-in slide-in-from-left">
        
        {/* Drawer Header */}
        <div className="p-5 border-b border-slate-200 flex items-center justify-between bg-slate-50/70">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center shadow-md shadow-sky-500/20 text-white">
              <Bot className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900 leading-tight">Utility Bot</h2>
              <p className="text-xs text-slate-500">Document & Label Suite</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 transition"
            aria-label="Close menu"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Menu Navigation */}
        <div className="flex-1 overflow-y-auto p-4 space-y-1.5">
          <div className="px-3 pb-2 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
            Menu Navigation
          </div>

          {menuItems.map((item) => {
            const Icon = item.icon;
            const isCurrent = item.active;

            return (
              <button
                key={item.id}
                onClick={item.action}
                className={`w-full text-left px-3.5 py-3 rounded-xl flex items-center justify-between transition-all group ${
                  isCurrent 
                    ? 'bg-sky-50 text-sky-900 border border-sky-200 shadow-sm font-semibold' 
                    : 'text-slate-700 hover:bg-slate-100 hover:text-slate-900'
                }`}
              >
                <div className="flex items-center space-x-3 min-w-0">
                  <div className={`p-2 rounded-lg transition ${
                    isCurrent 
                      ? 'bg-sky-600 text-white shadow-sm' 
                      : 'bg-slate-100 text-slate-600 group-hover:bg-slate-200 group-hover:text-slate-800'
                  }`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <div className="truncate">
                    <div className="text-sm font-medium leading-tight truncate">
                      {item.label}
                    </div>
                    {item.description && (
                      <div className="text-[11px] text-slate-400 truncate mt-0.5">
                        {item.description}
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center space-x-1.5 flex-shrink-0 ml-2">
                  {item.badge && (
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                      item.badgeColor || (isCurrent ? 'bg-sky-100 text-sky-800 border-sky-200' : 'bg-slate-100 text-slate-600 border-slate-200')
                    }`}>
                      {item.badge}
                    </span>
                  )}
                  <ChevronRight className={`w-4 h-4 transition ${isCurrent ? 'text-sky-600' : 'text-slate-300 group-hover:text-slate-500'}`} />
                </div>
              </button>
            );
          })}
        </div>

        {/* Drawer Footer */}
        <div className="p-4 border-t border-slate-200 bg-slate-50/50 space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span className="font-medium">Version</span>
            <span className="font-semibold text-slate-700">v2.5.0</span>
          </div>
          <div className="text-[11px] text-slate-400 leading-normal">
            Enterprise Document Verification & Multi-Label Intelligence Suite.
          </div>
        </div>

      </div>
    </div>
  );
}
