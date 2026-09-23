import React, { useEffect, useState } from 'react';
import { applicationsApi, bugsApi, BACKEND_URL } from '../services/api';
import { Application, Bug, BugSummary } from '../types';
import {
  Bug as BugIcon,
  ShieldAlert,
  AlertCircle,
  CheckCircle2,
  Clock,
  Filter,
  ExternalLink,
  Download,
  Terminal,
  Layers,
  Activity,
  Maximize2,
  Check,
  RotateCw,
  Sparkles,
  Plus,
  RefreshCw
} from 'lucide-react';

interface BugsDashboardProps {
  initialAppId?: number;
  onSelectApp?: (id: number) => void;
  onNavigate: (tab: string, contextId?: number) => void;
}

export const BugsDashboard: React.FC<BugsDashboardProps> = ({ initialAppId, onSelectApp, onNavigate }) => {
  const [apps, setApps] = useState<Application[]>([]);
  const [selectedAppId, setSelectedAppId] = useState<number | ''>(initialAppId || '');
  const [bugs, setBugs] = useState<Bug[]>([]);
  const [summary, setSummary] = useState<BugSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Standalone Bug Logging & Defect Scan State
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [creatingBug, setCreatingBug] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [newBugData, setNewBugData] = useState({
    title: '',
    category: 'FUNCTIONAL',
    severity: 'HIGH',
    priority: 'HIGH',
    affected_page: 'http://127.0.0.1:3000',
    expected_behavior: '',
    actual_behavior: '',
    description: ''
  });

  // Filters
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [selectedSeverity, setSelectedSeverity] = useState<string>('all');

  // Selected Bug Modal
  const [inspectedBug, setInspectedBug] = useState<Bug | null>(null);
  const [updatingStatus, setUpdatingStatus] = useState(false);

  useEffect(() => {
    if (initialAppId) {
      setSelectedAppId(initialAppId);
    }
  }, [initialAppId]);

  useEffect(() => {
    const loadApps = async () => {
      try {
        const data = await applicationsApi.getAll();
        setApps(data);
        if (data.length > 0) {
          if (!selectedAppId || !data.some(a => a.id === selectedAppId)) {
            const pref = data.find(a => a.id === 2) || data[0];
            setSelectedAppId(pref.id);
            onSelectApp?.(pref.id);
          }
        } else {
          setSelectedAppId('');
        }
      } catch (err: any) {
        console.error(err);
        setError('Failed to load applications.');
      }
    };
    loadApps();
  }, []);

  const loadBugsData = async (appId: number) => {
    if (!appId) {
      setBugs([]);
      setSummary(null);
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const params: any = {};
      if (selectedStatus !== 'all') params.status = selectedStatus;
      if (selectedSeverity !== 'all') params.severity = selectedSeverity;

      const [bugsRes, summaryRes] = await Promise.allSettled([
        bugsApi.getByApp(appId, params),
        bugsApi.getSummary(appId)
      ]);

      const bugsData = bugsRes.status === 'fulfilled' ? bugsRes.value || [] : [];
      const summaryData = summaryRes.status === 'fulfilled' ? summaryRes.value : null;

      setBugs(bugsData);
      setSummary(summaryData);
    } catch (err: any) {
      console.error(err);
      setError('Failed to load defect records.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedAppId) {
      loadBugsData(Number(selectedAppId));
    }
  }, [selectedAppId, selectedStatus, selectedSeverity]);

  const handleStatusChange = async (bugId: number, newStatus: string) => {
    try {
      setUpdatingStatus(true);
      const updated = await bugsApi.updateStatus(bugId, newStatus);
      setBugs((prev) => prev.map((b) => (b.id === bugId ? updated : b)));
      if (inspectedBug?.id === bugId) {
        setInspectedBug(updated);
      }
      if (selectedAppId) {
        const sum = await bugsApi.getSummary(Number(selectedAppId));
        setSummary(sum);
      }
    } catch (err: any) {
      alert(`Failed to update status: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setUpdatingStatus(false);
    }
  };

  const handleCreateManualBug = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAppId) return;
    try {
      setCreatingBug(true);
      const res = await bugsApi.createBug(Number(selectedAppId), newBugData);
      setBugs((prev) => [res, ...prev]);
      setShowCreateModal(false);
      setNewBugData({
        title: '',
        category: 'FUNCTIONAL',
        severity: 'HIGH',
        priority: 'HIGH',
        affected_page: 'http://127.0.0.1:3000',
        expected_behavior: '',
        actual_behavior: '',
        description: ''
      });
      const sum = await bugsApi.getSummary(Number(selectedAppId));
      setSummary(sum);
    } catch (err: any) {
      alert(`Failed to log defect: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setCreatingBug(false);
    }
  };

  const handleScanDefects = async () => {
    if (!selectedAppId) return;
    try {
      setScanning(true);
      setError(null);
      await bugsApi.scanDefects(Number(selectedAppId));
      await loadBugsData(Number(selectedAppId));
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Defect scan failed.');
    } finally {
      setScanning(false);
    }
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity.toUpperCase()) {
      case 'CRITICAL':
        return 'bg-red-950 text-red-400 border border-red-800';
      case 'HIGH':
        return 'bg-amber-950 text-amber-400 border border-amber-800';
      case 'MEDIUM':
        return 'bg-blue-950 text-blue-400 border border-blue-800';
      default:
        return 'bg-gray-800 text-gray-400 border border-gray-700';
    }
  };

  const getConfidenceBadge = (level: string, score?: number) => {
    const scoreText = score !== undefined ? ` (${score}%)` : '';
    switch (level.toUpperCase()) {
      case 'CONFIRMED':
        return (
          <span className="px-2 py-0.5 text-xs font-bold bg-emerald-950 text-emerald-400 border border-emerald-800 rounded">
            CONFIRMED{scoreText}
          </span>
        );
      case 'LIKELY':
        return (
          <span className="px-2 py-0.5 text-xs font-bold bg-blue-950 text-blue-300 border border-blue-800 rounded">
            LIKELY{scoreText}
          </span>
        );
      case 'POSSIBLE':
        return (
          <span className="px-2 py-0.5 text-xs font-bold bg-amber-950 text-amber-300 border border-amber-800 rounded">
            POSSIBLE{scoreText}
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 text-xs font-bold bg-gray-800 text-gray-400 border border-gray-700 rounded">
            UNKNOWN{scoreText}
          </span>
        );
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status.toUpperCase()) {
      case 'OPEN':
        return 'bg-red-950/80 text-red-300 border border-red-800';
      case 'TRIAGED':
        return 'bg-blue-950/80 text-blue-300 border border-blue-800';
      case 'IN_PROGRESS':
        return 'bg-amber-950/80 text-amber-300 border border-amber-800';
      case 'FIXED':
        return 'bg-emerald-950/80 text-emerald-300 border border-emerald-800';
      case 'CLOSED':
        return 'bg-gray-800 text-gray-400 border border-gray-700';
      default:
        return 'bg-gray-800 text-gray-300 border border-gray-700';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">Defects & Root Cause Analysis</h1>
            <span className="px-2 py-0.5 text-xs font-bold bg-rose-950 text-rose-400 border border-rose-800 rounded">
              Phase 4 • AI Bug Intelligence
            </span>
          </div>
          <p className="text-sm text-gray-400 mt-1">
            Intelligent root-cause diagnosis from Playwright execution evidence. Zero hallucinated defects.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {apps.length > 0 && (
            <select
              value={selectedAppId}
              onChange={(e) => {
                const id = Number(e.target.value);
                setSelectedAppId(id);
                onSelectApp?.(id);
              }}
              className="bg-gray-800 border border-gray-700 text-sm text-white rounded-lg px-3 py-2 focus:outline-none focus:border-emerald-500"
            >
              {apps.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
          )}

          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center space-x-1.5 px-3 py-2 bg-rose-900/60 hover:bg-rose-900/90 text-rose-300 border border-rose-800 rounded-lg text-xs font-semibold transition shadow"
          >
            <Plus className="h-3.5 w-3.5 text-rose-400" />
            <span>Log Defect</span>
          </button>

          <button
            onClick={handleScanDefects}
            disabled={scanning || !selectedAppId}
            className="flex items-center space-x-1.5 px-3 py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-700 rounded-lg text-xs font-medium transition"
          >
            <Sparkles className={`h-3.5 w-3.5 text-emerald-400 ${scanning ? 'animate-spin' : ''}`} />
            <span>{scanning ? 'Scanning...' : 'Scan Defects'}</span>
          </button>

          <button
            onClick={() => onNavigate('executions', Number(selectedAppId))}
            className="flex items-center space-x-1.5 px-3 py-2 bg-gray-800 hover:bg-gray-700 text-emerald-400 border border-emerald-500/30 rounded-lg text-xs font-medium transition"
          >
            <Activity className="h-3.5 w-3.5" />
            <span>Executions</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-950/50 border border-red-800 rounded-lg text-red-300 text-sm flex items-center space-x-2">
          <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* KPI Cards */}
      {summary && summary.has_bugs ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          <div className="p-4 bg-gray-900 border border-gray-800 rounded-xl">
            <span className="text-xs text-gray-400 uppercase font-semibold">Total Defects</span>
            <div className="text-2xl font-bold text-white mt-1 font-mono">{summary.total_bugs}</div>
            <span className="text-[11px] text-gray-500">Documented bugs</span>
          </div>

          <div className="p-4 bg-gray-900 border border-gray-800 rounded-xl">
            <span className="text-xs text-red-400 uppercase font-semibold">Active Open</span>
            <div className="text-2xl font-bold text-red-400 mt-1 font-mono">{summary.open_bugs}</div>
            <span className="text-[11px] text-red-500/80 font-medium">Require triage</span>
          </div>

          <div className="p-4 bg-gray-900 border border-gray-800 rounded-xl">
            <span className="text-xs text-rose-400 uppercase font-semibold">Critical</span>
            <div className="text-2xl font-bold text-rose-400 mt-1 font-mono">{summary.critical_bugs}</div>
            <span className="text-[11px] text-rose-500/80">Blocking failures</span>
          </div>

          <div className="p-4 bg-gray-900 border border-gray-800 rounded-xl">
            <span className="text-xs text-amber-400 uppercase font-semibold">High Severity</span>
            <div className="text-2xl font-bold text-amber-400 mt-1 font-mono">{summary.high_bugs}</div>
            <span className="text-[11px] text-amber-500/80">Workflow defects</span>
          </div>

          <div className="p-4 bg-gray-900 border border-gray-800 rounded-xl">
            <span className="text-xs text-blue-400 uppercase font-semibold">Medium / Low</span>
            <div className="text-2xl font-bold text-blue-400 mt-1 font-mono">
              {summary.medium_bugs + summary.low_bugs}
            </div>
            <span className="text-[11px] text-blue-500/80">Non-blocking</span>
          </div>

          <div className="p-4 bg-gray-900 border border-gray-800 rounded-xl">
            <span className="text-xs text-emerald-400 uppercase font-semibold">Resolved</span>
            <div className="text-2xl font-bold text-emerald-400 mt-1 font-mono">{summary.resolved_bugs}</div>
            <span className="text-[11px] text-emerald-500/80">Fixed / Closed</span>
          </div>
        </div>
      ) : (
        /* Zero Defects State */
        <div className="p-8 bg-gray-900 border border-gray-800 rounded-xl text-center space-y-4">
          <CheckCircle2 className="h-10 w-10 mx-auto text-emerald-400" />
          <div>
            <h3 className="text-base font-semibold text-white">No application bugs detected.</h3>
            <p className="text-xs text-gray-400 max-w-md mx-auto mt-1">
              Test suites executed against the target environment without unhandled exceptions or application defects. Zero false bugs are manufactured.
            </p>
          </div>
          <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
            <button
              onClick={() => setShowCreateModal(true)}
              className="flex items-center space-x-1.5 px-4 py-2 bg-rose-900/60 hover:bg-rose-900/90 text-rose-300 border border-rose-800 rounded-lg text-xs font-medium transition shadow"
            >
              <Plus className="h-4 w-4 text-rose-400" />
              <span>Log Defect Manually</span>
            </button>
            <button
              onClick={handleScanDefects}
              disabled={scanning || !selectedAppId}
              className="flex items-center space-x-1.5 px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-700 rounded-lg text-xs font-medium transition"
            >
              <Sparkles className={`h-4 w-4 text-emerald-400 ${scanning ? 'animate-spin' : ''}`} />
              <span>{scanning ? 'Scanning...' : 'Scan Executions for Defects'}</span>
            </button>
          </div>
        </div>
      )}

      {/* Filter Bar */}
      <div className="bg-gray-900 border border-gray-800 p-4 rounded-xl flex flex-wrap items-center justify-between gap-4 text-xs">
        <div className="flex items-center space-x-2">
          <span className="text-gray-400 font-medium flex items-center space-x-1">
            <Filter className="h-3.5 w-3.5" />
            <span>Status:</span>
          </span>
          {['all', 'OPEN', 'TRIAGED', 'IN_PROGRESS', 'FIXED', 'CLOSED'].map((st) => (
            <button
              key={st}
              onClick={() => setSelectedStatus(st)}
              className={`px-2.5 py-1 rounded uppercase font-medium transition ${
                selectedStatus === st
                  ? 'bg-emerald-600 text-white font-bold'
                  : 'bg-gray-800 text-gray-400 hover:text-white'
              }`}
            >
              {st}
            </button>
          ))}
        </div>

        <div className="flex items-center space-x-2">
          <span className="text-gray-400 font-medium">Severity:</span>
          {['all', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((sev) => (
            <button
              key={sev}
              onClick={() => setSelectedSeverity(sev)}
              className={`px-2.5 py-1 rounded uppercase font-medium transition ${
                selectedSeverity === sev
                  ? 'bg-emerald-600 text-white font-bold'
                  : 'bg-gray-800 text-gray-400 hover:text-white'
              }`}
            >
              {sev}
            </button>
          ))}
        </div>
      </div>

      {/* Defects Table */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between">
          <h2 className="text-base font-semibold text-white">Documented Defects</h2>
          <span className="text-xs text-gray-400">{bugs.length} Defects Found</span>
        </div>

        {loading ? (
          <div className="p-12 text-center text-gray-400 text-sm">Loading defect records...</div>
        ) : bugs.length === 0 ? (
          <div className="p-12 text-center text-gray-500 text-xs">
            No defect records matching the current filter criteria.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-gray-300">
              <thead className="bg-gray-800/50 text-xs uppercase text-gray-400">
                <tr>
                  <th className="px-4 py-3">Bug ID</th>
                  <th className="px-4 py-3">Title & Category</th>
                  <th className="px-4 py-3">Severity</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Confidence</th>
                  <th className="px-4 py-3">Occurrences</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {bugs.map((b) => (
                  <tr key={b.id} className="hover:bg-gray-800/30 transition">
                    <td className="px-4 py-4 font-mono font-medium text-rose-400">
                      BUG-{String(b.id).padStart(3, '0')}
                    </td>
                    <td className="px-4 py-4 max-w-sm">
                      <div className="font-semibold text-white truncate">{b.title}</div>
                      <div className="flex items-center space-x-2 mt-1">
                        <span className="px-2 py-0.2 text-[10px] uppercase font-bold bg-gray-800 text-gray-300 rounded">
                          {b.category}
                        </span>
                        <span className="text-xs text-gray-400 truncate max-w-[200px]">
                          {b.affected_page || 'App-wide'}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <span className={`px-2 py-0.5 text-xs uppercase font-bold rounded ${getSeverityBadge(b.severity)}`}>
                        {b.severity}
                      </span>
                    </td>
                    <td className="px-4 py-4">
                      <span className={`px-2 py-0.5 text-xs font-bold uppercase rounded ${getStatusBadge(b.status)}`}>
                        {b.status}
                      </span>
                    </td>
                    <td className="px-4 py-4">
                      {getConfidenceBadge(b.confidence_level, b.root_cause_confidence)}
                    </td>
                    <td className="px-4 py-4 text-xs font-mono text-gray-300">
                      {b.occurrence_count}x
                    </td>
                    <td className="px-4 py-4 text-right">
                      <button
                        onClick={async () => {
                          const full = await bugsApi.getById(b.id);
                          setInspectedBug(full);
                        }}
                        className="px-3 py-1 bg-gray-800 hover:bg-gray-700 text-emerald-400 rounded text-xs font-medium transition border border-gray-700"
                      >
                        Inspect Defect
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Bug Details Modal */}
      {inspectedBug && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
            {/* Modal Header */}
            <div className="p-5 border-b border-gray-800 flex items-start justify-between bg-gray-950">
              <div>
                <div className="flex items-center space-x-2">
                  <span className="font-mono text-sm font-bold text-rose-400">
                    BUG-{String(inspectedBug.id).padStart(3, '0')}
                  </span>
                  <h3 className="text-lg font-bold text-white">{inspectedBug.title}</h3>
                  <span className={`px-2 py-0.5 text-xs uppercase font-bold rounded ${getSeverityBadge(inspectedBug.severity)}`}>
                    {inspectedBug.severity}
                  </span>
                </div>
                <p className="text-xs text-gray-400 mt-1">{inspectedBug.summary}</p>
              </div>

              <button
                onClick={() => setInspectedBug(null)}
                className="text-gray-400 hover:text-white text-xs px-2.5 py-1.5 bg-gray-800 rounded-lg hover:bg-gray-700 transition"
              >
                Close
              </button>
            </div>

            {/* Lifecycle Status Action Bar */}
            <div className="px-5 py-3 bg-gray-950/70 border-b border-gray-800 flex flex-wrap items-center justify-between gap-3 text-xs">
              <div className="flex items-center space-x-2">
                <span className="text-gray-400 font-medium">Lifecycle Status:</span>
                <span className={`px-2.5 py-0.5 font-bold rounded uppercase ${getStatusBadge(inspectedBug.status)}`}>
                  {inspectedBug.status}
                </span>
                <span className="text-gray-500">({inspectedBug.occurrence_count} execution occurrences)</span>
              </div>

              <div className="flex items-center space-x-1.5">
                <span className="text-gray-400 mr-1">Move to:</span>
                {['OPEN', 'TRIAGED', 'IN_PROGRESS', 'FIXED', 'CLOSED'].map((st) => (
                  <button
                    key={st}
                    disabled={updatingStatus || inspectedBug.status === st}
                    onClick={() => handleStatusChange(inspectedBug.id, st)}
                    className={`px-2 py-1 rounded text-[11px] font-semibold transition ${
                      inspectedBug.status === st
                        ? 'bg-gray-800 text-gray-500 cursor-default'
                        : 'bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white border border-gray-700'
                    }`}
                  >
                    {st}
                  </button>
                ))}
              </div>
            </div>

            {/* Modal Content */}
            <div className="p-5 overflow-y-auto flex-1 space-y-5 text-xs bg-gray-900">
              {/* Context Summary Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 bg-gray-950 border border-gray-800 rounded-xl">
                <div>
                  <span className="text-gray-500 block text-[11px]">Category</span>
                  <span className="font-semibold text-white mt-0.5 block">{inspectedBug.category}</span>
                </div>
                <div>
                  <span className="text-gray-500 block text-[11px]">Classification</span>
                  <span className="font-semibold text-emerald-400 mt-0.5 block font-mono">
                    {inspectedBug.classification}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500 block text-[11px]">Failed Step</span>
                  <span className="font-mono text-gray-300 mt-0.5 block truncate">
                    {inspectedBug.failed_step || '—'}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500 block text-[11px]">Affected Page</span>
                  <span className="font-mono text-gray-300 mt-0.5 block truncate">
                    {inspectedBug.affected_page || '—'}
                  </span>
                </div>
              </div>

              {/* Expected vs Actual Behavior */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="p-4 bg-emerald-950/20 border border-emerald-800/40 rounded-xl space-y-1">
                  <span className="font-bold text-emerald-400 flex items-center space-x-1.5">
                    <Check className="h-4 w-4" />
                    <span>Expected Behavior</span>
                  </span>
                  <p className="text-gray-300 font-sans mt-1 leading-relaxed">
                    {inspectedBug.expected_behavior}
                  </p>
                </div>

                <div className="p-4 bg-red-950/20 border border-red-800/40 rounded-xl space-y-1">
                  <span className="font-bold text-red-400 flex items-center space-x-1.5">
                    <AlertCircle className="h-4 w-4" />
                    <span>Observed Failure Behavior</span>
                  </span>
                  <p className="text-gray-300 font-mono text-[11px] mt-1 leading-relaxed whitespace-pre-wrap">
                    {inspectedBug.actual_behavior}
                  </p>
                </div>
              </div>

              {/* Root Cause Analysis Card */}
              <div className="p-4 bg-gray-950 border border-gray-800 rounded-xl space-y-3">
                <div className="flex items-center justify-between border-b border-gray-800 pb-2">
                  <div className="flex items-center space-x-2">
                    <Sparkles className="h-4 w-4 text-emerald-400" />
                    <span className="font-bold text-white text-sm">Root-Cause Diagnosis</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="text-gray-400 text-[11px]">Confidence Assessment:</span>
                    {getConfidenceBadge(inspectedBug.confidence_level, inspectedBug.root_cause_confidence)}
                  </div>
                </div>

                <div className="space-y-1">
                  <span className="text-gray-400 block font-semibold">Inferred Root Cause:</span>
                  <p className="text-gray-200 font-mono text-xs leading-relaxed bg-gray-900 p-3 rounded-lg border border-gray-800">
                    {inspectedBug.root_cause}
                  </p>
                </div>

                {inspectedBug.severity_explanation && (
                  <div className="space-y-1 pt-1">
                    <span className="text-gray-400 block font-semibold">Severity Justification:</span>
                    <p className="text-gray-300 text-xs">
                      {inspectedBug.severity_explanation}
                    </p>
                  </div>
                )}
              </div>

              {/* Captured Evidence Section */}
              <div>
                <span className="font-semibold text-gray-300 uppercase tracking-wider block mb-2">
                  Captured Defect Evidence:
                </span>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {inspectedBug.evidence && inspectedBug.evidence.map((ev) => {
                    if (ev.type === 'screenshot' && ev.file_path) {
                      const cleanPath = ev.file_path.replace(/^\.\//, '').replace(/^artifacts\//, '');
                      const url = `${BACKEND_URL}/artifacts/${cleanPath}`;

                      return (
                        <div key={ev.id} className="p-3 bg-gray-950 border border-gray-800 rounded-xl space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-white">{ev.description || 'Failure Screenshot'}</span>
                            <a
                              href={url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-emerald-400 hover:text-emerald-300 flex items-center space-x-1"
                            >
                              <Maximize2 className="h-3 w-3" />
                              <span>Full Size</span>
                            </a>
                          </div>
                          <div className="rounded-lg overflow-hidden border border-gray-800 bg-black aspect-video flex items-center justify-center">
                            <img src={url} alt="Failure Screenshot" className="w-full h-full object-contain" />
                          </div>
                        </div>
                      );
                    }

                    if (ev.type === 'trace' && ev.file_path) {
                      const cleanPath = ev.file_path.replace(/^\.\//, '').replace(/^artifacts\//, '');
                      const url = `${BACKEND_URL}/artifacts/${cleanPath}`;

                      return (
                        <div key={ev.id} className="p-4 bg-gray-950 border border-gray-800 rounded-xl flex items-center justify-between">
                          <div className="space-y-1">
                            <span className="font-semibold text-white flex items-center space-x-1.5">
                              <Terminal className="h-4 w-4 text-emerald-400" />
                              <span>Playwright Trace Artifact</span>
                            </span>
                            <p className="text-[11px] text-gray-400">
                              Contains DOM snapshots at point of failure.
                            </p>
                          </div>
                          <a
                            href={url}
                            download
                            className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-emerald-400 border border-emerald-500/30 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition"
                          >
                            <Download className="h-3.5 w-3.5" />
                            <span>Download .zip</span>
                          </a>
                        </div>
                      );
                    }

                    return null;
                  })}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Log Defect Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl w-full max-w-lg p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-gray-800">
              <h2 className="text-lg font-bold text-white flex items-center space-x-2">
                <Plus className="h-5 w-5 text-rose-400" />
                <span>Log Defect Manually</span>
              </h2>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-gray-400 hover:text-white text-xs px-2 py-1 rounded bg-gray-800"
              >
                Close
              </button>
            </div>

            <form onSubmit={handleCreateManualBug} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-300 uppercase mb-1">
                  Defect Title *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Broken checkout form validation on empty cart"
                  value={newBugData.title}
                  onChange={(e) => setNewBugData({ ...newBugData, title: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-rose-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-300 uppercase mb-1">
                    Severity
                  </label>
                  <select
                    value={newBugData.severity}
                    onChange={(e) => setNewBugData({ ...newBugData, severity: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-rose-500"
                  >
                    <option value="CRITICAL">CRITICAL</option>
                    <option value="HIGH">HIGH</option>
                    <option value="MEDIUM">MEDIUM</option>
                    <option value="LOW">LOW</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-300 uppercase mb-1">
                    Category
                  </label>
                  <select
                    value={newBugData.category}
                    onChange={(e) => setNewBugData({ ...newBugData, category: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-rose-500"
                  >
                    <option value="JAVASCRIPT">JAVASCRIPT</option>
                    <option value="API">API (HTTP 500)</option>
                    <option value="VALIDATION">VALIDATION</option>
                    <option value="FUNCTIONAL">FUNCTIONAL</option>
                    <option value="UI">UI</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300 uppercase mb-1">
                  Affected Page URL
                </label>
                <input
                  type="url"
                  value={newBugData.affected_page}
                  onChange={(e) => setNewBugData({ ...newBugData, affected_page: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-rose-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-300 uppercase mb-1">
                    Expected Behavior
                  </label>
                  <textarea
                    rows={2}
                    placeholder="Should show helpful validation message"
                    value={newBugData.expected_behavior}
                    onChange={(e) => setNewBugData({ ...newBugData, expected_behavior: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-rose-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-300 uppercase mb-1">
                    Observed Actual Failure
                  </label>
                  <textarea
                    rows={2}
                    placeholder="Form crashes or unhandled TypeError occurs"
                    value={newBugData.actual_behavior}
                    onChange={(e) => setNewBugData({ ...newBugData, actual_behavior: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-rose-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300 uppercase mb-1">
                  Description / Investigation Notes
                </label>
                <textarea
                  rows={2}
                  placeholder="Additional context from manual QA investigation"
                  value={newBugData.description}
                  onChange={(e) => setNewBugData({ ...newBugData, description: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-rose-500"
                />
              </div>

              <div className="flex items-center justify-end space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs font-medium rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creatingBug}
                  className="px-4 py-2 bg-rose-600 hover:bg-rose-500 disabled:opacity-50 text-white text-xs font-semibold rounded-lg shadow"
                >
                  {creatingBug ? 'Logging...' : 'Save & Log Defect'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
