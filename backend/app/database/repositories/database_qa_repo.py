from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from backend.app.database.models.models import (
    DatabaseConnection,
    DatabaseSchema,
    DatabaseTable,
    DatabaseColumn,
    DatabaseRelationship,
    DatabaseTestCase,
    DatabaseTestExecution,
    DatabaseEvidence
)

class DatabaseQARepository:
    def __init__(self, db: Session):
        self.db = db

    # --- CONNECTIONS ---
    def create_connection(
        self,
        application_id: int,
        name: str,
        database_type: str,
        database_name: str,
        environment_id: Optional[int] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        read_only: bool = True
    ) -> DatabaseConnection:
        conn = DatabaseConnection(
            application_id=application_id,
            environment_id=environment_id,
            name=name,
            database_type=database_type.lower(),
            host=host,
            port=port,
            database_name=database_name,
            username=username,
            password_encrypted=password,  # Stored internally, never returned to client
            read_only=read_only,
            status="DISCONNECTED"
        )
        self.db.add(conn)
        self.db.commit()
        self.db.refresh(conn)
        return conn

    def get_connection(self, connection_id: int) -> Optional[DatabaseConnection]:
        return self.db.query(DatabaseConnection).filter(DatabaseConnection.id == connection_id).first()

    def get_connections_by_application(self, application_id: int) -> List[DatabaseConnection]:
        return self.db.query(DatabaseConnection).filter(
            DatabaseConnection.application_id == application_id
        ).order_by(DatabaseConnection.created_at.desc()).all()

    def update_connection_status(
        self,
        connection_id: int,
        status: str,
        last_error: Optional[str] = None
    ) -> Optional[DatabaseConnection]:
        conn = self.get_connection(connection_id)
        if conn:
            conn.status = status
            conn.last_tested_at = datetime.utcnow()
            conn.last_error = last_error
            self.db.commit()
            self.db.refresh(conn)
        return conn

    def delete_connection(self, connection_id: int) -> bool:
        conn = self.get_connection(connection_id)
        if conn:
            self.db.delete(conn)
            self.db.commit()
            return True
        return False

    # --- SCHEMA DISCOVERY PERSISTENCE ---
    def save_discovered_schema(
        self,
        connection_id: int,
        schemas_data: List[Dict[str, Any]]
    ) -> List[DatabaseSchema]:
        """
        Replaces/updates discovered schema structures for the connection cleanly.
        """
        # Delete old schemas for clean sync
        old_schemas = self.db.query(DatabaseSchema).filter(
            DatabaseSchema.database_connection_id == connection_id
        ).all()
        for s in old_schemas:
            self.db.delete(s)
        self.db.commit()

        created_schemas = []
        table_name_to_id = {}

        # 1. Create Schemas, Tables, Columns
        for s_data in schemas_data:
            db_schema = DatabaseSchema(
                database_connection_id=connection_id,
                schema_name=s_data.get("schema_name", "public")
            )
            self.db.add(db_schema)
            self.db.flush()

            for t_data in s_data.get("tables", []):
                db_table = DatabaseTable(
                    database_schema_id=db_schema.id,
                    table_name=t_data.get("name"),
                    row_count=t_data.get("row_count", 0),
                    description=t_data.get("description")
                )
                self.db.add(db_table)
                self.db.flush()
                table_name_to_id[db_table.table_name] = db_table.id

                for c_data in t_data.get("columns", []):
                    db_col = DatabaseColumn(
                        database_table_id=db_table.id,
                        column_name=c_data.get("name"),
                        data_type=str(c_data.get("type", "TEXT")),
                        nullable=c_data.get("nullable", True),
                        is_primary_key=c_data.get("is_primary_key", False),
                        is_foreign_key=c_data.get("is_foreign_key", False),
                        default_value=str(c_data.get("default")) if c_data.get("default") is not None else None
                    )
                    self.db.add(db_col)

            created_schemas.append(db_schema)

        self.db.flush()

        # 2. Create Relationships across tables
        for s_data in schemas_data:
            for t_data in s_data.get("tables", []):
                source_id = table_name_to_id.get(t_data.get("name"))
                if not source_id:
                    continue
                for r_data in t_data.get("relationships", []):
                    rel_table_name = r_data.get("related_table")
                    rel_id = table_name_to_id.get(rel_table_name)
                    rel = DatabaseRelationship(
                        database_table_id=source_id,
                        related_table_id=rel_id,
                        source_column=r_data.get("source_column"),
                        target_column=r_data.get("target_column"),
                        relationship_type=r_data.get("relationship_type", "foreign_key")
                    )
                    self.db.add(rel)

        self.db.commit()
        return self.get_schemas_with_details(connection_id)

    def get_schemas_with_details(self, connection_id: int) -> List[DatabaseSchema]:
        return self.db.query(DatabaseSchema).filter(
            DatabaseSchema.database_connection_id == connection_id
        ).options(
            joinedload(DatabaseSchema.tables)
            .joinedload(DatabaseTable.columns),
            joinedload(DatabaseSchema.tables)
            .joinedload(DatabaseTable.source_relationships)
        ).all()

    def get_table(self, table_id: int) -> Optional[DatabaseTable]:
        return self.db.query(DatabaseTable).filter(
            DatabaseTable.id == table_id
        ).options(
            joinedload(DatabaseTable.columns),
            joinedload(DatabaseTable.source_relationships)
        ).first()

    # --- TEST CASES ---
    def create_test_case(
        self,
        application_id: int,
        database_connection_id: int,
        name: str,
        category: str,
        priority: str,
        validation_definition: Dict[str, Any],
        environment_id: Optional[int] = None,
        source_test_case_id: Optional[int] = None,
        description: Optional[str] = None
    ) -> DatabaseTestCase:
        tc = DatabaseTestCase(
            application_id=application_id,
            environment_id=environment_id,
            database_connection_id=database_connection_id,
            name=name,
            description=description,
            category=category,
            priority=priority,
            source_test_case_id=source_test_case_id,
            validation_definition=validation_definition,
            status="active"
        )
        self.db.add(tc)
        self.db.commit()
        self.db.refresh(tc)
        return tc

    def get_test_case(self, test_case_id: int) -> Optional[DatabaseTestCase]:
        return self.db.query(DatabaseTestCase).filter(DatabaseTestCase.id == test_case_id).first()

    def get_test_cases_by_application(self, application_id: int) -> List[DatabaseTestCase]:
        return self.db.query(DatabaseTestCase).filter(
            DatabaseTestCase.application_id == application_id
        ).order_by(DatabaseTestCase.created_at.desc()).all()

    def get_test_cases_by_connection(self, connection_id: int) -> List[DatabaseTestCase]:
        return self.db.query(DatabaseTestCase).filter(
            DatabaseTestCase.database_connection_id == connection_id
        ).order_by(DatabaseTestCase.created_at.desc()).all()

    # --- EXECUTIONS & EVIDENCE ---
    def create_execution(self, database_test_case_id: int) -> DatabaseTestExecution:
        exec_record = DatabaseTestExecution(
            database_test_case_id=database_test_case_id,
            status="RUNNING",
            started_at=datetime.utcnow()
        )
        self.db.add(exec_record)
        self.db.commit()
        self.db.refresh(exec_record)
        return exec_record

    def update_execution(
        self,
        execution_id: int,
        status: str,
        duration_ms: int,
        expected_result: Optional[Dict[str, Any]] = None,
        actual_result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> Optional[DatabaseTestExecution]:
        rec = self.db.query(DatabaseTestExecution).filter(DatabaseTestExecution.id == execution_id).first()
        if rec:
            rec.status = status
            rec.duration_ms = duration_ms
            rec.completed_at = datetime.utcnow()
            rec.expected_result = expected_result
            rec.actual_result = actual_result
            rec.error_message = error_message
            self.db.commit()
            self.db.refresh(rec)
        return rec

    def add_evidence(
        self,
        execution_id: int,
        sanitized_query: str,
        parameters: Optional[Dict[str, Any]] = None,
        comparison_summary: Optional[str] = None,
        raw_data: Optional[Dict[str, Any]] = None
    ) -> DatabaseEvidence:
        ev = DatabaseEvidence(
            execution_id=execution_id,
            sanitized_query=sanitized_query,
            parameters=parameters,
            comparison_summary=comparison_summary,
            raw_data=raw_data
        )
        self.db.add(ev)
        self.db.commit()
        self.db.refresh(ev)
        return ev

    def get_executions_by_test_case(self, test_case_id: int, limit: int = 20) -> List[DatabaseTestExecution]:
        return self.db.query(DatabaseTestExecution).filter(
            DatabaseTestExecution.database_test_case_id == test_case_id
        ).options(
            joinedload(DatabaseTestExecution.evidence)
        ).order_by(DatabaseTestExecution.created_at.desc()).limit(limit).all()

    def get_execution_details(self, execution_id: int) -> Optional[DatabaseTestExecution]:
        return self.db.query(DatabaseTestExecution).filter(
            DatabaseTestExecution.id == execution_id
        ).options(
            joinedload(DatabaseTestExecution.evidence),
            joinedload(DatabaseTestExecution.test_case)
        ).first()

    # --- SUMMARY ---
    def get_connection_summary(self, connection_id: int) -> Dict[str, Any]:
        conn = self.get_connection(connection_id)
        if not conn:
            return {}

        schema_count = self.db.query(DatabaseSchema).filter(DatabaseSchema.database_connection_id == connection_id).count()
        table_count = self.db.query(DatabaseTable).join(DatabaseSchema).filter(DatabaseSchema.database_connection_id == connection_id).count()
        column_count = self.db.query(DatabaseColumn).join(DatabaseTable).join(DatabaseSchema).filter(DatabaseSchema.database_connection_id == connection_id).count()
        rel_count = self.db.query(DatabaseRelationship).join(DatabaseTable, DatabaseRelationship.database_table_id == DatabaseTable.id).join(DatabaseSchema).filter(DatabaseSchema.database_connection_id == connection_id).count()
        test_case_count = self.db.query(DatabaseTestCase).filter(DatabaseTestCase.database_connection_id == connection_id).count()

        execs = self.db.query(DatabaseTestExecution).join(DatabaseTestCase).filter(
            DatabaseTestCase.database_connection_id == connection_id
        ).all()
        passed_count = sum(1 for e in execs if e.status == "PASSED")
        failed_count = sum(1 for e in execs if e.status in ("FAILED", "ERROR"))
        blocked_count = sum(1 for e in execs if e.status == "BLOCKED")

        return {
            "connection_id": conn.id,
            "name": conn.name,
            "database_type": conn.database_type,
            "status": conn.status,
            "read_only": conn.read_only,
            "schemas_count": schema_count,
            "tables_count": table_count,
            "columns_count": column_count,
            "relationships_count": rel_count,
            "test_cases_count": test_case_count,
            "executions_total": len(execs),
            "executions_passed": passed_count,
            "executions_failed": failed_count,
            "executions_blocked": blocked_count,
            "last_tested_at": conn.last_tested_at.isoformat() if conn.last_tested_at else None
        }
