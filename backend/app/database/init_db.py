from sqlalchemy import inspect, text
from backend.app.database.connection import engine, SessionLocal
from backend.app.database.models.models import (
    Base, Application, Environment, EnvironmentType,
    Page, Workflow, WorkflowStep, TestCase, TestStep
)
from backend.app.core.logging import logger

def seed_initial_data(db):
    """Seed default application and baseline records if database is empty."""
    try:
        if db.query(Application).count() == 0:
            logger.info("Database is empty. Seeding baseline application and demo data...")
            app = Application(
                name="Target Test Application",
                description="Autonomous crawl validation target app"
            )
            db.add(app)
            db.commit()
            db.refresh(app)

            env = Environment(
                application_id=app.id,
                name="Local Test Server",
                base_url="http://127.0.0.1:3000",
                environment_type=EnvironmentType.DEV
            )
            db.add(env)
            db.commit()
            db.refresh(env)

            # Seed baseline pages
            p1 = Page(
                application_id=app.id,
                environment_id=env.id,
                url="http://127.0.0.1:3000/",
                title="Dashboard",
                page_type="dashboard"
            )
            p2 = Page(
                application_id=app.id,
                environment_id=env.id,
                url="http://127.0.0.1:3000/products",
                title="Products Catalog",
                page_type="catalog"
            )
            p3 = Page(
                application_id=app.id,
                environment_id=env.id,
                url="http://127.0.0.1:3000/login",
                title="User Login",
                page_type="auth"
            )
            db.add_all([p1, p2, p3])
            db.commit()

            # Seed sample workflow
            wf = Workflow(
                application_id=app.id,
                name="Authentication & Catalog Flow",
                description="End-to-end journey from authentication to product browsing",
                risk_level="medium"
            )
            db.add(wf)
            db.commit()
            db.refresh(wf)

            s1 = WorkflowStep(workflow_id=wf.id, step_order=1, description="Navigate to login page", action_type="navigate", target_url="http://127.0.0.1:3000/login")
            s2 = WorkflowStep(workflow_id=wf.id, step_order=2, description="Submit login credentials", action_type="submit", target_url="http://127.0.0.1:3000/dashboard")
            s3 = WorkflowStep(workflow_id=wf.id, step_order=3, description="Explore product catalog", action_type="click", target_url="http://127.0.0.1:3000/products")
            db.add_all([s1, s2, s3])

            # Seed sample test case
            tc = TestCase(
                application_id=app.id,
                name="Verify Login Redirection to Dashboard",
                category="functional",
                priority="high",
                description="Validate successful login flow and dashboard access",
                preconditions="Server is running"
            )
            db.add(tc)
            db.commit()
            db.refresh(tc)

            t1 = TestStep(test_case_id=tc.id, step_order=1, action="navigate", target="http://127.0.0.1:3000/login", expected_result="Login form is displayed")
            t2 = TestStep(test_case_id=tc.id, step_order=2, action="fill", target="#email", value="admin@example.com", expected_result="Email entered")
            t3 = TestStep(test_case_id=tc.id, step_order=3, action="submit", target="form", expected_result="Navigated to dashboard")
            db.add_all([t1, t2, t3])

            db.commit()
            logger.info("Successfully seeded baseline application, workflow, and test cases.")
    except Exception as e:
        db.rollback()
        logger.warning(f"Notice during database baseline seed: {e}")

def init_db():
    """Create database tables if they do not exist, ensure columns are up to date, and seed baseline data."""
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    
    # Auto-migrate missing columns for SQLite/PostgreSQL
    try:
        inspector = inspect(engine)
        if "exploration_runs" in inspector.get_table_names():
            columns = [col["name"] for col in inspector.get_columns("exploration_runs")]
            if "target_url" not in columns:
                logger.info("Migrating schema: Adding 'target_url' column to 'exploration_runs' table...")
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE exploration_runs ADD COLUMN target_url VARCHAR(1000)"))
                logger.info("Successfully added 'target_url' column to 'exploration_runs'.")
    except Exception as e:
        logger.warning(f"Schema migration check notice: {e}")

    # Seed baseline data if database is empty
    with SessionLocal() as db:
        seed_initial_data(db)

    logger.info("Database tables and baseline data successfully initialized.")

if __name__ == "__main__":
    init_db()
