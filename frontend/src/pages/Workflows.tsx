import React, { useEffect, useState } from 'react';
import { applicationsApi, workflowsApi, analysisApi } from '../services/api';
import { Application, Workflow, AnalysisStatusResponse } from '../types';
import { Network, Sparkles, RefreshCw, AlertCircle, ArrowRight, ShieldAlert, CheckCircle2, Clock } from 'lucide-react';

interface WorkflowsProps {
  initialAppId?: number;
  onSelectApp?: (id: number) => void;
  onNavigate: (tab: string, contextId?: number) => void;
}

export const Workflows: React.FC<WorkflowsProps> = ({ initialAppId, onSelectApp, onNavigate }) => {
  const [apps, setApps] = useState<Application[]>([]);
  const [selectedAppId, setSelectedAppId] = useState<number | ''>(initialAppId || '');
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initialAppId) {
      setSelectedAppId(initialAppId);
    }
  }, [initialAppId]);

  // Analysis status polling
  const [analysisStatus, setAnalysisStatus] = useState<AnalysisStatusResponse | null>(null);
  const [analyzing, setAnalyzing] = useState(false);

  // Selected workflow for detail inspection
  const [selectedWorkflow, setSelectedWorkflow] = useState<Workflow | null>(null);

  useEffect(() => {
    const loadApps = async () => {
      try {
        const data = await applicationsApi.getAll();
        setApps(data);
        if (data.length > 0) {
          if (!selectedAppId || !data.some(a => a.id === selectedAppId)) {
            setSelectedAppId(data[0].id);
            onSelectApp?.(data[0].id);
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

  const loadWorkflows = async (appId: number) => {
    if (!appId) {
      setWorkflows([]);
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const [wfsRes, statusRes] = await Promise.allSettled([
        workflowsApi.getByApp(appId),
        analysisApi.getStatus(appId)
      ]);
      
      if (wfsRes.status === 'fulfilled') {
        setWorkflows(wfsRes.value || []);
      } else {
        setWorkflows([]);
      }

      if (statusRes.status === 'fulfilled') {
        setAnalysisStatus(statusRes.value);
        setAnalyzing(statusRes.value.status !== 'IDLE' && statusRes.value.status !== 'COMPLETED' && statusRes.value.status !== 'FAILED');
      } else {
        setAnalysisStatus({
          status: 'IDLE',
          stage: 'Ready for analysis',
          workflows_count: 0,
          test_cases_count: 0,
          activity_log: []
        });
      }
    } catch (err: any) {
      console.error(err);
      setError('Failed to load workflows.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedAppId) {
      loadWorkflows(Number(selectedAppId));
    } else {
      setWorkflows([]);
      setLoading(false);
    }
  }, [selectedAppId]);

  // Status polling during active analysis
  useEffect(() => {
    if (!analyzing || !selectedAppId) return;

    const interval = setInterval(async () => {
      try {
        const statusData = await analysisApi.getStatus(Number(selectedAppId));
        setAnalysisStatus(statusData);

        if (statusData.status === 'COMPLETED' || statusData.status === 'FAILED') {
          setAnalyzing(false);
          const wfs = await workflowsApi.getByApp(Number(selectedAppId));
          setWorkflows(wfs);
        }
      } catch (err) {
        console.error(err);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [analyzing, selectedAppId]);

  const handleTriggerAnalysis = async () => {
    if (!selectedAppId) return;
    try {
      setAnalyzing(true);
      setError(null);
      await analysisApi.startAnalysis(Number(selectedAppId));
      loadWorkflows(Number(selectedAppId));
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || err.message || 'Failed to trigger AI analysis.');
      setAnalyzing(false);
    }
  };

  const getRiskBadge = (risk: string) => {
    switch (risk.toLowerCase()) {
      case 'critical':
        return 'bg-red-950 text-red-400 border border-red-800';
      case 'high':
        return 'bg-amber-950 text-amber-400 border border-amber-800';
      case 'medium':
        return 'bg-blue-950 text-blue-400 border border-blue-800';
      default:
        return 'bg-gray-800 text-gray-400 border border-gray-700';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Application Workflows</h1>
          <p className="text-sm text-gray-400">
            Autonomous business workflow identification derived from actual explored pages and interactive controls.
          </p>
        </div>

        <div className="flex items-center space-x-3">
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
            onClick={handleTriggerAnalysis}
            disabled={analyzing || !selectedAppId}
            className="flex items-center space-x-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-medium rounded-lg text-sm shadow transition"
          >
            <Sparkles className={`h-4 w-4 ${analyzing ? 'animate-spin' : ''}`} />
            <span>{analyzing ? 'Analyzing App...' : 'Run AI Analysis'}</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-950/50 border border-red-800 rounded-lg text-red-300 text-sm flex items-center space-x-2">
          <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Live Stage Progress Indicator */}
      {analysisStatus && analysisStatus.status !== 'IDLE' && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-3">
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center space-x-2">
              <span className={`px-2 py-0.5 font-bold uppercase rounded ${
                analysisStatus.status === 'COMPLETED'
                  ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                  : analysisStatus.status === 'FAILED'
                  ? 'bg-red-950 text-red-400 border border-red-800'
                  : 'bg-blue-950 text-blue-400 border border-blue-800 animate-pulse'
              }`}>
                {analysisStatus.status}
              </span>
              <span className="text-gray-300 font-medium">{analysisStatus.stage}</span>
            </div>
            <span className="text-gray-400 text-[11px]">
              {analysisStatus.workflows_count} Workflows • {analysisStatus.test_cases_count} Test Cases
            </span>
          </div>

          {analysisStatus.activity_log && analysisStatus.activity_log.length > 0 && (
            <div className="bg-gray-950 rounded p-3 font-mono text-xs text-gray-300 max-h-32 overflow-y-auto space-y-1">
              {analysisStatus.activity_log.map((log, idx) => (
                <div key={idx} className="flex items-start space-x-2">
                  <span className="text-emerald-400">→</span>
                  <span className="text-gray-300">{log}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Workflows Cards */}
      {loading && !analyzing ? (
        <div className="p-12 text-center text-gray-400 text-sm">Loading workflows from database...</div>
      ) : workflows.length === 0 ? (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-12 text-center space-y-4">
          <Network className="h-10 w-10 text-gray-600 mx-auto" />
          <h3 className="text-base font-semibold text-white">No workflows discovered yet</h3>
          <p className="text-sm text-gray-400 max-w-md mx-auto">
            Run AI Analysis to synthesize discovered application pages, forms, and interactive buttons into coherent user workflows.
          </p>
          <button
            onClick={handleTriggerAnalysis}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium rounded-lg transition"
          >
            Trigger AI Analysis
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {workflows.map((wf) => (
            <div
              key={wf.id}
              onClick={() => setSelectedWorkflow(wf)}
              className="bg-gray-900 border border-gray-800 hover:border-gray-700 rounded-xl p-5 cursor-pointer transition flex flex-col justify-between group"
            >
              <div>
                <div className="flex items-start justify-between">
                  <h3 className="text-base font-bold text-white group-hover:text-emerald-400 transition">
                    {wf.name}
                  </h3>
                  <span className={`px-2 py-0.5 text-[11px] font-bold uppercase rounded ${getRiskBadge(wf.risk_level)}`}>
                    {wf.risk_level} RISK
                  </span>
                </div>
                <p className="text-xs text-gray-400 mt-2 line-clamp-2">
                  {wf.description || 'No description provided.'}
                </p>
              </div>

              <div className="mt-5 pt-3 border-t border-gray-800/80 flex items-center justify-between text-xs text-gray-400">
                <div className="flex items-center space-x-1.5">
                  <Clock className="h-3.5 w-3.5 text-gray-500" />
                  <span>{wf.steps_count} Sequential Steps</span>
                </div>
                <div className="flex items-center space-x-1 text-emerald-400 font-medium">
                  <span>Inspect Steps</span>
                  <ArrowRight className="h-3 w-3" />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Workflow Steps Modal */}
      {selectedWorkflow && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl w-full max-w-2xl max-h-[80vh] flex flex-col shadow-2xl">
            <div className="p-5 border-b border-gray-800 flex items-start justify-between">
              <div>
                <div className="flex items-center space-x-2">
                  <h3 className="text-lg font-bold text-white">{selectedWorkflow.name}</h3>
                  <span className={`px-2 py-0.5 text-xs font-bold uppercase rounded ${getRiskBadge(selectedWorkflow.risk_level)}`}>
                    {selectedWorkflow.risk_level}
                  </span>
                </div>
                <p className="text-xs text-gray-400 mt-1">{selectedWorkflow.description}</p>
              </div>
              <button
                onClick={() => setSelectedWorkflow(null)}
                className="text-gray-400 hover:text-white text-xs px-2 py-1 bg-gray-800 rounded"
              >
                Close
              </button>
            </div>

            <div className="p-5 overflow-y-auto flex-1 space-y-3">
              <span className="text-xs font-semibold text-gray-300 uppercase tracking-wider block mb-2">
                Workflow Step Sequence:
              </span>
              {selectedWorkflow.steps.length === 0 ? (
                <div className="text-xs text-gray-500 text-center py-6">No steps recorded for this workflow.</div>
              ) : (
                selectedWorkflow.steps.map((step) => (
                  <div key={step.id} className="p-3 bg-gray-950 border border-gray-800 rounded-lg text-xs space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-emerald-400">Step {step.sequence}: {step.action}</span>
                    </div>
                    {step.expected_behavior && (
                      <div className="text-gray-300 mt-1">
                        Expected: <span className="text-gray-400">{step.expected_behavior}</span>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>

            <div className="p-4 border-t border-gray-800 flex justify-end">
              <button
                onClick={() => onNavigate('test-cases', selectedWorkflow.application_id)}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium rounded-lg transition"
              >
                View Generated Test Cases
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
