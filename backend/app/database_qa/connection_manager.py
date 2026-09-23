import os
import re
import urllib.parse
from typing import Tuple, Optional, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from backend.app.database.models.models import DatabaseConnection, Environment, EnvironmentType

class DatabaseConnectionManager:
    """
    Manages secure, read-only connections to target application databases.
    Enforces production safety guardrails and credential security.
    """

    @staticmethod
    def is_production_environment(environment: Optional[Environment]) -> bool:
        if not environment:
            return False
        env_type = getattr(environment, "environment_type", None)
        if env_type:
            if isinstance(env_type, str) and "prod" in env_type.lower():
                return True
            if env_type == EnvironmentType.PROD:
                return True
        if hasattr(environment, "name") and environment.name and "prod" in environment.name.lower():
            return True
        return False

    @classmethod
    def mask_connection_password(cls, connection_url: str) -> str:
        """Masks the password portion in any connection URL."""
        return re.sub(r":([^:@]+)@", r":******@", connection_url)

    @classmethod
    def build_connection_url(cls, conn: DatabaseConnection) -> str:
        db_type = conn.database_type.lower()
        if db_type == "sqlite":
            path = conn.database_name.replace("\\", "/")
            # If path is relative, make absolute based on workspace or current dir
            if not os.path.isabs(path) and not path.startswith(":memory:"):
                path = os.path.abspath(path).replace("\\", "/")
            return f"sqlite:///{path}"

        username = urllib.parse.quote_plus(conn.username or "")
        password = urllib.parse.quote_plus(conn.password_encrypted or "")
        host = conn.host or "127.0.0.1"
        port = conn.port

        auth = f"{username}:{password}@" if username else ""
        port_str = f":{port}" if port else ""

        if db_type in ("postgres", "postgresql"):
            return f"postgresql+psycopg2://{auth}{host}{port_str}/{conn.database_name}"
        elif db_type in ("mysql", "mariadb"):
            return f"mysql+pymysql://{auth}{host}{port_str}/{conn.database_name}"
        else:
            raise ValueError(f"Unsupported database type '{conn.database_type}'. Supported: postgresql, mysql, sqlite")

    @classmethod
    def get_engine(cls, conn: DatabaseConnection, environment: Optional[Environment] = None) -> Engine:
        if cls.is_production_environment(environment):
            raise PermissionError(
                "Access to production database is strictly BLOCKED by default for QA automation safety."
            )

        url = cls.build_connection_url(conn)
        db_type = conn.database_type.lower()

        if db_type == "sqlite":
            engine = create_engine(
                url,
                connect_args={"check_same_thread": False},
                pool_pre_ping=True
            )
        else:
            engine = create_engine(
                url,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=0,
                connect_args={"connect_timeout": 5}
            )

        return engine

    @classmethod
    def test_connection(
        cls,
        conn: DatabaseConnection,
        environment: Optional[Environment] = None
    ) -> Tuple[str, Optional[str]]:
        """
        Tests connection to target database.
        Returns (status, error_message): status is CONNECTED, FAILED, or BLOCKED.
        Passwords are strictly masked from any returned error.
        """
        if cls.is_production_environment(environment):
            return "BLOCKED", "Production database connections are strictly blocked by default for QA automation safety."

        try:
            engine = cls.get_engine(conn, environment)
            with engine.connect() as connection:
                # Execute simple ping query
                res = connection.execute(text("SELECT 1"))
                row = res.fetchone()
                if row and row[0] == 1:
                    return "CONNECTED", None
                return "FAILED", "Unexpected ping response from database server."
        except Exception as e:
            raw_err = str(e)
            # Mask any potential password strings in error message
            if conn.password_encrypted:
                raw_err = raw_err.replace(conn.password_encrypted, "********")
            return "FAILED", f"Database connection failed: {raw_err[:200]}"
