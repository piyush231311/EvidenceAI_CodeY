import React from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Briefcase, 
  FileText, 
  Image as ImageIcon, 
  Mic, 
  FileCheck, 
  History, 
  UploadCloud, 
  PlusCircle, 
  ArrowUpRight, 
  HardDrive,
  CheckCircle2,
  Lock,
  ChevronRight
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { CaseStatusBadge, EvidenceTypeBadge } from '../components/common/Badge';
import { Button } from '../components/common/Button';

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { cases, evidence, activities, activeCase } = useApp();

  const imageCount = evidence.filter((e) => e.fileType === 'image').length;
  const audioCount = evidence.filter((e) => e.fileType === 'audio').length;
  const docCount = evidence.filter((e) => e.fileType === 'document' || e.fileType === 'text').length;
  const totalSizeBytes = evidence.reduce((sum, e) => sum + e.fileSize, 0);

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const statCards = [
    {
      title: 'Total Cases',
      value: cases.length,
      subtitle: `${cases.filter((c) => c.status === 'Active').length} Active Investigations`,
      icon: Briefcase,
      color: 'text-blue-400',
      bgColor: 'bg-blue-500/10',
      borderColor: 'border-blue-500/20',
      onClick: () => navigate('/cases')
    },
    {
      title: 'Total Evidence Files',
      value: evidence.length,
      subtitle: 'Fingerprinted & Preserved',
      icon: FileCheck,
      color: 'text-cyan-400',
      bgColor: 'bg-cyan-500/10',
      borderColor: 'border-cyan-500/20',
      onClick: () => navigate('/vault')
    },
    {
      title: 'Screenshots & Images',
      value: imageCount,
      subtitle: 'EXIF & Resolution intact',
      icon: ImageIcon,
      color: 'text-purple-400',
      bgColor: 'bg-purple-500/10',
      borderColor: 'border-purple-500/20',
      onClick: () => navigate('/vault')
    },
    {
      title: 'Audio Recordings',
      value: audioCount,
      subtitle: 'Voicemails & Statements',
      icon: Mic,
      color: 'text-emerald-400',
      bgColor: 'bg-emerald-500/10',
      borderColor: 'border-emerald-500/20',
      onClick: () => navigate('/vault')
    },
    {
      title: 'Documents & Logs',
      value: docCount,
      subtitle: 'PDFs, Chats, Emails',
      icon: FileText,
      color: 'text-amber-400',
      bgColor: 'bg-amber-500/10',
      borderColor: 'border-amber-500/20',
      onClick: () => navigate('/vault')
    },
    {
      title: 'Recent Case Events',
      value: activities.length,
      subtitle: 'Logged in session ledger',
      icon: History,
      color: 'text-indigo-400',
      bgColor: 'bg-indigo-500/10',
      borderColor: 'border-indigo-500/20',
      onClick: () => navigate('/activity')
    },
  ];

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Top Banner / Hero */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Overview Dashboard</h1>
          <p className="text-xs text-slate-400 mt-1">
            Victim-first digital evidence collection, cryptographic preservation, and case organization.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={() => navigate('/cases')}>
            <Briefcase className="w-3.5 h-3.5 text-blue-400" />
            <span>Manage Cases</span>
          </Button>
          <Button variant="cyan" size="sm" onClick={() => navigate('/upload')}>
            <UploadCloud className="w-3.5 h-3.5" />
            <span>Upload Evidence</span>
          </Button>
        </div>
      </div>

      {/* Primary Stat Cards Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3.5">
        {statCards.map((card, i) => {
          const Icon = card.icon;
          return (
            <div
              key={i}
              onClick={card.onClick}
              className="bg-[#162032] border border-slate-800 hover:border-slate-700/80 rounded-2xl p-4 transition-all duration-200 hover:-translate-y-0.5 cursor-pointer shadow-sm group"
            >
              <div className="flex items-center justify-between mb-3">
                <div className={`w-8 h-8 rounded-xl ${card.bgColor} border ${card.borderColor} ${card.color} flex items-center justify-center`}>
                  <Icon className="w-4 h-4" />
                </div>
                <ArrowUpRight className="w-3.5 h-3.5 text-slate-600 group-hover:text-slate-400 transition-colors" />
              </div>
              <div className="text-xl font-bold text-white tracking-tight">{card.value}</div>
              <div className="text-xs font-medium text-slate-300 mt-0.5 truncate">{card.title}</div>
              <div className="text-[11px] text-slate-400 mt-1 truncate">{card.subtitle}</div>
            </div>
          );
        })}
      </div>

      {/* Middle Row: Active Case Banner & Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Active Case Spotlight */}
        <div className="lg:col-span-2 bg-[#162032] border border-slate-800 rounded-2xl p-6 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-blue-500/5 rounded-full blur-3xl pointer-events-none" />
          <div className="flex items-center justify-between mb-4">
            <span className="text-[11px] font-mono uppercase tracking-wider text-blue-400 font-semibold flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
              Active Workspace Focus
            </span>
            {activeCase && <CaseStatusBadge status={activeCase.status} />}
          </div>

          {activeCase ? (
            <div>
              <div className="flex items-baseline gap-2 mb-2">
                <h2 className="text-lg font-bold text-white tracking-tight">{activeCase.title}</h2>
                <span className="text-xs font-mono text-slate-400">[{activeCase.id}]</span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed max-w-2xl mb-5">
                {activeCase.description}
              </p>

              <div className="grid grid-cols-3 gap-4 pt-4 border-t border-slate-800/80 mb-5">
                <div>
                  <span className="text-[11px] text-slate-400 block">Case Evidence</span>
                  <span className="text-sm font-semibold text-white mt-0.5 block font-mono">
                    {evidence.filter((e) => e.caseId === activeCase.id).length} files
                  </span>
                </div>
                <div>
                  <span className="text-[11px] text-slate-400 block">Investigative Notes</span>
                  <span className="text-sm font-semibold text-white mt-0.5 block font-mono">
                    {activeCase.notes?.length || 0} notes
                  </span>
                </div>
                <div>
                  <span className="text-[11px] text-slate-400 block">Created On</span>
                  <span className="text-sm font-semibold text-white mt-0.5 block font-mono">
                    {new Date(activeCase.createdAt).toLocaleDateString()}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <Button size="sm" onClick={() => navigate(`/cases/${activeCase.id}`)}>
                  Open Case Workspace →
                </Button>
                <Button variant="outline" size="sm" onClick={() => navigate('/upload')}>
                  <UploadCloud className="w-3.5 h-3.5" />
                  Add to this Case
                </Button>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-slate-400 text-xs">
              No active case selected. Select or create an investigation case.
            </div>
          )}
        </div>

        {/* Storage & Chain of Custody Card */}
        <div className="bg-[#162032] border border-slate-800 rounded-2xl p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <HardDrive className="w-4 h-4 text-cyan-400" />
                Storage & Integrity
              </h3>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                LOCAL FIRST
              </span>
            </div>

            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-xs mb-1.5">
                  <span className="text-slate-400">Preserved Volume</span>
                  <span className="font-mono text-white font-medium">{formatBytes(totalSizeBytes)}</span>
                </div>
                <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-gradient-to-r from-blue-500 to-cyan-400 h-full rounded-full"
                    style={{ width: `${Math.min(100, Math.max(8, (totalSizeBytes / 100000000) * 100))}%` }}
                  />
                </div>
              </div>

              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
                <div className="flex items-start gap-2 text-[11px] text-slate-300">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                  <span>SHA-256 cryptographic hashes computed on raw byte stream.</span>
                </div>
                <div className="flex items-start gap-2 text-[11px] text-slate-300">
                  <Lock className="w-3.5 h-3.5 text-blue-400 shrink-0 mt-0.5" />
                  <span>Files saved untouched with original timestamps preserved.</span>
                </div>
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-800 text-[11px] text-slate-400">
            Files are retained in local storage and never transmitted to external cloud servers.
          </div>
        </div>
      </div>

      {/* Bottom Row: Recent Cases & Recently Added Evidence */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Cases */}
        <div className="bg-[#162032] border border-slate-800 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-white">Investigation Cases</h3>
            <Button variant="ghost" size="sm" onClick={() => navigate('/cases')} className="text-xs text-blue-400 hover:text-blue-300">
              View all ({cases.length}) →
            </Button>
          </div>

          <div className="space-y-2.5">
            {cases.slice(0, 3).map((item) => (
              <div
                key={item.id}
                onClick={() => navigate(`/cases/${item.id}`)}
                className="p-3.5 rounded-xl bg-slate-800/40 border border-slate-800 hover:border-slate-700 hover:bg-slate-800/70 transition-all cursor-pointer flex items-center justify-between group"
              >
                <div className="min-w-0 pr-4">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-mono font-semibold text-blue-400">{item.id}</span>
                    <CaseStatusBadge status={item.status} />
                  </div>
                  <h4 className="text-xs font-semibold text-white truncate group-hover:text-blue-400 transition-colors">
                    {item.title}
                  </h4>
                  <p className="text-[11px] text-slate-400 truncate mt-0.5">{item.description}</p>
                </div>
                <div className="text-right shrink-0">
                  <span className="text-xs font-mono text-slate-300 block">{item.evidenceCount || 0} files</span>
                  <span className="text-[10px] text-slate-400 block mt-0.5">
                    {new Date(item.updatedAt).toLocaleDateString()}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Recently Added Evidence */}
        <div className="bg-[#162032] border border-slate-800 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-white">Recent Evidence Added</h3>
            <Button variant="ghost" size="sm" onClick={() => navigate('/vault')} className="text-xs text-cyan-400 hover:text-cyan-300">
              View vault ({evidence.length}) →
            </Button>
          </div>

          <div className="space-y-2.5">
            {evidence.slice(0, 4).map((file) => (
              <div
                key={file.id}
                onClick={() => navigate(`/vault/${file.id}`)}
                className="p-3 rounded-xl bg-slate-800/40 border border-slate-800 hover:border-slate-700 hover:bg-slate-800/70 transition-all cursor-pointer flex items-center justify-between group"
              >
                <div className="flex items-center gap-3 min-w-0 pr-2">
                  <div className="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0">
                    {file.fileType === 'image' && <ImageIcon className="w-4 h-4 text-purple-400" />}
                    {file.fileType === 'audio' && <Mic className="w-4 h-4 text-cyan-400" />}
                    {file.fileType === 'document' && <FileText className="w-4 h-4 text-blue-400" />}
                    {file.fileType === 'text' && <FileCheck className="w-4 h-4 text-amber-400" />}
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium text-white truncate group-hover:text-cyan-400 transition-colors">
                        {file.displayName}
                      </span>
                      <EvidenceTypeBadge type={file.fileType} />
                    </div>
                    <span className="text-[11px] font-mono text-slate-400 block truncate mt-0.5">
                      {file.fileName} • {formatBytes(file.fileSize)}
                    </span>
                  </div>
                </div>

                <div className="text-right shrink-0">
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                    {file.caseId}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
