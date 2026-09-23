import pytest
import os
from sqlalchemy.orm import Session
from backend.app.database.connection import SessionLocal
from backend.app.database.models.models import (
    Application,
    Environment,
    DatabaseConnection,
    DatabaseSchema,
    DatabaseTestCase,
    DatabaseTestExecution,
    Bug
)
from backend.app.database_qa.validator import DatabaseSafetyValidator, UnsafeQueryException
from backend.app.database_qa.connection_manager import DatabaseConnectionManager
from backend.app.database_qa.inspector import DatabaseInspector
from backend.app.database_qa.generator import DatabaseTestCaseGenerator
from backend.app.database_qa.runner import DatabaseTestRunner
from backend.app.database.repositories.database_qa_repo import DatabaseQARepository


def test_safety_validator_accepts_read_only():
    """Verify read-only SELECT queries pass validation."""
    safe_queries = [
        "SELECT count(*) as count FROM products WHERE price < 0",
        "SELECT id, name FROM users WHERE email IS NULL",
        "SELECT o.id FROM orders o LEFT JOIN users u ON o.user_id = u.id WHERE u.id IS NULL",
        "select 1 from categories"
    ]
    for q in safe_queries:
        sanitized = DatabaseSafetyValidator.validate_read_only(q)
        assert sanitized.lower().startswith("select")


def test_safety_validator_blocks_mutations():
    """Verify all destructive and mutation statements are strictly rejected."""
    dangerous_queries = [
        "DELETE FROM products WHERE id = 1",
        "DROP TABLE users",
        "UPDATE products SET price = 100",
        "INSERT INTO categories (name) VALUES ('Test')",
        "TRUNCATE TABLE order_items",
        "ALTER TABLE users ADD COLUMN hacked text",
        "CREATE TABLE test (id int)",
        "SELECT * FROM products; DROP TABLE products;",
        "SELECT * FROM products; DELETE FROM users;"
    ]
    for q in dangerous_queries:
        with pytest.raises(UnsafeQueryException):
            DatabaseSafetyValidator.validate_read_only(q)


def test_connection_safety_guards():
    """Verify production environments and credentials exposure protections."""
    # Mask password
    masked = DatabaseConnectionManager.mask_connection_password("sqlite:///test.db")
    assert "sqlite" in masked

    postgres_url = "postgresql://qa_user:super_secret_password_123@db.internal:5432/crm_db"
    masked_pg = DatabaseConnectionManager.mask_connection_password(postgres_url)
    assert "super_secret_password_123" not in masked_pg
    assert "******" in masked_pg

    # Reject production environment
    prod_env = Environment(name="Production", base_url="https://crm.company.com", environment_type="production")
    conn = DatabaseConnection(
        application_id=1,
        name="Prod DB",
        database_type="postgresql",
        database_name="prod_db",
        host="prod-db.company.internal",
        read_only=True
    )
    status, err = DatabaseConnectionManager.test_connection(conn, prod_env)
    assert status == "BLOCKED"
    assert "Production database connections are strictly blocked" in err


def test_target_schema_discovery():
    """Verify live schema discovery against the target CRM SQLite database."""
    target_db_path = os.path.abspath("test-app/crm_development.db")
    if not os.path.exists(target_db_path):
        import sys
        sys.path.insert(0, os.path.abspath("test-app"))
        from db import init_crm_db
        init_crm_db()

    conn = DatabaseConnection(
        application_id=2,
        name="CRM Dev DB",
        database_type="sqlite",
        database_name=target_db_path,
        read_only=True
    )

    engine = DatabaseConnectionManager.get_engine(conn)
    discovered = DatabaseInspector.discover_database(engine)

    assert len(discovered) >= 1
    main_schema = discovered[0]
    assert "tables" in main_schema
    table_names = [t["name"] for t in main_schema["tables"]]
    assert "products" in table_names
    assert "categories" in table_names
    assert "users" in table_names
    assert "orders" in table_names
    assert "order_items" in table_names

    # Check columns of products table
    products_table = next(t for t in main_schema["tables"] if t["name"] == "products")
    col_names = [c["name"] for c in products_table["columns"]]
    assert "id" in col_names
    assert "title" in col_names
    assert "price" in col_names
    assert "category_id" in col_names

    # Check relationships
    assert len(products_table["relationships"]) >= 1
    fk = products_table["relationships"][0]
    assert fk["source_column"] == "category_id"
    assert fk["related_table"] == "categories"


def test_test_case_synthesis_from_schema():
    """Verify automated synthesis of data integrity test cases from schema."""
    db: Session = SessionLocal()
    try:
        repo = DatabaseQARepository(db)
        app = db.query(Application).filter(Application.id == 2).first()
        if not app:
            app = Application(id=2, name="Target Test Application")
            db.add(app)
            db.commit()

        # Get existing connection or create one
        conns = repo.get_connections_by_application(2)
        if not conns:
            target_db_path = os.path.abspath("test-app/crm_development.db")
            conn = repo.create_connection(
                application_id=2,
                name="CRM Test DB",
                database_type="sqlite",
                database_name=target_db_path,
                read_only=True
            )
        else:
            conn = conns[0]

        schemas = repo.get_schemas_with_details(conn.id)
        if not schemas:
            engine = DatabaseConnectionManager.get_engine(conn)
            discovered_data = DatabaseInspector.discover_database(engine)
            schemas = repo.save_discovered_schema(conn.id, discovered_data)

        # Generate test cases
        test_defs = DatabaseTestCaseGenerator.generate_test_cases(schemas)
        assert len(test_defs) > 0

        categories = {td["category"] for td in test_defs}
        assert "REFERENTIAL_INTEGRITY" in categories or "DATA_INTEGRITY" in categories
    finally:
        db.close()


@pytest.mark.asyncio
async def test_database_test_case_execution_passed():
    """Verify execution of passing data integrity test case with evidence capture."""
    db: Session = SessionLocal()
    try:
        repo = DatabaseQARepository(db)
        conns = repo.get_connections_by_application(2)
        if not conns:
            target_db_path = os.path.abspath("test-app/crm_development.db").replace("\\", "/")
            conn = repo.create_connection(
                application_id=2,
                name="CRM Test DB",
                database_type="sqlite",
                database_name=target_db_path,
                read_only=True
            )
        else:
            conn = conns[0]

        # Create a passing test case
        tc = repo.create_test_case(
            application_id=2,
            database_connection_id=conn.id,
            name="Valid Non-Null Primary Keys: Categories",
            category="DATA_INTEGRITY",
            priority="HIGH",
            validation_definition={
                "type": "custom_sql",
                "table": "categories",
                "query": "SELECT count(*) as count FROM categories WHERE id IS NULL",
                "expected_condition": "count == 0"
            }
        )

        runner = DatabaseTestRunner(db)
        exec_res = await runner.execute_test_case(tc.id)

        assert exec_res.status == "PASSED"
        assert exec_res.actual_result.get("count") == 0
        assert exec_res.duration_ms >= 0

        # Verify evidence
        details = repo.get_execution_details(exec_res.id)
        assert details is not None
        assert len(details.evidence) >= 1
        assert "categories" in details.evidence[0].sanitized_query
    finally:
        db.close()


@pytest.mark.asyncio
async def test_database_test_case_execution_failed_and_bug_filed():
    """Verify failing assertion logs defect under Phase 4 Bug Intelligence."""
    db: Session = SessionLocal()
    try:
        repo = DatabaseQARepository(db)
        conns = repo.get_connections_by_application(2)
        if not conns:
            target_db_path = os.path.abspath("test-app/crm_development.db").replace("\\", "/")
            conn = repo.create_connection(
                application_id=2,
                name="CRM Test DB",
                database_type="sqlite",
                database_name=target_db_path,
                read_only=True
            )
        else:
            conn = conns[0]

        import time
        unique_name = f"Empty Categories Audit Failure {int(time.time() * 1000)}"
        tc = repo.create_test_case(
            application_id=2,
            database_connection_id=conn.id,
            name=unique_name,
            category="DATA_INTEGRITY",
            priority="CRITICAL",
            validation_definition={
                "type": "custom_sql",
                "table": "categories",
                "query": "SELECT count(*) as count FROM categories",
                "expected_condition": "count == 0"
            }
        )

        runner = DatabaseTestRunner(db)
        exec_res = await runner.execute_test_case(tc.id)

        assert exec_res.status == "FAILED"
        assert exec_res.actual_result.get("count") > 0

        # Verify bug ticket was filed in bugs table
        bug = db.query(Bug).filter(
            Bug.application_id == 2,
            Bug.category == "DATABASE_INTEGRITY_BUG",
            Bug.title.contains(unique_name)
        ).first()

        assert bug is not None
        assert bug.classification == "APPLICATION_BUG"
        assert bug.category == "DATABASE_INTEGRITY_BUG"
        assert "[DATABASE_INTEGRITY_BUG]" in bug.title
    finally:
        db.close()
