import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  FolderLock, 
  Grid, 
  List, 
  Search, 
  Filter, 
  ArrowUpDown, 
  Image as ImageIcon, 
  Mic, 
  FileText, 
  FileCheck, 
  Trash2, 
  Download, 
  ExternalLink,
  Copy,
  Check,
  Eye,
  CheckSquare,
  Square
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { EvidenceFile, EvidenceType } from '../types';
import { EvidenceTypeBadge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import { ConfirmDialog } from '../components/common/ConfirmDialog';

export const EvidenceVault: React.FC = () => {
  const navigate = useNavigate();
  const { evidence, cases, deleteEvidenceItem, deleteMultipleEvidence } = useApp();

  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');
  const [search, setSearch] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<string>('All');
  const [caseFilter, setCaseFilter] = useState<string>('All');
  const [sortBy, setSortBy] = useState<'date' | 'name' | 'size'>('date');
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  // Delete confirmations
  const [deleteSingleTarget, setDeleteSingleTarget] = useState<EvidenceFile | null>(null);
  const [isBulkDeleteOpen, setIsBulkDeleteOpen] = useState<boolean>(false);

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const handleCopyHash = (hash: string, id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(hash);
    setCopiedHash(id);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const handleDownload = (file: EvidenceFile, e: React.MouseEvent) => {
    e.stopPropagation();
    if (file.fileObject) {
      const url = URL.createObjectURL(file.fileObject);
      const a = document.createElement('a');
      a.href = url;
      a.download = file.fileName;
      a.click();
      URL.revokeObjectURL(url);
    } else if (file.textContent) {
      const blob = new Blob([file.textContent], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = file.fileName;
      a.click();
      URL.revokeObjectURL(url);
    } else {
      // Demo download placeholder
      const blob = new Blob([`Evidence AI Preserved File: ${file.fileName}\nSHA-256: ${file.metadata.sha256}`], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = file.fileName;
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  const toggleSelectOne = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const toggleSelectAll = () => {
    if (selectedIds.length === filteredEvidence.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(filteredEvidence.map((e) => e.id));
    }
  };

  const handleConfirmSingleDelete = async () => {
    if (deleteSingleTarget) {
      await deleteEvidenceItem(deleteSingleTarget.id);
      setSelectedIds((prev) => prev.filter((id) => id !== deleteSingleTarget.id));
      setDeleteSingleTarget(null);
    }
  };

  const handleConfirmBulkDelete = async () => {
    await deleteMultipleEvidence(selectedIds);
    setSelectedIds([]);
    setIsBulkDeleteOpen(false);
  };

  // Filter & Sort
  const filteredEvidence = evidence
    .filter((e) => {
      const matchesSearch =
        e.displayName.toLowerCase().includes(search.toLowerCase()) ||
        e.fileName.toLowerCase().includes(search.toLowerCase()) ||
        e.id.toLowerCase().includes(search.toLowerCase()) ||
        (e.metadata.sha256 && e.metadata.sha256.toLowerCase().includes(search.toLowerCase()));
      const matchesType = typeFilter === 'All' || e.fileType === typeFilter;
      const matchesCase = caseFilter === 'All' || e.caseId === caseFilter;
      return matchesSearch && matchesType && matchesCase;
    })
    .sort((a, b) => {
      if (sortBy === 'date') return new Date(b.dateAdded).getTime() - new Date(a.dateAdded).getTime();
      if (sortBy === 'name') return a.displayName.localeCompare(b.displayName);
      if (sortBy === 'size') return b.fileSize - a.fileSize;
      return 0;
    });

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <FolderLock className="w-6 h-6 text-cyan-400" />
            Evidence Vault
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Browse, inspect, and verify preserved evidence records with complete cryptographic metadata.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {selectedIds.length > 0 && (
            <Button
              variant="danger"
              size="sm"
              onClick={() => setIsBulkDeleteOpen(true)}
            >
              <Trash2 className="w-4 h-4" />
              <span>Delete Selected ({selectedIds.length})</span>
            </Button>
          )}

          <Button variant="cyan" size="sm" onClick={() => navigate('/upload')}>
            + Ingest Evidence
          </Button>
        </div>
      </div>

      {/* Filter and View Controls Bar */}
      <div className="flex flex-col md:flex-row items-center justify-between gap-3 bg-[#162032] border border-slate-800 rounded-xl p-3">
        {/* Search */}
        <div className="relative w-full md:w-72">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5 pointer-events-none" />
          <input
            type="text"
            placeholder="Search by name, ID, or SHA-256..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-[#0F172A] border border-slate-700 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-400 focus:outline-none focus:border-cyan-500"
          />
        </div>

        {/* Dropdown Filters */}
        <div className="flex flex-wrap items-center gap-2 w-full md:w-auto justify-end">
          {/* File Type Filter */}
          <div className="flex items-center gap-1.5 bg-[#0F172A] border border-slate-700 rounded-lg px-2.5 py-1">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="bg-transparent text-xs text-slate-300 focus:outline-none cursor-pointer"
            >
              <option value="All" className="bg-[#162032]">All Types</option>
              <option value="image" className="bg-[#162032]">Images</option>
              <option value="audio" className="bg-[#162032]">Audio</option>
              <option value="document" className="bg-[#162032]">Documents</option>
              <option value="text" className="bg-[#162032]">Text / Logs</option>
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

          {/* Sort By */}
          <div className="flex items-center gap-1.5 bg-[#0F172A] border border-slate-700 rounded-lg px-2.5 py-1">
            <ArrowUpDown className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="bg-transparent text-xs text-slate-300 focus:outline-none cursor-pointer"
            >
              <option value="date" className="bg-[#162032]">Sort by Date</option>
              <option value="name" className="bg-[#162032]">Sort by Name</option>
              <option value="size" className="bg-[#162032]">Sort by Size</option>
            </select>
          </div>

          {/* View Mode Toggle */}
          <div className="flex items-center border border-slate-700 rounded-lg overflow-hidden bg-[#0F172A]">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-1.5 transition-colors ${viewMode === 'grid' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white'}`}
              title="Grid View"
            >
              <Grid className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('table')}
              className={`p-1.5 transition-colors ${viewMode === 'table' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white'}`}
              title="Table View"
            >
              <List className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Vault Content */}
      {filteredEvidence.length === 0 ? (
        <div className="bg-[#162032] border border-slate-800 rounded-2xl p-16 text-center text-slate-400">
          <FolderLock className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-sm font-semibold text-white mb-1">No evidence items match your filters</h3>
          <p className="text-xs text-slate-400 mb-4">Try clearing filters or ingest new digital evidence.</p>
          <Button variant="primary" size="sm" onClick={() => navigate('/upload')}>
            + Upload Evidence
          </Button>
        </div>
      ) : viewMode === 'grid' ? (
        /* Grid View */
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filteredEvidence.map((file) => {
            const isSelected = selectedIds.includes(file.id);
            const truncatedHash = file.metadata.sha256 
              ? `${file.metadata.sha256.substring(0, 8)}...${file.metadata.sha256.substring(file.metadata.sha256.length - 6)}` 
              : 'Uncalculated';

            return (
              <div
                key={file.id}
                onClick={() => navigate(`/vault/${file.id}`)}
                className={`bg-[#162032] border rounded-xl overflow-hidden transition-all duration-200 hover:-translate-y-0.5 cursor-pointer flex flex-col justify-between group shadow-sm ${
                  isSelected ? 'border-cyan-500 ring-1 ring-cyan-500' : 'border-slate-800 hover:border-slate-700'
                }`}
              >
                {/* Card Top / Thumbnail */}
                <div className="relative aspect-video bg-[#0F172A] flex items-center justify-center overflow-hidden border-b border-slate-800/80">
                  {file.previewUrl ? (
                    <img
                      src={file.previewUrl}
                      alt={file.displayName}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    />
                  ) : (
                    <div className="flex flex-col items-center gap-1.5 text-slate-600">
                      {file.fileType === 'audio' && <Mic className="w-8 h-8 text-cyan-400/80" />}
                      {file.fileType === 'document' && <FileText className="w-8 h-8 text-blue-400/80" />}
                      {file.fileType === 'text' && <FileCheck className="w-8 h-8 text-amber-400/80" />}
                      <span className="text-[10px] font-mono uppercase tracking-wider">{file.fileExtension}</span>
                    </div>
                  )}

                  {/* Multi-select check */}
                  <button
                    onClick={(e) => toggleSelectOne(file.id, e)}
                    className="absolute top-2 left-2 p-1 rounded bg-[#0F172A]/80 border border-slate-700 text-slate-300 hover:text-white"
                  >
                    {isSelected ? <CheckSquare className="w-4 h-4 text-cyan-400" /> : <Square className="w-4 h-4" />}
                  </button>

                  <div className="absolute top-2 right-2">
                    <EvidenceTypeBadge type={file.fileType} />
                  </div>
                </div>

                {/* Card Details */}
                <div className="p-4 flex-1 flex flex-col justify-between">
                  <div>
                    <h3 className="text-xs font-semibold text-white truncate group-hover:text-cyan-400 transition-colors mb-1" title={file.displayName}>
                      {file.displayName}
                    </h3>
                    <p className="text-[11px] font-mono text-slate-400 truncate mb-2.5" title={file.fileName}>
                      {file.fileName}
                    </p>

                    {file.notes && (
                      <p className="text-[11px] text-slate-400 line-clamp-2 mb-3 leading-snug">
                        {file.notes}
                      </p>
                    )}
                  </div>

                  <div className="space-y-2 pt-3 border-t border-slate-800/80 text-[11px] font-mono text-slate-400">
                    <div className="flex justify-between items-center">
                      <span>Size: {formatBytes(file.fileSize)}</span>
                      <span className="text-blue-400">{file.caseId}</span>
                    </div>

                    <div className="flex items-center justify-between">
                      <button
                        onClick={(e) => handleCopyHash(file.metadata.sha256 || '', file.id, e)}
                        className="flex items-center gap-1 text-[10px] text-slate-400 hover:text-slate-200"
                        title="Click to copy full SHA-256 hash"
                      >
                        <code>{truncatedHash}</code>
                        {copiedHash === file.id ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                      </button>

                      <div className="flex items-center gap-1">
                        <button
                          onClick={(e) => handleDownload(file, e)}
                          className="p-1 rounded text-slate-400 hover:text-cyan-400 hover:bg-slate-800"
                          title="Download original file"
                        >
                          <Download className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setDeleteSingleTarget(file);
                          }}
                          className="p-1 rounded text-slate-400 hover:text-rose-400 hover:bg-rose-500/10"
                          title="Delete evidence"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        /* Table View */
        <div className="bg-[#162032] border border-slate-800 rounded-xl overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-800 bg-[#0F172A]/80 text-slate-400 font-mono text-[11px]">
                <th className="p-3 w-10">
                  <button onClick={toggleSelectAll}>
                    {selectedIds.length === filteredEvidence.length ? (
                      <CheckSquare className="w-4 h-4 text-cyan-400" />
                    ) : (
                      <Square className="w-4 h-4 text-slate-400" />
                    )}
                  </button>
                </th>
                <th className="p-3">File / Label</th>
                <th className="p-3">Category</th>
                <th className="p-3">Case</th>
                <th className="p-3">Size</th>
                <th className="p-3">SHA-256 Fingerprint</th>
                <th className="p-3">Date Added</th>
                <th className="p-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {filteredEvidence.map((file) => {
                const isSelected = selectedIds.includes(file.id);
                const truncatedHash = file.metadata.sha256 
                  ? `${file.metadata.sha256.substring(0, 8)}...${file.metadata.sha256.substring(file.metadata.sha256.length - 6)}` 
                  : '—';

                return (
                  <tr
                    key={file.id}
                    onClick={() => navigate(`/vault/${file.id}`)}
                    className={`hover:bg-slate-800/40 transition-colors cursor-pointer ${
                      isSelected ? 'bg-cyan-500/5' : ''
                    }`}
                  >
                    <td className="p-3" onClick={(e) => toggleSelectOne(file.id, e)}>
                      {isSelected ? (
                        <CheckSquare className="w-4 h-4 text-cyan-400" />
                      ) : (
                        <Square className="w-4 h-4 text-slate-500" />
                      )}
                    </td>
                    <td className="p-3 font-medium text-white max-w-xs truncate">
                      <div className="font-semibold text-slate-100">{file.displayName}</div>
                      <div className="text-[11px] font-mono text-slate-400">{file.fileName}</div>
                    </td>
                    <td className="p-3">
                      <EvidenceTypeBadge type={file.fileType} />
                    </td>
                    <td className="p-3 font-mono text-blue-400">{file.caseId}</td>
                    <td className="p-3 font-mono text-slate-300">{formatBytes(file.fileSize)}</td>
                    <td className="p-3 font-mono text-slate-400">
                      <button
                        onClick={(e) => handleCopyHash(file.metadata.sha256 || '', file.id, e)}
                        className="inline-flex items-center gap-1 text-[11px] hover:text-slate-200"
                      >
                        <code>{truncatedHash}</code>
                        {copiedHash === file.id ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3 text-slate-500" />}
                      </button>
                    </td>
                    <td className="p-3 font-mono text-slate-400">
                      {new Date(file.dateAdded).toLocaleDateString()}
                    </td>
                    <td className="p-3 text-right">
                      <div className="inline-flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
                        <button
                          onClick={(e) => handleDownload(file, e)}
                          className="p-1.5 rounded text-slate-400 hover:text-cyan-400 hover:bg-slate-800"
                          title="Download file"
                        >
                          <Download className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => setDeleteSingleTarget(file)}
                          className="p-1.5 rounded text-slate-400 hover:text-rose-400 hover:bg-rose-500/10"
                          title="Delete evidence"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Delete Single Confirmation */}
      <ConfirmDialog
        isOpen={deleteSingleTarget !== null}
        onClose={() => setDeleteSingleTarget(null)}
        onConfirm={handleConfirmSingleDelete}
        title="Delete Evidence Item?"
        message={`Are you sure you want to delete "${deleteSingleTarget?.displayName}"? This will remove the cryptographic record from the vault.`}
      />

      {/* Delete Multiple Confirmation */}
      <ConfirmDialog
        isOpen={isBulkDeleteOpen}
        onClose={() => setIsBulkDeleteOpen(false)}
        onConfirm={handleConfirmBulkDelete}
        title={`Delete ${selectedIds.length} Evidence Items?`}
        message="This action will permanently remove all selected items from the evidence vault."
      />
    </div>
  );
};
