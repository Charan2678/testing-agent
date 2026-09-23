import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.database.models.models import (
    DatabaseTestCase,
    DatabaseTestExecution,
    DatabaseConnection,
    Bug,
    BugEvidence,
    EvidenceType
)
from backend.app.database.repositories.database_qa_repo import DatabaseQARepository
from backend.app.database.repositories.bug_repo import BugRepository
from backend.app.database_qa.connection_manager import DatabaseConnectionManager
from backend.app.database_qa.validator import DatabaseSafetyValidator

logger = logging.getLogger("autonomous-qa-agent.db_runner")

class DatabaseTestRunner:
    """
    Executes database integrity and validation test cases against target database.
    Evaluates expected vs actual values, captures evidence, and integrates
    failures with the Phase 4 defect tracking system.
    """

    def __init__(self, db: Session):
        self.db = db
        self.repo = DatabaseQARepository(db)
        self.bug_repo = BugRepository(db)

    async def execute_test_case(self, test_case_id: int) -> DatabaseTestExecution:
        tc = self.repo.get_test_case(test_case_id)
        if not tc:
            raise ValueError(f"Database test case #{test_case_id} not found.")

        conn_config = tc.database_connection
        if not conn_config:
            raise ValueError(f"No database connection configured for test case #{test_case_id}.")

        exec_record = self.repo.create_execution(test_case_id)
        start_mono = time.monotonic()

        sanitized_query = ""
        sanitized_params = {}
        expected_res: Dict[str, Any] = {}
        actual_res: Dict[str, Any] = {}
        status = "PASSED"
        err_msg: Optional[str] = None
        comparison_summary = ""

        try:
            engine = DatabaseConnectionManager.get_engine(conn_config, conn_config.environment)
            val_def = tc.validation_definition or {}
            val_type = val_def.get("type", "field_comparison")

            with engine.connect() as target_conn:
                if val_type == "field_comparison":
                    table = val_def.get("table")
                    lookup = val_def.get("lookup", {})
                    expected_fields = val_def.get("expected_fields", {})
                    lookup_col = lookup.get("column")
                    lookup_val = lookup.get("value")

                    query_str = f"SELECT * FROM {table} WHERE {lookup_col} = :lookup_val"
                    DatabaseSafetyValidator.validate_sql_read_only(query_str)
                    sanitized_query = query_str
                    sanitized_params = DatabaseSafetyValidator.sanitize_evidence_params({"lookup_val": lookup_val})

                    res = target_conn.execute(text(query_str), {"lookup_val": lookup_val})
                    row = res.mappings().fetchone()

                    expected_res = {"lookup": lookup, "fields": expected_fields}

                    if not row:
                        status = "FAILED"
                        err_msg = f"Target record with {lookup_col}='{lookup_val}' was not found in table '{table}'."
                        actual_res = {"found": False}
                        comparison_summary = f"Expected record with {lookup_col}='{lookup_val}' to exist, but 0 rows returned."
                    else:
                        actual_fields = dict(row)
                        actual_res = {"found": True, "fields": {k: actual_fields.get(k) for k in expected_fields}}
                        mismatches = []

                        for field, expected_val in expected_fields.items():
                            actual_val = actual_fields.get(field)
                            # Handle numeric conversions safely (e.g. float comparison)
                            is_match = False
                            if isinstance(expected_val, (int, float)) and isinstance(actual_val, (int, float)):
                                is_match = abs(float(expected_val) - float(actual_val)) < 0.001
                            else:
                                is_match = str(expected_val) == str(actual_val)

                            if not is_match:
                                mismatches.append(f"{field}: expected '{expected_val}', got '{actual_val}'")

                        if mismatches:
                            status = "FAILED"
                            err_msg = f"Data integrity mismatch in {table}: " + "; ".join(mismatches)
                            comparison_summary = f"Mismatches detected: {'; '.join(mismatches)}"
                        else:
                            status = "PASSED"
                            comparison_summary = f"All {len(expected_fields)} expected field values matched actual database state."

                elif val_type == "orphan_check":
                    s_table = val_def.get("source_table")
                    s_col = val_def.get("source_column")
                    r_table = val_def.get("related_table")
                    r_col = val_def.get("related_column")

                    query_str = f"""
                    SELECT s.{s_col} 
                    FROM {s_table} s 
                    LEFT JOIN {r_table} r ON s.{s_col} = r.{r_col} 
                    WHERE r.{r_col} IS NULL AND s.{s_col} IS NOT NULL
                    """
                    DatabaseSafetyValidator.validate_sql_read_only(query_str)
                    sanitized_query = " ".join(query_str.split())

                    res = target_conn.execute(text(query_str))
                    orphan_rows = res.fetchall()

                    expected_res = {"orphan_records_count": 0}
                    actual_res = {"orphan_records_count": len(orphan_rows)}

                    if len(orphan_rows) > 0:
                        status = "FAILED"
                        err_msg = f"Referential integrity violation: Found {len(orphan_rows)} orphan records in {s_table}.{s_col} with no parent in {r_table}.{r_col}."
                        comparison_summary = err_msg
                    else:
                        status = "PASSED"
                        comparison_summary = f"Referential integrity verified: 0 orphan records found between {s_table} and {r_table}."

                elif val_type == "nullability_check":
                    table = val_def.get("table")
                    columns = val_def.get("columns", [])
                    null_violations = []

                    for col in columns:
                        query_str = f"SELECT COUNT(*) FROM {table} WHERE {col} IS NULL"
                        DatabaseSafetyValidator.validate_sql_read_only(query_str)
                        res = target_conn.execute(text(query_str))
                        cnt = res.scalar() or 0
                        if cnt > 0:
                            null_violations.append(f"{col} has {cnt} NULL rows")

                    sanitized_query = f"SELECT COUNT(*) FROM {table} WHERE [col] IS NULL"
                    expected_res = {"unexpected_nulls_count": 0}
                    actual_res = {"null_violations": null_violations}

                    if null_violations:
                        status = "FAILED"
                        err_msg = f"Nullability constraint violation in {table}: " + "; ".join(null_violations)
                        comparison_summary = err_msg
                    else:
                        status = "PASSED"
                        comparison_summary = f"Nullability verified: Required columns in {table} contain 0 NULL rows."

                elif val_type == "custom_sql":
                    query_str = val_def.get("query", "")
                    DatabaseSafetyValidator.validate_sql_read_only(query_str)
                    sanitized_query = " ".join(query_str.split())
                    expected_cond = val_def.get("expected_condition", "count == 0")

                    res = target_conn.execute(text(query_str))
                    row = res.mappings().fetchone()
                    actual_dict = dict(row) if row else {}
                    actual_res = actual_dict
                    expected_res = {"condition": expected_cond}

                    passed = False
                    if "==" in expected_cond:
                        key, val = [p.strip() for p in expected_cond.split("==")]
                        expected_val = int(val) if val.isdigit() else val
                        actual_val = actual_dict.get(key)
                        if str(actual_val) == str(expected_val):
                            passed = True
                    elif ">" in expected_cond:
                        key, val = [p.strip() for p in expected_cond.split(">")]
                        passed = float(actual_dict.get(key, 0)) > float(val)

                    if passed:
                        status = "PASSED"
                        comparison_summary = f"Custom SQL assertion passed: {expected_cond} matched {actual_dict}."
                    else:
                        status = "FAILED"
                        err_msg = f"Custom SQL assertion failed: expected {expected_cond}, but actual result was {actual_dict}."
                        comparison_summary = err_msg

                else:
                    status = "ERROR"
                    err_msg = f"Unknown validation type '{val_type}'"

        except Exception as ex:
            status = "ERROR"
            err_msg = f"Database test execution failed: {str(ex)}"
            logger.error(f"Error executing DB test #{test_case_id}: {ex}")

        duration_ms = int((time.monotonic() - start_mono) * 1000)

        # Update execution record
        updated_exec = self.repo.update_execution(
            execution_id=exec_record.id,
            status=status,
            duration_ms=duration_ms,
            expected_result=expected_res,
            actual_result=actual_res,
            error_message=err_msg
        )

        # Store evidence
        self.repo.add_evidence(
            execution_id=exec_record.id,
            sanitized_query=sanitized_query or "N/A",
            parameters=sanitized_params,
            comparison_summary=comparison_summary or err_msg,
            raw_data=actual_res
        )

        # Integrate failure with Phase 4 Bug Engine
        if status in ("FAILED", "ERROR"):
            try:
                self._file_database_bug(tc, updated_exec, err_msg, expected_res, actual_res)
            except Exception as bug_err:
                logger.warning(f"Could not file database defect for test #{test_case_id}: {bug_err}")

        return updated_exec

    def _file_database_bug(
        self,
        test_case: DatabaseTestCase,
        execution: DatabaseTestExecution,
        error_message: Optional[str],
        expected_res: Dict[str, Any],
        actual_res: Dict[str, Any]
    ) -> Bug:
        import hashlib
        sig_input = f"{test_case.application_id}:database:{test_case.name}:{error_message or ''}"
        sig = hashlib.sha256(sig_input.encode("utf-8")).hexdigest()[:16]

        # Check existing open bug for deduplication
        existing = self.db.query(Bug).filter(
            Bug.application_id == test_case.application_id,
            Bug.failure_signature == sig,
            Bug.status != "CLOSED"
        ).first()

        if existing:
            existing.occurrence_count += 1
            existing.updated_at = datetime.utcnow()
            self.db.commit()
            return existing

        bug = self.bug_repo.create_bug(
            application_id=test_case.application_id,
            environment_id=test_case.environment_id,
            title=f"[DATABASE_INTEGRITY_BUG] {test_case.name}",
            summary=f"Database state divergence detected during {test_case.category} validation.",
            description=error_message or "Data verification failed.",
            classification="APPLICATION_BUG",
            category="DATABASE_INTEGRITY_BUG",
            severity=test_case.priority.upper() if test_case.priority else "HIGH",
            priority="HIGH",
            status="OPEN",
            affected_page=f"Database Table: {test_case.validation_definition.get('table', 'unknown')}",
            affected_workflow_id=None,
            affected_test_case_id=test_case.source_test_case_id,
            affected_execution_id=None,
            failed_step=f"Database validation check '{test_case.category}'",
            expected_behavior=str(expected_res),
            actual_behavior=str(actual_res),
            root_cause="Database record values do not conform to expected business entity constraints or workflow side effects.",
            root_cause_confidence=92,
            confidence_level="CONFIRMED",
            severity_explanation="Data persistence inaccuracy compromises business workflows and application state integrity.",
            failure_signature=sig
        )
        return bug
