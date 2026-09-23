import React, { useEffect, useState } from 'react';
import { applicationsApi, testCasesApi, executionsApi, analysisApi, BACKEND_URL } from '../services/api';
import { Application, TestCase, GeneratedTest, TestExecution } from '../types';
import {
  CheckSquare,
  Filter,
  ArrowRight,
  ShieldAlert,
  Sparkles,
  AlertCircle,
  Play,
  FileCode,
  CheckCircle2,
  XCircle,
  Clock,
  ExternalLink,
  Download,
  Terminal,
  Layers,
  Activity,
  Maximize2,
  Plus,
  RefreshCw
} from 'lucide-react';

interface TestCasesProps {
  initialAppId?: number;
  onSelectApp?: (id: number) => void;
  onNavigate: (tab: string, contextId?: number) => void;
}

export const TestCases: React.FC<TestCasesProps> = ({ initialAppId, onSelectApp, onNavigate }) => {
  const [apps, setApps] = useState<Application[]>([]);
  const [selectedAppId, setSelectedAppId] = useState<number | ''>(initialAppId || '');
  const [testCases, setTestCases] = useState<TestCase[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Standalone generation & creation state
  const [generatingSuite, setGeneratingSuite] = useState(false);
  const [generationMsg, setGenerationMsg] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [creatingCase, setCreatingCase] = useState(false);
  const [newCaseData, setNewCaseData] = useState({
    name: '',
    category: 'functional',
    priority: 'medium',
    description: '',
    preconditions: '',
    action: 'navigate',
    target: 'http://127.0.0.1:3000/login',
    value: '',
    expected_result: 'Page loads successfully'
  });

  // Filters
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedPriority, setSelectedPriority] = useState<string>('all');

  // Executions map: testCaseId -> latest TestExecution
  const [executionsMap, setExecutionsMap] = useState<Record<number, TestExecution>>({});
  const [executingCaseId, setExecutingCaseId] = useState<number | null>(null);
  const [generatingCaseId, setGeneratingCaseId] = useState<number | null>(null);

  // Inspector Modal State
  const [selectedTestCase, setSelectedTestCase] = useState<TestCase | null>(null);
  const [inspectorTab, setInspectorTab] = useState<'steps' | 'code' | 'execution'>('steps');
  const [activeGeneratedTest, setActiveGeneratedTest] = useState<GeneratedTest | null>(null);
  const [activeExecution, setActiveExecution] = useState<TestExecution | null>(null);
  const [codeLoading, setCodeLoading] = useState(false);
  const [modalExecutionLoading, setModalExecutionLoading] = useState(false);
  const [copiedCode, setCopiedCode] = useState(false);

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

  const loadTestCasesAndExecutions = async (appId: number) => {
    if (!appId) {
      setTestCases([]);
      setExecutionsMap({});
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const params: any = {};
      if (selectedCategory !== 'all') params.category = selectedCategory;
      if (selectedPriority !== 'all') params.priority = selectedPriority;

      const [casesRes, execsRes] = await Promise.allSettled([
        testCasesApi.getByApp(appId, params),
        executionsApi.getByApp(appId, 100)
      ]);

      const casesData = casesRes.status === 'fulfilled' ? casesRes.value || [] : [];
      const execsData = execsRes.status === 'fulfilled' ? execsRes.value || [] : [];

      setTestCases(casesData);

      // Build map of latest execution for each test case
      const mapping: Record<number, TestExecution> = {};
      execsData.forEach((exec) => {
        if (!mapping[exec.test_case_id]) {
          mapping[exec.test_case_id] = exec;
        }
      });
      setExecutionsMap(mapping);
    } catch (err: any) {
      console.error(err);
      setError('Failed to load test cases and executions.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedAppId) {
      loadTestCasesAndExecutions(Number(selectedAppId));
    }
  }, [selectedAppId, selectedCategory, selectedPriority]);

  // Open modal and load latest generated code / execution
  const handleInspect = async (tc: TestCase, defaultTab: 'steps' | 'code' | 'execution' = 'steps') => {
    setSelectedTestCase(tc);
    setInspectorTab(defaultTab);
    setActiveGeneratedTest(null);
    setActiveExecution(executionsMap[tc.id] || null);

    try {
      setCodeLoading(true);
      const gen = await testCasesApi.getGeneratedTest(tc.id);
      setActiveGeneratedTest(gen);
    } catch {
      setActiveGeneratedTest(null);
    } finally {
      setCodeLoading(false);
    }

    if (executionsMap[tc.id]) {
      try {
        const fullExec = await executionsApi.getById(executionsMap[tc.id].id);
        setActiveExecution(fullExec);
      } catch {
        // Fallback to cached summary
      }
    }
  };

  // Generate test handler
  const handleGenerateCode = async (testCaseId: number) => {
    try {
      setGeneratingCaseId(testCaseId);
      const gen = await testCasesApi.generateTest(testCaseId);
      if (selectedTestCase?.id === testCaseId) {
        setActiveGeneratedTest(gen);
      }
    } catch (err: any) {
      alert(`Generation failed: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setGeneratingCaseId(null);
    }
  };

  // Real Playwright execution handler
  const handleExecuteTest = async (testCaseId: number) => {
    try {
      setExecutingCaseId(testCaseId);
      setModalExecutionLoading(true);
      const execution = await executionsApi.execute(testCaseId);
      
      // Update executions map
      setExecutionsMap((prev) => ({
        ...prev,
        [testCaseId]: execution
      }));

      if (selectedTestCase?.id === testCaseId) {
        setActiveExecution(execution);
        setInspectorTab('execution');
      }
    } catch (err: any) {
      alert(`Execution failed: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setExecutingCaseId(null);
      setModalExecutionLoading(false);
    }
  };

  const handleGenerateSuite = async () => {
    if (!selectedAppId) return;
    try {
      setGeneratingSuite(true);
      setGenerationMsg('Initiating AI test case generation...');
      setError(null);
      await testCasesApi.generateTestsForApp(Number(selectedAppId));

      const interval = setInterval(async () => {
        try {
          const statusData = await analysisApi.getStatus(Number(selectedAppId));
          setGenerationMsg(statusData.stage || 'Generating tests with AI...');
          if (statusData.status === 'COMPLETED' || statusData.status === 'FAILED') {
            clearInterval(interval);
            setGeneratingSuite(false);
            setGenerationMsg(null);
            loadTestCasesAndExecutions(Number(selectedAppId));
          }
        } catch {
          clearInterval(interval);
          setGeneratingSuite(false);
          setGenerationMsg(null);
        }
      }, 2000);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Failed to generate test cases.');
      setGeneratingSuite(false);
      setGenerationMsg(null);
    }
  };

  const handleCreateCustomTestCase = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAppId) return;
    try {
      setCreatingCase(true);
      const preconditionsList = newCaseData.preconditions
        ? newCaseData.preconditions.split('\n').map(s => s.trim()).filter(Boolean)
        : [];
      const payload = {
        name: newCaseData.name,
        category: newCaseData.category,
        priority: newCaseData.priority,
        description: newCaseData.description,
        preconditions: preconditionsList,
        steps: [
          {
            sequence: 1,
            action: newCaseData.action,
            target: newCaseData.target,
            value: newCaseData.value || null,
            expected_result: newCaseData.expected_result
          }
        ]
      };
      await testCasesApi.createTestCase(Number(selectedAppId), payload);
      setShowCreateModal(false);
      setNewCaseData({
        name: '',
        category: 'functional',
        priority: 'medium',
        description: '',
        preconditions: '',
        action: 'navigate',
        target: 'http://127.0.0.1:3000/login',
        value: '',
        expected_result: 'Page loads successfully'
      });
      loadTestCasesAndExecutions(Number(selectedAppId));
    } catch (err: any) {
      alert(`Failed to create test case: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setCreatingCase(false);
    }
  };

  const getPriorityBadge = (priority: string) => {
    switch (priority.toLowerCase()) {
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

  const getCategoryBadge = (category: string) => {
    switch (category.toLowerCase()) {
      case 'smoke':
        return 'bg-emerald-950 text-emerald-300 border border-emerald-800';
      case 'negative':
        return 'bg-rose-950 text-rose-300 border border-rose-800';
      case 'boundary':
        return 'bg-purple-950 text-purple-300 border border-purple-800';
      case 'form validation':
        return 'bg-cyan-950 text-cyan-300 border border-cyan-800';
      default:
        return 'bg-gray-800 text-gray-300 border border-gray-700';
    }
  };

  const getStatusBadge = (status?: string) => {
    if (!status) {
      return (
        <span className="px-2 py-0.5 text-xs text-gray-400 bg-gray-800/80 border border-gray-700 rounded inline-flex items-center space-x-1">
          <span>Not Executed</span>
        </span>
      );
    }
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
            <h1 className="text-2xl font-bold text-white tracking-tight">Structured Test Cases</h1>
            <span className="px-2 py-0.5 text-xs font-bold bg-emerald-950 text-emerald-400 border border-emerald-800 rounded">
              Phase 3 • Playwright Engine
            </span>
          </div>
          <p className="text-sm text-gray-400 mt-1">
            Generate and execute real Playwright tests against target application. Real browser CDP execution with trace and screenshots.
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
            onClick={handleGenerateSuite}
            disabled={generatingSuite || !selectedAppId}
            className="flex items-center space-x-1.5 px-3 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold shadow transition"
          >
            <Sparkles className={`h-3.5 w-3.5 ${generatingSuite ? 'animate-spin' : ''}`} />
            <span>{generatingSuite ? 'Generating...' : 'Generate AI Tests'}</span>
          </button>

          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center space-x-1.5 px-3 py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-700 rounded-lg text-xs font-medium transition"
          >
            <Plus className="h-3.5 w-3.5 text-emerald-400" />
            <span>New Test Case</span>
          </button>

          <button
            onClick={() => onNavigate('executions', Number(selectedAppId))}
            className="flex items-center space-x-1.5 px-3 py-2 bg-emerald-900/40 hover:bg-emerald-900/70 text-emerald-400 border border-emerald-500/30 rounded-lg text-xs font-medium transition"
          >
            <Activity className="h-3.5 w-3.5" />
            <span>Executions</span>
          </button>
        </div>
      </div>

      {generatingSuite && (
        <div className="p-4 bg-emerald-950/60 border border-emerald-700 rounded-xl text-emerald-300 text-sm flex items-center space-x-3 animate-pulse">
          <Sparkles className="h-5 w-5 text-emerald-400 animate-spin" />
          <span>{generationMsg || 'AI is synthesizing test cases from application pages and workflows...'}</span>
        </div>
      )}

      {error && (
        <div className="p-4 bg-red-950/50 border border-red-800 rounded-lg text-red-300 text-sm flex items-center space-x-2">
          <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Filter Bar */}
      <div className="bg-gray-900 border border-gray-800 p-4 rounded-xl flex flex-wrap items-center justify-between gap-4 text-xs">
        <div className="flex items-center space-x-2">
          <span className="text-gray-400 font-medium flex items-center space-x-1">
            <Filter className="h-3.5 w-3.5" />
            <span>Category:</span>
          </span>
          {['all', 'smoke', 'functional', 'negative', 'boundary', 'form validation'].map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-2.5 py-1 rounded capitalize transition ${
                selectedCategory === cat
                  ? 'bg-emerald-600 text-white font-medium'
                  : 'bg-gray-800 text-gray-400 hover:text-white'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        <div className="flex items-center space-x-2">
          <span className="text-gray-400 font-medium">Priority:</span>
          {['all', 'critical', 'high', 'medium', 'low'].map((prio) => (
            <button
              key={prio}
              onClick={() => setSelectedPriority(prio)}
              className={`px-2.5 py-1 rounded capitalize transition ${
                selectedPriority === prio
                  ? 'bg-emerald-600 text-white font-medium'
                  : 'bg-gray-800 text-gray-400 hover:text-white'
              }`}
            >
              {prio}
            </button>
          ))}
        </div>
      </div>

      {/* Test Cases Table */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between">
          <h2 className="text-base font-semibold text-white">Generated Test Cases</h2>
          <span className="text-xs text-gray-400">{testCases.length} Test Scenarios</span>
        </div>

        {loading ? (
          <div className="p-12 text-center text-gray-400 text-sm">Loading test cases...</div>
        ) : testCases.length === 0 ? (
          <div className="p-12 text-center text-gray-500 space-y-4">
            <CheckSquare className="h-10 w-10 mx-auto text-gray-600" />
            <div>
              <p className="text-sm text-gray-200 font-semibold">No test cases generated yet for this application.</p>
              <p className="text-xs text-gray-400 mt-1 max-w-md mx-auto">
                Generate automated Playwright tests with AI directly or create a custom manual test scenario.
              </p>
            </div>
            <div className="flex items-center justify-center space-x-3 pt-2">
              <button
                onClick={handleGenerateSuite}
                disabled={generatingSuite || !selectedAppId}
                className="flex items-center space-x-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-semibold rounded-lg shadow transition"
              >
                <Sparkles className={`h-4 w-4 ${generatingSuite ? 'animate-spin' : ''}`} />
                <span>{generatingSuite ? 'Synthesizing Tests...' : 'Generate AI Test Cases'}</span>
              </button>
              <button
                onClick={() => setShowCreateModal(true)}
                className="flex items-center space-x-1.5 px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 text-xs font-medium rounded-lg border border-gray-700 transition"
              >
                <Plus className="h-4 w-4 text-emerald-400" />
                <span>Create Manual Test Case</span>
              </button>
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-gray-300">
              <thead className="bg-gray-800/50 text-xs uppercase text-gray-400">
                <tr>
                  <th className="px-4 py-3">Test ID</th>
                  <th className="px-4 py-3">Name & Category</th>
                  <th className="px-4 py-3">Priority</th>
                  <th className="px-4 py-3">Execution Status</th>
                  <th className="px-4 py-3">Duration</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {testCases.map((tc, idx) => {
                  const exec = executionsMap[tc.id];
                  const isExecuting = executingCaseId === tc.id;
                  const isGenerating = generatingCaseId === tc.id;

                  return (
                    <tr key={tc.id} className="hover:bg-gray-800/30 transition">
                      <td className="px-4 py-4 font-mono font-medium text-emerald-400">
                        TC-{String(idx + 1).padStart(3, '0')}
                      </td>
                      <td className="px-4 py-4 max-w-xs">
                        <div className="font-medium text-white truncate">{tc.name}</div>
                        <div className="flex items-center space-x-2 mt-1">
                          <span className={`px-2 py-0.2 text-[10px] uppercase font-bold rounded ${getCategoryBadge(tc.category)}`}>
                            {tc.category}
                          </span>
                          <span className="text-xs text-gray-500">{tc.steps_count || tc.steps.length} steps</span>
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        <span className={`px-2 py-0.5 text-xs uppercase font-bold rounded ${getPriorityBadge(tc.priority)}`}>
                          {tc.priority}
                        </span>
                      </td>
                      <td className="px-4 py-4">
                        {isExecuting ? (
                          <span className="px-2 py-0.5 text-xs font-bold text-blue-400 bg-blue-950/80 border border-blue-800 rounded inline-flex items-center space-x-1 animate-pulse">
                            <Activity className="h-3 w-3 animate-spin" />
                            <span>Running Playwright...</span>
                          </span>
                        ) : (
                          getStatusBadge(exec?.status)
                        )}
                      </td>
                      <td className="px-4 py-4 text-xs font-mono text-gray-400">
                        {exec?.duration_ms ? `${exec.duration_ms} ms` : '—'}
                      </td>
                      <td className="px-4 py-4 text-right">
                        <div className="flex items-center justify-end space-x-2">
                          <button
                            onClick={() => handleGenerateCode(tc.id)}
                            disabled={isGenerating}
                            className="px-2.5 py-1 bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white rounded text-xs font-medium transition flex items-center space-x-1 border border-gray-700 disabled:opacity-50"
                            title="Generate Playwright Script"
                          >
                            <FileCode className="h-3.5 w-3.5 text-blue-400" />
                            <span>{isGenerating ? 'Generating...' : 'Script'}</span>
                          </button>

                          <button
                            onClick={() => handleExecuteTest(tc.id)}
                            disabled={isExecuting}
                            className="px-3 py-1 bg-emerald-700 hover:bg-emerald-600 text-white rounded text-xs font-semibold transition flex items-center space-x-1 disabled:opacity-50 shadow-sm"
                            title="Execute Test in Real Playwright Browser"
                          >
                            <Play className="h-3.5 w-3.5 fill-current" />
                            <span>{isExecuting ? 'Running...' : 'Execute'}</span>
                          </button>

                          <button
                            onClick={() => handleInspect(tc, exec ? 'execution' : 'steps')}
                            className="px-2.5 py-1 bg-gray-800 hover:bg-gray-700 text-emerald-400 rounded text-xs font-medium transition border border-gray-700"
                          >
                            Inspect
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
      </div>

      {/* Test Case Inspection Modal */}
      {selectedTestCase && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
            {/* Modal Header */}
            <div className="p-5 border-b border-gray-800 flex items-start justify-between bg-gray-950/60">
              <div>
                <div className="flex items-center space-x-2">
                  <h3 className="text-lg font-bold text-white">{selectedTestCase.name}</h3>
                  <span className={`px-2 py-0.5 text-xs uppercase font-bold rounded ${getCategoryBadge(selectedTestCase.category)}`}>
                    {selectedTestCase.category}
                  </span>
                  <span className={`px-2 py-0.5 text-xs uppercase font-bold rounded ${getPriorityBadge(selectedTestCase.priority)}`}>
                    {selectedTestCase.priority}
                  </span>
                </div>
                <p className="text-xs text-gray-400 mt-1">{selectedTestCase.description}</p>
              </div>

              <div className="flex items-center space-x-3">
                <button
                  onClick={() => handleExecuteTest(selectedTestCase.id)}
                  disabled={modalExecutionLoading}
                  className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition disabled:opacity-50 shadow"
                >
                  <Play className="h-3.5 w-3.5 fill-current" />
                  <span>{modalExecutionLoading ? 'Executing...' : 'Run Test Now'}</span>
                </button>

                <button
                  onClick={() => setSelectedTestCase(null)}
                  className="text-gray-400 hover:text-white text-xs px-2.5 py-1.5 bg-gray-800 rounded-lg hover:bg-gray-700 transition"
                >
                  Close
                </button>
              </div>
            </div>

            {/* Navigation Tabs */}
            <div className="flex border-b border-gray-800 bg-gray-950 px-5 space-x-4 text-xs font-medium">
              <button
                onClick={() => setInspectorTab('steps')}
                className={`py-3 border-b-2 transition flex items-center space-x-1.5 ${
                  inspectorTab === 'steps'
                    ? 'border-emerald-500 text-emerald-400'
                    : 'border-transparent text-gray-400 hover:text-white'
                }`}
              >
                <CheckSquare className="h-3.5 w-3.5" />
                <span>Test Steps ({selectedTestCase.steps.length})</span>
              </button>

              <button
                onClick={() => setInspectorTab('code')}
                className={`py-3 border-b-2 transition flex items-center space-x-1.5 ${
                  inspectorTab === 'code'
                    ? 'border-emerald-500 text-emerald-400'
                    : 'border-transparent text-gray-400 hover:text-white'
                }`}
              >
                <FileCode className="h-3.5 w-3.5" />
                <span>Generated Playwright Code</span>
              </button>

              <button
                onClick={() => setInspectorTab('execution')}
                className={`py-3 border-b-2 transition flex items-center space-x-1.5 ${
                  inspectorTab === 'execution'
                    ? 'border-emerald-500 text-emerald-400'
                    : 'border-transparent text-gray-400 hover:text-white'
                }`}
              >
                <Activity className="h-3.5 w-3.5" />
                <span>Execution & Evidence</span>
                {activeExecution && (
                  <span className="ml-1.5">{getStatusBadge(activeExecution.status)}</span>
                )}
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-5 overflow-y-auto flex-1 space-y-4 text-xs bg-gray-900">
              {/* TAB 1: STEPS */}
              {inspectorTab === 'steps' && (
                <div className="space-y-4">
                  {selectedTestCase.preconditions && selectedTestCase.preconditions.length > 0 && (
                    <div className="p-3 bg-gray-950 border border-gray-800 rounded-lg">
                      <span className="font-semibold text-gray-300 block mb-1">Preconditions:</span>
                      <ul className="list-disc list-inside text-gray-400 space-y-0.5">
                        {selectedTestCase.preconditions.map((p, i) => (
                          <li key={i}>{p}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div className="space-y-2">
                    <span className="font-semibold text-gray-300 uppercase tracking-wider block mb-2">
                      Ordered Execution Steps:
                    </span>
                    {selectedTestCase.steps.map((step) => (
                      <div key={step.id} className="p-3 bg-gray-950 border border-gray-800 rounded-lg space-y-1 font-mono">
                        <div className="flex items-center justify-between">
                          <span className="text-emerald-400 font-bold">Step {step.sequence}: {step.action.toUpperCase()}</span>
                          <span className="text-gray-400 text-xs truncate max-w-sm">{step.target}</span>
                        </div>
                        {step.value && (
                          <div className="text-gray-300">Value: <span className="text-amber-300">"{step.value}"</span></div>
                        )}
                        <div className="text-gray-400 font-sans mt-1">
                          Expected Outcome: <span className="text-gray-200">{step.expected_result}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* TAB 2: GENERATED PLAYWRIGHT CODE */}
              {inspectorTab === 'code' && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between bg-gray-950 p-3 rounded-lg border border-gray-800">
                    <div>
                      <span className="font-semibold text-white">Target Script: </span>
                      <span className="font-mono text-emerald-400">
                        {activeGeneratedTest ? activeGeneratedTest.file_path : 'Not generated yet'}
                      </span>
                      {activeGeneratedTest && (
                        <span className="ml-2 px-2 py-0.5 bg-gray-800 text-gray-300 rounded text-[10px]">
                          v{activeGeneratedTest.generation_version}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center space-x-2">
                      {activeGeneratedTest && (
                        <button
                          onClick={() => {
                            navigator.clipboard.writeText(activeGeneratedTest.generated_code);
                            setCopiedCode(true);
                            setTimeout(() => setCopiedCode(false), 2000);
                          }}
                          className="px-2.5 py-1 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded text-xs transition"
                        >
                          {copiedCode ? 'Copied!' : 'Copy Code'}
                        </button>
                      )}
                      <button
                        onClick={() => handleGenerateCode(selectedTestCase.id)}
                        disabled={generatingCaseId === selectedTestCase.id}
                        className="px-2.5 py-1 bg-blue-900/50 hover:bg-blue-800 text-blue-300 rounded text-xs transition border border-blue-700 disabled:opacity-50"
                      >
                        {generatingCaseId === selectedTestCase.id ? 'Generating...' : 'Re-Generate Script'}
                      </button>
                    </div>
                  </div>

                  {codeLoading ? (
                    <div className="p-8 text-center text-gray-400">Loading generated code...</div>
                  ) : activeGeneratedTest ? (
                    <pre className="p-4 bg-gray-950 rounded-lg border border-gray-800 text-gray-300 font-mono text-xs overflow-x-auto leading-relaxed">
                      <code>{activeGeneratedTest.generated_code}</code>
                    </pre>
                  ) : (
                    <div className="p-8 text-center text-gray-500 space-y-3 bg-gray-950 rounded-lg border border-gray-800">
                      <FileCode className="h-8 w-8 mx-auto text-gray-600" />
                      <p>Playwright code has not been generated for this test case yet.</p>
                      <button
                        onClick={() => handleGenerateCode(selectedTestCase.id)}
                        className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold transition"
                      >
                        Generate Script Now
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* TAB 3: EXECUTION & EVIDENCE */}
              {inspectorTab === 'execution' && (
                <div className="space-y-4">
                  {modalExecutionLoading ? (
                    <div className="p-12 text-center space-y-3 bg-gray-950 rounded-lg border border-gray-800">
                      <Activity className="h-8 w-8 mx-auto text-emerald-400 animate-spin" />
                      <p className="text-sm font-semibold text-white">Executing test in real Playwright browser...</p>
                      <p className="text-xs text-gray-400">Navigating to target application, capturing traces and DOM state.</p>
                    </div>
                  ) : !activeExecution ? (
                    <div className="p-12 text-center text-gray-500 space-y-3 bg-gray-950 rounded-lg border border-gray-800">
                      <Terminal className="h-8 w-8 mx-auto text-gray-600" />
                      <p>No execution recorded for this test case yet.</p>
                      <button
                        onClick={() => handleExecuteTest(selectedTestCase.id)}
                        className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold transition"
                      >
                        Execute in Playwright Now
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {/* Summary Banner */}
                      <div className="p-4 bg-gray-950 border border-gray-800 rounded-xl grid grid-cols-2 sm:grid-cols-4 gap-4">
                        <div>
                          <span className="text-gray-500 block text-[11px]">Outcome</span>
                          <div className="mt-1">{getStatusBadge(activeExecution.status)}</div>
                        </div>
                        <div>
                          <span className="text-gray-500 block text-[11px]">Duration</span>
                          <span className="font-mono text-sm text-white font-bold">
                            {activeExecution.duration_ms} ms
                          </span>
                        </div>
                        <div>
                          <span className="text-gray-500 block text-[11px]">Final Target URL</span>
                          <span className="text-xs text-gray-300 truncate block font-mono">
                            {activeExecution.final_url || '—'}
                          </span>
                        </div>
                        <div>
                          <span className="text-gray-500 block text-[11px]">Executed At</span>
                          <span className="text-xs text-gray-300">
                            {new Date(activeExecution.created_at).toLocaleTimeString()}
                          </span>
                        </div>
                      </div>

                      {/* Error Message if Failed */}
                      {activeExecution.error_message && (
                        <div className="p-4 bg-red-950/50 border border-red-800 rounded-xl text-red-300 space-y-1">
                          <span className="font-bold flex items-center space-x-1.5">
                            <ShieldAlert className="h-4 w-4 text-red-400" />
                            <span>Failure Diagnostics</span>
                          </span>
                          <p className="font-mono text-xs text-red-200 mt-1 whitespace-pre-wrap">
                            {activeExecution.error_message}
                          </p>
                        </div>
                      )}

                      {/* Step Execution Breakdown */}
                      <div>
                        <span className="font-semibold text-gray-300 uppercase tracking-wider block mb-2">
                          Step-by-Step Playwright Execution:
                        </span>
                        <div className="space-y-2">
                          {activeExecution.steps.map((st) => (
                            <div
                              key={st.id}
                              className={`p-3 rounded-lg border font-mono text-xs flex items-center justify-between ${
                                st.status === 'passed'
                                  ? 'bg-emerald-950/20 border-emerald-800/40 text-gray-300'
                                  : st.status === 'failed'
                                  ? 'bg-red-950/30 border-red-800 text-red-200'
                                  : 'bg-gray-950 border-gray-800 text-gray-500'
                              }`}
                            >
                              <div className="space-y-0.5">
                                <div className="flex items-center space-x-2">
                                  <span className="font-bold text-white">
                                    Step {st.sequence}: {st.action.toUpperCase()}
                                  </span>
                                  <span className="text-gray-400 truncate max-w-sm">{st.target}</span>
                                </div>
                                <div className="text-gray-400 font-sans text-[11px]">
                                  {st.actual_result}
                                </div>
                              </div>
                              <div className="text-right flex items-center space-x-3">
                                {st.duration_ms !== undefined && st.duration_ms !== null && (
                                  <span className="text-gray-400 text-[11px]">{st.duration_ms} ms</span>
                                )}
                                <div>{getStatusBadge(st.status)}</div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Evidence Files: Screenshots & Traces */}
                      <div>
                        <span className="font-semibold text-gray-300 uppercase tracking-wider block mb-2">
                          Real Captured Evidence:
                        </span>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                          {activeExecution.evidence.map((ev) => {
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
                                    <img
                                      src={url}
                                      alt="Playwright Execution"
                                      className="w-full h-full object-contain"
                                      onError={(e) => {
                                        (e.target as HTMLImageElement).alt = 'Screenshot rendered on local disk';
                                      }}
                                    />
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
                                      Contains step snapshots, action timings, and DOM snapshots.
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
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Create Manual Test Case Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl w-full max-w-lg p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-gray-800">
              <h2 className="text-lg font-bold text-white flex items-center space-x-2">
                <Plus className="h-5 w-5 text-emerald-400" />
                <span>Create Manual Test Case</span>
              </h2>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-gray-400 hover:text-white text-xs px-2 py-1 rounded bg-gray-800"
              >
                Close
              </button>
            </div>

            <form onSubmit={handleCreateCustomTestCase} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-300 uppercase mb-1">
                  Test Case Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. TC-005 Product Form Validation"
                  value={newCaseData.name}
                  onChange={(e) => setNewCaseData({ ...newCaseData, name: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-300 uppercase mb-1">
                    Category
                  </label>
                  <select
                    value={newCaseData.category}
                    onChange={(e) => setNewCaseData({ ...newCaseData, category: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
                  >
                    <option value="smoke">Smoke</option>
                    <option value="functional">Functional</option>
                    <option value="boundary">Boundary</option>
                    <option value="negative">Negative</option>
                    <option value="form validation">Form Validation</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-300 uppercase mb-1">
                    Priority
                  </label>
                  <select
                    value={newCaseData.priority}
                    onChange={(e) => setNewCaseData({ ...newCaseData, priority: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
                  >
                    <option value="critical">Critical</option>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300 uppercase mb-1">
                  Description
                </label>
                <input
                  type="text"
                  placeholder="Validate user interactions on target form"
                  value={newCaseData.description}
                  onChange={(e) => setNewCaseData({ ...newCaseData, description: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="p-3 bg-gray-950 border border-gray-800 rounded-lg space-y-3">
                <span className="text-xs font-semibold text-emerald-400 uppercase">Initial Step #1</span>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-[11px] text-gray-400 mb-1">Action</label>
                    <select
                      value={newCaseData.action}
                      onChange={(e) => setNewCaseData({ ...newCaseData, action: e.target.value })}
                      className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-xs text-white"
                    >
                      <option value="navigate">NAVIGATE</option>
                      <option value="click">CLICK</option>
                      <option value="fill">FILL</option>
                      <option value="assert">ASSERT</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-[11px] text-gray-400 mb-1">Target (URL or Selector)</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. #submit-btn or http://127.0.0.1:3000"
                      value={newCaseData.target}
                      onChange={(e) => setNewCaseData({ ...newCaseData, target: e.target.value })}
                      className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-xs text-white font-mono"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-[11px] text-gray-400 mb-1">Expected Result *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Page loads successfully with HTTP 200"
                    value={newCaseData.expected_result}
                    onChange={(e) => setNewCaseData({ ...newCaseData, expected_result: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-xs text-white"
                  />
                </div>
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
                  disabled={creatingCase}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-semibold rounded-lg shadow"
                >
                  {creatingCase ? 'Creating...' : 'Save & Add Test Case'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
