import React from 'react';
import { Bot, History, Clock, HardDrive } from 'lucide-react';

export default function Navbar({ onToggleHistory, isConnected }) {
  return (
    <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b border-slate-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        
        {/* Brand Logo & Title */}
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center shadow-md shadow-sky-500/20">
            <Bot className="w-6 h-6 text-white" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-base font-bold text-slate-900 tracking-tight">Utility Bot</h1>
              <span className="text-[10px] font-bold tracking-wider uppercase px-2 py-0.5 rounded-full bg-sky-50 text-sky-700 border border-sky-200">
                Document Verification
              </span>
            </div>
            <p className="text-xs text-slate-500">Aadhaar • PAN • Driving Licence Verification</p>
          </div>
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
            <span>Applicant History</span>
          </button>
        </div>

      </div>
    </header>
  );
}
