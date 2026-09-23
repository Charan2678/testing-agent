import os
import sys

# Configure isolated test database URL in environment BEFORE importing backend modules
TEST_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "test_autonomous_qa.db")).replace("\\", "/")
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

# Drop cached config or connection if loaded previously
for mod in list(sys.modules.keys()):
    if mod.startswith("backend.app.core.config") or mod.startswith("backend.app.database.connection"):
        del sys.modules[mod]

import pytest
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

# Import models and connection
import backend.app.database.connection as db_conn
from backend.app.database.models.models import (
    Base,
    Application,
    Environment,
    EnvironmentType,
    Page,
    Element,
    TestCase as DBTestCase,
    TestStep as DBTestStep,
    DatabaseConnection
)
from backend.app.main import app

# Create isolated test engine
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Rebind connection engine and SessionLocal in place so every imported reference uses test_engine
db_conn.engine = test_engine
db_conn.SessionLocal.configure(bind=test_engine)
db_conn.SessionLocal = TestingSessionLocal

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """
    Session-level fixture:
    1. Ensures dev DB is not used.
    2. Drops and recreates all tables in isolated test database.
    3. Seeds baseline application data for independent test execution.
    4. Cleans up test database upon completion.
    """
    assert "autonomous_qa.db" not in TEST_DATABASE_URL or "test_autonomous_qa.db" in TEST_DATABASE_URL, \
        "SAFETY ERROR: Tests attempted to use development database!"

    # Clean previous test database if exists
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    # Seed baseline Application #2 (Target Test Application) and test data so all tests can run independently
    seed_db = TestingSessionLocal()
    try:
        app2 = Application(
            id=2,
            name="Target Test Application",
            description="Autonomous crawl validation target app"
        )
        seed_db.add(app2)
        seed_db.commit()
        seed_db.refresh(app2)

        env2 = Environment(
            id=1,
            application_id=app2.id,
            name="Local Test Server",
            base_url="http://127.0.0.1:3000",
            environment_type=EnvironmentType.DEV
        )
        seed_db.add(env2)

        # Seed sample discovered pages so Phase 2 / Phase 3 / Phase 6 can run independently
        p1 = Page(
            id=1,
            application_id=app2.id,
            environment_id=env2.id,
            url="http://127.0.0.1:3000/",
            title="Dashboard",
            page_type="dashboard"
        )
        p2 = Page(
            id=2,
            application_id=app2.id,
            environment_id=env2.id,
            url="http://127.0.0.1:3000/products",
            title="Products Catalog",
            page_type="catalog"
        )
        p3 = Page(
            id=3,
            application_id=app2.id,
            environment_id=env2.id,
            url="http://127.0.0.1:3000/login",
            title="User Login",
            page_type="auth"
        )
        seed_db.add_all([p1, p2, p3])
        seed_db.commit()

        # Seed sample elements for products page
        e1 = Element(
            page_id=p2.id,
            element_type="button",
            tag_name="button",
            selector="#btn-add-product",
            text="Add Product",
            role="button",
            is_interactive=True
        )
        # Seed sample elements for login page
        e2 = Element(
            page_id=p3.id,
            element_type="text",
            tag_name="input",
            selector="#input-username",
            name="username",
            placeholder="Enter username",
            is_interactive=True
        )
        e3 = Element(
            page_id=p3.id,
            element_type="password",
            tag_name="input",
            selector="#input-password",
            name="password",
            placeholder="Enter password",
            is_interactive=True
        )
        e4 = Element(
            page_id=p3.id,
            element_type="button",
            tag_name="button",
            selector="#btn-login-submit",
            text="Sign In",
            role="button",
            is_interactive=True
        )
        seed_db.add_all([e1, e2, e3, e4])
        seed_db.commit()

        # Seed baseline TestCase for Application #2
        tc1 = DBTestCase(
            id=1,
            application_id=app2.id,
            name="View Products Catalog",
            category="smoke",
            priority="high",
            description="Verify products page loads and contains products table"
        )
        seed_db.add(tc1)
        seed_db.commit()

        ts1 = DBTestStep(
            test_case_id=tc1.id,
            sequence=1,
            action="navigate",
            target="http://127.0.0.1:3000/products",
            expected_result="Page loaded with status 200"
        )
        seed_db.add(ts1)

        # Seed Target Database Connection for App #2 (pointing to test-app/crm_development.db)
        crm_db_path = os.path.abspath("test-app/crm_development.db").replace("\\", "/")
        db_conn_record = DatabaseConnection(
            id=1,
            application_id=app2.id,
            environment_id=env2.id,
            name="CRM Development Database",
            database_type="sqlite",
            database_name=crm_db_path,
            read_only=True,
            status="CONNECTED"
        )
        seed_db.add(db_conn_record)
        seed_db.commit()
    finally:
        seed_db.close()

    yield

    # Teardown: Clean up test database
    try:
        test_engine.dispose()
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)
    except Exception:
        pass


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provides an isolated database session per test with automatic cleanup."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with overridden get_db dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[db_conn.get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
