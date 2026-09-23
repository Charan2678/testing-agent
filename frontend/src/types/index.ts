export type EnvironmentType = 'development' | 'qa' | 'staging' | 'uat' | 'production';

export type ExplorationStatus = 'pending' | 'running' | 'completed' | 'failed';

export type EvidenceType = 'screenshot' | 'trace' | 'video' | 'console_log' | 'network_log';

export interface Environment {
  id: number;
  application_id: number;
  name: string;
  base_url: string;
  environment_type: EnvironmentType;
  created_at: string;
}

export interface Application {
  id: number;
  name: string;
  description?: string;
  created_at: string;
  updated_at: string;
  environments?: Environment[];
}

export interface ExplorationRun {
  id: number;
  application_id: number;
  environment_id: number;
  target_url?: string;
  status: ExplorationStatus;
  started_at?: string;
  completed_at?: string;
  pages_discovered: number;
  actions_discovered: number;
  error_count: number;
}

export interface ExplorationStatusResponse {
  id: number;
  status: ExplorationStatus;
  pages_discovered: number;
  actions_discovered: number;
  error_count: number;
  current_url?: string;
  target_url?: string;
  url_source?: string;
  activity_log: string[];
}

export interface PageElement {
  id: number;
  page_id: number;
  element_type: string;
  tag_name: string;
  selector: string;
  text?: string;
  name?: string;
  placeholder?: string;
  role?: string;
  is_interactive: boolean;
  created_at: string;
}

export interface PageAction {
  id: number;
  page_id: number;
  element_id?: number;
  action_type: string;
  action_data?: Record<string, any>;
  result?: string;
  created_at: string;
}

export interface DiscoveredPage {
  id: number;
  application_id: number;
  environment_id: number;
  url: string;
  title?: string;
  status_code?: number;
  page_type?: string;
  first_seen_at: string;
  last_seen_at: string;
  elements_count: number;
  elements?: PageElement[];
  actions?: PageAction[];
}

export interface Evidence {
  id: number;
  exploration_run_id: number;
  type: EvidenceType;
  file_path?: string;
  url?: string;
  description?: string;
  metadata_json?: Record<string, any>;
  created_at: string;
}

// --- PHASE 2 TYPES ---

export interface WorkflowStep {
  id: number;
  workflow_id: number;
  sequence: number;
  action: string;
  expected_behavior?: string;
  page_id?: number;
  element_id?: number;
}

export interface Workflow {
  id: number;
  application_id: number;
  name: string;
  description?: string;
  risk_level: 'critical' | 'high' | 'medium' | 'low';
  discovered_at: string;
  steps_count: number;
  steps: WorkflowStep[];
}

export interface TestStep {
  id: number;
  test_case_id: number;
  sequence: number;
  action: string;
  target: string;
  value?: string;
  expected_result: string;
  source_page_id?: number;
  source_element_id?: number;
}

export interface TestCase {
  id: number;
  application_id: number;
  workflow_id?: number;
  name: string;
  description?: string;
  category: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  preconditions: string[];
  status: string;
  created_at: string;
  updated_at: string;
  steps_count: number;
  steps: TestStep[];
}

export interface AnalysisStatusResponse {
  status: 'IDLE' | 'ANALYZING' | 'IDENTIFYING WORKFLOWS' | 'GENERATING TEST CASES' | 'VALIDATING RESULTS' | 'COMPLETED' | 'FAILED';
  stage: string;
  workflows_count: number;
  test_cases_count: number;
  activity_log: string[];
}

// --- PHASE 3 PLAYWRIGHT ENGINE TYPES ---

export interface GeneratedTest {
  id: number;
  test_case_id: number;
  framework: string;
  language: string;
  file_path: string;
  generated_code: string;
  generation_version: number;
  created_at: string;
  updated_at: string;
}

export type ExecutionStatus = 'queued' | 'running' | 'passed' | 'failed' | 'skipped' | 'blocked' | 'error';

export interface TestExecutionStep {
  id: number;
  execution_id: number;
  test_step_id?: number;
  sequence: number;
  action: string;
  target: string;
  status: 'passed' | 'failed' | 'skipped' | 'blocked' | 'pending';
  started_at?: string;
  completed_at?: string;
  duration_ms?: number;
  error_message?: string;
  actual_result?: string;
}

export interface ExecutionEvidence {
  id: number;
  execution_id: number;
  type: 'screenshot' | 'trace' | 'video' | 'console_log' | 'network_log';
  file_path?: string;
  description?: string;
  metadata_json?: Record<string, any>;
  created_at: string;
}

export interface TestExecution {
  id: number;
  test_case_id: number;
  environment_id?: number;
  status: ExecutionStatus;
  started_at?: string;
  completed_at?: string;
  duration_ms?: number;
  error_message?: string;
  final_url?: string;
  created_at: string;
  steps: TestExecutionStep[];
  evidence: ExecutionEvidence[];
}

export interface ExecutionSummary {
  has_executions: boolean;
  total_executions: number;
  passed: number;
  failed: number;
  blocked: number;
  skipped: number;
  errors: number;
  pass_rate: number;
  avg_duration_ms: number;
}

// --- PHASE 4 BUG INTELLIGENCE TYPES ---

export type BugClassification =
  | 'APPLICATION_BUG'
  | 'TEST_BUG'
  | 'ENVIRONMENT_FAILURE'
  | 'INFRASTRUCTURE_FAILURE'
  | 'NETWORK_FAILURE'
  | 'TIMEOUT'
  | 'UNKNOWN';

export type BugSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export type BugStatus = 'OPEN' | 'TRIAGED' | 'IN_PROGRESS' | 'FIXED' | 'RETESTED' | 'CLOSED';

export interface BugEvidence {
  id: number;
  bug_id: number;
  type: 'screenshot' | 'trace' | 'video' | 'console_log' | 'network_log';
  file_path?: string;
  description?: string;
  created_at: string;
}

export interface Bug {
  id: number;
  application_id: number;
  environment_id?: number;
  title: string;
  summary?: string;
  description?: string;
  classification: BugClassification;
  category: string;
  severity: BugSeverity;
  priority: string;
  status: BugStatus;
  affected_page?: string;
  affected_workflow_id?: number;
  affected_test_case_id?: number;
  affected_execution_id?: number;
  failed_step?: string;
  expected_behavior?: string;
  actual_behavior?: string;
  root_cause?: string;
  root_cause_confidence?: number;
  confidence_level: 'CONFIRMED' | 'LIKELY' | 'POSSIBLE' | 'UNKNOWN';
  severity_explanation?: string;
  failure_signature?: string;
  occurrence_count: number;
  created_at: string;
  updated_at: string;
  evidence?: BugEvidence[];
}

export interface BugSummary {
  has_bugs: boolean;
  total_bugs: number;
  open_bugs: number;
  critical_bugs: number;
  high_bugs: number;
  medium_bugs: number;
  low_bugs: number;
  resolved_bugs: number;
}

// --- PHASE 6: DATABASE QA & DATA INTEGRITY ---
export type DatabaseType = 'postgresql' | 'mysql' | 'sqlite';
export type DatabaseConnectionStatus = 'CONNECTED' | 'FAILED' | 'BLOCKED' | 'DISCONNECTED';
export type DatabaseTestCategory = 'DATA_INTEGRITY' | 'CRUD_VALIDATION' | 'REFERENTIAL_INTEGRITY' | 'NULLABILITY' | 'DUPLICATE_DATA' | 'TYPE_VALIDATION' | 'CONSTRAINT';

export interface DatabaseConnection {
  id: number;
  application_id: number;
  environment_id?: number;
  name: string;
  database_type: DatabaseType;
  host?: string;
  port?: number;
  database_name: string;
  username?: string;
  read_only: boolean;
  status: DatabaseConnectionStatus;
  last_tested_at?: string;
  last_error?: string;
  created_at: string;
  updated_at: string;
}

export interface DatabaseColumn {
  id: number;
  column_name: string;
  data_type: string;
  nullable: boolean;
  is_primary_key: boolean;
  is_foreign_key: boolean;
  default_value?: string;
}

export interface DatabaseRelationship {
  id: number;
  source_column: string;
  target_column: string;
  relationship_type: string;
  related_table_id?: number;
  related_table_name?: string;
}

export interface DatabaseTable {
  id: number;
  table_name: string;
  row_count: number;
  description?: string;
  columns: DatabaseColumn[];
  relationships: DatabaseRelationship[];
}

export interface DatabaseSchema {
  id: number;
  schema_name: string;
  discovered_at: string;
  tables: DatabaseTable[];
}

export interface DatabaseTestCase {
  id: number;
  application_id: number;
  environment_id?: number;
  database_connection_id: number;
  name: string;
  description?: string;
  category: DatabaseTestCategory;
  priority: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  source_test_case_id?: number;
  validation_definition: Record<string, any>;
  status: string;
  created_at: string;
}

export interface DatabaseEvidence {
  id: number;
  sanitized_query: string;
  parameters?: Record<string, any>;
  comparison_summary?: string;
  raw_data?: Record<string, any>;
  created_at: string;
}

export interface DatabaseTestExecution {
  id: number;
  database_test_case_id: number;
  status: 'PASSED' | 'FAILED' | 'BLOCKED' | 'ERROR' | 'RUNNING';
  started_at: string;
  completed_at?: string;
  duration_ms: number;
  expected_result?: Record<string, any>;
  actual_result?: Record<string, any>;
  error_message?: string;
  created_at: string;
  evidence: DatabaseEvidence[];
}

export interface DatabaseSummary {
  connection_id?: number;
  name?: string;
  database_type?: string;
  status?: string;
  read_only?: boolean;
  schemas_count: number;
  tables_count: number;
  columns_count: number;
  relationships_count: number;
  test_cases_count: number;
  executions_total: number;
  executions_passed: number;
  executions_failed: number;
  executions_blocked: number;
  last_tested_at?: string;
}



