import React, { useEffect, useState } from 'react';
import {
  applicationsApi,
  databaseQaApi
} from '../services/api';
import {
  Application,
  DatabaseConnection,
  DatabaseSchema,
  DatabaseTable,
  DatabaseTestCase,
  DatabaseTestExecution,
  DatabaseSummary,
  DatabaseTestCategory
} from '../types';
import {
  Database,
  Table as TableIcon,
  Key,
  Link2,
  ShieldCheck,
  ShieldAlert,
  Play,
  RefreshCw,
  Plus,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  FileText,
  Layers,
  Search,
  ExternalLink,
  Eye,
  Code,
  Sparkles,
  Server,
  Lock,
  ArrowRight,
  Activity
} from 'lucide-react';

interface DatabaseQAProps {
  initialAppId?: number;
  onSelectApp?: (id: number) => void;
  onNavigate: (tab: string, contextId?: number) => void;
}

export const DatabaseQA: React.FC<DatabaseQAProps> = ({
  initialAppId,
  onSelectApp,
  onNavigate
}) => {
  const [apps, setApps] = useState<Application[]>([]);
  const [selectedAppId, setSelectedAppId] = useState<number | ''>(initialAppId || '');
  const [connections, setConnections] = useState<DatabaseConnection[]>([]);
  const [selectedConnection, setSelectedConnection] = useState<DatabaseConnection | null>(null);
  const [summary, setSummary] = useState<DatabaseSummary | null>(null);
  const [schemas, setSchemas] = useState<DatabaseSchema[]>([]);
  const [selectedTable, setSelectedTable] = useState<DatabaseTable | null>(null);
  const [testCases, setTestCases] = useState<DatabaseTestCase[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');

  // Execution states
  const [executingAll, setExecutingAll] = useState(false);
  const [runningTestId, setRunningTestId] = useState<number | null>(null);
  const [activeExecution, setActiveExecution] = useState<DatabaseTestExecution | null>(null);
  const [testExecutionsMap, setTestExecutionsMap] = useState<Record<number, DatabaseTestExecution>>({});

  // Discovery & Test Connection states
  const [testingConn, setTestingConn] = useState(false);
  const [testConnMessage, setTestConnMessage] = useState<{ status: string; message: string } | null>(null);
  const [discovering, setDiscovering] = useState(false);
  const [generatingTests, setGeneratingTests] = useState(false);

  // New Connection Modal
  const [showNewConnModal, setShowNewConnModal] = useState(false);
  const [newConnData, setNewConnData] = useState({
    name: 'CRM Development Database',
    database_type: 'sqlite' as 'sqlite' | 'postgresql' | 'mysql',
    database_name: 'test-app/crm_development.db',
    host: 'localhost',
    port: 5432,
    username: '',
    password: '',
    read_only: true
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initialAppId) {
      setSelectedAppId(initialAppId);
    }
  }, [initialAppId]);

  // Load applications
  useEffect(() => {
    const loadApps = async () => {
      try {
        const data = await applicationsApi.getAll();
        setApps(data);
        if (data.length > 0 && !selectedAppId) {
          const pref = data.find(a => a.id === 2) || data[0];
          setSelectedAppId(pref.id);
          onSelectApp?.(pref.id);
        }
      } catch (err: any) {
        console.error('Error loading apps:', err);
        setError('Failed to load applications.');
      }
    };
    loadApps();
  }, []);

  // Load connections when app changes
  useEffect(() => {
    if (!selectedAppId) return;

    const loadConnections = async () => {
      setLoading(true);
      setError(null);
      try {
        const conns = await databaseQaApi.getConnections(Number(selectedAppId));
        setConnections(conns);
        if (conns.length > 0) {
          setSelectedConnection(conns[0]);
        } else {
          setSelectedConnection(null);
          setSchemas([]);
          setSummary(null);
          setTestCases([]);
        }
      } catch (err: any) {
        console.error('Error loading connections:', err);
        setError('Failed to load database connections.');
      } finally {
        setLoading(false);
      }
    };
    loadConnections();
  }, [selectedAppId]);

  // Load schemas, summary, and test cases when connection changes
  useEffect(() => {
    if (!selectedConnection) return;

    const loadConnectionData = async () => {
      try {
        const [sum, scs, tcs] = await Promise.all([
          databaseQaApi.getSummary(selectedConnection.id).catch(() => null),
          databaseQaApi.getSchemas(selectedConnection.id).catch(() => []),
          databaseQaApi.getTestCases(Number(selectedAppId)).catch(() => [])
        ]);

        setSummary(sum);
        setSchemas(scs);
        setTestCases(tcs);

        if (scs.length > 0 && scs[0].tables.length > 0) {
          setSelectedTable(scs[0].tables[0]);
        } else {
          setSelectedTable(null);
        }

        // Preload recent execution for test cases
        const execMap: Record<number, DatabaseTestExecution> = {};
        for (const tc of tcs.slice(0, 15)) {
          try {
            const execs = await databaseQaApi.getTestCaseExecutions(tc.id, 1);
            if (execs.length > 0) {
              execMap[tc.id] = execs[0];
            }
          } catch (e) {
            // ignore
          }
        }
        setTestExecutionsMap(execMap);
      } catch (err: any) {
        console.error('Error loading connection data:', err);
      }
    };
    loadConnectionData();
  }, [selectedConnection]);

  // Handle Test Connection
  const handleTestConnection = async () => {
    if (!selectedConnection) return;
    setTestingConn(true);
    setTestConnMessage(null);
    try {
      const res = await databaseQaApi.testExistingConnection(selectedConnection.id);
      setTestConnMessage(res);
      // Refresh connection
      const conns = await databaseQaApi.getConnections(Number(selectedAppId));
      setConnections(conns);
      const updated = conns.find(c => c.id === selectedConnection.id);
      if (updated) setSelectedConnection(updated);
    } catch (err: any) {
      setTestConnMessage({
        status: 'FAILED',
        message: err.response?.data?.detail || err.message || 'Connection test failed'
      });
    } finally {
      setTestingConn(false);
    }
  };

  // Handle Schema Discovery
  const handleDiscoverSchema = async () => {
    if (!selectedConnection) return;
    setDiscovering(true);
    setError(null);
    try {
      const discovered = await databaseQaApi.discoverSchema(selectedConnection.id);
      setSchemas(discovered);
      if (discovered.length > 0 && discovered[0].tables.length > 0) {
        setSelectedTable(discovered[0].tables[0]);
      }
      const sum = await databaseQaApi.getSummary(selectedConnection.id);
      setSummary(sum);
    } catch (err: any) {
      console.error('Error discovering schema:', err);
      setError(err.response?.data?.detail || 'Failed to discover schema.');
    } finally {
      setDiscovering(false);
    }
  };

  // Handle Generate Tests
  const handleGenerateTests = async () => {
    if (!selectedConnection || !selectedAppId) return;
    setGeneratingTests(true);
    setError(null);
    try {
      const gen = await databaseQaApi.generateTestCases(Number(selectedAppId), selectedConnection.id);
      const allTests = await databaseQaApi.getTestCases(Number(selectedAppId));
      setTestCases(allTests);
      const sum = await databaseQaApi.getSummary(selectedConnection.id);
      setSummary(sum);
    } catch (err: any) {
      console.error('Error generating tests:', err);
      setError(err.response?.data?.detail || 'Failed to generate database test cases.');
    } finally {
      setGeneratingTests(false);
    }
  };

  // Execute Single Test
  const handleRunTest = async (testCaseId: number) => {
    setRunningTestId(testCaseId);
    try {
      const exec = await databaseQaApi.executeTestCase(testCaseId);
      setTestExecutionsMap(prev => ({ ...prev, [testCaseId]: exec }));
      setActiveExecution(exec);
      if (selectedConnection) {
        const sum = await databaseQaApi.getSummary(selectedConnection.id);
        setSummary(sum);
      }
    } catch (err: any) {
      console.error('Error running test:', err);
      setError(err.response?.data?.detail || 'Failed to execute database test case.');
    } finally {
      setRunningTestId(null);
    }
  };

  // Execute All Tests
  const handleRunAllTests = async () => {
    if (!selectedAppId || !selectedConnection) return;
    setExecutingAll(true);
    setError(null);
    try {
      const results = await databaseQaApi.executeAllTestCases(Number(selectedAppId), selectedConnection.id);
      const newMap: Record<number, DatabaseTestExecution> = { ...testExecutionsMap };
      for (const res of results) {
        newMap[res.database_test_case_id] = res;
      }
      setTestExecutionsMap(newMap);
      if (results.length > 0) {
        setActiveExecution(results[0]);
      }
      const sum = await databaseQaApi.getSummary(selectedConnection.id);
      setSummary(sum);
    } catch (err: any) {
      console.error('Error running all tests:', err);
      setError(err.response?.data?.detail || 'Failed to execute database test suite.');
    } finally {
      setExecutingAll(false);
    }
  };

  // Handle Create Connection Submit
  const handleCreateConnection = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAppId) return;
    try {
      const created = await databaseQaApi.createConnection(Number(selectedAppId), newConnData);
      setConnections(prev => [...prev, created]);
      setSelectedConnection(created);
      setShowNewConnModal(false);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to create database connection');
    }
  };

  const filteredTestCases = testCases.filter(tc => {
    if (selectedCategory === 'ALL') return true;
    return tc.category === selectedCategory;
  });

  return (
    <div className="space-y-6">
      {/* Header & App Selector */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gray-900/60 p-6 rounded-xl border border-gray-800 backdrop-blur-sm">
        <div>
          <div className="flex items-center space-x-3">
            <div className="p-2.5 bg-blue-500/10 rounded-lg border border-blue-500/30">
              <Database className="h-6 w-6 text-blue-400" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-2xl font-bold text-white tracking-tight">Database QA & Data Integrity</h1>
              </div>
              <p className="text-gray-400 text-sm mt-0.5">
                Safe read-only target schema discovery, data integrity assertions, referential audits & defect isolation.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <label className="text-xs text-gray-400 font-medium">Target App:</label>
          <select
            value={selectedAppId}
            onChange={(e) => {
              const id = Number(e.target.value);
              setSelectedAppId(id);
              onSelectApp?.(id);
            }}
            className="bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
          >
            {apps.map((a) => (
              <option key={a.id} value={a.id}>
                #{a.id} {a.name}
              </option>
            ))}
          </select>
          <button
            onClick={() => setShowNewConnModal(true)}
            className="flex items-center space-x-1.5 px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition"
          >
            <Plus className="h-4 w-4" />
            <span>Add Connection</span>
          </button>
        </div>
      </div>

      {/* Connection & Security Guardrail Banner */}
      {selectedConnection ? (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 shadow-lg">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
            <div className="flex items-start sm:items-center space-x-4">
              <div className="p-3 bg-gray-800 rounded-lg border border-gray-700">
                <Server className="h-5 w-5 text-gray-300" />
              </div>
              <div>
                <div className="flex items-center space-x-2 flex-wrap gap-y-1">
                  <span className="font-semibold text-white text-base">{selectedConnection.name}</span>
                  <span className="text-xs px-2 py-0.5 bg-gray-800 text-gray-300 border border-gray-700 rounded uppercase font-mono">
                    {selectedConnection.database_type}
                  </span>
                  <span className={`text-xs px-2 py-0.5 rounded font-mono font-semibold flex items-center space-x-1 ${
                    selectedConnection.status === 'CONNECTED'
                      ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                      : 'bg-rose-950 text-rose-400 border border-rose-800'
                  }`}>
                    {selectedConnection.status === 'CONNECTED' ? (
                      <CheckCircle2 className="h-3 w-3 inline mr-1" />
                    ) : (
                      <XCircle className="h-3 w-3 inline mr-1" />
                    )}
                    {selectedConnection.status}
                  </span>
                  <span className="text-xs px-2.5 py-0.5 bg-emerald-950 text-emerald-400 border border-emerald-700/60 rounded-full font-semibold flex items-center space-x-1">
                    <ShieldCheck className="h-3.5 w-3.5 inline mr-1" />
                    READ ONLY (ENFORCED)
                  </span>
                </div>
                <div className="text-xs text-gray-400 mt-1 flex items-center space-x-3 font-mono">
                  <span>DB: <strong className="text-gray-200">{selectedConnection.database_name}</strong></span>
                  {selectedConnection.host && <span>Host: {selectedConnection.host}:{selectedConnection.port}</span>}
                  <span>Credentials: <strong className="text-emerald-400">Zero-Exposure Encrypted</strong></span>
                </div>
              </div>
            </div>

            <div className="flex items-center space-x-2 flex-wrap">
              <button
                onClick={handleTestConnection}
                disabled={testingConn}
                className="flex items-center space-x-1.5 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-700 rounded-lg text-xs font-medium transition disabled:opacity-50"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${testingConn ? 'animate-spin' : ''}`} />
                <span>{testingConn ? 'Testing...' : 'Test Connection'}</span>
              </button>

              <button
                onClick={handleDiscoverSchema}
                disabled={discovering}
                className="flex items-center space-x-1.5 px-3.5 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-medium transition disabled:opacity-50 shadow-sm"
              >
                <Search className={`h-3.5 w-3.5 ${discovering ? 'animate-spin' : ''}`} />
                <span>{discovering ? 'Discovering Schema...' : 'Discover Schema'}</span>
              </button>

              <button
                onClick={handleGenerateTests}
                disabled={generatingTests || schemas.length === 0}
                className="flex items-center space-x-1.5 px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium transition disabled:opacity-50 shadow-sm"
              >
                <Sparkles className="h-3.5 w-3.5" />
                <span>{generatingTests ? 'Generating Tests...' : 'Generate DB Tests'}</span>
              </button>
            </div>
          </div>

          {testConnMessage && (
            <div className={`mt-3 p-2.5 rounded-lg text-xs flex items-center space-x-2 border ${
              testConnMessage.status === 'CONNECTED'
                ? 'bg-emerald-950/60 text-emerald-300 border-emerald-800'
                : 'bg-rose-950/60 text-rose-300 border-rose-800'
            }`}>
              {testConnMessage.status === 'CONNECTED' ? (
                <CheckCircle2 className="h-4 w-4 shrink-0" />
              ) : (
                <AlertTriangle className="h-4 w-4 shrink-0" />
              )}
              <span>{testConnMessage.message}</span>
            </div>
          )}
        </div>
      ) : (
        <div className="bg-gray-900/60 border border-dashed border-gray-700 rounded-xl p-8 text-center">
          <Database className="h-10 w-10 text-gray-500 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-gray-300">No Target Database Connected</h3>
          <p className="text-sm text-gray-400 max-w-md mx-auto mt-1 mb-4">
            Connect the Autonomous QA Agent to the target application's database in read-only mode to perform automated schema discovery and data integrity tests.
          </p>
          <button
            onClick={() => setShowNewConnModal(true)}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition inline-flex items-center space-x-2"
          >
            <Plus className="h-4 w-4" />
            <span>Connect Application Database</span>
          </button>
        </div>
      )}

      {/* Summary Metrics Cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div className="text-xs text-gray-400 font-medium">Schemas</div>
            <div className="text-2xl font-bold text-white mt-1">{summary.schemas_count}</div>
            <div className="text-xs text-blue-400 mt-1 flex items-center">
              <Layers className="h-3 w-3 mr-1" /> Active
            </div>
          </div>

          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div className="text-xs text-gray-400 font-medium">Discovered Tables</div>
            <div className="text-2xl font-bold text-white mt-1">{summary.tables_count}</div>
            <div className="text-xs text-gray-400 mt-1 flex items-center">
              <TableIcon className="h-3 w-3 mr-1" /> Live Target
            </div>
          </div>

          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div className="text-xs text-gray-400 font-medium">Columns Mapped</div>
            <div className="text-2xl font-bold text-white mt-1">{summary.columns_count}</div>
            <div className="text-xs text-gray-400 mt-1 flex items-center">
              <Key className="h-3 w-3 mr-1" /> Types & Nulls
            </div>
          </div>

          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div className="text-xs text-gray-400 font-medium">Foreign Keys</div>
            <div className="text-2xl font-bold text-white mt-1">{summary.relationships_count}</div>
            <div className="text-xs text-gray-400 mt-1 flex items-center">
              <Link2 className="h-3 w-3 mr-1" /> FK Relations
            </div>
          </div>

          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div className="text-xs text-gray-400 font-medium">Integrity Test Cases</div>
            <div className="text-2xl font-bold text-indigo-400 mt-1">{summary.test_cases_count}</div>
            <div className="text-xs text-indigo-300 mt-1 flex items-center">
              <Code className="h-3 w-3 mr-1" /> Synthesized
            </div>
          </div>

          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div className="text-xs text-gray-400 font-medium">Execution Pass Rate</div>
            <div className="text-2xl font-bold text-emerald-400 mt-1">
              {summary.executions_total > 0
                ? `${Math.round((summary.executions_passed / summary.executions_total) * 100)}%`
                : '100%'}
            </div>
            <div className="text-xs text-gray-400 mt-1">
              {summary.executions_passed} pass / {summary.executions_failed} fail
            </div>
          </div>
        </div>
      )}

      {/* Main Content Layout: Schema Explorer & Test Cases */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Schema & Table Explorer (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center space-x-2">
                <TableIcon className="h-4 w-4 text-blue-400" />
                <h3 className="font-semibold text-white text-sm">Discovered Schema Tables</h3>
              </div>
              <span className="text-xs text-gray-400">
                {schemas.reduce((acc, s) => acc + s.tables.length, 0)} tables
              </span>
            </div>

            {schemas.length === 0 ? (
              <div className="py-8 text-center text-xs text-gray-500">
                No schemas discovered yet. Click "Discover Schema" above.
              </div>
            ) : (
              <div className="space-y-2 max-h-[340px] overflow-y-auto pr-1">
                {schemas.flatMap(s => s.tables).map(t => (
                  <button
                    key={t.id}
                    onClick={() => setSelectedTable(t)}
                    className={`w-full text-left p-2.5 rounded-lg border transition text-xs flex items-center justify-between ${
                      selectedTable?.id === t.id
                        ? 'bg-blue-950/40 border-blue-600/50 text-blue-200'
                        : 'bg-gray-800/60 border-gray-800 text-gray-300 hover:bg-gray-800'
                    }`}
                  >
                    <div className="flex items-center space-x-2">
                      <TableIcon className="h-3.5 w-3.5 text-gray-400" />
                      <span className="font-mono font-medium">{t.table_name}</span>
                    </div>
                    <div className="flex items-center space-x-2 font-mono text-[11px] text-gray-400">
                      <span>{t.columns.length} cols</span>
                      <span>•</span>
                      <span className="text-emerald-400">{t.row_count} rows</span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Table Detail View */}
          {selectedTable && (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-4">
              <div className="flex items-center justify-between border-b border-gray-800 pb-3">
                <div>
                  <h4 className="font-mono font-bold text-white text-sm">{selectedTable.table_name}</h4>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {selectedTable.row_count} records • {selectedTable.columns.length} columns • {selectedTable.relationships.length} foreign keys
                  </p>
                </div>
                <span className="text-xs font-mono bg-gray-800 text-gray-300 px-2 py-0.5 rounded border border-gray-700">
                  Target Table
                </span>
              </div>

              {/* Columns list */}
              <div>
                <div className="text-xs font-semibold text-gray-300 mb-2 flex items-center space-x-1.5">
                  <Key className="h-3.5 w-3.5 text-yellow-400" />
                  <span>Columns & Constraints</span>
                </div>
                <div className="max-h-52 overflow-y-auto space-y-1.5 pr-1">
                  {selectedTable.columns.map(col => (
                    <div
                      key={col.id}
                      className="p-2 bg-gray-800/50 border border-gray-800/80 rounded text-xs flex items-center justify-between font-mono"
                    >
                      <div className="flex items-center space-x-2">
                        {col.is_primary_key && (
                          <span className="px-1.5 py-0.2 text-[10px] bg-amber-950 text-amber-400 border border-amber-800 rounded font-bold">
                            PK
                          </span>
                        )}
                        {col.is_foreign_key && (
                          <span className="px-1.5 py-0.2 text-[10px] bg-blue-950 text-blue-400 border border-blue-800 rounded font-bold">
                            FK
                          </span>
                        )}
                        <span className="text-gray-200">{col.column_name}</span>
                      </div>
                      <div className="flex items-center space-x-2 text-[11px]">
                        <span className="text-blue-300">{col.data_type}</span>
                        <span className={col.nullable ? 'text-gray-400' : 'text-rose-400 font-semibold'}>
                          {col.nullable ? 'NULL' : 'NOT NULL'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Relationships */}
              {selectedTable.relationships.length > 0 && (
                <div>
                  <div className="text-xs font-semibold text-gray-300 mb-2 flex items-center space-x-1.5">
                    <Link2 className="h-3.5 w-3.5 text-blue-400" />
                    <span>Foreign Key Relationships</span>
                  </div>
                  <div className="space-y-1.5">
                    {selectedTable.relationships.map(rel => (
                      <div
                        key={rel.id}
                        className="p-2 bg-gray-800/40 border border-gray-800 rounded text-xs flex items-center justify-between font-mono"
                      >
                        <span className="text-gray-300">{rel.source_column}</span>
                        <ArrowRight className="h-3 w-3 text-gray-500 mx-2" />
                        <span className="text-emerald-400">
                          {rel.related_table_name || 'table'}.{rel.target_column}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Column: Database Test Cases & Executions (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
              <div>
                <h3 className="font-semibold text-white text-base flex items-center space-x-2">
                  <ShieldCheck className="h-4 w-4 text-emerald-400" />
                  <span>Data Integrity Test Cases</span>
                </h3>
                <p className="text-xs text-gray-400 mt-0.5">
                  Automated checks validating orphaned FKs, negative prices, null constraints, and duplicate keys.
                </p>
              </div>

              <div className="flex items-center space-x-2">
                <button
                  onClick={handleRunAllTests}
                  disabled={executingAll || filteredTestCases.length === 0}
                  className="flex items-center space-x-1.5 px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-medium transition disabled:opacity-50 shadow"
                >
                  <Play className={`h-3.5 w-3.5 ${executingAll ? 'animate-spin' : ''}`} />
                  <span>{executingAll ? 'Running All...' : 'Run All Tests'}</span>
                </button>
              </div>
            </div>

            {/* Category Filter Pills */}
            <div className="flex items-center space-x-1.5 overflow-x-auto pb-2 border-b border-gray-800 text-xs">
              {['ALL', 'DATA_INTEGRITY', 'REFERENTIAL_INTEGRITY', 'NULLABILITY', 'CRUD_VALIDATION'].map(cat => (
                <button
                  key={cat}
                  onClick={() => setSelectedCategory(cat)}
                  className={`px-2.5 py-1 rounded-md whitespace-nowrap transition text-xs font-medium ${
                    selectedCategory === cat
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-800 text-gray-400 hover:text-gray-200 hover:bg-gray-700'
                  }`}
                >
                  {cat.replace('_', ' ')}
                </button>
              ))}
            </div>

            {/* Test Cases List */}
            <div className="mt-4 space-y-2.5 max-h-[420px] overflow-y-auto pr-1">
              {filteredTestCases.length === 0 ? (
                <div className="py-12 text-center text-xs text-gray-500">
                  No database test cases generated yet. Click "Generate DB Tests" to synthesize tests from your discovered schema.
                </div>
              ) : (
                filteredTestCases.map(tc => {
                  const exec = testExecutionsMap[tc.id];
                  const isRunning = runningTestId === tc.id;
                  return (
                    <div
                      key={tc.id}
                      className="p-3 bg-gray-800/40 border border-gray-800 hover:border-gray-700 rounded-lg transition space-y-2"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="flex items-center space-x-2 flex-wrap gap-y-1">
                            <span className="font-semibold text-gray-200 text-xs">{tc.name}</span>
                            <span className="text-[10px] px-1.5 py-0.2 bg-gray-800 text-gray-400 border border-gray-700 rounded font-mono">
                              {tc.category}
                            </span>
                            <span className={`text-[10px] px-1.5 py-0.2 rounded font-mono font-bold ${
                              tc.priority === 'CRITICAL'
                                ? 'bg-rose-950 text-rose-400 border border-rose-800'
                                : tc.priority === 'HIGH'
                                ? 'bg-amber-950 text-amber-400 border border-amber-800'
                                : 'bg-gray-800 text-gray-400'
                            }`}>
                              {tc.priority}
                            </span>
                          </div>
                          {tc.description && (
                            <p className="text-[11px] text-gray-400 mt-1 line-clamp-1">{tc.description}</p>
                          )}
                        </div>

                        <div className="flex items-center space-x-2 shrink-0">
                          {exec && (
                            <span className={`text-[10px] px-2 py-0.5 rounded font-mono font-semibold flex items-center space-x-1 ${
                              exec.status === 'PASSED'
                                ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                                : 'bg-rose-950 text-rose-400 border border-rose-800'
                            }`}>
                              {exec.status === 'PASSED' ? (
                                <CheckCircle2 className="h-3 w-3 inline mr-1" />
                              ) : (
                                <XCircle className="h-3 w-3 inline mr-1" />
                              )}
                              {exec.status} ({exec.duration_ms}ms)
                            </span>
                          )}

                          <button
                            onClick={() => handleRunTest(tc.id)}
                            disabled={isRunning}
                            className="px-2.5 py-1 bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-700 rounded text-xs font-medium transition disabled:opacity-50 flex items-center space-x-1"
                          >
                            <Play className={`h-3 w-3 ${isRunning ? 'animate-spin' : ''}`} />
                            <span>{isRunning ? 'Running' : 'Run'}</span>
                          </button>

                          {exec && (
                            <button
                              onClick={() => setActiveExecution(exec)}
                              className="p-1 bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-white rounded border border-gray-700 transition"
                              title="View Evidence & Diff"
                            >
                              <Eye className="h-3.5 w-3.5" />
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Rule preview */}
                      <div className="bg-gray-900/70 p-2 rounded text-[11px] font-mono text-gray-400 flex items-center justify-between">
                        <span className="truncate mr-2">
                          Rule: Expected {tc.validation_definition.expected_condition || tc.validation_definition.assertion || 'validity'}
                        </span>
                        {exec?.status === 'FAILED' && (
                          <button
                            onClick={() => onNavigate('bugs')}
                            className="text-rose-400 hover:text-rose-300 font-semibold flex items-center space-x-1 shrink-0"
                          >
                            <span>Filed in Bugs</span>
                            <ExternalLink className="h-3 w-3" />
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Active Execution Detail Panel */}
          {activeExecution && (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-3">
              <div className="flex items-center justify-between border-b border-gray-800 pb-3">
                <div className="flex items-center space-x-2">
                  <Activity className="h-4 w-4 text-blue-400" />
                  <h4 className="font-semibold text-white text-sm">Execution Evidence & Assertion Diff</h4>
                </div>
                <div className="flex items-center space-x-2">
                  <span className={`text-xs px-2 py-0.5 rounded font-mono font-bold ${
                    activeExecution.status === 'PASSED'
                      ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                      : 'bg-rose-950 text-rose-400 border border-rose-800'
                  }`}>
                    {activeExecution.status}
                  </span>
                  <span className="text-xs text-gray-400 font-mono">{activeExecution.duration_ms} ms</span>
                </div>
              </div>

              {/* Comparison Diff Box */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="bg-gray-800/40 border border-gray-800 rounded-lg p-3">
                  <div className="text-xs font-semibold text-gray-400 mb-1 flex items-center space-x-1">
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                    <span>Expected Result</span>
                  </div>
                  <pre className="text-xs font-mono text-emerald-300 bg-gray-900/80 p-2 rounded overflow-x-auto">
                    {JSON.stringify(activeExecution.expected_result, null, 2)}
                  </pre>
                </div>

                <div className="bg-gray-800/40 border border-gray-800 rounded-lg p-3">
                  <div className="text-xs font-semibold text-gray-400 mb-1 flex items-center space-x-1">
                    {activeExecution.status === 'PASSED' ? (
                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                    ) : (
                      <XCircle className="h-3.5 w-3.5 text-rose-400" />
                    )}
                    <span>Actual Database Result</span>
                  </div>
                  <pre className={`text-xs font-mono p-2 rounded overflow-x-auto bg-gray-900/80 ${
                    activeExecution.status === 'PASSED' ? 'text-emerald-300' : 'text-rose-300'
                  }`}>
                    {JSON.stringify(activeExecution.actual_result, null, 2)}
                  </pre>
                </div>
              </div>

              {/* Sanitized Query Evidence */}
              {activeExecution.evidence && activeExecution.evidence.length > 0 && (
                <div>
                  <div className="text-xs font-semibold text-gray-400 mb-1 flex items-center space-x-1">
                    <Code className="h-3.5 w-3.5 text-blue-400" />
                    <span>Sanitized Read-Only SQL Executed</span>
                  </div>
                  <pre className="text-xs font-mono text-blue-300 bg-gray-950 p-2.5 rounded border border-gray-800 overflow-x-auto">
                    {activeExecution.evidence[0].sanitized_query}
                  </pre>
                </div>
              )}

              {/* Bug Filing Link for Failed Tests */}
              {activeExecution.status === 'FAILED' && (
                <div className="p-3 bg-rose-950/40 border border-rose-800/80 rounded-lg flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <AlertTriangle className="h-4 w-4 text-rose-400 shrink-0" />
                    <div className="text-xs text-rose-300">
                      <strong>Automated Defect Logged:</strong> Bug ticket filed under Phase 4 Bug Intelligence with category <code className="bg-rose-900/60 px-1 py-0.5 rounded">DATABASE_INTEGRITY_BUG</code>.
                    </div>
                  </div>
                  <button
                    onClick={() => onNavigate('bugs')}
                    className="px-3 py-1.5 bg-rose-600 hover:bg-rose-500 text-white rounded text-xs font-medium transition flex items-center space-x-1 shrink-0 ml-3"
                  >
                    <span>View Bug</span>
                    <ExternalLink className="h-3 w-3" />
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* New Connection Modal */}
      {showNewConnModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-gray-800 pb-3">
              <div className="flex items-center space-x-2">
                <Database className="h-5 w-5 text-blue-400" />
                <h3 className="font-bold text-white text-base">Target Database Connection</h3>
              </div>
              <button
                onClick={() => setShowNewConnModal(false)}
                className="text-gray-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateConnection} className="space-y-3 text-xs">
              <div>
                <label className="block text-gray-300 font-medium mb-1">Connection Name</label>
                <input
                  type="text"
                  value={newConnData.name}
                  onChange={(e) => setNewConnData({ ...newConnData, name: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white outline-none focus:border-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block text-gray-300 font-medium mb-1">Database Type</label>
                <select
                  value={newConnData.database_type}
                  onChange={(e) => setNewConnData({ ...newConnData, database_type: e.target.value as any })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white outline-none focus:border-blue-500"
                >
                  <option value="sqlite">SQLite (e.g. test-app/crm_development.db)</option>
                  <option value="postgresql">PostgreSQL</option>
                  <option value="mysql">MySQL</option>
                </select>
              </div>

              <div>
                <label className="block text-gray-300 font-medium mb-1">
                  Database Path / Name
                </label>
                <input
                  type="text"
                  value={newConnData.database_name}
                  onChange={(e) => setNewConnData({ ...newConnData, database_name: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white outline-none focus:border-blue-500 font-mono"
                  placeholder="test-app/crm_development.db or production_db"
                  required
                />
              </div>

              {newConnData.database_type !== 'sqlite' && (
                <>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="block text-gray-300 font-medium mb-1">Host</label>
                      <input
                        type="text"
                        value={newConnData.host}
                        onChange={(e) => setNewConnData({ ...newConnData, host: e.target.value })}
                        className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white outline-none focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-gray-300 font-medium mb-1">Port</label>
                      <input
                        type="number"
                        value={newConnData.port}
                        onChange={(e) => setNewConnData({ ...newConnData, port: Number(e.target.value) })}
                        className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white outline-none focus:border-blue-500"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="block text-gray-300 font-medium mb-1">Username</label>
                      <input
                        type="text"
                        value={newConnData.username}
                        onChange={(e) => setNewConnData({ ...newConnData, username: e.target.value })}
                        className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white outline-none focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-gray-300 font-medium mb-1">Password</label>
                      <input
                        type="password"
                        value={newConnData.password}
                        onChange={(e) => setNewConnData({ ...newConnData, password: e.target.value })}
                        className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white outline-none focus:border-blue-500"
                      />
                    </div>
                  </div>
                </>
              )}

              <div className="p-3 bg-emerald-950/40 border border-emerald-800/80 rounded-lg flex items-center space-x-2">
                <ShieldCheck className="h-4 w-4 text-emerald-400 shrink-0" />
                <span className="text-emerald-300 text-[11px]">
                  <strong>Enforced READ-ONLY Mode:</strong> Mutation queries (INSERT, UPDATE, DELETE, DROP) are strictly rejected by the validator.
                </span>
              </div>

              <div className="flex justify-end space-x-2 pt-3 border-t border-gray-800">
                <button
                  type="button"
                  onClick={() => setShowNewConnModal(false)}
                  className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded text-xs transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded text-xs transition"
                >
                  Save Connection
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
