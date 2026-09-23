import axios from 'axios';
import {
  Application,
  Environment,
  ExplorationRun,
  ExplorationStatusResponse,
  DiscoveredPage,
  PageElement,
  PageAction,
  Evidence,
  Workflow,
  WorkflowStep,
  TestCase,
  TestStep,
  AnalysisStatusResponse,
  GeneratedTest,
  TestExecution,
  TestExecutionStep,
  ExecutionEvidence,
  ExecutionSummary,
  Bug,
  BugEvidence,
  BugSummary,
  DatabaseConnection,
  DatabaseSchema,
  DatabaseTestCase,
  DatabaseTestExecution,
  DatabaseSummary
} from '../types';


export const BACKEND_URL = (
  import.meta.env.VITE_BACKEND_URL ||
  import.meta.env.VITE_API_URL?.replace(/\/api\/?$/, '') ||
  'http://127.0.0.1:8000'
).replace(/\/$/, '');

export const API_BASE_URL = `${BACKEND_URL}/api`;

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const applicationsApi = {
  getAll: async (): Promise<Application[]> => {
    const res = await api.get('/applications');
    return res.data;
  },
  getById: async (id: number): Promise<Application> => {
    const res = await api.get(`/applications/${id}`);
    return res.data;
  },
  create: async (data: { name: string; description?: string }): Promise<Application> => {
    const res = await api.post('/applications', data);
    return res.data;
  },
  delete: async (id: number): Promise<void> => {
    await api.delete(`/applications/${id}`);
  },
  getEnvironments: async (appId: number): Promise<Environment[]> => {
    const res = await api.get(`/applications/${appId}/environments`);
    return res.data;
  },
  createEnvironment: async (appId: number, data: { name: string; base_url: string; environment_type: string }): Promise<Environment> => {
    const res = await api.post(`/applications/${appId}/environments`, data);
    return res.data;
  },
  getPages: async (appId: number): Promise<DiscoveredPage[]> => {
    const res = await api.get(`/applications/${appId}/pages`);
    return res.data;
  },
  getSummary: async (appId: number): Promise<any> => {
    const res = await api.get(`/applications/${appId}/summary`);
    return res.data;
  },
};

// --- PHASE 1 APIS ---

export const explorationsApi = {
  getAll: async (appId?: number): Promise<ExplorationRun[]> => {
    const params = appId ? { application_id: appId } : {};
    const res = await api.get('/explorations', { params });
    return res.data;
  },
  getById: async (id: number): Promise<ExplorationRun> => {
    const res = await api.get(`/explorations/${id}`);
    return res.data;
  },
  create: async (data: { application_id: number; environment_id: number; target_url?: string; max_pages?: number; max_depth?: number }): Promise<ExplorationRun> => {
    const res = await api.post('/explorations', data);
    return res.data;
  },
  start: async (id: number, maxPages: number = 30, maxDepth: number = 3): Promise<ExplorationStatusResponse> => {
    const res = await api.post(`/explorations/${id}/start?max_pages=${maxPages}&max_depth=${maxDepth}`);
    return res.data;
  },
  getStatus: async (id: number): Promise<ExplorationStatusResponse> => {
    const res = await api.get(`/explorations/${id}/status`);
    return res.data;
  },
  getEvidence: async (id: number, type?: string): Promise<Evidence[]> => {
    const params = type ? { type } : {};
    const res = await api.get(`/explorations/${id}/evidence`, { params });
    return res.data;
  },
  cancel: async (runId: number): Promise<{ message: string }> => {
    const res = await api.post(`/explorations/${runId}/cancel`);
    return res.data;
  },
  getPages: async (runId: number): Promise<DiscoveredPage[]> => {
    const res = await api.get(`/explorations/${runId}/pages`);
    return res.data;
  },
  getRuns: async (appId: number): Promise<ExplorationRun[]> => {
    const res = await api.get(`/applications/${appId}/explorations`);
    return res.data;
  },
};

export const explorationApi = explorationsApi;

export const pagesApi = {
  getById: async (id: number): Promise<DiscoveredPage> => {
    const res = await api.get(`/pages/${id}`);
    return res.data;
  },
  getElements: async (id: number): Promise<PageElement[]> => {
    const res = await api.get(`/pages/${id}/elements`);
    return res.data;
  },
  getActions: async (id: number): Promise<PageAction[]> => {
    const res = await api.get(`/pages/${id}/actions`);
    return res.data;
  },
};

// --- PHASE 2 APIS ---

export const analysisApi = {
  startAnalysis: async (appId: number): Promise<{ message: string; status: string; application_id: number }> => {
    const res = await api.post(`/applications/${appId}/analyze`);
    return res.data;
  },
  getStatus: async (appId: number): Promise<AnalysisStatusResponse> => {
    const res = await api.get(`/applications/${appId}/analysis-status`);
    return res.data;
  },
};

export const workflowsApi = {
  getByApp: async (appId: number): Promise<Workflow[]> => {
    const res = await api.get(`/applications/${appId}/workflows`);
    return res.data;
  },
  getById: async (id: number): Promise<Workflow> => {
    const res = await api.get(`/workflows/${id}`);
    return res.data;
  },
  getSteps: async (id: number): Promise<WorkflowStep[]> => {
    const res = await api.get(`/workflows/${id}/steps`);
    return res.data;
  },
};

export const testCasesApi = {
  getByApp: async (
    appId: number,
    params?: { workflow_id?: number; category?: string; priority?: string }
  ): Promise<TestCase[]> => {
    const res = await api.get(`/applications/${appId}/test-cases`, { params });
    return res.data;
  },
  getById: async (id: number): Promise<TestCase> => {
    const res = await api.get(`/test-cases/${id}`);
    return res.data;
  },
  getSteps: async (id: number): Promise<TestStep[]> => {
    const res = await api.get(`/test-cases/${id}/steps`);
    return res.data;
  },
  generateTest: async (id: number, baseUrl?: string): Promise<GeneratedTest> => {
    const params = baseUrl ? { base_url: baseUrl } : {};
    const res = await api.post(`/test-cases/${id}/generate`, null, { params });
    return res.data;
  },
  getGeneratedTest: async (id: number): Promise<GeneratedTest> => {
    const res = await api.get(`/test-cases/${id}/generated-test`);
    return res.data;
  },
  getAllGeneratedTests: async (id: number): Promise<GeneratedTest[]> => {
    const res = await api.get(`/test-cases/${id}/generated-tests`);
    return res.data;
  },
  generateTestsForApp: async (appId: number): Promise<{ message: string; status: string }> => {
    const res = await api.post(`/applications/${appId}/generate-tests`);
    return res.data;
  },
  createTestCase: async (appId: number, data: any): Promise<TestCase> => {
    const res = await api.post(`/applications/${appId}/test-cases`, data);
    return res.data;
  },
};

// --- PHASE 3 EXECUTION APIS ---

export const executionsApi = {
  execute: async (testCaseId: number, envId?: number, baseUrl?: string): Promise<TestExecution> => {
    const params: any = {};
    if (envId) params.environment_id = envId;
    if (baseUrl) params.base_url = baseUrl;
    const res = await api.post(`/test-cases/${testCaseId}/execute`, null, { params, timeout: 120000 });
    return res.data;
  },
  getById: async (id: number): Promise<TestExecution> => {
    const res = await api.get(`/test-executions/${id}`);
    return res.data;
  },
  getSteps: async (id: number): Promise<TestExecutionStep[]> => {
    const res = await api.get(`/test-executions/${id}/steps`);
    return res.data;
  },
  getEvidence: async (id: number): Promise<ExecutionEvidence[]> => {
    const res = await api.get(`/test-executions/${id}/evidence`);
    return res.data;
  },
  getByApp: async (appId: number, limit: number = 50): Promise<TestExecution[]> => {
    const res = await api.get(`/applications/${appId}/test-executions`, { params: { limit } });
    return res.data;
  },
  getSummary: async (appId: number): Promise<ExecutionSummary> => {
    const res = await api.get(`/applications/${appId}/test-executions/summary`);
    return res.data;
  },
};

// --- PHASE 4 BUGS APIS ---

export const bugsApi = {
  getByApp: async (
    appId: number,
    params?: { status?: string; severity?: string; category?: string; limit?: number }
  ): Promise<Bug[]> => {
    const res = await api.get(`/applications/${appId}/bugs`, { params });
    return res.data;
  },
  getSummary: async (appId: number): Promise<BugSummary> => {
    const res = await api.get(`/applications/${appId}/bugs/summary`);
    return res.data;
  },
  getById: async (id: number): Promise<Bug> => {
    const res = await api.get(`/bugs/${id}`);
    return res.data;
  },
  getEvidence: async (id: number): Promise<BugEvidence[]> => {
    const res = await api.get(`/bugs/${id}/evidence`);
    return res.data;
  },
  analyzeExecution: async (executionId: number): Promise<Bug | null> => {
    const res = await api.post(`/test-executions/${executionId}/analyze`);
    return res.data;
  },
  updateStatus: async (id: number, status: string): Promise<Bug> => {
    const res = await api.patch(`/bugs/${id}`, { status });
    return res.data;
  },
  createBug: async (appId: number, data: any): Promise<Bug> => {
    const res = await api.post(`/applications/${appId}/bugs`, data);
    return res.data;
  },
  scanDefects: async (appId: number): Promise<Bug[]> => {
    const res = await api.post(`/applications/${appId}/scan-defects`);
    return res.data;
  },
};

// --- PHASE 6 DATABASE QA APIS ---

export const databaseQaApi = {
  createConnection: async (appId: number, data: any): Promise<DatabaseConnection> => {
    const res = await api.post(`/applications/${appId}/databases`, data);
    return res.data;
  },
  getConnections: async (appId: number): Promise<DatabaseConnection[]> => {
    const res = await api.get(`/applications/${appId}/databases`);
    return res.data;
  },
  testNewConnection: async (appId: number, data: any): Promise<{ status: string; message: string }> => {
    const res = await api.post(`/applications/${appId}/databases/test-connection`, data);
    return res.data;
  },
  testExistingConnection: async (connectionId: number): Promise<{ status: string; message: string }> => {
    const res = await api.post(`/databases/${connectionId}/test-connection`);
    return res.data;
  },
  discoverSchema: async (connectionId: number): Promise<DatabaseSchema[]> => {
    const res = await api.post(`/databases/${connectionId}/discover`);
    return res.data;
  },
  getSchemas: async (connectionId: number): Promise<DatabaseSchema[]> => {
    const res = await api.get(`/databases/${connectionId}/schemas`);
    return res.data;
  },
  getSummary: async (connectionId: number): Promise<DatabaseSummary> => {
    const res = await api.get(`/databases/${connectionId}/summary`);
    return res.data;
  },
  generateTestCases: async (appId: number, connectionId: number): Promise<DatabaseTestCase[]> => {
    const res = await api.post(`/applications/${appId}/database-test-cases/generate?connection_id=${connectionId}`);
    return res.data;
  },
  createTestCase: async (appId: number, data: any): Promise<DatabaseTestCase> => {
    const res = await api.post(`/applications/${appId}/database-test-cases`, data);
    return res.data;
  },
  getTestCases: async (appId: number): Promise<DatabaseTestCase[]> => {
    const res = await api.get(`/applications/${appId}/database-test-cases`);
    return res.data;
  },
  executeTestCase: async (testCaseId: number): Promise<DatabaseTestExecution> => {
    const res = await api.post(`/database-test-cases/${testCaseId}/execute`);
    return res.data;
  },
  executeAllTestCases: async (appId: number, connectionId?: number): Promise<DatabaseTestExecution[]> => {
    const params = connectionId ? { connection_id: connectionId } : {};
    const res = await api.post(`/applications/${appId}/database-test-cases/execute-all`, null, { params });
    return res.data;
  },
  getTestCaseExecutions: async (testCaseId: number, limit: number = 20): Promise<DatabaseTestExecution[]> => {
    const res = await api.get(`/database-test-cases/${testCaseId}/executions`, { params: { limit } });
    return res.data;
  },
  getExecutionDetails: async (executionId: number): Promise<DatabaseTestExecution> => {
    const res = await api.get(`/database-test-executions/${executionId}`);
    return res.data;
  },
};

export default api;
