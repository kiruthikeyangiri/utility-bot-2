import React, { useState, useEffect } from 'react';
import { X, Trash2, FileText, Search, RefreshCw, ChevronRight, Clock, HardDrive, Sparkles, AlertCircle, Image as ImageIcon } from 'lucide-react';
import { getHistoryApi, deleteHistoryApi, getStorageStatsApi, cleanStorageApi } from '../services/api';

export default function HistoryDrawer({ isOpen, onClose, onSelectDocument }) {
  const [history, setHistory] = useState([]);
  const [stats, setStats] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isCleaning, setIsCleaning] = useState(false);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('');

  const fetchHistoryAndStats = async () => {
    setIsLoading(true);
    try {
      const [historyData, statsData] = await Promise.all([
        getHistoryApi({ limit: 50, type: typeFilter || undefined }),
        getStorageStatsApi(),
      ]);
      setHistory(historyData.documents || []);
      setStats(statsData);
    } catch (e) {
      console.error('Failed to fetch history:', e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchHistoryAndStats();
    }
  }, [isOpen, typeFilter]);

  const handleDelete = async (e, id) => {
    e.stopPropagation();
    if (!window.confirm('Delete this verification record?')) return;
    try {
      await deleteHistoryApi(id);
      setHistory((prev) => prev.filter((d) => d._id !== id));
      getStorageStatsApi().then(setStats).catch(() => {});
    } catch (e) {
      alert('Failed to delete record.');
    }
  };

  const handleCleanStorage = async () => {
    if (!window.confirm('Purge expired records (>30 days) from storage?')) return;
    setIsCleaning(true);
    try {
      await cleanStorageApi(false);
      await fetchHistoryAndStats();
    } catch (e) {
      alert('Failed to clean storage.');
    } finally {
      setIsCleaning(false);
    }
  };

  const getDaysRemaining = (createdAtStr) => {
    if (!createdAtStr) return '30d';
    try {
      const created = new Date(createdAtStr);
      const now = new Date();
      const diffDays = Math.max(0, 30 - Math.floor((now - created) / (1000 * 60 * 60 * 24)));
      return `${diffDays} days left`;
    } catch {
      return '30d';
    }
  };

  if (!isOpen) return null;

  const filteredHistory = history.filter((doc) => {
    const term = search.toLowerCase();
    const docType = (doc.documentType || '').toLowerCase();
    const name = (doc.data?.name || '').toLowerCase();
    const idNum = (
      doc.data?.aadhaar_number ||
      doc.data?.pan_number ||
      doc.data?.dl_number ||
      ''
    ).toLowerCase();
    return docType.includes(term) || name.includes(term) || idNum.includes(term);
  });

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div 
        onClick={onClose}
        className="absolute inset-0 bg-slate-900/30 backdrop-blur-sm transition-opacity"
      />

      <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-md bg-white border-l border-slate-200 shadow-2xl flex flex-col">
          
          {/* Header */}
          <div className="p-5 border-b border-slate-200 flex items-center justify-between bg-slate-50">
            <div>
              <div className="flex items-center space-x-2">
                <h2 className="text-base font-bold text-slate-900">Verification History</h2>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-200">
                  30-Day TTL
                </span>
              </div>
              <div className="flex items-center space-x-1.5 text-xs text-slate-500 mt-0.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block"></span>
                <span>Private to this browser</span>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg bg-white hover:bg-slate-100 text-slate-500 hover:text-slate-700 border border-slate-200 transition"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Storage Meter Bar */}
          {stats && (
            <div className="px-5 py-3 bg-slate-50/80 border-b border-slate-200 text-xs">
              <div className="flex items-center justify-between text-slate-600 mb-1.5 font-medium">
                <div className="flex items-center space-x-1.5">
                  <HardDrive className="w-3.5 h-3.5 text-sky-600" />
                  <span>Storage Usage:</span>
                  <strong className="text-slate-800">{stats.storageSizeKB} KB ({stats.totalRecords}/{stats.maxRecords} records)</strong>
                </div>
                <button
                  onClick={handleCleanStorage}
                  disabled={isCleaning}
                  className="text-[11px] font-semibold text-rose-600 hover:text-rose-700 underline"
                >
                  {isCleaning ? 'Cleaning...' : 'Clean Storage'}
                </button>
              </div>
              <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                <div 
                  className={`h-full transition-all duration-300 ${
                    stats.percentUsed > 80 ? 'bg-rose-500' : stats.percentUsed > 50 ? 'bg-amber-500' : 'bg-sky-600'
                  }`}
                  style={{ width: `${Math.max(4, stats.percentUsed)}%` }}
                />
              </div>
            </div>
          )}

          {/* Search & Filters */}
          <div className="p-4 border-b border-slate-100 bg-white space-y-3">
            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search by applicant name, ID number..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-800 focus:outline-none focus:border-sky-500"
              />
            </div>

            <div className="flex gap-2">
              {['', 'aadhaar', 'pan', 'driving_licence'].map((t) => (
                <button
                  key={t}
                  onClick={() => setTypeFilter(t)}
                  className={`text-[11px] px-2.5 py-1 rounded-md font-medium capitalize transition ${
                    typeFilter === t
                      ? 'bg-sky-600 text-white shadow-sm'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {t === '' ? 'All' : t.replace('_', ' ')}
                </button>
              ))}
            </div>
          </div>

          {/* List Area */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-slate-50/50">
            {isLoading ? (
              <div className="flex flex-col items-center justify-center py-16 text-slate-400">
                <RefreshCw className="w-6 h-6 animate-spin text-sky-600 mb-2" />
                <p className="text-xs font-medium">Loading applicant history...</p>
              </div>
            ) : filteredHistory.length === 0 ? (
              <div className="text-center py-16 text-slate-400">
                <FileText className="w-10 h-10 mx-auto mb-2 text-slate-300" />
                <p className="text-xs font-semibold text-slate-700">No records found</p>
                <p className="text-[11px] text-slate-500 mt-1">Verified ID documents will be stored here for 30 days.</p>
              </div>
            ) : (
              filteredHistory.map((doc) => (
                <div
                  key={doc._id}
                  onClick={() => {
                    onSelectDocument({
                      document_type: doc.documentType,
                      is_valid: doc.isValid,
                      short_circuited: doc.shortCircuited,
                      data: doc.data,
                      warnings: doc.warnings,
                      ocr_confidence: doc.ocrConfidence,
                      quality_report: doc.qualityReport,
                      raw_ocr_text: doc.rawOcrText,
                      images: doc.thumbnail ? { original: doc.thumbnail } : {},
                    });
                    onClose();
                  }}
                  className="bg-white border border-slate-200 rounded-xl p-3 hover:border-sky-400 hover:shadow-sm cursor-pointer transition flex items-center justify-between group gap-3"
                >
                  {/* Photo Thumbnail */}
                  <div className="w-12 h-12 rounded-lg bg-slate-100 border border-slate-200 overflow-hidden flex-shrink-0 flex items-center justify-center">
                    {doc.thumbnail ? (
                      <img src={doc.thumbnail} alt="Doc thumbnail" className="w-full h-full object-cover" />
                    ) : (
                      <ImageIcon className="w-5 h-5 text-slate-400" />
                    )}
                  </div>

                  {/* Info */}
                  <div className="overflow-hidden flex-1">
                    <div className="flex items-center space-x-2 mb-0.5">
                      <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-sky-50 text-sky-700 border border-sky-200">
                        {doc.documentType || 'document'}
                      </span>
                      <span className="text-[10px] font-medium text-amber-700 flex items-center space-x-0.5">
                        <Clock className="w-2.5 h-2.5" />
                        <span>{getDaysRemaining(doc.createdAt)}</span>
                      </span>
                    </div>
                    <h4 className="text-xs font-bold text-slate-800 truncate">
                      {doc.data?.name || doc.originalFileName || 'Unnamed Applicant'}
                    </h4>
                    <p className="text-[11px] font-mono text-slate-500 truncate">
                      {doc.data?.aadhaar_number || doc.data?.pan_number || doc.data?.dl_number || 'No ID'}
                    </p>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center space-x-1 flex-shrink-0">
                    <button
                      onClick={(e) => handleDelete(e, doc._id)}
                      className="p-1.5 text-slate-400 hover:text-rose-600 rounded-md hover:bg-rose-50 transition"
                      title="Delete record"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                    <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-sky-600 transition" />
                  </div>
                </div>
              ))
            )}
          </div>

        </div>
      </div>
    </div>
  );
}
