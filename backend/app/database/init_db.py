from sqlalchemy import inspect, text
from backend.app.database.connection import engine
from backend.app.database.models.models import Base
from backend.app.core.logging import logger

def init_db():
    """Create database tables if they do not exist and ensure columns are up to date."""
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

    logger.info("Database tables successfully initialized.")

if __name__ == "__main__":
    init_db()
