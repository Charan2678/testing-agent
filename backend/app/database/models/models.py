from datetime import datetime
from typing import Optional, List
import enum
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum as SQLEnum, JSON
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class EnvironmentType(str, enum.Enum):
    DEV = "development"
    QA = "qa"
    STAGING = "staging"
    UAT = "uat"
    PROD = "production"

class ExplorationStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class EvidenceType(str, enum.Enum):
    SCREENSHOT = "screenshot"
    TRACE = "trace"
    VIDEO = "video"
    CONSOLE_LOG = "console_log"
    NETWORK_LOG = "network_log"

class ActionType(str, enum.Enum):
    CLICK = "click"
    FILL = "fill"
    SUBMIT = "submit"
    SELECT = "select"
    NAVIGATE = "navigate"

# 1. Applications
class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    environments = relationship("Environment", back_populates="application", cascade="all, delete-orphan")
    exploration_runs = relationship("ExplorationRun", back_populates="application", cascade="all, delete-orphan")
    pages = relationship("Page", back_populates="application", cascade="all, delete-orphan")
    workflows = relationship("Workflow", back_populates="application", cascade="all, delete-orphan")
    test_cases = relationship("TestCase", back_populates="application", cascade="all, delete-orphan")
    bugs = relationship("Bug", back_populates="application", cascade="all, delete-orphan")
    database_connections = relationship("DatabaseConnection", back_populates="application", cascade="all, delete-orphan")


# 2. Environments
class Environment(Base):
    __tablename__ = "environments"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    base_url = Column(String(500), nullable=False)
    environment_type = Column(SQLEnum(EnvironmentType), default=EnvironmentType.DEV, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    application = relationship("Application", back_populates="environments")
    exploration_runs = relationship("ExplorationRun", back_populates="environment", cascade="all, delete-orphan")
    pages = relationship("Page", back_populates="environment", cascade="all, delete-orphan")

# 3. Exploration Runs
class ExplorationRun(Base):
    __tablename__ = "exploration_runs"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    environment_id = Column(Integer, ForeignKey("environments.id", ondelete="CASCADE"), nullable=False)
    target_url = Column(String(1000), nullable=True)
    status = Column(SQLEnum(ExplorationStatus), default=ExplorationStatus.PENDING, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    pages_discovered = Column(Integer, default=0, nullable=False)
    actions_discovered = Column(Integer, default=0, nullable=False)
    error_count = Column(Integer, default=0, nullable=False)

    # Relationships
    application = relationship("Application", back_populates="exploration_runs")
    environment = relationship("Environment", back_populates="exploration_runs")
    evidence = relationship("Evidence", back_populates="exploration_run", cascade="all, delete-orphan")

# 4. Pages
class Page(Base):
    __tablename__ = "pages"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    environment_id = Column(Integer, ForeignKey("environments.id", ondelete="CASCADE"), nullable=False)
    url = Column(String(1000), nullable=False, index=True)
    title = Column(String(500), nullable=True)
    status_code = Column(Integer, nullable=True)
    page_type = Column(String(50), default="standard", nullable=True)
    first_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    application = relationship("Application", back_populates="pages")
    environment = relationship("Environment", back_populates="pages")
    elements = relationship("Element", back_populates="page", cascade="all, delete-orphan")
    actions = relationship("Action", back_populates="page", cascade="all, delete-orphan")

# 5. Elements
class Element(Base):
    __tablename__ = "elements"

    id = Column(Integer, primary_key=True, index=True)
    page_id = Column(Integer, ForeignKey("pages.id", ondelete="CASCADE"), nullable=False)
    element_type = Column(String(50), nullable=False)  # button, input, select, link, checkbox, form
    tag_name = Column(String(50), nullable=False)
    selector = Column(Text, nullable=False)
    text = Column(Text, nullable=True)
    name = Column(String(255), nullable=True)
    placeholder = Column(String(255), nullable=True)
    role = Column(String(100), nullable=True)
    is_interactive = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    page = relationship("Page", back_populates="elements")
    actions = relationship("Action", back_populates="element")

# 6. Actions
class Action(Base):
    __tablename__ = "actions"

    id = Column(Integer, primary_key=True, index=True)
    page_id = Column(Integer, ForeignKey("pages.id", ondelete="CASCADE"), nullable=False)
    element_id = Column(Integer, ForeignKey("elements.id", ondelete="SET NULL"), nullable=True)
    action_type = Column(SQLEnum(ActionType), nullable=False)
    action_data = Column(JSON, nullable=True)
    result = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    page = relationship("Page", back_populates="actions")
    element = relationship("Element", back_populates="actions")

# 7. Evidence
class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True, index=True)
    exploration_run_id = Column(Integer, ForeignKey("exploration_runs.id", ondelete="CASCADE"), nullable=False)
    type = Column(SQLEnum(EvidenceType), nullable=False)
    file_path = Column(String(1000), nullable=True)
    url = Column(String(1000), nullable=True)
    description = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    exploration_run = relationship("ExplorationRun", back_populates="evidence")

# 8. Workflows
class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    risk_level = Column(String(50), default="medium", nullable=False)  # critical, high, medium, low
    discovered_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    application = relationship("Application", back_populates="workflows")
    steps = relationship("WorkflowStep", back_populates="workflow", cascade="all, delete-orphan", order_by="WorkflowStep.sequence")
    test_cases = relationship("TestCase", back_populates="workflow", cascade="all, delete-orphan")

# 9. Workflow Steps
class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)
    sequence = Column(Integer, nullable=False)
    page_id = Column(Integer, ForeignKey("pages.id", ondelete="SET NULL"), nullable=True)
    element_id = Column(Integer, ForeignKey("elements.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False)
    expected_behavior = Column(Text, nullable=True)

    # Relationships
    workflow = relationship("Workflow", back_populates="steps")
    page = relationship("Page")
    element = relationship("Element")

# 10. Test Cases
class TestCase(Base):
    __test__ = False
    __tablename__ = "test_cases"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    workflow_id = Column(Integer, ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), default="functional", nullable=False)  # smoke, functional, e2e, negative, etc.
    priority = Column(String(50), default="medium", nullable=False)  # critical, high, medium, low
    preconditions = Column(JSON, nullable=True)
    status = Column(String(50), default="draft", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    application = relationship("Application", back_populates="test_cases")
    workflow = relationship("Workflow", back_populates="test_cases")
    steps = relationship("TestStep", back_populates="test_case", cascade="all, delete-orphan", order_by="TestStep.sequence")
    generated_tests = relationship("GeneratedTest", back_populates="test_case", cascade="all, delete-orphan", order_by="GeneratedTest.generation_version.desc()")
    executions = relationship("TestExecution", back_populates="test_case", cascade="all, delete-orphan", order_by="TestExecution.created_at.desc()")

# 11. Test Steps
class TestStep(Base):
    __test__ = False
    __tablename__ = "test_steps"

    id = Column(Integer, primary_key=True, index=True)
    test_case_id = Column(Integer, ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False)
    sequence = Column(Integer, nullable=False)
    action = Column(String(100), nullable=False)
    target = Column(String(255), nullable=False)
    value = Column(String(500), nullable=True)
    expected_result = Column(Text, nullable=True)
    source_page_id = Column(Integer, ForeignKey("pages.id", ondelete="SET NULL"), nullable=True)
    source_element_id = Column(Integer, ForeignKey("elements.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    test_case = relationship("TestCase", back_populates="steps")
    source_page = relationship("Page")
    source_element = relationship("Element")

# 12. Generated Tests
class GeneratedTest(Base):
    __tablename__ = "generated_tests"

    id = Column(Integer, primary_key=True, index=True)
    test_case_id = Column(Integer, ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False)
    framework = Column(String(50), default="playwright", nullable=False)
    language = Column(String(50), default="python", nullable=False)
    file_path = Column(String(1000), nullable=False)
    generated_code = Column(Text, nullable=False)
    generation_version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    test_case = relationship("TestCase", back_populates="generated_tests")

# Execution Status Enum
class ExecutionStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"
    ERROR = "error"

# 13. Test Executions
class TestExecution(Base):
    __test__ = False
    __tablename__ = "test_executions"

    id = Column(Integer, primary_key=True, index=True)
    test_case_id = Column(Integer, ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False)
    environment_id = Column(Integer, ForeignKey("environments.id", ondelete="SET NULL"), nullable=True)
    status = Column(SQLEnum(ExecutionStatus), default=ExecutionStatus.QUEUED, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    final_url = Column(String(1000), nullable=True)
    classification = Column(String(50), nullable=True)  # APPLICATION_BUG, TEST_BUG, ENVIRONMENT_FAILURE, etc.
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    test_case = relationship("TestCase", back_populates="executions")
    environment = relationship("Environment")
    steps = relationship("TestExecutionStep", back_populates="execution", cascade="all, delete-orphan", order_by="TestExecutionStep.sequence")
    evidence = relationship("ExecutionEvidence", back_populates="execution", cascade="all, delete-orphan")
    bugs = relationship("Bug", back_populates="execution")

# 14. Test Execution Steps
class TestExecutionStep(Base):
    __test__ = False
    __tablename__ = "test_execution_steps"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("test_executions.id", ondelete="CASCADE"), nullable=False)
    test_step_id = Column(Integer, ForeignKey("test_steps.id", ondelete="SET NULL"), nullable=True)
    sequence = Column(Integer, nullable=False)
    action = Column(String(100), nullable=False)
    target = Column(String(500), nullable=False)
    status = Column(String(50), default="pending", nullable=False)  # passed, failed, skipped, blocked
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    actual_result = Column(Text, nullable=True)

    execution = relationship("TestExecution", back_populates="steps")
    test_step = relationship("TestStep")

# 15. Execution Evidence
class ExecutionEvidence(Base):
    __tablename__ = "execution_evidence"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("test_executions.id", ondelete="CASCADE"), nullable=False)
    type = Column(SQLEnum(EvidenceType), nullable=False)
    file_path = Column(String(1000), nullable=True)
    description = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    execution = relationship("TestExecution", back_populates="evidence")

# 16. Bugs
class Bug(Base):
    __tablename__ = "bugs"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    environment_id = Column(Integer, ForeignKey("environments.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    classification = Column(String(50), default="APPLICATION_BUG", nullable=False)
    category = Column(String(50), default="FUNCTIONAL", nullable=False)
    severity = Column(String(50), default="MEDIUM", nullable=False)  # CRITICAL, HIGH, MEDIUM, LOW
    priority = Column(String(50), default="MEDIUM", nullable=False)  # CRITICAL, HIGH, MEDIUM, LOW
    status = Column(String(50), default="OPEN", nullable=False)      # OPEN, TRIAGED, IN_PROGRESS, FIXED, RETESTED, CLOSED
    affected_page = Column(String(500), nullable=True)
    affected_workflow_id = Column(Integer, ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True)
    affected_test_case_id = Column(Integer, ForeignKey("test_cases.id", ondelete="SET NULL"), nullable=True)
    affected_execution_id = Column(Integer, ForeignKey("test_executions.id", ondelete="SET NULL"), nullable=True)
    failed_step = Column(String(255), nullable=True)
    expected_behavior = Column(Text, nullable=True)
    actual_behavior = Column(Text, nullable=True)
    root_cause = Column(Text, nullable=True)
    root_cause_confidence = Column(Integer, default=50, nullable=True)  # percentage integer 0-100
    confidence_level = Column(String(50), default="LIKELY", nullable=False)  # CONFIRMED, LIKELY, POSSIBLE, UNKNOWN
    severity_explanation = Column(Text, nullable=True)
    failure_signature = Column(String(255), nullable=True, index=True)
    occurrence_count = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    application = relationship("Application", back_populates="bugs")
    environment = relationship("Environment")
    workflow = relationship("Workflow")
    test_case = relationship("TestCase")
    execution = relationship("TestExecution", back_populates="bugs")
    evidence = relationship("BugEvidence", back_populates="bug", cascade="all, delete-orphan")

# 17. Bug Evidence
class BugEvidence(Base):
    __tablename__ = "bug_evidence"

    id = Column(Integer, primary_key=True, index=True)
    bug_id = Column(Integer, ForeignKey("bugs.id", ondelete="CASCADE"), nullable=False)
    type = Column(SQLEnum(EvidenceType), nullable=False)
    file_path = Column(String(1000), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    bug = relationship("Bug", back_populates="evidence")


# ========================================================
# PHASE 6: DATABASE QA & DATA INTEGRITY MODELS
# ========================================================

# 18. Database Connections
class DatabaseConnection(Base):
    __tablename__ = "database_connections"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    environment_id = Column(Integer, ForeignKey("environments.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(255), nullable=False)
    database_type = Column(String(50), nullable=False)  # postgresql, mysql, sqlite
    host = Column(String(255), nullable=True)
    port = Column(Integer, nullable=True)
    database_name = Column(String(255), nullable=False)
    username = Column(String(255), nullable=True)
    password_encrypted = Column(Text, nullable=True)
    read_only = Column(Boolean, default=True, nullable=False)
    status = Column(String(50), default="DISCONNECTED", nullable=False)  # CONNECTED, FAILED, BLOCKED, DISCONNECTED
    last_tested_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    application = relationship("Application", back_populates="database_connections")
    environment = relationship("Environment")
    schemas = relationship("DatabaseSchema", back_populates="database_connection", cascade="all, delete-orphan")
    test_cases = relationship("DatabaseTestCase", back_populates="database_connection", cascade="all, delete-orphan")


# 19. Database Schemas
class DatabaseSchema(Base):
    __tablename__ = "database_schemas"

    id = Column(Integer, primary_key=True, index=True)
    database_connection_id = Column(Integer, ForeignKey("database_connections.id", ondelete="CASCADE"), nullable=False)
    schema_name = Column(String(255), nullable=False)
    discovered_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    database_connection = relationship("DatabaseConnection", back_populates="schemas")
    tables = relationship("DatabaseTable", back_populates="schema", cascade="all, delete-orphan")


# 20. Database Tables
class DatabaseTable(Base):
    __tablename__ = "database_tables"

    id = Column(Integer, primary_key=True, index=True)
    database_schema_id = Column(Integer, ForeignKey("database_schemas.id", ondelete="CASCADE"), nullable=False)
    table_name = Column(String(255), nullable=False)
    row_count = Column(Integer, default=0, nullable=False)
    description = Column(Text, nullable=True)
    discovered_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    schema = relationship("DatabaseSchema", back_populates="tables")
    columns = relationship("DatabaseColumn", back_populates="table", cascade="all, delete-orphan")
    source_relationships = relationship("DatabaseRelationship", foreign_keys="DatabaseRelationship.database_table_id", back_populates="source_table", cascade="all, delete-orphan")


# 21. Database Columns
class DatabaseColumn(Base):
    __tablename__ = "database_columns"

    id = Column(Integer, primary_key=True, index=True)
    database_table_id = Column(Integer, ForeignKey("database_tables.id", ondelete="CASCADE"), nullable=False)
    column_name = Column(String(255), nullable=False)
    data_type = Column(String(100), nullable=False)
    nullable = Column(Boolean, default=True, nullable=False)
    is_primary_key = Column(Boolean, default=False, nullable=False)
    is_foreign_key = Column(Boolean, default=False, nullable=False)
    default_value = Column(String(255), nullable=True)
    discovered_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    table = relationship("DatabaseTable", back_populates="columns")


# 22. Database Relationships
class DatabaseRelationship(Base):
    __tablename__ = "database_relationships"

    id = Column(Integer, primary_key=True, index=True)
    database_table_id = Column(Integer, ForeignKey("database_tables.id", ondelete="CASCADE"), nullable=False)
    related_table_id = Column(Integer, ForeignKey("database_tables.id", ondelete="CASCADE"), nullable=True)
    source_column = Column(String(255), nullable=False)
    target_column = Column(String(255), nullable=False)
    relationship_type = Column(String(50), default="foreign_key", nullable=False)
    discovered_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    source_table = relationship("DatabaseTable", foreign_keys=[database_table_id], back_populates="source_relationships")
    related_table = relationship("DatabaseTable", foreign_keys=[related_table_id])


# 23. Database Test Cases
class DatabaseTestCase(Base):
    __tablename__ = "database_test_cases"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    environment_id = Column(Integer, ForeignKey("environments.id", ondelete="SET NULL"), nullable=True)
    database_connection_id = Column(Integer, ForeignKey("database_connections.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), default="DATA_INTEGRITY", nullable=False)  # DATA_INTEGRITY, CRUD_VALIDATION, REFERENTIAL_INTEGRITY, NULLABILITY, DUPLICATE_DATA, TYPE_VALIDATION, CONSTRAINT
    priority = Column(String(50), default="HIGH", nullable=False)  # CRITICAL, HIGH, MEDIUM, LOW
    source_test_case_id = Column(Integer, ForeignKey("test_cases.id", ondelete="SET NULL"), nullable=True)
    validation_definition = Column(JSON, nullable=False)  # table, lookup, checks
    status = Column(String(50), default="active", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    application = relationship("Application")
    database_connection = relationship("DatabaseConnection", back_populates="test_cases")
    source_test_case = relationship("TestCase")
    executions = relationship("DatabaseTestExecution", back_populates="test_case", cascade="all, delete-orphan", order_by="DatabaseTestExecution.created_at.desc()")


# 24. Database Test Executions
class DatabaseTestExecution(Base):
    __tablename__ = "database_test_executions"

    id = Column(Integer, primary_key=True, index=True)
    database_test_case_id = Column(Integer, ForeignKey("database_test_cases.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(50), default="QUEUED", nullable=False)  # QUEUED, RUNNING, PASSED, FAILED, BLOCKED, ERROR
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, default=0, nullable=False)
    expected_result = Column(JSON, nullable=True)
    actual_result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    test_case = relationship("DatabaseTestCase", back_populates="executions")
    evidence = relationship("DatabaseEvidence", back_populates="execution", cascade="all, delete-orphan")


# 25. Database Evidence
class DatabaseEvidence(Base):
    __tablename__ = "database_evidence"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("database_test_executions.id", ondelete="CASCADE"), nullable=False)
    sanitized_query = Column(Text, nullable=False)
    parameters = Column(JSON, nullable=True)  # sensitive values redacted
    comparison_summary = Column(Text, nullable=True)
    raw_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    execution = relationship("DatabaseTestExecution", back_populates="evidence")



