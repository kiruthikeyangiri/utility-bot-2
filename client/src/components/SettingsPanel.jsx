import React, { useState, useEffect } from 'react';
import { Sliders, Cpu, Layers } from 'lucide-react';
import { getModelsApi } from '../services/api';

export default function SettingsPanel({ settings, onChange }) {
  const [models, setModels] = useState([
    'openai/gpt-oss-120b',
    'openai/gpt-oss-20b',
    'qwen/qwen3.6-27b',
    'groq/compound-mini',
    'llama-3.3-70b-versatile',
  ]);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    getModelsApi()
      .then((data) => {
        if (data.models && data.models.length > 0) {
          setModels(data.models);
        }
      })
      .catch(() => {});
  }, []);

  const handleChange = (key, value) => {
    onChange({ ...settings, [key]: value });
  };

  return (
    <div className="bg-white border border-slate-200/80 rounded-2xl p-5 shadow-sm">
      
      {/* Header toggle */}
      <div 
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between cursor-pointer select-none"
      >
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-lg bg-sky-50 border border-sky-100 text-sky-600">
            <Sliders className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-800">Extraction Settings</h3>
            <p className="text-[11px] text-slate-500">Model selection, OCR PSM mode, & image filters</p>
          </div>
        </div>
        <span className="text-xs font-semibold text-sky-600 hover:text-sky-700">
          {isOpen ? "Hide Settings ▲" : "Customize Settings ▼"}
        </span>
      </div>

      {/* Collapsible Settings Area */}
      {isOpen && (
        <div className="mt-5 pt-4 border-t border-slate-100 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          
          {/* 1. Groq Model */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-slate-700 flex items-center space-x-1.5">
              <Cpu className="w-3.5 h-3.5 text-sky-600" />
              <span>AI Model</span>
            </label>
            <select
              value={settings.model_name || 'openai/gpt-oss-120b'}
              onChange={(e) => handleChange('model_name', e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:border-sky-500 transition"
            >
              {models.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>

          {/* 2. OCR Segmentation Mode */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-slate-700 flex items-center space-x-1.5">
              <Layers className="w-3.5 h-3.5 text-indigo-600" />
              <span>OCR Segmentation Mode</span>
            </label>
            <select
              value={settings.psm_mode || 11}
              onChange={(e) => handleChange('psm_mode', parseInt(e.target.value))}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:border-sky-500 transition"
            >
              <option value={11}>11 - Sparse Text (Recommended for ID cards)</option>
              <option value={3}>3 - Fully Automatic Segmentation</option>
              <option value={4}>4 - Single Column Variable Text</option>
              <option value={6}>6 - Single Uniform Block of Text</option>
            </select>
          </div>

          {/* 3. Min OCR Confidence Slider */}
          <div className="space-y-1.5">
            <div className="flex justify-between items-center text-xs">
              <span className="text-slate-700 font-medium">Min Confidence:</span>
              <span className="text-sky-600 font-semibold">{settings.min_confidence || 25}%</span>
            </div>
            <input
              type="range"
              min="10"
              max="80"
              step="5"
              value={settings.min_confidence || 25}
              onChange={(e) => handleChange('min_confidence', parseFloat(e.target.value))}
              className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-sky-600"
            />
          </div>

          {/* 4. Preprocessing Toggles */}
          <div className="space-y-2">
            <span className="text-xs font-medium text-slate-700 block">Image Enhancement</span>
            <div className="flex flex-wrap gap-2 text-xs">
              <label className="flex items-center space-x-1.5 bg-slate-50 px-2.5 py-1 rounded-md border border-slate-200 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.enable_glare ?? true}
                  onChange={(e) => handleChange('enable_glare', e.target.checked)}
                  className="rounded bg-white text-sky-600 focus:ring-0 border-slate-300"
                />
                <span className="text-[11px] text-slate-700">Glare Reducer</span>
              </label>

              <label className="flex items-center space-x-1.5 bg-slate-50 px-2.5 py-1 rounded-md border border-slate-200 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.enable_clahe ?? true}
                  onChange={(e) => handleChange('enable_clahe', e.target.checked)}
                  className="rounded bg-white text-sky-600 focus:ring-0 border-slate-300"
                />
                <span className="text-[11px] text-slate-700">CLAHE Contrast</span>
              </label>
            </div>
          </div>

        </div>
      )}

    </div>
  );
}
