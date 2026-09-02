import React, { useState } from 'react';
import { Layers, Maximize2, X } from 'lucide-react';

export default function VisualPipeline({ images }) {
  const [selectedImg, setSelectedImg] = useState(null);

  if (!images || Object.keys(images).length === 0) {
    return (
      <div className="bg-white border border-slate-200 rounded-2xl p-10 text-center shadow-sm">
        <Layers className="w-10 h-10 text-slate-400 mx-auto mb-2" />
        <h4 className="text-sm font-semibold text-slate-800">No Visual Pipeline Available</h4>
        <p className="text-xs text-slate-500 mt-1">Upload and extract an image to inspect the visual pipeline stages.</p>
      </div>
    );
  }

  const stages = [
    {
      key: 'original',
      title: '1. Original Document',
      desc: 'Raw image as captured / uploaded.',
      badge: 'Input',
      badgeColor: 'bg-slate-100 text-slate-700 border-slate-200',
    },
    {
      key: 'preprocessed',
      title: '2. OpenCV Enhanced',
      desc: 'Glare reduction, CLAHE contrast & denoising.',
      badge: 'Cleaned',
      badgeColor: 'bg-sky-50 text-sky-700 border-sky-200',
    },
    {
      key: 'annotated',
      title: '3. OCR Bounding Boxes',
      desc: 'Detected text bounding boxes & confidence.',
      badge: 'EasyOCR',
      badgeColor: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    },
  ];

  return (
    <div className="space-y-6">
      
      {/* 3-Column Pipeline Gallery */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {stages.map((stage) => {
          const imgSrc = images[stage.key];
          if (!imgSrc) return null;

          return (
            <div
              key={stage.key}
              className="bg-white border border-slate-200/80 rounded-2xl overflow-hidden shadow-sm flex flex-col hover:border-slate-300 transition"
            >
              {/* Header */}
              <div className="p-4 border-b border-slate-100 flex items-center justify-between">
                <div>
                  <h4 className="text-xs font-bold text-slate-900">{stage.title}</h4>
                  <p className="text-[11px] text-slate-500 mt-0.5">{stage.desc}</p>
                </div>
                <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${stage.badgeColor}`}>
                  {stage.badge}
                </span>
              </div>

              {/* Image Preview */}
              <div className="relative group bg-slate-100 flex-1 flex items-center justify-center p-3 min-h-[220px]">
                <img
                  src={imgSrc}
                  alt={stage.title}
                  className="max-h-56 w-auto object-contain rounded-lg shadow-sm group-hover:opacity-95 transition"
                />

                {/* Hover Zoom Overlay */}
                <button
                  onClick={() => setSelectedImg({ src: imgSrc, title: stage.title })}
                  className="absolute inset-0 bg-slate-900/30 backdrop-blur-[2px] opacity-0 group-hover:opacity-100 transition flex items-center justify-center text-white space-x-2 text-xs font-semibold"
                >
                  <div className="px-3 py-1.5 rounded-lg bg-slate-900/80 border border-white/20 flex items-center space-x-1.5 shadow-lg">
                    <Maximize2 className="w-4 h-4" />
                    <span>View Full Size</span>
                  </div>
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Full-Screen Zoom Modal */}
      {selectedImg && (
        <div
          onClick={() => setSelectedImg(null)}
          className="fixed inset-0 z-50 bg-slate-900/80 backdrop-blur-sm flex items-center justify-center p-4"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="bg-white rounded-2xl max-w-4xl w-full p-4 border border-slate-200 shadow-2xl relative"
          >
            <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-100">
              <h3 className="text-sm font-bold text-slate-900">{selectedImg.title}</h3>
              <button
                onClick={() => setSelectedImg(null)}
                className="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-600 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="max-h-[75vh] overflow-auto flex items-center justify-center bg-slate-50 p-2 rounded-xl border border-slate-100">
              <img src={selectedImg.src} alt={selectedImg.title} className="max-w-full h-auto rounded-lg shadow-sm" />
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
