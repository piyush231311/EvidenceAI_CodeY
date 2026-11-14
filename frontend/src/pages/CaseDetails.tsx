import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, Upload, Trash2, Download, Copy, Check, Zap,
  Users, FileText, CheckCircle2, XCircle, AlertCircle, AlertTriangle,
  Eye, RefreshCw, Layers, ShieldCheck, UserCheck, UserX, Split, Link2,
  Clock, HelpCircle, FileCheck, ExternalLink, Sparkles, Calendar, Scale,
  ChevronRight, ChevronLeft, ChevronDown, ChevronUp, Play
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { api, ApiAnalysisJob, ApiAnalysisStage } from '../services/api';
import {
  EvidenceFile, CandidateMatch, EventCandidate, TimelineData,
  ContradictionRecord, ClarificationQuestion, ReportResponse, PreliminaryCaseUnderstanding,
  MVPCaseAnalysis
} from '../types';
import { Button } from '../components/common/Button';
import { ConfirmDialog } from '../components/common/ConfirmDialog';
import { Modal } from '../components/common/Modal';

export const CaseDetails: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { cases, deleteCase, deleteEvidence, setActiveCaseId } = useApp();

  const [activeTab, setActiveTab] = useState<'evidence' | 'entities' | 'events' | 'timeline' | 'quiz' | 'report'>('evidence');
  const [caseEvidence, setCaseEvidence] = useState<EvidenceFile[]>([]);
  const [isLoadingFiles, setIsLoadingFiles] = useState<boolean>(true);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);
  const [deleteEvidenceTarget, setDeleteEvidenceTarget] = useState<EvidenceFile | null>(null);
  const [isDeleteCaseOpen, setIsDeleteCaseOpen] = useState<boolean>(false);

  // MVP Analysis states
  const [mvpAnalysis, setMvpAnalysis] = useState<MVPCaseAnalysis | null>(null);
  const [isAnalyzingMvp, setIsAnalyzingMvp] = useState<boolean>(false);

  // One-Click Orchestrated Pipeline states
  const [analysisJob, setAnalysisJob] = useState<ApiAnalysisJob | null>(null);
  const [isStartingJob, setIsStartingJob] = useState<boolean>(false);
  const [isSubmittingJobQuiz, setIsSubmittingJobQuiz] = useState<boolean>(false);
  const [showTechnicalAppendix, setShowTechnicalAppendix] = useState<boolean>(false);
  const [showStagesList, setShowStagesList] = useState<boolean>(true);
  const [jobQuizAnswers, setJobQuizAnswers] = useState<Record<string, {
    selected_option: string;
    user_surety: string;
    knowledge_basis: string;
    free_text?: string;
  }>>({});

  // Extraction states
  const [extractingIds, setExtractingIds] = useState<Set<string>>(new Set());
  const [isExtractingAll, setIsExtractingAll] = useState<boolean>(false);
  const [viewingEvidence, setViewingEvidence] = useState<EvidenceFile | null>(null);

  // Entity matching states
  const [candidateMatches, setCandidateMatches] = useState<CandidateMatch[]>([]);
  const [isLoadingEntities, setIsLoadingEntities] = useState<boolean>(false);
  const [isMatchingEntities, setIsMatchingEntities] = useState<boolean>(false);
  const [entityFilter, setEntityFilter] = useState<string>('all');
  const [reviewingMatchId, setReviewingMatchId] = useState<string | null>(null);
  const [actionSuccessMsg, setActionSuccessMsg] = useState<string | null>(null);

  // Event Extraction states
  const [events, setEvents] = useState<EventCandidate[]>([]);
  const [isLoadingEvents, setIsLoadingEvents] = useState<boolean>(false);
  const [isExtractingEvents, setIsExtractingEvents] = useState<boolean>(false);
  const [eventModalityFilter, setEventModalityFilter] = useState<string>('all');

  // Timeline & Contradiction states
  const [timelineData, setTimelineData] = useState<TimelineData | null>(null);
  const [isLoadingTimeline, setIsLoadingTimeline] = useState<boolean>(false);
  const [contradictions, setContradictions] = useState<ContradictionRecord[]>([]);
  const [isLoadingContradictions, setIsLoadingContradictions] = useState<boolean>(false);

  // Clarification Quiz states
  const [quizQuestions, setQuizQuestions] = useState<ClarificationQuestion[]>([]);
  const [isLoadingQuiz, setIsLoadingQuiz] = useState<boolean>(false);
  const [isGeneratingQuiz, setIsGeneratingQuiz] = useState<boolean>(false);
  const [caseUnderstanding, setCaseUnderstanding] = useState<PreliminaryCaseUnderstanding | null>(null);
  const [isLoadingUnderstanding, setIsLoadingUnderstanding] = useState<boolean>(false);
  const [activeQuestionIndex, setActiveQuestionIndex] = useState<number>(0);
  const [quizFormState, setQuizFormState] = useState<Record<string, {
    selected_option: string;
    free_text: string;
    user_surety: string;
    knowledge_basis: string;
  }>>({});
  const [submittingQuestionId, setSubmittingQuestionId] = useState<string | null>(null);
  const [answeredQuestionIds, setAnsweredQuestionIds] = useState<Set<string>>(new Set());

  // Report states
  const [reportData, setReportData] = useState<ReportResponse | null>(null);
  const [isLoadingReport, setIsLoadingReport] = useState<boolean>(false);
  const [isGeneratingReport, setIsGeneratingReport] = useState<boolean>(false);

  const currentCase = cases.find((c) => c.id === id);

  const loadCaseFiles = async () => {
    if (!id) return;
    try {
      setIsLoadingFiles(true);
      const files = await api.getCaseEvidence(id);
      setCaseEvidence(files);
    } catch (err) {
      console.error('Failed to load case evidence', err);
    } finally {
      setIsLoadingFiles(false);
    }
  };

  const loadEntities = async () => {
    if (!id) return;
    try {
      setIsLoadingEntities(true);
      const matches = await api.getCaseEntities(id);
      setCandidateMatches(matches);
    } catch (err) {
      console.error('Failed to load entities', err);
    } finally {
      setIsLoadingEntities(false);
    }
  };

  const loadEvents = async () => {
    if (!id) return;
    try {
      setIsLoadingEvents(true);
      const data = await api.getCaseEvents(id);
      setEvents(data);
    } catch (err) {
      console.error('Failed to load events', err);
    } finally {
      setIsLoadingEvents(false);
    }
  };

  const loadTimeline = async () => {
    if (!id) return;
    try {
      setIsLoadingTimeline(true);
      const data = await api.getCaseTimeline(id);
      setTimelineData(data);
    } catch (err) {
      console.error('Failed to load timeline', err);
    } finally {
      setIsLoadingTimeline(false);
    }
  };

  const loadContradictions = async () => {
    if (!id) return;
    try {
      setIsLoadingContradictions(true);
      const data = await api.getCaseContradictions(id);
      setContradictions(data);
    } catch (err) {
      console.error('Failed to load contradictions', err);
    } finally {
      setIsLoadingContradictions(false);
    }
  };

  const loadQuiz = async () => {
    if (!id) return;
    try {
      setIsLoadingQuiz(true);
      const data = await api.getClarificationQuiz(id);
      setQuizQuestions(data);
      const answered = new Set<string>(data.filter((q: any) => q.status === 'answered').map((q: any) => String(q.id)));
      setAnsweredQuestionIds(answered);
    } catch (err) {
      console.error('Failed to load quiz', err);
    } finally {
      setIsLoadingQuiz(false);
    }
  };

  const loadCaseUnderstanding = async () => {
    if (!id) return;
    try {
      setIsLoadingUnderstanding(true);
      const data = await api.getCaseUnderstanding(id);
      setCaseUnderstanding(data);
    } catch (err) {
      console.error('Failed to load case understanding', err);
    } finally {
      setIsLoadingUnderstanding(false);
    }
  };

  const loadReport = async () => {
    if (!id) return;
    try {
      setIsLoadingReport(true);
      const data = await api.getReport(id);
      setReportData(data);
    } catch (err) {
      console.warn('Report not available yet:', err);
      setReportData(null);
    } finally {
      setIsLoadingReport(false);
    }
  };

  const loadMvpAnalysis = async () => {
    if (!id) return;
    try {
      const data = await api.getCaseAnalysis(id);
      setMvpAnalysis(data);
    } catch (err) {
      setMvpAnalysis(null);
    }
  };

  const handleAnalyzeCaseMvp = async () => {
    if (!id) return;
    try {
      setIsAnalyzingMvp(true);
      const data = await api.analyzeCase(id);
      if (data && data.id && data.current_stage) {
        setAnalysisJob(data);
      }
      if (data?.artifacts?.mvp_analysis) {
        setMvpAnalysis(data.artifacts.mvp_analysis);
      }
      // Refresh quiz questions
      const qs = await api.getClarificationQuiz(id);
      setQuizQuestions(qs);
      showNotification('Case analyzed successfully. Preliminary narrative and cited facts generated.');
    } catch (err: any) {
      console.error('Failed to run MVP case analysis', err);
      showNotification(err?.message || 'Failed to analyze case');
    } finally {
      setIsAnalyzingMvp(false);
    }
  };

  const loadActiveJob = async () => {
    if (!id) return;
    try {
      const job = await api.getActiveCaseJob(id);
      if (job && job.id && job.current_stage) {
        setAnalysisJob(job);
        if (job.artifacts?.mvp_analysis) {
          setMvpAnalysis(job.artifacts.mvp_analysis);
        } else if (job.status === 'WAITING_FOR_USER' || job.status === 'COMPLETED') {
          loadMvpAnalysis();
        }
        if (job.status === 'WAITING_FOR_USER' || job.status === 'COMPLETED') {
          const qs = await api.getAnalysisJobQuiz(job.id);
          if (qs && qs.length > 0) setQuizQuestions(qs);
        }
        if (job.status === 'COMPLETED' || job.artifacts?.report_id) {
          loadReport();
        }
      } else {
        setAnalysisJob(null);
      }
    } catch (err) {
      console.warn('No active analysis job found:', err);
      setAnalysisJob(null);
    }
  };

  const handleStartOneClickAnalysis = async () => {
    if (!id) return;
    try {
      setIsStartingJob(true);
      const job = await api.analyzeCase(id);
      if (job && job.id && job.current_stage) {
        setAnalysisJob(job);
        showNotification('One-Click Analysis started. Tracking 15 pipeline stages live.');
      } else {
        showNotification('Analysis job created. Syncing pipeline state...');
        await loadActiveJob();
      }
    } catch (err: any) {
      console.error('Failed to start analysis', err);
      showNotification(err?.message || 'Failed to start analysis');
    } finally {
      setIsStartingJob(false);
    }
  };

  const handleRetryJob = async () => {
    if (!analysisJob) return;
    try {
      const updated = await api.retryAnalysisJob(analysisJob.id);
      setAnalysisJob(updated);
      showNotification(`Resuming pipeline from failed stage: ${updated.current_stage}`);
    } catch (err: any) {
      showNotification(err?.message || 'Failed to retry job');
    }
  };

  const handleSubmitJobQuiz = async () => {
    if (!analysisJob) return;
    try {
      setIsSubmittingJobQuiz(true);
      const answers = Object.entries(jobQuizAnswers)
        .filter(([_, val]) => val.selected_option && val.selected_option.trim() !== '')
        .map(([qid, val]) => ({
          question_id: qid,
          selected_option: val.selected_option,
          user_surety: val.user_surety || 'Fairly sure',
          knowledge_basis: val.knowledge_basis || 'Direct first-hand knowledge',
          free_text_clarification: val.free_text || ''
        }));

      if (answers.length === 0) {
        showNotification('Please select an option for at least one question.');
        return;
      }

      const res = await api.submitAnalysisJobQuiz(analysisJob.id, answers);
      setAnalysisJob(res.job);
      showNotification('Clarifications recorded. Synthesizing final forensic report.');
    } catch (err: any) {
      console.error('Failed to submit testimony', err);
      showNotification(err?.message || 'Failed to submit testimony');
    } finally {
      setIsSubmittingJobQuiz(false);
    }
  };

  useEffect(() => {
    loadCaseFiles();
    loadEntities();
    loadEvents();
    loadTimeline();
    loadContradictions();
    loadQuiz();
    loadCaseUnderstanding();
    loadActiveJob();
    if (id) setActiveCaseId(id);
  }, [id]);

  // Polling loop for active analysis job
  useEffect(() => {
    if (!analysisJob || !analysisJob.id || !['RUNNING', 'PENDING', 'RESUMED'].includes(analysisJob.status)) return;

    const interval = setInterval(async () => {
      try {
        const updated = await api.getAnalysisJob(analysisJob.id);
        if (updated && updated.id && updated.current_stage) {
          setAnalysisJob(updated);
          if (updated.artifacts?.mvp_analysis) {
            setMvpAnalysis(updated.artifacts.mvp_analysis);
          }
          if (!['RUNNING', 'PENDING', 'RESUMED'].includes(updated.status)) {
            clearInterval(interval);
            loadCaseFiles();
            loadEntities();
            loadEvents();
            loadTimeline();
            loadContradictions();
            if (updated.status === 'WAITING_FOR_USER' || updated.status === 'COMPLETED') {
              const qs = await api.getAnalysisJobQuiz(updated.id);
              if (qs && qs.length > 0) setQuizQuestions(qs);
            }
            if (updated.status === 'COMPLETED' || updated.artifacts?.report_id) {
              loadReport();
            }
          }
        }
      } catch (e) {
        console.error('Job polling error', e);
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [analysisJob?.id, analysisJob?.status]);

  const showNotification = (msg: string) => {
    setActionSuccessMsg(msg);
    setTimeout(() => setActionSuccessMsg(null), 3500);
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const handleCopyHash = (hash: string, fileId: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(fileId);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const handleConfirmDeleteEvidence = async () => {
    if (deleteEvidenceTarget) {
      await deleteEvidence(deleteEvidenceTarget.id);
      setDeleteEvidenceTarget(null);
      await loadCaseFiles();
    }
  };

  const handleConfirmDeleteCase = async () => {
    if (id) {
      await deleteCase(id);
      navigate('/cases');
    }
  };

  // Run Extraction on single file
  const handleExtractSingle = async (file: EvidenceFile) => {
    setExtractingIds((prev) => new Set(prev).add(file.id));
    try {
      const updated = await api.triggerExtraction(file.id);
      setCaseEvidence((prev) =>
        prev.map((f) => (f.id === file.id ? { ...f, ...updated } : f))
      );
      if (viewingEvidence?.id === file.id) {
        setViewingEvidence((prev) => (prev ? { ...prev, ...updated } : null));
      }
      showNotification(`Extracted intelligence from "${file.original_filename}"`);
    } catch (err: any) {
      alert(`Extraction failed: ${err.message}`);
    } finally {
      setExtractingIds((prev) => {
        const next = new Set(prev);
        next.delete(file.id);
        return next;
      });
    }
  };

  // Run Batch Extraction on all files in case
  const handleExtractAll = async () => {
    if (!id) return;
    setIsExtractingAll(true);
    try {
      const updated = await api.extractAllCaseEvidence(id);
      setCaseEvidence(updated);
      showNotification(`Batch extraction completed for ${updated.length} file(s).`);
    } catch (err: any) {
      alert(`Batch extraction failed: ${err.message}`);
    } finally {
      setIsExtractingAll(false);
    }
  };

  // Run Cross-Evidence Entity Extraction & Matching
  const handleMatchEntities = async () => {
    if (!id) return;
    setIsMatchingEntities(true);
    try {
      const matches = await api.matchCaseEntities(id);
      setCandidateMatches(matches);
      setActiveTab('entities');
      showNotification(`Entity intelligence completed. Found ${matches.length} candidate clusters.`);
    } catch (err: any) {
      alert(`Entity analysis failed: ${err.message}`);
    } finally {
      setIsMatchingEntities(false);
    }
  };

  // Review Candidate Match
  const handleReviewMatch = async (matchId: string, action: 'confirm' | 'reject' | 'separate' | 'undo') => {
    setReviewingMatchId(matchId);
    try {
      const updated = await api.reviewEntityMatch(matchId, action);
      setCandidateMatches((prev) =>
        prev.map((m) => (m.id === matchId ? updated : m))
      );
      const actionLabels = {
        confirm: 'Identity match confirmed',
        reject: 'Match rejected',
        separate: 'Entities marked as separate individuals',
        undo: 'Review decision reset to pending'
      };
      showNotification(actionLabels[action]);
    } catch (err: any) {
      alert(`Review action failed: ${err.message}`);
    } finally {
      setReviewingMatchId(null);
    }
  };

  // Event Extraction
  const handleExtractEvents = async () => {
    if (!id) return;
    setIsExtractingEvents(true);
    try {
      const extracted = await api.extractCaseEvents(id);
      setEvents(extracted);
      await loadTimeline();
      await loadContradictions();
      setActiveTab('events');
      showNotification(`Extracted ${extracted.length} structured event candidates`);
    } catch (err: any) {
      alert(`Event extraction failed: ${err.message}`);
    } finally {
      setIsExtractingEvents(false);
    }
  };

  // Clarification Quiz Generation
  const handleGenerateQuiz = async () => {
    if (!id) return;
    setIsGeneratingQuiz(true);
    try {
      const qs = await api.generateClarificationQuiz(id);
      setQuizQuestions(qs);
      await loadCaseUnderstanding();
      setActiveTab('quiz');
      setActiveQuestionIndex(0);
      showNotification(`Generated ${qs.length} targeted clarification question(s)`);
    } catch (err: any) {
      alert(`Quiz generation failed: ${err.message}`);
    } finally {
      setIsGeneratingQuiz(false);
    }
  };

  // Submit Single Quiz Answer
  const handleSubmitQuizAnswer = async (qId: string) => {
    if (!id) return;
    const form = quizFormState[qId];
    if (!form || !form.selected_option) {
      alert('Please select an option before submitting.');
      return;
    }
    setSubmittingQuestionId(qId);
    try {
      await api.submitQuizAnswer(id, {
        question_id: qId,
        selected_option: form.selected_option,
        free_text_clarification: form.free_text || undefined,
        user_surety: form.user_surety || 'Fairly sure',
        knowledge_basis: form.knowledge_basis || 'Not specified'
      });
      setAnsweredQuestionIds((prev) => new Set(prev).add(qId));
      await loadQuiz();
      await loadTimeline();
      await loadCaseUnderstanding();
      showNotification('Clarification recorded with surety weighting and timeline refreshed');
      setActiveQuestionIndex((prev) => Math.min(prev + 1, Math.max(0, quizQuestions.length - 1)));
    } catch (err: any) {
      alert(`Submission failed: ${err.message}`);
    } finally {
      setSubmittingQuestionId(null);
    }
  };

  // Re-run Timeline Reconstruction
  const handleTriggerReconstruction = async () => {
    if (!id) return;
    try {
      const res = await api.triggerReconstruction(id);
      setTimelineData(res.timeline);
      setContradictions(res.contradictions);
      showNotification('Reconstructed timeline with user surety adjustments');
    } catch (err: any) {
      alert(`Reconstruction failed: ${err.message}`);
    }
  };

  // Generate Forensic Report
  const handleGenerateReport = async () => {
    if (!id) return;
    setIsGeneratingReport(true);
    try {
      const rep = await api.generateReport(id);
      setReportData(rep);
      setActiveTab('report');
      showNotification('Forensic incident report generated successfully');
    } catch (err: any) {
      alert(`Report generation failed: ${err.message}`);
    } finally {
      setIsGeneratingReport(false);
    }
  };

  const filteredEvents = events.filter((ev) => {
    if (eventModalityFilter === 'all') return true;
    return ev.modality.toLowerCase() === eventModalityFilter.toLowerCase();
  });

  const handleSelectOption = (qId: string, option: string) => {
    setQuizFormState((prev) => ({
      ...prev,
      [qId]: {
        ...(prev[qId] || { user_surety: 'Fairly sure', knowledge_basis: 'Directly witnessed', free_text: '' }),
        selected_option: option
      }
    }));
  };

  const handleSetSurety = (qId: string, surety: string) => {
    setQuizFormState((prev) => ({
      ...prev,
      [qId]: {
        ...(prev[qId] || { selected_option: '', knowledge_basis: 'Directly witnessed', free_text: '' }),
        user_surety: surety
      }
    }));
  };

  const handleSetKnowledgeBasis = (qId: string, basis: string) => {
    setQuizFormState((prev) => ({
      ...prev,
      [qId]: {
        ...(prev[qId] || { selected_option: '', user_surety: 'Fairly sure', free_text: '' }),
        knowledge_basis: basis
      }
    }));
  };

  const handleSetFreeText = (qId: string, text: string) => {
    setQuizFormState((prev) => ({
      ...prev,
      [qId]: {
        ...(prev[qId] || { selected_option: '', user_surety: 'Fairly sure', knowledge_basis: 'Directly witnessed' }),
        free_text: text
      }
    }));
  };

  const needsVerificationCount = candidateMatches.filter(
    (m) => m.is_low_confidence || m.requires_source_verification
  ).length;

  const filteredMatches = candidateMatches.filter((m) => {
    if (entityFilter === 'all') return true;
    if (entityFilter === 'needs_verification') {
      return m.is_low_confidence || m.requires_source_verification;
    }
    return m.entity_type.toLowerCase() === entityFilter.toLowerCase();
  });

  if (!currentCase) {
    return (
      <div className="py-12 text-center max-w-sm mx-auto">
        <h2 className="text-sm font-semibold text-[#1C1917] mb-1">Case not found</h2>
        <p className="text-xs text-[#6B6862] mb-4">This case ID does not exist in the database.</p>
        <Button variant="secondary" size="sm" onClick={() => navigate('/cases')}>
          Back to cases
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Toast Notification */}
      {actionSuccessMsg && (
        <div className="fixed top-4 right-4 z-50 bg-[#1C1917] text-white text-xs px-3.5 py-2.5 rounded shadow-lg flex items-center gap-2 border border-stone-700 animate-fade-in">
          <CheckCircle2 className="w-3.5 h-3.5 text-[#2DD4BF]" />
          <span>{actionSuccessMsg}</span>
        </div>
      )}

            {/* Header and Controls */}
      <div>
        <button
          onClick={() => navigate('/cases')}
          className="inline-flex items-center gap-1.5 text-xs text-[#6B6862] hover:text-[#1C1917] mb-3"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to cases
        </button>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-[#E6E4DF]">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs text-[#6B6862]">Case</span>
              <span className="font-mono text-xs font-semibold text-[#1C1917] bg-[#F5F5F0] px-1.5 py-0.5 rounded">
                {currentCase.id}
              </span>
            </div>
            <p className="text-xs text-[#6B6862]">
              Created {new Date(currentCase.created_at).toLocaleString()} • {caseEvidence.length} file{caseEvidence.length === 1 ? '' : 's'}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={handleExtractAll}
              disabled={isExtractingAll || caseEvidence.length === 0}
              title="Run extraction across all files in this case"
            >
              <Zap className={`w-3.5 h-3.5 text-amber-600 ${isExtractingAll ? 'animate-spin' : ''}`} />
              <span>{isExtractingAll ? 'Extracting All...' : 'Extract All'}</span>
            </Button>

            <Button
              variant="secondary"
              size="sm"
              onClick={handleMatchEntities}
              disabled={isMatchingEntities || caseEvidence.length === 0}
              className="text-[#0F766E] border-[#0F766E]/30 hover:bg-[#0F766E]/5"
              title="Detect and match entities across all evidence using GLiNER + RapidFuzz"
            >
              <Users className={`w-3.5 h-3.5 ${isMatchingEntities ? 'animate-pulse' : ''}`} />
              <span>{isMatchingEntities ? 'Matching...' : 'Match Entities'}</span>
            </Button>

            <Button
              variant="secondary"
              size="sm"
              onClick={handleExtractEvents}
              disabled={isExtractingEvents || caseEvidence.length === 0}
              className="text-indigo-700 border-indigo-200 hover:bg-indigo-50"
              title="Extract structured event candidates and validate grounded text spans"
            >
              <Sparkles className={`w-3.5 h-3.5 ${isExtractingEvents ? 'animate-spin' : ''}`} />
              <span>{isExtractingEvents ? 'Extracting Events...' : 'Extract Events'}</span>
            </Button>

            <Button
              variant="secondary"
              size="sm"
              onClick={handleGenerateReport}
              disabled={isGeneratingReport || caseEvidence.length === 0}
              className="text-stone-700 border-stone-300 hover:bg-stone-100"
              title="Synthesize forensic incident reconstruction report"
            >
              <FileCheck className={`w-3.5 h-3.5 ${isGeneratingReport ? 'animate-spin' : ''}`} />
              <span>{isGeneratingReport ? 'Synthesizing...' : 'Forensic Report'}</span>
            </Button>

            <Button
              variant="primary"
              size="sm"
              onClick={() => navigate('/upload')}
            >
              <Upload className="w-3.5 h-3.5" />
              <span>Add evidence</span>
            </Button>

            <Button
              variant="secondary"
              size="sm"
              onClick={() => setIsDeleteCaseOpen(true)}
              className="text-rose-600 hover:bg-rose-50"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-[#E6E4DF] text-xs font-medium overflow-x-auto pb-0">
        <button
          onClick={() => setActiveTab('evidence')}
          className={`pb-2.5 px-2 inline-flex items-center gap-1.5 border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'evidence'
              ? 'border-[#0F766E] text-[#0F766E]'
              : 'border-transparent text-[#6B6862] hover:text-[#1C1917]'
          }`}
        >
          <FileText className="w-4 h-4" />
          <span>Evidence Files ({caseEvidence.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('entities')}
          className={`pb-2.5 px-2 inline-flex items-center gap-1.5 border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'entities'
              ? 'border-[#0F766E] text-[#0F766E]'
              : 'border-transparent text-[#6B6862] hover:text-[#1C1917]'
          }`}
        >
          <Users className="w-4 h-4" />
          <span>Entity Matching ({candidateMatches.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('events')}
          className={`pb-2.5 px-2 inline-flex items-center gap-1.5 border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'events'
              ? 'border-[#0F766E] text-[#0F766E]'
              : 'border-transparent text-[#6B6862] hover:text-[#1C1917]'
          }`}
        >
          <Sparkles className="w-4 h-4" />
          <span>Event Extraction ({events.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('timeline')}
          className={`pb-2.5 px-2 inline-flex items-center gap-1.5 border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'timeline'
              ? 'border-[#0F766E] text-[#0F766E]'
              : 'border-transparent text-[#6B6862] hover:text-[#1C1917]'
          }`}
        >
          <Clock className="w-4 h-4" />
          <span>Timeline ({timelineData ? timelineData.scheduled_events.length + timelineData.unscheduled_events.length : 0})</span>
        </button>

        <button
          onClick={() => setActiveTab('quiz')}
          className={`pb-2.5 px-2 inline-flex items-center gap-1.5 border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'quiz'
              ? 'border-[#0F766E] text-[#0F766E]'
              : 'border-transparent text-[#6B6862] hover:text-[#1C1917]'
          }`}
        >
          <HelpCircle className="w-4 h-4" />
          <span>Clarification Quiz ({quizQuestions.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('report')}
          className={`pb-2.5 px-2 inline-flex items-center gap-1.5 border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'report'
              ? 'border-[#0F766E] text-[#0F766E]'
              : 'border-transparent text-[#6B6862] hover:text-[#1C1917]'
          }`}
        >
          <FileCheck className="w-4 h-4" />
          <span>Incident Report</span>
        </button>
      </div>

      {/* TAB 1: Evidence Files & Intelligence */}
      {activeTab === 'evidence' && (
        <div>
          {isLoadingFiles ? (
            <div className="py-12 text-center text-xs text-[#6B6862]">Loading evidence files...</div>
          ) : caseEvidence.length === 0 ? (
            <div className="bg-white border border-[#E6E4DF] rounded-md p-10 text-center max-w-md mx-auto my-6">
              <h3 className="text-sm font-semibold text-[#1C1917] mb-1">No evidence in this case yet</h3>
              <p className="text-xs text-[#6B6862] mb-4">
                Upload images, audio recordings, PDFs, DOCX, or chat logs to preserve and analyze them.
              </p>
              <Button variant="primary" size="sm" onClick={() => navigate('/upload')}>
                Add evidence to this case
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              {/* ONE-CLICK END-TO-END ORCHESTRATED PIPELINE CARD */}
              <div className="bg-white border border-[#E6E4DF] rounded-lg p-5 space-y-5 shadow-xs">
                {/* Header & Controls */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#E6E4DF] pb-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-[#0F766E]" />
                      <h4 className="text-sm font-bold text-[#1C1917]">One-Click End-to-End Case Analysis</h4>
                      {analysisJob ? (
                        <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold flex items-center gap-1.5 border ${
                          ['RUNNING', 'PENDING', 'RESUMED'].includes(analysisJob.status)
                            ? 'bg-teal-50 text-[#0F766E] border-teal-200 animate-pulse'
                            : analysisJob.status === 'WAITING_FOR_USER'
                            ? 'bg-amber-50 text-amber-800 border-amber-200'
                            : analysisJob.status === 'COMPLETED'
                            ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                            : 'bg-rose-50 text-rose-800 border-rose-200'
                        }`}>
                          {['RUNNING', 'PENDING', 'RESUMED'].includes(analysisJob.status) && <RefreshCw className="w-3 h-3 animate-spin" />}
                          {analysisJob.status === 'WAITING_FOR_USER' && <Clock className="w-3 h-3" />}
                          {analysisJob.status === 'COMPLETED' && <CheckCircle2 className="w-3 h-3 text-emerald-600" />}
                          {analysisJob.status === 'FAILED' && <XCircle className="w-3 h-3 text-rose-600" />}
                          <span>
                            {['RUNNING', 'PENDING', 'RESUMED'].includes(analysisJob.status)
                              ? `Analyzing: ${analysisJob.current_stage?.replace(/_/g, ' ') || 'Stage 1: Validate Evidence'} (${analysisJob.progress_percentage ?? 0}%)`
                              : analysisJob.status === 'WAITING_FOR_USER'
                              ? 'Analysis ready — clarification needed'
                              : analysisJob.status === 'COMPLETED'
                              ? 'Analysis Complete (100%)'
                              : `Failed at ${analysisJob.failed_stage?.replace(/_/g, ' ') || analysisJob.current_stage?.replace(/_/g, ' ') || 'Execution'}`}
                          </span>
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-stone-100 text-stone-600 border border-stone-200">
                          15-Stage Pipeline Ready
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-[#6B6862] mt-1">
                      Orchestrates cryptographic validation, OCR/transcription, entity matching, timeline construction, clarification quiz, and final forensic report.
                    </p>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {analysisJob && analysisJob.status === 'FAILED' ? (
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={handleRetryJob}
                        className="bg-amber-600 hover:bg-amber-700 text-white"
                      >
                        <RefreshCw className="w-3.5 h-3.5 mr-1" />
                        <span>Retry from Failed Stage</span>
                      </Button>
                    ) : (
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={handleStartOneClickAnalysis}
                        disabled={isStartingJob || (analysisJob && ['RUNNING', 'PENDING', 'RESUMED'].includes(analysisJob.status)) || caseEvidence.length === 0}
                      >
                        <Sparkles className={`w-3.5 h-3.5 ${isStartingJob || (analysisJob && ['RUNNING', 'PENDING', 'RESUMED'].includes(analysisJob.status)) ? 'animate-spin' : ''}`} />
                        <span>
                          {isStartingJob || (analysisJob && ['RUNNING', 'PENDING', 'RESUMED'].includes(analysisJob.status))
                            ? 'Analyzing Case...'
                            : analysisJob
                            ? 'Re-Analyze Case'
                            : 'Analyze Case'}
                        </span>
                      </Button>
                    )}
                  </div>
                </div>

                {/* Progress Bar & Stepper Toggle */}
                {analysisJob && analysisJob.id && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between text-xs text-[#6B6862]">
                      <span className="font-mono">
                        Stage: <strong className="text-[#1C1917]">{analysisJob.current_stage?.replace(/_/g, ' ') || 'Stage 1: Validate Evidence'}</strong>
                      </span>
                      <div className="flex items-center gap-3">
                        <span className="font-mono font-bold text-[#0F766E]">{analysisJob.progress_percentage ?? 0}%</span>
                        <button
                          onClick={() => setShowStagesList(!showStagesList)}
                          className="inline-flex items-center gap-1 text-[11px] text-[#0F766E] hover:underline"
                        >
                          <span>{showStagesList ? 'Hide 15 Stages' : 'Show 15 Stages'}</span>
                          {showStagesList ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                        </button>
                      </div>
                    </div>

                    <div className="w-full bg-stone-100 rounded-full h-2 overflow-hidden border border-[#E6E4DF]">
                      <div
                        className="bg-[#0F766E] h-2 transition-all duration-500 rounded-full"
                        style={{ width: `${analysisJob.progress_percentage ?? 0}%` }}
                      />
                    </div>

                    {/* 15 Discrete Stages List */}
                    {showStagesList && (
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-2 pt-2 border-t border-[#E6E4DF]">
                        {[
                          { key: 'VALIDATE_EVIDENCE', label: '1. Validate Evidence', desc: 'SHA-256 integrity' },
                          { key: 'EXTRACT_CONTENT', label: '2. Extract Content', desc: 'OCR & ASR models' },
                          { key: 'NORMALIZE_CONTENT', label: '3. Normalize Content', desc: 'Encoding & segments' },
                          { key: 'EXTRACT_ENTITIES', label: '4. Extract Entities', desc: 'GLiNER entity extraction' },
                          { key: 'MATCH_ENTITIES', label: '5. Disambiguate Entities', desc: 'RapidFuzz alias matching' },
                          { key: 'UNDERSTAND_CASE', label: '6. Understand Case', desc: 'Domain & grounded facts' },
                          { key: 'EXTRACT_EVENTS', label: '7. Extract Events', desc: 'Multi-line bank & chats' },
                          { key: 'BUILD_TIMELINE', label: '8. Build Timeline', desc: 'Deterministic chronology' },
                          { key: 'IDENTIFY_UNCERTAINTIES', label: '9. Identify Uncertainties', desc: 'Cross-evidence discrepancies' },
                          { key: 'GENERATE_PRELIMINARY_STORY', label: '10. Preliminary Story', desc: '150–250 word draft' },
                          { key: 'GENERATE_CONTEXTUAL_QUIZ', label: '11. Contextual Quiz', desc: 'Case unknown questions' },
                          { key: 'AWAIT_USER_ANSWERS', label: '12. Awaiting Testimony', desc: 'Clarification answers' },
                          { key: 'INCORPORATE_CLARIFICATIONS', label: '13. Incorporate Input', desc: 'Refining weights' },
                          { key: 'GENERATE_FINAL_REPORT', label: '14. Final Report', desc: '200–350 word narrative' },
                          { key: 'COMPLETE', label: '15. Complete', desc: 'Investigation finalized' },
                        ].map((stageDef) => {
                          const stageRec = analysisJob.stages?.find(s => s.stage_name === stageDef.key);
                          const isDone = analysisJob.completed_stages?.includes(stageDef.key) || stageRec?.status === 'COMPLETED';
                          const isRunning = analysisJob.current_stage === stageDef.key && analysisJob.status === 'RUNNING';
                          const isWaiting = stageDef.key === 'AWAIT_USER_ANSWERS' && analysisJob.status === 'WAITING_FOR_USER';
                          const isFailed = analysisJob.failed_stage === stageDef.key;

                          return (
                            <div
                              key={stageDef.key}
                              className={`p-2 rounded border text-xs flex items-start gap-2 transition-colors ${
                                isRunning
                                  ? 'bg-teal-50 border-[#0F766E]/40'
                                  : isWaiting
                                  ? 'bg-amber-50 border-amber-300'
                                  : isDone
                                  ? 'bg-emerald-50/50 border-emerald-200'
                                  : isFailed
                                  ? 'bg-rose-50 border-rose-300'
                                  : 'bg-[#F9F9F7] border-stone-200 opacity-60'
                              }`}
                            >
                              <div className="pt-0.5 shrink-0">
                                {isDone ? (
                                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                                ) : isRunning ? (
                                  <RefreshCw className="w-3.5 h-3.5 text-[#0F766E] animate-spin" />
                                ) : isWaiting ? (
                                  <Clock className="w-3.5 h-3.5 text-amber-600 animate-pulse" />
                                ) : isFailed ? (
                                  <XCircle className="w-3.5 h-3.5 text-rose-600" />
                                ) : (
                                  <div className="w-3 h-3 rounded-full border border-stone-300" />
                                )}
                              </div>
                              <div className="min-w-0 flex-1">
                                <div className="flex items-center justify-between gap-1">
                                  <span className={`font-semibold truncate ${
                                    isRunning ? 'text-[#0F766E]' : isWaiting ? 'text-amber-800' : isDone ? 'text-emerald-900' : 'text-stone-700'
                                  }`}>
                                    {stageDef.label}
                                  </span>
                                  {stageRec?.duration_ms && (
                                    <span className="text-[10px] text-stone-500 font-mono">
                                      {stageRec.duration_ms > 1000
                                        ? `${(stageRec.duration_ms / 1000).toFixed(1)}s`
                                        : `${Math.round(stageRec.duration_ms)}ms`}
                                    </span>
                                  )}
                                </div>
                                <p className="text-[11px] text-stone-500 truncate">{stageDef.desc}</p>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}

                {/* STAGE 10+: PRELIMINARY CASE STORY & EVIDENCE-BACKED FACTS */}
                {(analysisJob?.artifacts?.mvp_analysis || mvpAnalysis) && (
                  <div className="border-t border-[#E6E4DF] pt-4 space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="text-[11px] uppercase tracking-wider text-[#0F766E] font-semibold block">
                          Preliminary Case Story (Grounded Narrative)
                        </span>
                        <h4 className="text-sm font-bold text-[#1C1917]">
                          {(analysisJob?.artifacts?.mvp_analysis?.case_title) || mvpAnalysis?.case_title}
                        </h4>
                      </div>
                      <span className="text-xs text-[#6B6862] font-mono">
                        {(analysisJob?.artifacts?.mvp_analysis?.narrative_word_count) || mvpAnalysis?.narrative_word_count} words
                      </span>
                    </div>

                    <p className="text-xs text-[#334155] leading-relaxed whitespace-pre-wrap bg-[#F9F9F7] p-4 rounded border border-[#E6E4DF]">
                      {(analysisJob?.artifacts?.mvp_analysis?.preliminary_narrative) || mvpAnalysis?.preliminary_narrative}
                    </p>

                    {/* Evidence-Backed Facts Grid */}
                    {(((analysisJob?.artifacts?.mvp_analysis?.evidence_backed_facts) || mvpAnalysis?.evidence_backed_facts) || []).length > 0 && (
                      <div className="space-y-2">
                        <h5 className="text-xs font-semibold uppercase tracking-wider text-[#6B6862]">
                          Key Evidence-Backed Facts ({(((analysisJob?.artifacts?.mvp_analysis?.evidence_backed_facts) || mvpAnalysis?.evidence_backed_facts) || []).length})
                        </h5>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                          {(((analysisJob?.artifacts?.mvp_analysis?.evidence_backed_facts) || mvpAnalysis?.evidence_backed_facts) || []).map((fact: any, fIdx: number) => (
                            <div key={fIdx} className="bg-white p-3 rounded border border-[#E6E4DF] text-xs space-y-1">
                              <span className="font-semibold text-[#1C1917] block">{fact.topic}</span>
                              <p className="text-[#334155] text-[11px] leading-relaxed">{fact.claim_text}</p>
                              <div className="pt-1 text-[10px] text-[#6B6862] font-mono truncate" title={fact.citation?.verbatim_quote}>
                                <span className="font-semibold text-[#0F766E]">{fact.citation?.filename}:</span> "{fact.citation?.verbatim_quote}"
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* STAGE 12: CONTEXTUAL CLARIFICATION QUIZ (AUTOMATIC PAUSE FOR TESTIMONY) */}
                {analysisJob && analysisJob.status === 'WAITING_FOR_USER' && quizQuestions.length > 0 && (
                  <div className="border-t-2 border-amber-300 pt-4 space-y-4 bg-amber-50/30 p-4 rounded-lg">
                    <div className="flex items-center gap-2">
                      <Clock className="w-4 h-4 text-amber-600 animate-pulse" />
                      <div>
                        <h4 className="text-sm font-bold text-amber-950">Clarification Quiz — Case Uncertainties</h4>
                        <p className="text-xs text-amber-800">
                          The pipeline has paused at Stage 12. Clarify these key unknowns to finalize the chronological reconstruction and forensic report.
                        </p>
                      </div>
                    </div>

                    <div className="space-y-4">
                      {quizQuestions.map((q, qIdx) => {
                        const currentAns = jobQuizAnswers[q.id] || {
                          selected_option: '',
                          user_surety: 'Fairly sure',
                          knowledge_basis: 'Direct first-hand knowledge',
                          free_text: ''
                        };

                        return (
                          <div key={q.id} className="bg-white p-4 rounded-md border border-amber-200 shadow-xs space-y-3">
                            <div className="flex items-start justify-between gap-2">
                              <div className="space-y-1">
                                <span className="text-[10px] uppercase font-bold tracking-wider text-amber-800">
                                  Question {qIdx + 1} of {quizQuestions.length}
                                  {q.activity_name ? ` — ${q.activity_name}` : ''}
                                </span>
                                <h5 className="text-xs font-semibold text-[#1C1917]">{q.question_text || q.prompt}</h5>
                              </div>
                            </div>

                            {q.why_it_matters && (
                              <div className="text-[11px] text-amber-900 bg-amber-50/70 p-2 rounded border border-amber-200/80">
                                <span className="font-semibold">Why this matters: </span>
                                {q.why_it_matters}
                              </div>
                            )}

                            {(q.context_excerpt || q.context_summary) && (
                              <p className="text-[11px] text-[#6B6862] bg-[#F9F9F7] p-2 rounded border border-stone-200 font-mono">
                                <span className="font-semibold text-[#1C1917] not-italic">Relevant evidence: </span>
                                {q.context_excerpt || q.context_summary}
                              </p>
                            )}

                            {/* Candidate Options */}
                            <div className="space-y-1.5">
                              {q.options.map((opt, optIdx) => (
                                <label
                                  key={optIdx}
                                  className={`flex items-center gap-2.5 p-2 rounded border text-xs cursor-pointer transition-colors ${
                                    currentAns.selected_option === opt
                                      ? 'border-[#0F766E] bg-teal-50/40 font-medium text-[#0F766E]'
                                      : 'border-stone-200 hover:bg-stone-50 text-[#334155]'
                                  }`}
                                >
                                  <input
                                    type="radio"
                                    name={`job-quiz-${q.id}`}
                                    value={opt}
                                    checked={currentAns.selected_option === opt}
                                    onChange={() => {
                                      setJobQuizAnswers({
                                        ...jobQuizAnswers,
                                        [q.id]: { ...currentAns, selected_option: opt }
                                      });
                                    }}
                                    className="text-[#0F766E] focus:ring-[#0F766E]"
                                  />
                                  <span>{opt}</span>
                                </label>
                              ))}
                            </div>

                            {/* Optional Explanation Input */}
                            <div className="pt-1">
                              <label className="text-[10px] font-semibold text-[#6B6862] uppercase block mb-1">
                                Optional Explanation / Additional Context
                              </label>
                              <input
                                type="text"
                                value={currentAns.free_text || ''}
                                onChange={(e) => {
                                  setJobQuizAnswers({
                                    ...jobQuizAnswers,
                                    [q.id]: { ...currentAns, free_text: e.target.value }
                                  });
                                }}
                                placeholder="Add any additional context, dates, or witness details (optional)..."
                                className="w-full text-xs p-2 rounded border border-[#E6E4DF] bg-[#F9F9F7] focus:bg-white text-[#1C1917]"
                              />
                            </div>

                            {/* Surety & Knowledge Basis Controls */}
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2 border-t border-stone-100">
                              <div>
                                <label className="text-[10px] font-semibold text-[#6B6862] uppercase block mb-1">
                                  Your Surety Level
                                </label>
                                <select
                                  value={currentAns.user_surety}
                                  onChange={(e) => {
                                    setJobQuizAnswers({
                                      ...jobQuizAnswers,
                                      [q.id]: { ...currentAns, user_surety: e.target.value }
                                    });
                                  }}
                                  className="w-full text-xs p-1.5 rounded border border-[#E6E4DF] bg-white text-[#1C1917]"
                                >
                                  <option value="Very sure">Very sure (100% confidence)</option>
                                  <option value="Fairly sure">Fairly sure (75% confidence)</option>
                                  <option value="Somewhat sure">Somewhat sure (50% confidence)</option>
                                  <option value="Unsure">Unsure (25% confidence)</option>
                                  <option value="Do not remember">Do not remember (0% confidence)</option>
                                </select>
                              </div>

                              <div>
                                <label className="text-[10px] font-semibold text-[#6B6862] uppercase block mb-1">
                                  Basis of Knowledge
                                </label>
                                <select
                                  value={currentAns.knowledge_basis}
                                  onChange={(e) => {
                                    setJobQuizAnswers({
                                      ...jobQuizAnswers,
                                      [q.id]: { ...currentAns, knowledge_basis: e.target.value }
                                    });
                                  }}
                                  className="w-full text-xs p-1.5 rounded border border-[#E6E4DF] bg-white text-[#1C1917]"
                                >
                                  <option value="Direct first-hand knowledge">Direct first-hand knowledge</option>
                                  <option value="Contemporaneous written record">Contemporaneous written record</option>
                                  <option value="Told by someone else">Told by someone else</option>
                                  <option value="Inferred from circumstances">Inferred from circumstances</option>
                                </select>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    <div className="pt-2 flex items-center justify-between border-t border-amber-200">
                      <span className="text-xs text-amber-800">
                        Submitting testimony will automatically resume the pipeline and generate the final report.
                      </span>
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={handleSubmitJobQuiz}
                        disabled={isSubmittingJobQuiz}
                        className="bg-[#0F766E] hover:bg-[#0D655E] text-white"
                      >
                        <Sparkles className={`w-3.5 h-3.5 mr-1 ${isSubmittingJobQuiz ? 'animate-spin' : ''}`} />
                        <span>{isSubmittingJobQuiz ? 'Submitting & Resuming...' : 'Submit Testimony & Generate Final Report'}</span>
                      </Button>
                    </div>
                  </div>
                )}

                {/* STAGE 15: COMPLETE — FINAL FORENSIC INCIDENT REPORT & COLLAPSIBLE APPENDIX */}
                {analysisJob && analysisJob.status === 'COMPLETED' && (
                  <div className="border-t-2 border-emerald-500 pt-4 space-y-4 bg-emerald-50/20 p-4 rounded-lg">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                        <div>
                          <h4 className="text-sm font-bold text-emerald-950">Final Reconstructed Incident Report</h4>
                          <span className="text-xs text-emerald-700">Synthesized from validated documentary evidence and investigator testimony</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <a
                          href={api.getReportHtmlUrl(id || '')}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-xs px-2.5 py-1.5 rounded border border-[#E6E4DF] bg-white text-[#1C1917] hover:bg-stone-50"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                          <span>Print / Export HTML</span>
                        </a>
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => setActiveTab('report')}
                        >
                          <FileCheck className="w-3.5 h-3.5 mr-1 text-[#0F766E]" />
                          <span>View Full Report Tab</span>
                        </Button>
                      </div>
                    </div>

                    {/* Final Reconstructed Narrative */}
                    <div className="bg-white p-4 rounded border border-emerald-200 space-y-2">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-800">
                        Reconstructed Incident Narrative (200–350 Words)
                      </span>
                      <p className="text-xs text-[#1C1917] leading-relaxed whitespace-pre-wrap">
                        {reportData?.report_data?.what_happened ||
                         analysisJob?.artifacts?.report?.what_happened ||
                         analysisJob?.artifacts?.mvp_analysis?.preliminary_narrative ||
                         'Report narrative finalized.'}
                      </p>
                    </div>

                    {/* Collapsible Technical Appendix */}
                    <div className="border border-[#E6E4DF] rounded-md bg-white overflow-hidden">
                      <button
                        onClick={() => setShowTechnicalAppendix(!showTechnicalAppendix)}
                        className="w-full p-3 flex items-center justify-between text-xs font-semibold text-[#1C1917] hover:bg-stone-50 transition-colors text-left"
                      >
                        <div className="flex items-center gap-2">
                          <Layers className="w-4 h-4 text-[#0F766E]" />
                          <span>Technical Appendix & Forensic Audit Log</span>
                        </div>
                        {showTechnicalAppendix ? <ChevronUp className="w-4 h-4 text-[#6B6862]" /> : <ChevronDown className="w-4 h-4 text-[#6B6862]" />}
                      </button>

                      {showTechnicalAppendix && (
                        <div className="p-4 border-t border-[#E6E4DF] space-y-4 text-xs bg-[#F9F9F7]">
                          {/* Chronological Event Timeline */}
                          <div className="space-y-1.5">
                            <h5 className="font-semibold text-[#1C1917] flex items-center gap-1.5">
                              <Clock className="w-3.5 h-3.5 text-[#0F766E]" />
                              <span>Reconstructed Chronological Events</span>
                            </h5>
                            <div className="bg-white rounded border border-[#E6E4DF] overflow-x-auto">
                              <table className="w-full text-left text-[11px]">
                                <thead className="bg-stone-50 border-b border-[#E6E4DF] text-[#6B6862]">
                                  <tr>
                                    <th className="p-2">Timestamp</th>
                                    <th className="p-2">Event Title</th>
                                    <th className="p-2">Modality</th>
                                    <th className="p-2">Source</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-stone-100">
                                  {(timelineData?.scheduled_events || []).map((e, idx) => (
                                    <tr key={idx} className="hover:bg-stone-50">
                                      <td className="p-2 font-mono">{e.datetime_formatted || e.datetime}</td>
                                      <td className="p-2 font-medium text-[#1C1917]">{e.title}</td>
                                      <td className="p-2 capitalize">{e.modality}</td>
                                      <td className="p-2 text-stone-500 font-mono truncate max-w-xs">{e.source_filename}</td>
                                    </tr>
                                  ))}
                                  {(!timelineData?.scheduled_events || timelineData.scheduled_events.length === 0) && (
                                    <tr>
                                      <td colSpan={4} className="p-3 text-center text-stone-500 italic">No scheduled events extracted</td>
                                    </tr>
                                  )}
                                </tbody>
                              </table>
                            </div>
                          </div>

                          {/* Contradictions & Discrepancies */}
                          <div className="space-y-1.5">
                            <h5 className="font-semibold text-[#1C1917] flex items-center gap-1.5">
                              <Scale className="w-3.5 h-3.5 text-amber-600" />
                              <span>Cross-Evidence Contradictions ({contradictions.length})</span>
                            </h5>
                            <div className="bg-white rounded border border-[#E6E4DF] overflow-x-auto">
                              <table className="w-full text-left text-[11px]">
                                <thead className="bg-stone-50 border-b border-[#E6E4DF] text-[#6B6862]">
                                  <tr>
                                    <th className="p-2">Type</th>
                                    <th className="p-2">Description</th>
                                    <th className="p-2">Source A</th>
                                    <th className="p-2">Source B</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-stone-100">
                                  {contradictions.map((c, idx) => (
                                    <tr key={idx} className="hover:bg-stone-50">
                                      <td className="p-2 uppercase text-[10px] font-semibold text-amber-700">{c.contradiction_type}</td>
                                      <td className="p-2">{c.description}</td>
                                      <td className="p-2 font-mono text-[10px] text-stone-600">{c.source_a}</td>
                                      <td className="p-2 font-mono text-[10px] text-stone-600">{c.source_b}</td>
                                    </tr>
                                  ))}
                                  {contradictions.length === 0 && (
                                    <tr>
                                      <td colSpan={4} className="p-3 text-center text-stone-500 italic">No contradictions identified across documentary evidence</td>
                                    </tr>
                                  )}
                                </tbody>
                              </table>
                            </div>
                          </div>

                          {/* Cryptographic SHA-256 Hashes */}
                          <div className="space-y-1.5">
                            <h5 className="font-semibold text-[#1C1917] flex items-center gap-1.5">
                              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                              <span>Evidence Cryptographic Chain of Custody</span>
                            </h5>
                            <div className="bg-white rounded border border-[#E6E4DF] p-2 space-y-1">
                              {caseEvidence.map(ev => (
                                <div key={ev.id} className="flex items-center justify-between text-[10px] font-mono text-stone-600">
                                  <span className="truncate max-w-xs text-[#1C1917]">{ev.original_filename}</span>
                                  <span className="text-stone-400">{ev.sha256}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Evidence Table */}
              <div className="bg-white border border-[#E6E4DF] rounded-md overflow-hidden">
                <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-[#E6E4DF] bg-[#F9F9F7] text-[#6B6862]">
                    <th className="py-2.5 px-4 font-medium">Filename</th>
                    <th className="py-2.5 px-4 font-medium">Type</th>
                    <th className="py-2.5 px-4 font-medium">Size</th>
                    <th className="py-2.5 px-4 font-medium">SHA-256</th>
                    <th className="py-2.5 px-4 font-medium">Extraction Status</th>
                    <th className="py-2.5 px-4 font-medium text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E6E4DF]">
                  {caseEvidence.map((file) => {
                    const truncatedHash = `${file.sha256.substring(0, 8)}...${file.sha256.substring(file.sha256.length - 6)}`;
                    const isCopied = copiedHash === file.id;
                    const isExtracting = extractingIds.has(file.id);
                    const hasExtractedText = Boolean(file.extracted_text && file.extracted_text.trim());

                    return (
                      <tr key={file.id} className="hover:bg-[#F9F9F7] transition-colors">
                        <td className="py-3 px-4 font-medium text-[#1C1917] max-w-xs truncate" title={file.original_filename}>
                          {file.original_filename}
                        </td>
                        <td className="py-3 px-4 text-[#6B6862] uppercase text-[11px]">
                          {file.file_type}
                        </td>
                        <td className="py-3 px-4 text-[#6B6862] font-mono text-[11px]">
                          {formatBytes(file.size_bytes)}
                        </td>
                        <td className="py-3 px-4">
                          <button
                            onClick={() => handleCopyHash(file.sha256, file.id)}
                            className="inline-flex items-center gap-1 font-mono text-[11px] text-[#6B6862] hover:text-[#1C1917]"
                            title="Click to copy full SHA-256 hash"
                          >
                            <code>{truncatedHash}</code>
                            {isCopied ? <Check className="w-3 h-3 text-[#0F766E]" /> : <Copy className="w-3 h-3 text-[#9C9890]" />}
                          </button>
                        </td>

                        {/* Extraction Status & Quick View */}
                        <td className="py-3 px-4">
                          {isExtracting ? (
                            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] bg-amber-50 text-amber-700 font-medium animate-pulse">
                              <RefreshCw className="w-3 h-3 animate-spin" />
                              Extracting...
                            </span>
                          ) : hasExtractedText ? (
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => setViewingEvidence(file)}
                                className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] bg-emerald-50 text-emerald-800 hover:bg-emerald-100 border border-emerald-200 transition-colors font-medium"
                                title="Click to view full extracted text and metadata"
                              >
                                <Eye className="w-3 h-3 text-emerald-600" />
                                <span>{(file.extraction_confidence ? (file.extraction_confidence * 100).toFixed(1) : 100)}% conf</span>
                                {file.processing_time_ms && (
                                  <span className="text-emerald-700 font-mono text-[10px]">
                                    ({Math.round(file.processing_time_ms)}ms)
                                  </span>
                                )}
                              </button>
                            </div>
                          ) : (
                            <button
                              onClick={() => handleExtractSingle(file)}
                              className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] bg-stone-100 text-stone-700 hover:bg-stone-200 border border-stone-200 transition-colors font-medium"
                            >
                              <Zap className="w-3 h-3 text-amber-600" />
                              <span>Extract</span>
                            </button>
                          )}
                        </td>

                        {/* Actions */}
                        <td className="py-3 px-4 text-right">
                          <div className="inline-flex items-center gap-1.5">
                            {hasExtractedText && (
                              <button
                                onClick={() => setViewingEvidence(file)}
                                className="p-1 text-[#6B6862] hover:text-[#0F766E] rounded hover:bg-stone-100"
                                title="View extracted text"
                              >
                                <Eye className="w-3.5 h-3.5" />
                              </button>
                            )}
                            <a
                              href={api.getFileUrl(file.id)}
                              download={file.original_filename}
                              className="p-1 text-[#6B6862] hover:text-[#0F766E] rounded hover:bg-stone-100"
                              title="Download original file"
                            >
                              <Download className="w-3.5 h-3.5" />
                            </a>
                            <button
                              onClick={() => setDeleteEvidenceTarget(file)}
                              className="p-1 text-[#9C9890] hover:text-rose-600 rounded hover:bg-stone-100"
                              title="Delete evidence"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            </div>
          )}
        </div>
      )}

            {/* TAB 2: Entity Intelligence & Disambiguation */}
      {activeTab === 'entities' && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[#F9F9F7] p-3 rounded-md border border-[#E6E4DF]">
            <div>
              <h3 className="text-xs font-semibold text-[#1C1917]">Cross-Evidence Entity Intelligence</h3>
              <p className="text-[11px] text-[#6B6862]">
                GLiNER extracted entities grouped with RapidFuzz similarity scoring. Review and confirm matches below.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="primary"
                size="sm"
                onClick={handleMatchEntities}
                disabled={isMatchingEntities}
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isMatchingEntities ? 'animate-spin' : ''}`} />
                <span>{isMatchingEntities ? 'Analyzing...' : 'Re-run Analysis'}</span>
              </Button>
            </div>
          </div>

          {/* Filter Pills */}
          <div className="flex flex-wrap items-center gap-1.5">
            {['all', 'person', 'organization', 'location', 'date', 'time', 'identifier', 'needs_verification'].map((filterKey) => {
              const isNeedsVerify = filterKey === 'needs_verification';
              const isSelected = entityFilter === filterKey;

              let label = filterKey === 'all' ? `All (${candidateMatches.length})` : filterKey;
              if (isNeedsVerify) {
                label = `Needs Verification (${needsVerificationCount})`;
              }

              return (
                <button
                  key={filterKey}
                  onClick={() => setEntityFilter(filterKey)}
                  className={`px-2.5 py-1 rounded text-xs capitalize transition-colors font-medium flex items-center gap-1.5 ${
                    isSelected
                      ? isNeedsVerify ? 'bg-amber-700 text-white' : 'bg-[#0F766E] text-white'
                      : isNeedsVerify && needsVerificationCount > 0
                      ? 'bg-amber-50 border border-amber-300 text-amber-900 hover:bg-amber-100'
                      : 'bg-white border border-[#E6E4DF] text-[#6B6862] hover:text-[#1C1917]'
                  }`}
                >
                  {isNeedsVerify && <AlertTriangle className="w-3 h-3 text-amber-500" />}
                  <span>{label}</span>
                </button>
              );
            })}
          </div>

          {/* Candidate Matches List */}
          {isLoadingEntities ? (
            <div className="py-12 text-center text-xs text-[#6B6862]">Loading entity intelligence...</div>
          ) : filteredMatches.length === 0 ? (
            <div className="bg-white border border-[#E6E4DF] rounded-md p-10 text-center max-w-md mx-auto my-6">
              <Users className="w-8 h-8 text-[#9C9890] mx-auto mb-2" />
              <h3 className="text-sm font-semibold text-[#1C1917] mb-1">No entity matches found</h3>
              <p className="text-xs text-[#6B6862] mb-4">
                Click "Match Entities" to run GLiNER and RapidFuzz across your case evidence.
              </p>
              <Button variant="primary" size="sm" onClick={handleMatchEntities} disabled={isMatchingEntities}>
                Detect & Match Entities
              </Button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filteredMatches.map((cand) => {
                const isReviewing = reviewingMatchId === cand.id;
                const distinctFiles = Array.from(new Set(cand.mentions.map((m) => m.filename)));

                return (
                  <div
                    key={cand.id}
                    className={`bg-white border rounded-md p-4 space-y-3 transition-shadow ${
                      cand.status === 'confirmed'
                        ? 'border-emerald-300 ring-1 ring-emerald-200'
                        : cand.status === 'rejected'
                        ? 'border-rose-200 opacity-75'
                        : cand.status === 'separate'
                        ? 'border-stone-300'
                        : 'border-[#E6E4DF] hover:shadow-sm'
                    }`}
                  >
                    {/* Header */}
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-semibold text-[#1C1917]">
                            {cand.canonical_name}
                          </span>
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-medium uppercase tracking-wider bg-stone-100 text-stone-600">
                            {cand.entity_type}
                          </span>
                        </div>
                        <div className="text-[11px] text-[#6B6862] mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5">
                          <span>
                            Found across {distinctFiles.length} evidence file{distinctFiles.length === 1 ? '' : 's'} ({cand.mentions.length} mention{cand.mentions.length === 1 ? '' : 's'})
                          </span>
                          <span className="text-[#9C9890]">
                            • GLiNER conf: {Math.round((cand.classification_confidence ?? cand.extraction_confidence ?? 1) * 100)}%
                          </span>
                          {cand.ocr_confidence !== undefined && cand.ocr_confidence !== null && (
                            <span className="text-stone-600 font-mono">
                              • OCR conf: {Math.round(cand.ocr_confidence * 100)}%
                            </span>
                          )}
                          {cand.match_type && cand.match_type !== 'single_occurrence' && (
                            <span className="text-teal-700 font-medium">
                              • {cand.match_type?.replace(/_/g, ' ') || 'match'}
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Similarity & Status Badge */}
                      <div className="flex flex-col items-end gap-1">
                        {cand.is_single_occurrence ? (
                          <span className="font-mono text-[11px] font-medium px-2 py-0.5 rounded bg-stone-100 text-stone-700 border border-stone-200">
                            Single occurrence
                          </span>
                        ) : (
                          <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-blue-50 text-blue-800 border border-blue-200">
                            {cand.similarity_score}% similarity
                          </span>
                        )}
                        {cand.status === 'confirmed' && (
                          <span className="inline-flex items-center gap-1 text-[11px] text-emerald-700 font-medium">
                            <CheckCircle2 className="w-3 h-3" /> Confirmed
                          </span>
                        )}
                        {cand.status === 'rejected' && (
                          <span className="inline-flex items-center gap-1 text-[11px] text-rose-600 font-medium">
                            <XCircle className="w-3 h-3" /> Rejected
                          </span>
                        )}
                        {cand.status === 'separate' && (
                          <span className="inline-flex items-center gap-1 text-[11px] text-stone-600 font-medium">
                            <Split className="w-3 h-3" /> Separate
                          </span>
                        )}
                        {cand.status === 'pending' && (
                          <span className="text-[11px] text-amber-700 font-medium">
                            Pending Review
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Verification & Ambiguity Warning Callout */}
                    {(cand.requires_source_verification || cand.is_low_confidence) && (
                      <div className="bg-amber-50 border border-amber-200 rounded p-2.5 text-xs text-amber-900 space-y-1">
                        <div className="flex items-center gap-1.5 font-semibold text-amber-800">
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                          <span>Needs Source Verification / Low Confidence</span>
                        </div>
                        {cand.verification_reasons && cand.verification_reasons.length > 0 && (
                          <div className="text-[11px] text-amber-700 space-x-2">
                            {cand.verification_reasons.map((r, rIdx) => (
                              <span key={rIdx} className="inline-block bg-amber-100/70 px-1.5 py-0.5 rounded border border-amber-200 text-[10px] font-mono">
                                {r?.replace(/_/g, ' ') || ''}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Candidate Organizational Relationships (Not Merged) */}
                    {cand.related_entities && cand.related_entities.length > 0 && (
                      <div className="bg-slate-50 border border-slate-200 rounded p-2 text-xs space-y-1">
                        <div className="text-[10px] uppercase font-semibold text-slate-500 tracking-wider flex items-center gap-1">
                          <Link2 className="w-3 h-3 text-slate-500" />
                          <span>Candidate Relationships (Kept Separate):</span>
                        </div>
                        <div className="flex flex-wrap gap-1.5 pt-0.5">
                          {cand.related_entities.map((rel, rIdx) => (
                            <span
                              key={rIdx}
                              className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] bg-white border border-slate-200 text-slate-800"
                              title={rel.rationale}
                            >
                              <span className="font-semibold text-indigo-700">[{rel.relationship_type?.replace(/_/g, ' ') || 'related'}]</span>
                              <span>{rel.target_canonical_name}</span>
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Mentions Provenance */}
                    <div className="bg-[#F9F9F7] rounded p-2.5 text-xs space-y-1.5 border border-[#E6E4DF]">
                      <div className="text-[10px] uppercase font-semibold text-[#9C9890] tracking-wider">
                        Source Mentions & Provenance:
                      </div>
                      {cand.mentions.map((m, mIdx) => {
                        const sourceFile = caseEvidence.find((f) => f.id === m.evidence_id);
                        return (
                          <div key={mIdx} className="flex items-center justify-between text-[11px] gap-2">
                            <span className="font-medium text-[#1C1917] truncate max-w-[200px] flex items-center gap-1.5">
                              <span>"{m.text}"</span>
                              {m.is_low_confidence && (
                                <span className="px-1 py-0.2 rounded text-[9px] bg-amber-100 text-amber-800 font-normal">
                                  Low conf
                                </span>
                              )}
                              {m.requires_source_verification && (
                                <span className="px-1 py-0.2 rounded text-[9px] bg-rose-100 text-rose-800 font-normal">
                                  Verify
                                </span>
                              )}
                            </span>
                            <div className="flex items-center gap-1.5 text-[#6B6862]">
                              {sourceFile && (
                                <button
                                  type="button"
                                  onClick={() => setViewingEvidence(sourceFile)}
                                  className="text-[10px] text-teal-700 hover:text-teal-900 underline font-medium"
                                  title="View original evidence file"
                                >
                                  [inspect]
                                </button>
                              )}
                              <a
                                href={api.getFileUrl(m.evidence_id)}
                                download={m.filename}
                                className="hover:text-[#0F766E] underline truncate max-w-[120px]"
                                title={`Download original file: ${m.filename}`}
                              >
                                {m.filename}
                              </a>
                              <span className="text-[10px] font-mono text-[#9C9890]">
                                ({Math.round(m.confidence * 100)}%)
                              </span>
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    {/* Review Controls */}
                    <div className="pt-2 border-t border-[#E6E4DF] flex items-center justify-between gap-2">
                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={() => handleReviewMatch(cand.id, 'confirm')}
                          disabled={isReviewing || cand.status === 'confirmed'}
                          className={`inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                            cand.status === 'confirmed'
                              ? 'bg-emerald-600 text-white cursor-default'
                              : 'bg-white border border-[#E6E4DF] text-emerald-700 hover:bg-emerald-50'
                          }`}
                          title="Confirm that these mentions correspond to the same individual or entity"
                        >
                          <UserCheck className="w-3.5 h-3.5" />
                          <span>Confirm</span>
                        </button>

                        <button
                          onClick={() => handleReviewMatch(cand.id, 'separate')}
                          disabled={isReviewing || cand.status === 'separate'}
                          className={`inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                            cand.status === 'separate'
                              ? 'bg-stone-600 text-white cursor-default'
                              : 'bg-white border border-[#E6E4DF] text-stone-700 hover:bg-stone-100'
                          }`}
                          title="Explicitly mark these mentions as distinct separate individuals"
                        >
                          <Split className="w-3.5 h-3.5" />
                          <span>Separate</span>
                        </button>

                        <button
                          onClick={() => handleReviewMatch(cand.id, 'reject')}
                          disabled={isReviewing || cand.status === 'rejected'}
                          className={`inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                            cand.status === 'rejected'
                              ? 'bg-rose-600 text-white cursor-default'
                              : 'bg-white border border-[#E6E4DF] text-rose-700 hover:bg-rose-50'
                          }`}
                          title="Reject false candidate match"
                        >
                          <UserX className="w-3.5 h-3.5" />
                          <span>Reject</span>
                        </button>
                      </div>

                      {cand.status !== 'pending' && (
                        <button
                          onClick={() => handleReviewMatch(cand.id, 'undo')}
                          disabled={isReviewing}
                          className="text-[11px] text-[#6B6862] hover:text-[#1C1917] underline"
                        >
                          Reset
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: Event Extraction & Intelligence */}
      {activeTab === 'events' && (
        <div className="space-y-4">
          {/* Header & Filter Controls */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[#F9F9F7] p-3 rounded-md border border-[#E6E4DF]">
            <div className="flex flex-wrap items-center gap-1.5 text-xs">
              <span className="text-[#6B6862] mr-1">Modality:</span>
              {(['all', 'completed', 'planned', 'alleged', 'denied'] as const).map((mod) => (
                <button
                  key={mod}
                  onClick={() => setEventModalityFilter(mod)}
                  className={`px-2.5 py-1 rounded capitalize transition-colors ${
                    eventModalityFilter === mod
                      ? 'bg-[#1C1917] text-white font-medium'
                      : 'bg-white border border-[#E6E4DF] text-[#6B6862] hover:text-[#1C1917]'
                  }`}
                >
                  {mod === 'all' ? `All (${events.length})` : `${mod} (${events.filter((e) => e.modality === mod).length})`}
                </button>
              ))}
            </div>

            <Button
              variant="secondary"
              size="sm"
              onClick={handleExtractEvents}
              disabled={isExtractingEvents || caseEvidence.length === 0}
              className="text-indigo-700 border-indigo-200 hover:bg-indigo-50"
            >
              <Sparkles className={`w-3.5 h-3.5 ${isExtractingEvents ? 'animate-spin' : ''}`} />
              <span>{isExtractingEvents ? 'Extracting Events...' : 'Extract Events'}</span>
            </Button>
          </div>

          {isLoadingEvents ? (
            <div className="py-12 text-center text-xs text-[#6B6862]">Loading structured events...</div>
          ) : events.length === 0 ? (
            <div className="bg-white border border-[#E6E4DF] rounded-md p-10 text-center max-w-md mx-auto my-6">
              <Sparkles className="w-8 h-8 text-indigo-400 mx-auto mb-3" />
              <h3 className="text-sm font-semibold text-[#1C1917] mb-1">No events extracted yet</h3>
              <p className="text-xs text-[#6B6862] mb-4">
                Extract structured actions, modalities (completed vs planned), and actors grounded in verbatim source evidence.
              </p>
              <Button
                variant="primary"
                size="sm"
                onClick={handleExtractEvents}
                disabled={isExtractingEvents || caseEvidence.length === 0}
              >
                Extract Structured Events
              </Button>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-3">
              {filteredEvents.map((ev) => {
                const modalityStyles: Record<string, string> = {
                  completed: 'bg-emerald-50 text-emerald-800 border-emerald-200',
                  planned: 'bg-amber-50 text-amber-800 border-amber-200',
                  alleged: 'bg-purple-50 text-purple-800 border-purple-200',
                  denied: 'bg-rose-50 text-rose-800 border-rose-200'
                };
                const badgeStyle = modalityStyles[ev.modality] || 'bg-stone-50 text-stone-800 border-stone-200';

                return (
                  <div
                    key={ev.id}
                    className="bg-white border border-[#E6E4DF] rounded-md p-4 space-y-3 hover:border-stone-400 transition-colors"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#E6E4DF] pb-2.5">
                      <div className="flex items-center gap-2">
                        <span className={`text-[11px] font-semibold uppercase px-2 py-0.5 rounded border ${badgeStyle}`}>
                          {ev.modality}
                        </span>
                        <h4 className="text-sm font-semibold text-[#1C1917]">{ev.title}</h4>
                      </div>

                      <div className="flex items-center gap-2 text-xs text-[#6B6862]">
                        <span className="font-mono bg-stone-100 px-1.5 py-0.5 rounded text-[11px]">
                          {ev.event_type}
                        </span>
                        <span>•</span>
                        <span className="text-[11px]">{ev.explicit_or_inferred?.replace('_', ' ') || ''}</span>
                      </div>
                    </div>

                    <p className="text-xs text-[#1C1917] leading-relaxed">{ev.description}</p>

                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2 text-xs bg-[#F9F9F7] p-2.5 rounded border border-[#E6E4DF]">
                      <div>
                        <span className="text-[#6B6862] block text-[11px]">Action</span>
                        <span className="font-medium text-[#1C1917] capitalize">{ev.action}</span>
                      </div>

                      <div>
                        <span className="text-[#6B6862] block text-[11px]">Actors</span>
                        <div className="flex flex-wrap gap-1 mt-0.5">
                          {ev.actors.map((actor, idx) => (
                            <span key={idx} className="bg-white border border-[#E6E4DF] px-1.5 py-0.2 rounded font-mono text-[11px]">
                              {actor}
                            </span>
                          ))}
                        </div>
                      </div>

                      <div>
                        <span className="text-[#6B6862] block text-[11px]">Time Expression</span>
                        <span className="font-medium text-[#1C1917]">
                          {ev.original_time_expression || 'Unanchored / Relative'}
                        </span>
                        {ev.normalized_start_time && (
                          <span className="block font-mono text-[10px] text-[#6B6862]">
                            {new Date(ev.normalized_start_time).toLocaleString()}
                          </span>
                        )}
                      </div>

                      <div>
                        <span className="text-[#6B6862] block text-[11px]">Location</span>
                        <span className="font-medium text-[#1C1917]">{ev.location || 'Not specified'}</span>
                      </div>
                    </div>

                    {/* Grounded Text Spans */}
                    <div className="space-y-1">
                      <span className="text-[11px] font-medium text-[#6B6862] uppercase tracking-wide">
                        Grounded Source Spans ({ev.supporting_text_spans.length})
                      </span>
                      <div className="space-y-1">
                        {ev.supporting_text_spans.map((span, sIdx) => (
                          <div
                            key={sIdx}
                            className="bg-stone-50 border-l-2 border-[#0F766E] px-3 py-1.5 text-xs text-[#1C1917] font-mono leading-relaxed"
                          >
                            "{span}"
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Uncertainty flags */}
                    {ev.uncertainty_flags && ev.uncertainty_flags.length > 0 && (
                      <div className="flex items-center gap-1.5 text-amber-700 bg-amber-50 px-2 py-1 rounded text-[11px] border border-amber-200">
                        <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                        <span>Flags: {ev.uncertainty_flags.join(', ')}</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB 4: Chronological Timeline & Discrepancies */}
      {activeTab === 'timeline' && (
        <div className="space-y-6">
          {/* Summary Banner */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[#F9F9F7] p-4 rounded-md border border-[#E6E4DF]">
            <div className="flex flex-wrap items-center gap-4 text-xs">
              <div>
                <span className="text-[#6B6862] block">Total Events</span>
                <span className="text-base font-semibold text-[#1C1917]">
                  {timelineData ? timelineData.total_events_count : 0}
                </span>
              </div>
              <div className="border-l border-[#E6E4DF] pl-4">
                <span className="text-[#6B6862] block">Corroborated</span>
                <span className="text-base font-semibold text-emerald-700">
                  {timelineData ? timelineData.corroborated_count : 0}
                </span>
              </div>
              <div className="border-l border-[#E6E4DF] pl-4">
                <span className="text-[#6B6862] block">Conflicting Discrepancies</span>
                <span className="text-base font-semibold text-rose-700">
                  {contradictions.length}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={handleTriggerReconstruction}
                title="Re-run timeline reconciliation with latest witness clarifications"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Re-Reconstruct Timeline</span>
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setActiveTab('quiz')}
                className="text-[#0F766E] border-[#0F766E]/30"
              >
                <HelpCircle className="w-3.5 h-3.5" />
                <span>Open Clarification Quiz</span>
              </Button>
            </div>
          </div>

          {/* Cross-Evidence Contradictions & Discrepancies */}
          {contradictions.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-600" />
                <h3 className="text-sm font-semibold text-rose-900">
                  Detected Cross-Evidence Contradictions ({contradictions.length})
                </h3>
              </div>

              <div className="grid grid-cols-1 gap-3">
                {contradictions.map((c) => (
                  <div
                    key={c.id}
                    className="bg-rose-50/50 border border-rose-200 rounded-md p-4 space-y-3"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono font-semibold uppercase text-rose-800 bg-rose-100 px-2 py-0.5 rounded">
                        {c.contradiction_type?.replace(/_/g, ' ') || 'discrepancy'}
                      </span>
                      <span className="text-[11px] text-rose-700">{c.resolution_status}</span>
                    </div>

                    <p className="text-xs font-medium text-rose-950">{c.description}</p>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                      <div className="bg-white p-2.5 rounded border border-rose-200">
                        <span className="text-[11px] font-semibold text-stone-600 block mb-1">
                          Source A: {c.source_a}
                        </span>
                        <p className="text-[#1C1917] italic">"{c.statement_a}"</p>
                      </div>

                      <div className="bg-white p-2.5 rounded border border-rose-200">
                        <span className="text-[11px] font-semibold text-stone-600 block mb-1">
                          Source B: {c.source_b}
                        </span>
                        <p className="text-[#1C1917] italic">"{c.statement_b}"</p>
                      </div>
                    </div>

                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pt-1 border-t border-rose-200/60 text-xs">
                      <div className="flex items-center gap-1.5 text-rose-900 font-medium">
                        <HelpCircle className="w-3.5 h-3.5" />
                        <span>Unresolved Question: {c.unresolved_question}</span>
                      </div>
                      <button
                        onClick={() => setActiveTab('quiz')}
                        className="text-[11px] font-medium text-[#0F766E] hover:underline"
                      >
                        Clarify in Quiz &rarr;
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Chronological Scheduled Timeline */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-[#1C1917] flex items-center gap-2">
              <Clock className="w-4 h-4 text-[#0F766E]" />
              <span>Chronological Reconstruction ({timelineData?.scheduled_events.length || 0} Anchored Events)</span>
            </h3>

            {isLoadingTimeline ? (
              <div className="py-12 text-center text-xs text-[#6B6862]">Loading timeline reconstruction...</div>
            ) : (!timelineData || timelineData.scheduled_events.length === 0) ? (
              <div className="bg-white border border-[#E6E4DF] rounded-md p-8 text-center text-xs text-[#6B6862]">
                No anchored timeline events detected yet. Extract structured events first.
              </div>
            ) : (
              <div className="relative border-l-2 border-[#E6E4DF] ml-4 pl-6 space-y-6">
                {timelineData.scheduled_events.map((item, idx) => {
                  const isConflicting = item.timeline_status === 'conflicting_evidence';
                  const isCorroborated = item.timeline_status === 'corroborated';

                  return (
                    <div key={item.entry_id} className="relative group">
                      {/* Timeline Node Icon */}
                      <div
                        className={`absolute -left-[31px] top-1 w-4 h-4 rounded-full border-2 bg-white flex items-center justify-center ${
                          isConflicting
                            ? 'border-rose-600 bg-rose-50'
                            : isCorroborated
                            ? 'border-emerald-600 bg-emerald-50'
                            : 'border-[#0F766E]'
                        }`}
                      />

                      <div className="bg-white border border-[#E6E4DF] rounded-md p-4 space-y-2 hover:border-stone-400 transition-colors">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#E6E4DF] pb-2">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-xs font-semibold text-[#0F766E] bg-teal-50 px-2 py-0.5 rounded border border-teal-200">
                              {item.timestamp ? new Date(item.timestamp).toLocaleString() : item.original_time_expression}
                            </span>
                            <h4 className="text-sm font-semibold text-[#1C1917]">{item.title}</h4>
                          </div>

                          <div className="flex items-center gap-2">
                            <span
                              className={`text-[11px] font-medium px-2 py-0.5 rounded ${
                                isConflicting
                                  ? 'bg-rose-100 text-rose-800'
                                  : isCorroborated
                                  ? 'bg-emerald-100 text-emerald-800'
                                  : 'bg-stone-100 text-stone-700'
                              }`}
                            >
                              {item.timeline_status?.replace(/_/g, ' ') || 'event'}
                            </span>
                          </div>
                        </div>

                        <p className="text-xs text-[#1C1917]">{item.description}</p>

                        <div className="flex flex-wrap items-center gap-4 text-[11px] text-[#6B6862]">
                          <div>
                            <span className="font-medium text-[#1C1917]">Actors: </span>
                            <span>{item.actors.join(', ')}</span>
                          </div>
                          {item.location && (
                            <div>
                              <span className="font-medium text-[#1C1917]">Location: </span>
                              <span>{item.location}</span>
                            </div>
                          )}
                          <div>
                            <span className="font-medium text-[#1C1917]">Modality: </span>
                            <span className="capitalize">{item.modality}</span>
                          </div>
                        </div>

                        {item.supporting_text_spans.length > 0 && (
                          <div className="bg-stone-50 border-l border-stone-300 p-2 text-xs font-mono text-stone-800 italic">
                            "{item.supporting_text_spans[0]}"
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Unscheduled / Time Unknown Section */}
          {timelineData && timelineData.unscheduled_events.length > 0 && (
            <div className="space-y-3 pt-4 border-t border-[#E6E4DF]">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-[#1C1917] flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 text-amber-600" />
                    <span>Unscheduled / Ambiguous Time Events ({timelineData.unscheduled_events.length})</span>
                  </h3>
                  <p className="text-xs text-[#6B6862] mt-0.5">
                    Forensically preserved events without unambiguous date/time anchors. No timestamps fabricated.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {timelineData.unscheduled_events.map((u) => (
                  <div
                    key={u.entry_id}
                    className="bg-amber-50/40 border border-amber-200 rounded-md p-3.5 space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-mono text-amber-800 bg-amber-100 px-1.5 py-0.5 rounded">
                        {u.original_time_expression || 'No timestamp'}
                      </span>
                      <span className="text-[11px] text-[#6B6862] capitalize">{u.modality}</span>
                    </div>

                    <h4 className="text-xs font-semibold text-[#1C1917]">{u.title}</h4>
                    <p className="text-xs text-[#6B6862]">{u.description}</p>

                    <div className="flex items-center justify-between text-[11px] pt-1">
                      <span className="text-[#6B6862]">Actors: {u.actors.join(', ')}</span>
                      <button
                        onClick={() => setActiveTab('quiz')}
                        className="text-[#0F766E] font-medium hover:underline"
                      >
                        Clarify Time &rarr;
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 5: Clarification Quiz (Investigator Questionnaire) */}
      {activeTab === 'quiz' && (
        <div className="space-y-6">
          {/* Header & Controls */}
          <div className="bg-[#F9F9F7] p-4 rounded-md border border-[#E6E4DF] space-y-2">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-[#1C1917] flex items-center gap-2">
                  <HelpCircle className="w-4 h-4 text-[#0F766E]" />
                  <span>Case Clarification & Forensic Synthesis</span>
                </h3>
                <p className="text-xs text-[#6B6862]">
                  Review what the system has reconstructed so far, and clarify genuine unresolved uncertainties.
                  Responses carry ordinal witness weighting (0–4) and never overwrite documentary evidence.
                </p>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handleGenerateQuiz}
                  disabled={isGeneratingQuiz || caseEvidence.length === 0}
                  className="text-[#0F766E] border-[#0F766E]/30"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isGeneratingQuiz ? 'animate-spin' : ''}`} />
                  <span>{isGeneratingQuiz ? 'Analyzing...' : 'Refresh Understanding & Quiz'}</span>
                </Button>
              </div>
            </div>
          </div>

          {/* SECTION 1: WHAT WE UNDERSTAND SO FAR */}
          {caseUnderstanding && (
            <div className="bg-white border border-[#E6E4DF] rounded-lg p-5 space-y-5 shadow-xs">
              <div className="flex items-center justify-between border-b border-[#E6E4DF] pb-3">
                <div className="flex items-center gap-2">
                  <span className="p-1.5 bg-teal-50 text-[#0F766E] rounded-md">
                    <Sparkles className="w-4 h-4" />
                  </span>
                  <div>
                    <h4 className="text-sm font-semibold text-[#1C1917]">What We Understand So Far</h4>
                    <p className="text-[11px] text-[#6B6862]">Preliminary synthesis of verified documents, communications, and open questions</p>
                  </div>
                </div>
                <span className="text-[11px] font-mono text-[#0F766E] bg-teal-50 px-2.5 py-1 rounded-full font-medium">
                  {caseUnderstanding.evidence_sources.length} Sources Analyzed
                </span>
              </div>

              {/* Plain-language narrative summary */}
              <div className="bg-stone-50 border-l-3 border-[#0F766E] p-3.5 rounded-r text-xs text-[#1C1917] leading-relaxed">
                <span className="font-semibold text-[#0F766E] block text-[11px] uppercase tracking-wider mb-1">
                  Incident Overview:
                </span>
                {caseUnderstanding.narrative_summary}
              </div>

              {/* 4 Structured Information Categories */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* 1. Key Parties */}
                <div className="bg-[#FAF9F5] border border-[#E6E4DF] rounded-md p-3.5 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-[#1C1917] flex items-center gap-1.5">
                      <Users className="w-3.5 h-3.5 text-[#0F766E]" />
                      Key Parties Identified
                    </span>
                    <span className="text-[10px] text-[#6B6862] font-mono">{caseUnderstanding.key_parties.length} found</span>
                  </div>
                  {caseUnderstanding.key_parties.length === 0 ? (
                    <p className="text-[11px] text-[#6B6862]">No distinct parties recognized yet.</p>
                  ) : (
                    <div className="flex flex-wrap gap-1.5">
                      {caseUnderstanding.key_parties.map((party, idx) => (
                        <div
                          key={idx}
                          className="bg-white border border-[#E6E4DF] px-2 py-1 rounded text-xs text-[#1C1917] flex items-center gap-1.5 shadow-2xs"
                        >
                          <span className="font-medium">{party.name}</span>
                          <span className="text-[9px] bg-stone-100 text-[#6B6862] px-1 rounded font-mono uppercase">
                            {party.entity_type}
                          </span>
                          <span className="text-[10px] text-[#0F766E] font-semibold font-mono">
                            {party.mentions}x
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* 2. Established Facts */}
                <div className="bg-[#FAF9F5] border border-[#E6E4DF] rounded-md p-3.5 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-[#1C1917] flex items-center gap-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                      Documented & Established Facts
                    </span>
                    <span className="text-[10px] text-[#6B6862] font-mono">{caseUnderstanding.established_facts.length} items</span>
                  </div>
                  {caseUnderstanding.established_facts.length === 0 ? (
                    <p className="text-[11px] text-[#6B6862]">No documented facts extracted yet.</p>
                  ) : (
                    <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
                      {caseUnderstanding.established_facts.slice(0, 5).map((fact, idx) => (
                        <div key={idx} className="bg-white border border-[#E6E4DF] p-2 rounded text-xs text-[#1C1917] space-y-1 shadow-2xs">
                          <div className="flex items-center justify-between gap-1">
                            <span className="font-medium text-[11px] line-clamp-1">{fact.fact_statement}</span>
                            {fact.timestamp && (
                              <span className="font-mono text-[10px] text-[#0F766E] bg-teal-50 px-1.5 py-0.5 rounded shrink-0">
                                {fact.timestamp}
                              </span>
                            )}
                          </div>
                          <span className="text-[10px] text-[#6B6862] block font-mono">
                            Source: {fact.evidence_title || 'Document'}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* 3. Proposed / Unconfirmed Events */}
                <div className="bg-[#FAF9F5] border border-[#E6E4DF] rounded-md p-3.5 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-[#1C1917] flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5 text-amber-600" />
                      Proposed / Unconfirmed Events
                    </span>
                    <span className="text-[10px] text-amber-700 bg-amber-100 px-1.5 py-0.2 rounded font-mono font-medium">
                      Requires Confirmation
                    </span>
                  </div>
                  {caseUnderstanding.proposed_or_planned.length === 0 ? (
                    <p className="text-[11px] text-[#6B6862]">No unconfirmed proposals found.</p>
                  ) : (
                    <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
                      {caseUnderstanding.proposed_or_planned.slice(0, 5).map((prop, idx) => (
                        <div key={idx} className="bg-white border border-amber-200/70 p-2 rounded text-xs text-[#1C1917] space-y-1 shadow-2xs">
                          <div className="flex items-center justify-between gap-1">
                            <span className="font-medium text-[11px] line-clamp-1">{prop.activity}</span>
                            {prop.proposed_time && (
                              <span className="font-mono text-[10px] text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded shrink-0">
                                {prop.proposed_time}
                              </span>
                            )}
                          </div>
                          <span className="text-[10px] text-[#6B6862] block">
                            Proposed in: {prop.evidence_title} (execution unconfirmed)
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* 4. Unclear or Disputed Matters */}
                <div className="bg-[#FAF9F5] border border-[#E6E4DF] rounded-md p-3.5 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-[#1C1917] flex items-center gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
                      Unclear or Disputed Matters
                    </span>
                    <span className="text-[10px] text-[#6B6862] font-mono">{caseUnderstanding.unclear_or_disputed.length} items</span>
                  </div>
                  {caseUnderstanding.unclear_or_disputed.length === 0 ? (
                    <p className="text-[11px] text-emerald-700 font-medium">No material contradictions detected across evidence files.</p>
                  ) : (
                    <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
                      {caseUnderstanding.unclear_or_disputed.slice(0, 4).map((disp, idx) => (
                        <div key={idx} className="bg-white border border-rose-200/70 p-2 rounded text-xs text-[#1C1917] space-y-1 shadow-2xs">
                          <span className="font-medium text-[11px] text-rose-800 line-clamp-1">
                            {disp.issue}
                          </span>
                          <span className="text-[10px] text-[#6B6862] block font-mono">
                            Type: {disp.contradiction_type?.replace(/_/g, ' ') || 'discrepancy'}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* SECTION 2: CLARIFICATION QUESTIONS */}
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#E6E4DF] pb-2">
              <div>
                <h4 className="text-sm font-semibold text-[#1C1917]">Clarification Questions</h4>
                <p className="text-xs text-[#6B6862]">
                  We found a few things that are still unclear. Your answers may help clarify them.
                </p>
              </div>

              {quizQuestions.length > 0 && (
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-[#0F766E] bg-teal-50 px-2.5 py-1 rounded font-medium">
                    {answeredQuestionIds.size} of {quizQuestions.length} Answered
                  </span>
                </div>
              )}
            </div>

            {isLoadingQuiz ? (
              <div className="py-12 text-center text-xs text-[#6B6862]">Loading clarification questions...</div>
            ) : quizQuestions.length === 0 ? (
              <div className="bg-white border border-[#E6E4DF] rounded-md p-10 text-center max-w-md mx-auto my-4 shadow-xs">
                <HelpCircle className="w-8 h-8 text-[#0F766E]/50 mx-auto mb-3" />
                <h3 className="text-sm font-semibold text-[#1C1917] mb-1">No clarification questions needed</h3>
                <p className="text-xs text-[#6B6862] mb-4">
                  The evidence currently contains no unresolved contradictions or unconfirmed critical actions.
                </p>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleGenerateQuiz}
                  disabled={isGeneratingQuiz}
                >
                  Analyze & Generate Quiz
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                {/* Step / Question Pills Navigation */}
                <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
                  {quizQuestions.map((q, qIdx) => {
                    const isAns = answeredQuestionIds.has(q.id) || q.status === 'answered';
                    const isCurr = qIdx === activeQuestionIndex;
                    return (
                      <button
                        key={q.id}
                        type="button"
                        onClick={() => setActiveQuestionIndex(qIdx)}
                        className={`px-3 py-1.5 rounded text-xs font-medium flex items-center gap-1.5 transition-all shrink-0 ${
                          isCurr
                            ? 'bg-[#0F766E] text-white shadow-xs'
                            : isAns
                            ? 'bg-emerald-100 text-emerald-800 hover:bg-emerald-200'
                            : 'bg-white border border-[#E6E4DF] text-[#6B6862] hover:text-[#1C1917] hover:border-stone-400'
                        }`}
                      >
                        {isAns && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />}
                        <span>Question {qIdx + 1}</span>
                      </button>
                    );
                  })}
                </div>

                {/* Active Question Card */}
                {(() => {
                  const q = quizQuestions[activeQuestionIndex] || quizQuestions[0];
                  if (!q) return null;
                  const isAnswered = answeredQuestionIds.has(q.id) || q.status === 'answered';
                  const currentForm = quizFormState[q.id] || {
                    selected_option: '',
                    free_text: '',
                    user_surety: 'Fairly sure',
                    knowledge_basis: 'Not specified'
                  };
                  const isSubmitting = submittingQuestionId === q.id;

                  return (
                    <div
                      key={q.id}
                      className={`bg-white border rounded-lg p-6 space-y-5 transition-all shadow-xs ${
                        isAnswered ? 'border-emerald-300 bg-emerald-50/10' : 'border-[#E6E4DF]'
                      }`}
                    >
                      {/* Top Badges & Title */}
                      <div className="space-y-2">
                        <div className="flex items-center justify-between gap-3">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-xs font-semibold text-[#0F766E] bg-teal-50 px-2.5 py-0.5 rounded">
                              Question {activeQuestionIndex + 1} of {quizQuestions.length}
                            </span>
                            {q.activity_name ? (
                              <span className="text-xs font-semibold text-stone-700 bg-stone-100 px-2 py-0.5 rounded">
                                {q.activity_name}
                              </span>
                            ) : (
                              <span className="text-[11px] font-mono text-[#0F766E] uppercase bg-stone-100 px-2 py-0.5 rounded">
                                {q.question_type?.replace(/_/g, ' ') || 'clarification'}
                              </span>
                            )}
                          </div>

                          {isAnswered ? (
                            <span className="inline-flex items-center gap-1 text-xs text-emerald-700 bg-emerald-100 px-2.5 py-1 rounded font-medium shrink-0">
                              <CheckCircle2 className="w-3.5 h-3.5" />
                              <span>Clarified</span>
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-xs text-amber-700 bg-amber-100 px-2.5 py-1 rounded font-medium shrink-0">
                              <AlertCircle className="w-3.5 h-3.5" />
                              <span>Needs Clarification</span>
                            </span>
                          )}
                        </div>

                        <h3 className="text-base font-semibold text-[#1C1917] leading-snug">
                          {q.prompt}
                        </h3>

                        {q.why_it_matters && (
                          <div className="text-xs text-[#0F766E] bg-teal-50/60 border border-teal-100 p-2.5 rounded-md flex items-start gap-2">
                            <Sparkles className="w-4 h-4 shrink-0 mt-0.5" />
                            <span><strong>Why this matters:</strong> {q.why_it_matters}</span>
                          </div>
                        )}
                      </div>

                      {/* Evidence Context */}
                      <div className="bg-stone-50 border-l-3 border-stone-400 p-3 rounded-r text-xs text-[#1C1917] font-mono leading-relaxed">
                        <span className="text-[10px] text-[#6B6862] uppercase block font-sans font-semibold mb-1">
                          Source Quotation / Document Excerpt:
                        </span>
                        "{q.context_excerpt}"
                      </div>

                      {/* Options selection */}
                      <div className="space-y-2">
                        <span className="text-xs font-semibold text-[#1C1917] block">Select the most accurate account:</span>
                        <div className="grid grid-cols-1 gap-2">
                          {q.options.map((opt, optIdx) => (
                            <label
                              key={optIdx}
                              className={`flex items-center gap-3 p-3 rounded-md border text-xs cursor-pointer transition-all ${
                                currentForm.selected_option === opt
                                  ? 'bg-teal-50/70 border-[#0F766E] text-[#0F766E] font-medium shadow-xs'
                                  : 'bg-white border-[#E6E4DF] text-[#1C1917] hover:bg-[#F9F9F7] hover:border-stone-300'
                              }`}
                            >
                              <input
                                type="radio"
                                name={`question_${q.id}`}
                                value={opt}
                                checked={currentForm.selected_option === opt}
                                onChange={() => handleSelectOption(q.id, opt)}
                                className="text-[#0F766E] focus:ring-[#0F766E] h-4 w-4"
                              />
                              <span className="leading-snug">{opt}</span>
                            </label>
                          ))}
                        </div>
                      </div>

                      {/* Optional Notes */}
                      <div className="space-y-1.5">
                        <label className="text-xs font-medium text-[#1C1917] block">
                          Additional Context / Observations (Optional):
                        </label>
                        <input
                          type="text"
                          value={currentForm.free_text || ''}
                          onChange={(e) => handleSetFreeText(q.id, e.target.value)}
                          placeholder="State any relevant details or reasons..."
                          className="w-full text-xs p-2.5 rounded-md border border-[#E6E4DF] focus:border-[#0F766E] focus:ring-1 focus:ring-[#0F766E] focus:outline-none"
                        />
                      </div>

                      {/* Surety & Knowledge Basis Controls */}
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-3 border-t border-[#E6E4DF] text-xs">
                        <div>
                          <span className="font-medium text-[#1C1917] block mb-1.5">
                            Surety Level (Witness Certainty):
                          </span>
                          <div className="flex flex-wrap gap-1.5">
                            {[
                              { label: 'Very sure', score: 4 },
                              { label: 'Fairly sure', score: 3 },
                              { label: 'Somewhat sure', score: 2 },
                              { label: 'Unsure', score: 1 },
                              { label: 'Do not remember', score: 0 }
                            ].map((item) => (
                              <button
                                key={item.label}
                                type="button"
                                onClick={() => handleSetSurety(q.id, item.label)}
                                className={`px-2.5 py-1 rounded text-[11px] border transition-colors ${
                                  currentForm.user_surety === item.label
                                    ? 'bg-[#0F766E] text-white border-[#0F766E] font-medium'
                                    : 'bg-white border-[#E6E4DF] text-[#6B6862] hover:text-[#1C1917]'
                                }`}
                              >
                                {item.label} ({item.score})
                              </button>
                            ))}
                          </div>
                        </div>

                        <div>
                          <span className="font-medium text-[#1C1917] block mb-1.5">Knowledge Basis:</span>
                          <select
                            value={currentForm.knowledge_basis || 'Not specified'}
                            onChange={(e) => handleSetKnowledgeBasis(q.id, e.target.value)}
                            className="w-full text-xs p-2 rounded-md border border-[#E6E4DF] bg-white text-[#1C1917] focus:outline-none focus:border-[#0F766E]"
                          >
                            <option value="Not specified">Not specified (General recollection)</option>
                            <option value="Directly witnessed">Directly witnessed</option>
                            <option value="Personally participated">Personally participated</option>
                            <option value="Heard from another person">Heard from another person</option>
                            <option value="Inferred">Inferred from circumstances</option>
                            <option value="Document review only">Document review only</option>
                          </select>
                        </div>
                      </div>

                      {/* Navigation & Submit Footer */}
                      <div className="flex items-center justify-between pt-4 border-t border-[#E6E4DF]">
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => setActiveQuestionIndex((prev) => Math.max(0, prev - 1))}
                          disabled={activeQuestionIndex === 0}
                        >
                          <ChevronLeft className="w-3.5 h-3.5 mr-1" />
                          <span>Previous</span>
                        </Button>

                        <div className="flex items-center gap-2">
                          {activeQuestionIndex < quizQuestions.length - 1 && (
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => setActiveQuestionIndex((prev) => prev + 1)}
                            >
                              <span>Skip</span>
                              <ChevronRight className="w-3.5 h-3.5 ml-1" />
                            </Button>
                          )}

                          <Button
                            variant="primary"
                            size="sm"
                            onClick={() => handleSubmitQuizAnswer(q.id)}
                            disabled={isSubmitting || !currentForm.selected_option}
                          >
                            {isSubmitting ? 'Recording...' : isAnswered ? 'Update Answer' : 'Submit & Next'}
                          </Button>
                        </div>
                      </div>
                    </div>
                  );
                })()}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 6: Forensic Incident Reconstruction Report */}
      {activeTab === 'report' && (
        <div className="space-y-6">
          {/* Header & Controls */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[#F9F9F7] p-4 rounded-md border border-[#E6E4DF]">
            <div>
              <h3 className="text-sm font-semibold text-[#1C1917] flex items-center gap-2">
                <FileCheck className="w-4 h-4 text-[#0F766E]" />
                <span>Forensic Incident Reconstruction Report</span>
              </h3>
              <p className="text-xs text-[#6B6862]">
                Synthesizes evidence inventory, SHA-256 chain of custody, timeline, and witness clarifications.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={handleGenerateReport}
                disabled={isGeneratingReport || caseEvidence.length === 0}
              >
                <FileCheck className={`w-3.5 h-3.5 ${isGeneratingReport ? 'animate-spin' : ''}`} />
                <span>{isGeneratingReport ? 'Synthesizing...' : 'Generate / Rebuild Report'}</span>
              </Button>

              {reportData && id && (
                <a
                  href={api.getReportHtmlUrl(id)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#0F766E] text-white text-xs font-medium rounded hover:bg-[#0D655E] transition-colors"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  <span>Print / Open Full Report</span>
                </a>
              )}
            </div>
          </div>

          {/* AI Forensic Disclaimer */}
          <div className="bg-amber-50 border border-amber-200 p-3.5 rounded text-xs text-amber-900 flex items-start gap-2.5">
            <AlertTriangle className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold block mb-0.5">AI-ASSISTED FORENSIC RECONSTRUCTION DISCLAIMER</span>
              <p className="leading-relaxed text-[11px] text-amber-800">
                This document synthesizes findings generated by multi-modal machine learning models (PaddleOCR, Faster-Whisper, GLiNER, Qwen 2.5).
                Grounded textual assertions are cited directly from uploaded files. All investigative deductions are probabilistic and require human validation.
              </p>
            </div>
          </div>

          {isLoadingReport ? (
            <div className="py-12 text-center text-xs text-[#6B6862]">Synthesizing forensic report...</div>
          ) : !reportData ? (
            <div className="bg-white border border-[#E6E4DF] rounded-md p-10 text-center max-w-md mx-auto my-6">
              <FileCheck className="w-8 h-8 text-[#0F766E]/50 mx-auto mb-3" />
              <h3 className="text-sm font-semibold text-[#1C1917] mb-1">No report generated yet</h3>
              <p className="text-xs text-[#6B6862] mb-4">
                Click below to synthesize a comprehensive incident report based on extracted evidence, timeline, and clarifications.
              </p>
              <Button
                variant="primary"
                size="sm"
                onClick={handleGenerateReport}
                disabled={isGeneratingReport || caseEvidence.length === 0}
              >
                Generate Forensic Report
              </Button>
            </div>
          ) : (
            <div className="bg-white border border-[#E6E4DF] rounded-md p-6 space-y-6">
              {/* Executive Overview */}
              <div className="border-b border-[#E6E4DF] pb-4">
                <div className="flex items-center justify-between">
                  <h4 className="text-base font-semibold text-[#1C1917]">Executive Incident Overview</h4>
                  <span className="text-xs text-[#6B6862]">
                    Report ID: <span className="font-mono">{reportData.id.substring(0, 8)}...</span>
                  </span>
                </div>
                <p className="text-xs text-[#6B6862] mt-1">
                  Synthesized on {new Date(reportData.created_at).toLocaleString()}
                </p>
              </div>

              {/* Statistics Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="bg-[#F9F9F7] p-3 rounded border border-[#E6E4DF] text-xs">
                  <span className="text-[#6B6862] block">Total Evidence Items</span>
                  <span className="text-lg font-semibold text-[#1C1917]">
                    {reportData.report_data?.evidence_inventory?.length ?? caseEvidence.length}
                  </span>
                </div>

                <div className="bg-[#F9F9F7] p-3 rounded border border-[#E6E4DF] text-xs">
                  <span className="text-[#6B6862] block">Timeline Events</span>
                  <span className="text-lg font-semibold text-emerald-700">
                    {(reportData.report_data?.chronological_timeline?.length ?? 0) + (reportData.report_data?.unscheduled_events?.length ?? 0)}
                  </span>
                </div>

                <div className="bg-[#F9F9F7] p-3 rounded border border-[#E6E4DF] text-xs">
                  <span className="text-[#6B6862] block">Detected Conflicts</span>
                  <span className="text-lg font-semibold text-rose-700">
                    {reportData.report_data?.contradictions_and_discrepancies?.length ?? contradictions.length}
                  </span>
                </div>

                <div className="bg-[#F9F9F7] p-3 rounded border border-[#E6E4DF] text-xs">
                  <span className="text-[#6B6862] block">Witness Clarifications</span>
                  <span className="text-lg font-semibold text-indigo-700">
                    {reportData.report_data?.user_clarifications?.length ?? answeredQuestionIds.size}
                  </span>
                </div>
              </div>

              {/* Refined by Clarifications Banner */}
              {reportData.report_data?.updated_with_clarifications && (
                <div className="bg-blue-50 border border-blue-200 p-3 rounded-md text-xs text-blue-900 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-blue-600 shrink-0" />
                  <span>
                    <strong>Refined by Witness Testimony:</strong> This report has been dynamically updated with your clarification answers.
                  </span>
                </div>
              )}

              {/* SECTION A: What Appears to Have Happened */}
              <div className="space-y-3">
                <div className="flex items-center gap-2 border-b border-[#E6E4DF] pb-2">
                  <span className="w-6 h-6 rounded-full bg-teal-100 text-[#0F766E] font-bold text-xs flex items-center justify-center">A</span>
                  <h5 className="text-sm font-semibold text-[#1C1917]">
                    What Appears to Have Happened?
                  </h5>
                </div>
                <div className="bg-white border border-[#E6E4DF] p-4 rounded-md text-xs text-[#1C1917] leading-relaxed whitespace-pre-wrap">
                  {reportData.report_data?.what_happened || reportData.report_data?.incident_narrative || reportData.report_data?.case_overview}
                </div>

                {/* Subsections if available */}
                {reportData.report_data?.dispute_development_sections?.length > 0 && (
                  <div className="space-y-2 mt-2">
                    {reportData.report_data.dispute_development_sections.map((sec: any, sIdx: number) => (
                      <div key={sIdx} className="bg-[#F9F9F7] p-3 rounded border border-[#E6E4DF] text-xs">
                        <span className="font-semibold text-[#1C1917] block mb-1">{sec.heading}</span>
                        <p className="text-[#334155] leading-relaxed whitespace-pre-wrap">{sec.content}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Key Financial Findings if available */}
              {reportData.report_data?.financial_document_findings && Object.keys(reportData.report_data.financial_document_findings).length > 0 && (
                <div className="space-y-2">
                  <h5 className="text-xs font-semibold uppercase tracking-wider text-[#6B6862]">
                    Key Financial Findings & Document Verification
                  </h5>
                  <div className="bg-[#F9F9F7] p-3.5 rounded border border-[#E6E4DF] text-xs">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {Object.entries(reportData.report_data.financial_document_findings).map(([k, v]: [string, any], fIdx: number) => {
                        if (k.endsWith('_status') || k.endsWith('_note')) return null;
                        return (
                          <div key={fIdx} className="flex justify-between border-b border-stone-200 py-1">
                            <span className="text-[#6B6862] capitalize">{k?.replace(/_/g, ' ') || ''}:</span>
                            <span className="font-mono font-medium text-[#1C1917]">{String(v)}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              )}

              {/* SECTION B: What Remains Unclear */}
              <div className="space-y-2">
                <div className="flex items-center gap-2 border-b border-[#E6E4DF] pb-2">
                  <span className="w-6 h-6 rounded-full bg-amber-100 text-amber-800 font-bold text-xs flex items-center justify-center">B</span>
                  <h5 className="text-sm font-semibold text-[#1C1917]">
                    What Remains Unclear?
                  </h5>
                </div>
                <div className="bg-amber-50/60 border border-amber-200/80 p-4 rounded-md">
                  <p className="text-xs text-amber-900 font-medium mb-2">
                    Key unresolved facts that cannot be determined conclusively from available documentary evidence alone:
                  </p>
                  <ol className="list-decimal list-inside space-y-1.5 text-xs text-amber-950">
                    {(reportData.report_data?.what_remains_unclear || []).map((item: string, idx: number) => (
                      <li key={idx} className="leading-relaxed">{item}</li>
                    ))}
                  </ol>
                </div>
              </div>

              {/* SECTION C: What Additional Information Would Help */}
              <div className="space-y-2">
                <div className="flex items-center gap-2 border-b border-[#E6E4DF] pb-2">
                  <span className="w-6 h-6 rounded-full bg-emerald-100 text-emerald-800 font-bold text-xs flex items-center justify-center">C</span>
                  <h5 className="text-sm font-semibold text-[#1C1917]">
                    What Additional Information Would Help?
                  </h5>
                </div>
                <div className="bg-emerald-50/60 border border-emerald-200/80 p-4 rounded-md">
                  <p className="text-xs text-emerald-900 font-medium mb-2">
                    Clarifying these points through investigator testimony or secondary records will narrow remaining uncertainties:
                  </p>
                  <ul className="list-disc list-inside space-y-1.5 text-xs text-emerald-950">
                    {(reportData.report_data?.what_would_help || []).map((item: string, idx: number) => (
                      <li key={idx} className="leading-relaxed">{item}</li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Witness Clarifications if provided */}
              {reportData.report_data?.user_clarifications?.length > 0 && (
                <div className="space-y-2">
                  <h5 className="text-xs font-semibold uppercase tracking-wider text-[#6B6862]">
                    Witness Clarifications & Testimonial Inputs ({reportData.report_data.user_clarifications.length})
                  </h5>
                  <div className="space-y-2">
                    {reportData.report_data.user_clarifications.map((c: any, cIdx: number) => (
                      <div key={cIdx} className="bg-teal-50/50 border border-teal-200/80 p-3 rounded text-xs space-y-1">
                        <span className="font-semibold text-teal-900 block">{c.question}</span>
                        <div className="text-[#1C1917]">
                          <strong>Answer:</strong> {c.selected_option}
                          {c.free_text && <span className="italic ml-1">("{c.free_text}")</span>}
                        </div>
                        <div className="text-[11px] text-[#6B6862]">
                          Surety: <strong>{c.user_surety}</strong> ({c.surety_score}/4) • Knowledge Basis: <strong>{c.knowledge_basis}</strong>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Collapsible Technical Appendix */}
              <div className="pt-4 border-t border-[#E6E4DF]">
                <details className="group">
                  <summary className="cursor-pointer text-xs font-semibold text-[#0F766E] hover:underline flex items-center justify-between p-3 bg-[#F9F9F7] rounded border border-[#E6E4DF] select-none">
                    <span>Technical Appendix & Forensic Audit Details (Cryptographic Hashes, Timeline, Citations)</span>
                    <span className="text-[11px] text-[#6B6862] group-open:rotate-180 transition-transform">▼</span>
                  </summary>

                  <div className="p-4 bg-white border border-[#E6E4DF] border-t-0 rounded-b space-y-5">
                    {/* Evidence Inventory Table */}
                    <div className="space-y-2">
                      <h6 className="text-xs font-semibold uppercase tracking-wider text-[#6B6862]">
                        1. Cryptographic Evidence Inventory (SHA-256)
                      </h6>
                      <div className="border border-[#E6E4DF] rounded overflow-hidden">
                        <table className="w-full text-left text-xs border-collapse">
                          <thead>
                            <tr className="bg-[#F9F9F7] border-b border-[#E6E4DF] text-[#6B6862]">
                              <th className="py-2 px-3 font-medium">Filename</th>
                              <th className="py-2 px-3 font-medium">Type</th>
                              <th className="py-2 px-3 font-medium">SHA-256 Hash</th>
                              <th className="py-2 px-3 font-medium">Method</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-[#E6E4DF]">
                            {(reportData.report_data?.evidence_inventory || caseEvidence).map((e: any, idx: number) => (
                              <tr key={idx} className="hover:bg-[#F9F9F7]">
                                <td className="py-2 px-3 font-medium text-[#1C1917]">{e.original_filename || e.filename}</td>
                                <td className="py-2 px-3 uppercase text-[11px] text-[#6B6862]">{e.file_type}</td>
                                <td className="py-2 px-3 font-mono text-[11px] text-stone-700">{e.sha256}</td>
                                <td className="py-2 px-3 text-[11px] text-[#6B6862]">
                                  {e.extraction_method || (e.file_type === 'image' ? 'PaddleOCR' : e.file_type === 'audio' ? 'Faster-Whisper' : 'Doc Parser')}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>

                    {/* Timeline Events Table */}
                    {reportData.report_data?.chronological_timeline?.length > 0 && (
                      <div className="space-y-2">
                        <h6 className="text-xs font-semibold uppercase tracking-wider text-[#6B6862]">
                          2. Reconstructed Timeline Events ({reportData.report_data.chronological_timeline.length})
                        </h6>
                        <div className="border border-[#E6E4DF] rounded overflow-hidden max-h-72 overflow-y-auto">
                          <table className="w-full text-left text-xs border-collapse">
                            <thead>
                              <tr className="bg-[#F9F9F7] border-b border-[#E6E4DF] text-[#6B6862]">
                                <th className="py-2 px-3 font-medium w-36">Timestamp</th>
                                <th className="py-2 px-3 font-medium">Event & Supporting Provenance</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-[#E6E4DF]">
                              {reportData.report_data.chronological_timeline.map((ev: any, idx: number) => (
                                <tr key={idx} className="hover:bg-[#F9F9F7]">
                                  <td className="py-2 px-3 font-semibold text-[#0F766E] text-[11px] align-top">{ev.timestamp || 'Unscheduled'}</td>
                                  <td className="py-2 px-3">
                                    <span className="font-semibold text-[#1C1917] block">{ev.title}</span>
                                    <span className="text-[#334155] block">{ev.description}</span>
                                    <span className="text-[10px] text-[#6B6862]">Modality: {ev.modality} • Status: {ev.status}</span>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}
                  </div>
                </details>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Extracted Intelligence Inspection Modal */}
      {viewingEvidence && (
        <Modal
          isOpen={true}
          onClose={() => setViewingEvidence(null)}
          title={`Extracted Intelligence — ${viewingEvidence.original_filename}`}
        >
          <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-1">
            {/* Metadata Badges */}
            <div className="flex flex-wrap items-center gap-2 p-2.5 bg-[#F9F9F7] rounded border border-[#E6E4DF] text-xs">
              <span className="font-medium text-[#1C1917]">Confidence:</span>
              <span className="px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 font-semibold font-mono text-[11px]">
                {((viewingEvidence.extraction_confidence ?? 1.0) * 100).toFixed(1)}%
              </span>

              {viewingEvidence.processing_time_ms && (
                <>
                  <span className="text-[#9C9890]">•</span>
                  <span className="font-medium text-[#1C1917]">Processing Time:</span>
                  <span className="font-mono text-stone-700">
                    {Math.round(viewingEvidence.processing_time_ms)} ms
                  </span>
                </>
              )}

              <span className="text-[#9C9890]">•</span>
              <span className="font-medium text-[#1C1917]">Type:</span>
              <span className="uppercase font-mono text-stone-700">{viewingEvidence.file_type}</span>

              <div className="ml-auto">
                <a
                  href={api.getFileUrl(viewingEvidence.id)}
                  download={viewingEvidence.original_filename}
                  className="inline-flex items-center gap-1 text-[11px] text-[#0F766E] hover:underline"
                >
                  <Download className="w-3 h-3" />
                  <span>Download original</span>
                </a>
              </div>
            </div>

            {/* Extracted Text Content */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs text-[#6B6862]">
                <span className="font-medium text-[#1C1917]">Full Extracted Text:</span>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(viewingEvidence.extracted_text || '');
                    showNotification('Copied extracted text to clipboard');
                  }}
                  className="inline-flex items-center gap-1 hover:text-[#1C1917]"
                >
                  <Copy className="w-3 h-3" />
                  <span>Copy text</span>
                </button>
              </div>

              <div className="bg-stone-50 border border-[#E6E4DF] rounded p-3 font-mono text-xs whitespace-pre-wrap text-[#1C1917] max-h-80 overflow-y-auto leading-relaxed">
                {viewingEvidence.extracted_text || 'No text extracted from this file.'}
              </div>
            </div>

            {/* Re-run button */}
            <div className="flex justify-end gap-2 pt-2 border-t border-[#E6E4DF]">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => handleExtractSingle(viewingEvidence)}
                disabled={extractingIds.has(viewingEvidence.id)}
              >
                <RefreshCw className={`w-3.5 h-3.5 ${extractingIds.has(viewingEvidence.id) ? 'animate-spin' : ''}`} />
                <span>Re-run Extraction</span>
              </Button>
              <Button variant="primary" size="sm" onClick={() => setViewingEvidence(null)}>
                Close
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Delete Evidence Confirmation */}
      <ConfirmDialog
        isOpen={deleteEvidenceTarget !== null}
        onClose={() => setDeleteEvidenceTarget(null)}
        onConfirm={handleConfirmDeleteEvidence}
        title="Delete evidence file?"
        message={`This will delete "${deleteEvidenceTarget?.original_filename}" from this case.`}
      />

      {/* Delete Case Confirmation */}
      <ConfirmDialog
        isOpen={isDeleteCaseOpen}
        onClose={() => setIsDeleteCaseOpen(false)}
        onConfirm={handleConfirmDeleteCase}
        title="Delete this case?"
        message="This will delete this case and all evidence files associated with it."
      />
    </div>
  );
};
