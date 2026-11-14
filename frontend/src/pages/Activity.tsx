import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  History, 
  Search, 
  Filter, 
  Briefcase, 
  FileCheck, 
  PlusCircle, 
  Edit3, 
  Trash2, 
  FileText,
  Clock,
  ArrowUpDown,
  ShieldCheck,
  AlertCircle
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { ActivityAction } from '../types';
import { Button } from '../components/common/Button';

export const Activity: React.FC = () => {
  const navigate = useNavigate();
  const { activities, cases } = useApp();

  const [search, setSearch] = useState<string>('');
  const [caseFilter, setCaseFilter] = useState<string>('All');
  const [actionFilter, setActionFilter] = useState<string>('All');
  const [sortOrder, setSortOrder] = useState<'desc' | 'asc'>('desc');

  const getActionBadge = (action: ActivityAction) => {
    switch (action) {
      case 'EVIDENCE_ADDED':
        return <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">EVIDENCE ADDED</span>;
      case 'CASE_CREATED':
        return <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">CASE CREATED</span>;
      case 'CASE_STATUS_CHANGED':
        return <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">STATUS CHANGED</span>;
      case 'NOTE_ADDED':
      case 'NOTE_UPDATED':
        return <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">NOTE LOGGED</span>;
      case 'EVIDENCE_REMOVED':
      case 'CASE_DELETED':
      case 'NOTE_DELETED':
        return <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">REMOVED</span>;
      default:
        return <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">{action}</span>;
    }
  };

  const filteredActivities = activities
    .filter((a) => {
      const matchesSearch =
        a.description.toLowerCase().includes(search.toLowerCase()) ||
        a.caseId.toLowerCase().includes(search.toLowerCase()) ||
        (a.evidenceName && a.evidenceName.toLowerCase().includes(search.toLowerCase()));
      const matchesCase = caseFilter === 'All' || a.caseId === caseFilter;
      const matchesAction = actionFilter === 'All' || a.action === actionFilter;
      return matchesSearch && matchesCase && matchesAction;
    })
    .sort((a, b) => {
      const timeA = new Date(a.timestamp).getTime();
      const timeB = new Date(b.timestamp).getTime();
      return sortOrder === 'desc' ? timeB - timeA : timeA - timeB;
    });

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="pb-4 border-b border-slate-800">
        <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
          <History className="w-6 h-6 text-indigo-400" />
          Recent Activity Log
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Chronological record of case creation, metadata modifications, evidence uploads, and investigative notes.
        </p>
      </div>

      {/* Forensic Distinction Notice */}
      <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex items-start gap-3 text-xs text-slate-300">
        <ShieldCheck className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
        <p className="text-[11px] leading-relaxed">
          <strong>Notice:</strong> This interactive activity log records frontend session events. It is separate from the append-only cryptographic forensic ledger implemented in the backend database.
        </p>
      </div>

      {/* Filters Bar */}
      <div className="flex flex-col md:flex-row items-center justify-between gap-3 bg-[#162032] border border-slate-800 rounded-xl p-3">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5 pointer-events-none" />
          <input
            type="text"
            placeholder="Search activity description or case ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-[#0F172A] border border-slate-700 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-400 focus:outline-none focus:border-indigo-500"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2 w-full md:w-auto justify-end">
          {/* Action Filter */}
          <div className="flex items-center gap-1.5 bg-[#0F172A] border border-slate-700 rounded-lg px-2.5 py-1">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              className="bg-transparent text-xs text-slate-300 focus:outline-none cursor-pointer"
            >
              <option value="All" className="bg-[#162032]">All Event Types</option>
              <option value="EVIDENCE_ADDED" className="bg-[#162032]">Evidence Added</option>
              <option value="CASE_CREATED" className="bg-[#162032]">Case Created</option>
              <option value="CASE_STATUS_CHANGED" className="bg-[#162032]">Status Changed</option>
              <option value="NOTE_ADDED" className="bg-[#162032]">Note Added</option>
              <option value="EVIDENCE_REMOVED" className="bg-[#162032]">Evidence Removed</option>
            </select>
          </div>

          {/* Case Filter */}
          <div className="flex items-center gap-1.5 bg-[#0F172A] border border-slate-700 rounded-lg px-2.5 py-1">
            <select
              value={caseFilter}
              onChange={(e) => setCaseFilter(e.target.value)}
              className="bg-transparent text-xs text-slate-300 focus:outline-none cursor-pointer max-w-[140px] truncate"
            >
              <option value="All" className="bg-[#162032]">All Cases</option>
              {cases.map((c) => (
                <option key={c.id} value={c.id} className="bg-[#162032]">
                  {c.id}
                </option>
              ))}
            </select>
          </div>

          {/* Sort Order */}
          <div className="flex items-center gap-1.5 bg-[#0F172A] border border-slate-700 rounded-lg px-2.5 py-1">
            <ArrowUpDown className="w-3.5 h-3.5 text-slate-400" />
            <button
              onClick={() => setSortOrder((o) => (o === 'desc' ? 'asc' : 'desc'))}
              className="text-xs text-slate-300 hover:text-white"
            >
              {sortOrder === 'desc' ? 'Newest First' : 'Oldest First'}
            </button>
          </div>
        </div>
      </div>

      {/* Activity Timeline */}
      <div className="bg-[#162032] border border-slate-800 rounded-2xl p-6">
        {filteredActivities.length === 0 ? (
          <div className="text-center py-12 text-slate-400 text-xs">
            No activity records match your filter criteria.
          </div>
        ) : (
          <div className="relative pl-6 border-l border-slate-800 space-y-6">
            {filteredActivities.map((act) => (
              <div key={act.id} className="relative group">
                {/* Timeline Dot */}
                <span className="absolute -left-[31px] top-1.5 w-2.5 h-2.5 rounded-full bg-indigo-500 ring-4 ring-[#162032] group-hover:scale-125 transition-transform" />

                <div className="bg-[#0F172A]/80 border border-slate-800/80 rounded-xl p-4 transition-colors hover:border-slate-700">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2">
                      {getActionBadge(act.action)}
                      {act.caseId && (
                        <button
                          onClick={() => navigate(`/cases/${act.caseId}`)}
                          className="text-xs font-mono text-blue-400 hover:underline"
                        >
                          [{act.caseId}]
                        </button>
                      )}
                    </div>
                    <span className="text-[11px] font-mono text-slate-400">
                      {new Date(act.timestamp).toLocaleString()}
                    </span>
                  </div>

                  <p className="text-xs font-medium text-white leading-relaxed">{act.description}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
