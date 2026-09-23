import React, { useEffect, useState } from 'react';
import { applicationsApi, executionsApi, testCasesApi, BACKEND_URL } from '../services/api';
import { Application, TestExecution, ExecutionSummary, TestCase } from '../types';
import {
  Activity,
  CheckCircle2,
  XCircle,
  ShieldAlert,
  Clock,
  Layers,
  Terminal,
  Maximize2,
  Download,
  AlertCircle,
  Play,
  Sparkles,
  RefreshCw
} from 'lucide-react';

interface ExecutionsDashboardProps {
  initialAppId?: number;
  onSelectApp?: (id: number) => void;
  onNavigate: (tab: string, contextId?: number) => void;
}

export const ExecutionsDashboard: React.FC<ExecutionsDashboardProps> = ({ initialAppId, onSelectApp, onNavigate }) => {
  const [apps, setApps] = useState<Application[]>([]);
  const [selectedAppId, setSelectedAppId] = useState<number | ''>(initialAppId || '');
  const [summary, setSummary] = useState<ExecutionSummary | null>(null);
  const [executions, setExecutions] = useState<TestExecution[]>([]);
  const [testCases, setTestCases] = useState<TestCase[]>([]);
  const [selectedTestCaseId, setSelectedTestCaseId] = useState<number | ''>('');
  const [executing, setExecuting] = useState(false);
  const [executionMsg, setExecutionMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Inspector modal
  const [inspectedExecution, setInspectedExecution] = useState<TestExecution | null>(null);

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

  const loadExecutionData = async (appId: number) => {
    if (!appId) {
      setSummary(null);
      setExecutions([]);
      setTestCases([]);
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const [sumRes, execsRes, casesRes] = await Promise.allSettled([
        executionsApi.getSummary(appId),
        executionsApi.getByApp(appId, 100),
        testCasesApi.getByApp(appId)
      ]);
      const sumData = sumRes.status === 'fulfilled' ? sumRes.value : null;
      const execsData = execsRes.status === 'fulfilled' ? execsRes.value || [] : [];
      const casesData = casesRes.status === 'fulfilled' ? casesRes.value || [] : [];

      setSummary(sumData);
      setExecutions(execsData);
      setTestCases(casesData);
      if (casesData.length > 0 && !selectedTestCaseId) {
        setSelectedTestCaseId(casesData[0].id);
      }
    } catch (err: any) {
      console.error(err);
      setError('Failed to load execution data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedAppId) {
      loadExecutionData(Number(selectedAppId));
    }
  }, [selectedAppId]);

  const handleRunSingle = async (testCaseId: number) => {
    if (!testCaseId || !selectedAppId) return;
    try {
      setExecuting(true);
      setExecutionMsg(`Launching Playwright CDP runner for Test Case #${testCaseId}...`);
      setError(null);
      const res = await executionsApi.execute(testCaseId);
      setExecutions(prev => [res, ...prev]);
      const updatedSummary = await executionsApi.getSummary(Number(selectedAppId));
      setSummary(updatedSummary);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Execution failed.');
    } finally {
      setExecuting(false);
      setExecutionMsg(null);
    }
  };

  const handleRunAll = async () => {
    if (testCases.length === 0 || !selectedAppId) return;
    try {
      setExecuting(true);
      setError(null);
      for (let i = 0; i < testCases.length; i++) {
        const tc = testCases[i];
        setExecutionMsg(`Executing [${i + 1}/${testCases.length}]: ${tc.name}...`);
        try {
          const res = await executionsApi.execute(tc.id);
          setExecutions(prev => [res, ...prev]);
        } catch (e) {
          console.error(`Error running ${tc.id}:`, e);
        }
      }
      const updatedSummary = await executionsApi.getSummary(Number(selectedAppId));
      setSummary(updatedSummary);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Failed running test suite.');
    } finally {
      setExecuting(false);
      setExecutionMsg(null);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case 'passed':
        return (
          <span className="px-2 py-0.5 text-xs font-bold text-emerald-400 bg-emerald-950/80 border border-emerald-800 rounded inline-flex items-center space-x-1">
            <CheckCircle2 className="h-3 w-3" />
            <span>PASSED</span>
          </span>
        );
      case 'failed':
        return (
          <span className="px-2 py-0.5 text-xs font-bold text-red-400 bg-red-950/80 border border-red-800 rounded inline-flex items-center space-x-1">
            <XCircle className="h-3 w-3" />
            <span>FAILED</span>
          </span>
        );
      case 'blocked':
        return (
          <span className="px-2 py-0.5 text-xs font-bold text-amber-400 bg-amber-950/80 border border-amber-800 rounded inline-flex items-center space-x-1">
            <ShieldAlert className="h-3 w-3" />
            <span>BLOCKED</span>
          </span>
        );
      case 'running':
        return (
          <span className="px-2 py-0.5 text-xs font-bold text-blue-400 bg-blue-950/80 border border-blue-800 rounded inline-flex items-center space-x-1 animate-pulse">
            <Activity className="h-3 w-3 animate-spin" />
            <span>RUNNING</span>
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 text-xs text-gray-400 bg-gray-800 rounded">
            {status.toUpperCase()}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">Playwright Execution Dashboard</h1>
            <span className="px-2 py-0.5 text-xs font-bold bg-emerald-950 text-emerald-400 border border-emerald-800 rounded">
              Zero Mock Data
            </span>
          </div>
          <p className="text-sm text-gray-400 mt-1">
            Real-time execution metrics, duration tracking, and test evidence collected from Playwright CDP runs.
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

          {testCases.length > 0 && (
            <div className="flex items-center space-x-1.5 bg-gray-800/80 border border-gray-700 rounded-lg p-1">
              <select
                value={selectedTestCaseId}
                onChange={(e) => setSelectedTestCaseId(Number(e.target.value))}
                className="bg-transparent text-xs text-gray-200 px-2 py-1 focus:outline-none max-w-[180px] truncate"
              >
                {testCases.map((tc) => (
                  <option key={tc.id} value={tc.id} className="bg-gray-800 text-white">
                    {tc.name}
                  </option>
                ))}
              </select>
              <button
                onClick={() => selectedTestCaseId && handleRunSingle(Number(selectedTestCaseId))}
                disabled={executing || !selectedTestCaseId}
                className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded text-xs font-semibold flex items-center space-x-1 transition shadow"
              >
                <Play className="h-3 w-3 fill-current" />
                <span>Run</span>
              </button>
            </div>
          )}

          {testCases.length > 0 && (
            <button
              onClick={handleRunAll}
              disabled={executing}
              className="px-3 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition shadow"
            >
              <Play className={`h-3.5 w-3.5 fill-current ${executing ? 'animate-spin' : ''}`} />
              <span>{executing ? 'Running...' : 'Run All Tests'}</span>
            </button>
          )}

          <button
            onClick={() => onNavigate('test-cases', Number(selectedAppId))}
            className="px-3 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 border border-gray-700 rounded-lg text-xs font-medium transition"
          >
            <span>Test Cases</span>
          </button>
        </div>
      </div>

      {executing && (
        <div className="p-4 bg-blue-950/60 border border-blue-700 rounded-xl text-blue-300 text-sm flex items-center space-x-3 animate-pulse">
          <Activity className="h-5 w-5 text-blue-400 animate-spin" />
          <span>{executionMsg || 'Playwright CDP browser test execution in progress...'}</span>
        </div>
      )}

      {error && (
        <div className="p-4 bg-red-950/50 border border-red-800 rounded-lg text-red-300 text-sm flex items-center space-x-2">
          <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* KPI Cards */}
      {summary && summary.has_executions ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          <div className="p-4 bg-gray-900 border border-gray-800 rounded-xl">
            <span className="text-xs text-gray-400 uppercase font-semibold">Total Runs</span>
            <div className="text-2xl font-bold text-white mt-1 font-mono">{summary.total_executions}</div>
            <span className="text-[11px] text-gray-500">Real executions</span>
          </div>

          <div className="p-4 bg-gray-900 border border-gray-800 rounded-xl">
            <span className="text-xs text-emerald-400 uppercase font-semibold">Passed</span>
            <div className="text-2xl font-bold text-emerald-400 mt-1 font-mono">{summary.passed}</div>
            <span className="text-[11px] text-emerald-500/80 font-medium">{summary.pass_rate}% Pass Rate</span>
          </div>

          <div className="p-4 bg-gray-900 border border-gray-800 rounded-xl">
            <span className="text-xs text-red-400 uppercase font-semibold">Failed</span>
            <div className="text-2xl font-bold text-red-400 mt-1 font-mono">{summary.failed}</div>
            <span className="text-[11px] text-red-500/80">With failure traces</span>
          </div>

          <div className="p-4 bg-gray-900 border border-gray-800 rounded-xl">
            <span className="text-xs text-amber-400 uppercase font-semibold">Blocked</span>
            <div className="text-2xl font-bold text-amber-400 mt-1 font-mono">{summary.blocked}</div>
            <span className="text-[11px] text-amber-500/80">Safety guards</span>
          </div>

          <div className="p-4 bg-gray-900 border border-gray-800 rounded-xl">
            <span className="text-xs text-gray-400 uppercase font-semibold">Skipped / Err</span>
            <div className="text-2xl font-bold text-gray-300 mt-1 font-mono">{summary.skipped + summary.errors}</div>
            <span className="text-[11px] text-gray-500">Aborted / System</span>
          </div>

          <div className="p-4 bg-gray-900 border border-gray-800 rounded-xl">
            <span className="text-xs text-blue-400 uppercase font-semibold">Avg Duration</span>
            <div className="text-2xl font-bold text-blue-400 mt-1 font-mono">{summary.avg_duration_ms} <span className="text-xs text-blue-300">ms</span></div>
            <span className="text-[11px] text-blue-500/80">Browser execution</span>
          </div>
        </div>
      ) : (
        /* Zero Executions State */
        <div className="p-8 bg-gray-900 border border-gray-800 rounded-xl text-center space-y-4">
          <Clock className="h-10 w-10 mx-auto text-gray-600" />
          <div>
            <h3 className="text-base font-semibold text-white">No test executions recorded yet for this application.</h3>
            <p className="text-xs text-gray-400 max-w-md mx-auto mt-1">
              Test statistics are strictly computed from actual Playwright browser runs. Run an automated test case directly right now.
            </p>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
            {testCases.length > 0 ? (
              <>
                <button
                  onClick={handleRunAll}
                  disabled={executing}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold flex items-center space-x-2 transition shadow"
                >
                  <Play className="h-3.5 w-3.5 fill-current" />
                  <span>Execute All Tests ({testCases.length})</span>
                </button>
                {selectedTestCaseId && (
                  <button
                    onClick={() => handleRunSingle(Number(selectedTestCaseId))}
                    disabled={executing}
                    className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-700 rounded-lg text-xs font-medium flex items-center space-x-1.5 transition"
                  >
                    <Play className="h-3 w-3 fill-emerald-400" />
                    <span>Run First Test</span>
                  </button>
                )}
              </>
            ) : (
              <div className="text-xs text-gray-400">
                <span>No test cases available yet. Create or generate test cases to execute.</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Execution History Table */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between">
          <h2 className="text-base font-semibold text-white">Execution History</h2>
          <span className="text-xs text-gray-400">{executions.length} Total Records</span>
        </div>

        {loading ? (
          <div className="p-12 text-center text-gray-400 text-sm">Loading execution history...</div>
        ) : executions.length === 0 ? (
          <div className="p-12 text-center text-gray-500 text-xs">
            No execution runs found. Execute a test case to generate real history.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-gray-300">
              <thead className="bg-gray-800/50 text-xs uppercase text-gray-400">
                <tr>
                  <th className="px-6 py-3">Exec ID</th>
                  <th className="px-6 py-3">Test Case ID</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Duration</th>
                  <th className="px-6 py-3">Target URL</th>
                  <th className="px-6 py-3">Timestamp</th>
                  <th className="px-6 py-3 text-right">Evidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {executions.map((exec) => (
                  <tr key={exec.id} className="hover:bg-gray-800/30 transition">
                    <td className="px-6 py-4 font-mono font-medium text-emerald-400">
                      #EXEC-{String(exec.id).padStart(4, '0')}
                    </td>
                    <td className="px-6 py-4 font-mono text-xs text-white">
                      TC-{exec.test_case_id}
                    </td>
                    <td className="px-6 py-4">
                      {getStatusBadge(exec.status)}
                    </td>
                    <td className="px-6 py-4 text-xs font-mono text-gray-300">
                      {exec.duration_ms !== null && exec.duration_ms !== undefined ? `${exec.duration_ms} ms` : '—'}
                    </td>
                    <td className="px-6 py-4 text-xs font-mono text-gray-400 truncate max-w-xs">
                      {exec.final_url || '—'}
                    </td>
                    <td className="px-6 py-4 text-xs text-gray-400">
                      {new Date(exec.created_at).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={async () => {
                          const full = await executionsApi.getById(exec.id);
                          setInspectedExecution(full);
                        }}
                        className="px-3 py-1 bg-gray-800 hover:bg-gray-700 text-emerald-400 rounded text-xs font-medium transition border border-gray-700"
                      >
                        Inspect Evidence
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Execution Evidence Modal */}
      {inspectedExecution && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
            <div className="p-5 border-b border-gray-800 flex items-center justify-between bg-gray-950">
              <div>
                <div className="flex items-center space-x-2">
                  <h3 className="text-lg font-bold text-white">
                    Execution #EXEC-{String(inspectedExecution.id).padStart(4, '0')}
                  </h3>
                  {getStatusBadge(inspectedExecution.status)}
                  <span className="font-mono text-xs text-gray-400 ml-2">
                    {inspectedExecution.duration_ms} ms
                  </span>
                </div>
                <p className="text-xs font-mono text-gray-400 mt-1">
                  URL: {inspectedExecution.final_url}
                </p>
              </div>

              <button
                onClick={() => setInspectedExecution(null)}
                className="text-gray-400 hover:text-white text-xs px-2.5 py-1.5 bg-gray-800 rounded-lg hover:bg-gray-700 transition"
              >
                Close
              </button>
            </div>

            <div className="p-5 overflow-y-auto flex-1 space-y-4 text-xs">
              {/* Failure Error Banner */}
              {inspectedExecution.error_message && (
                <div className="p-4 bg-red-950/50 border border-red-800 rounded-xl text-red-300">
                  <span className="font-bold flex items-center space-x-1.5 mb-1">
                    <ShieldAlert className="h-4 w-4 text-red-400" />
                    <span>Error Description</span>
                  </span>
                  <p className="font-mono text-xs whitespace-pre-wrap">{inspectedExecution.error_message}</p>
                </div>
              )}

              {/* Step Results */}
              <div>
                <span className="font-semibold text-gray-300 uppercase tracking-wider block mb-2">
                  Execution Steps:
                </span>
                <div className="space-y-2">
                  {inspectedExecution.steps.map((st) => (
                    <div
                      key={st.id}
                      className="p-3 bg-gray-950 border border-gray-800 rounded-lg flex items-center justify-between font-mono text-xs"
                    >
                      <div>
                        <span className="text-white font-bold">
                          Step {st.sequence}: {st.action.toUpperCase()}
                        </span>
                        <span className="text-gray-400 ml-2">{st.target}</span>
                        <div className="text-[11px] text-gray-500 font-sans mt-0.5">{st.actual_result}</div>
                      </div>
                      <div className="flex items-center space-x-2">
                        <span className="text-gray-400">{st.duration_ms} ms</span>
                        {getStatusBadge(st.status)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Evidence Artifacts */}
              <div>
                <span className="font-semibold text-gray-300 uppercase tracking-wider block mb-2">
                  Execution Evidence:
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {inspectedExecution.evidence.map((ev) => {
                    if (ev.type === 'screenshot' && ev.file_path) {
                      const cleanPath = ev.file_path.replace(/^\.\//, '').replace(/^artifacts\//, '');
                      const url = `${BACKEND_URL}/artifacts/${cleanPath}`;

                      return (
                        <div key={ev.id} className="p-3 bg-gray-950 border border-gray-800 rounded-xl space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-white">{ev.description || 'Execution Screenshot'}</span>
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
                            <img src={url} alt="Execution Screenshot" className="w-full h-full object-contain" />
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
                              Full CDP snapshot, actions, network waterfall, and console logs.
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
    </div>
  );
};
