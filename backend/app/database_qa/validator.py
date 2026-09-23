import re
from typing import List, Dict, Any, Optional

class UnsafeQueryException(ValueError):
    """Raised when an unsafe or non-read-only SQL query is detected."""
    pass

class DatabaseSafetyValidator:
    """
    Enforces strict READ-ONLY SQL validation.
    Prevents any modification, DDL, or unauthorized operations on the target database.
    """

    FORBIDDEN_KEYWORDS = [
        "delete", "update", "insert", "drop", "truncate", "alter",
        "create", "replace", "grant", "revoke", "exec", "execute",
        "merge", "call", "vacuum", "reindex", "attach", "detach"
    ]

    @classmethod
    def validate_sql_read_only(cls, sql_query: str) -> str:
        """
        Validates that a query string is strictly a safe read-only SELECT query.
        Raises UnsafeQueryException if any modification verb is detected.
        Returns the sanitized query.
        """
        cleaned = re.sub(r"--.*$", "", sql_query, flags=re.MULTILINE)  # remove line comments
        cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.DOTALL)    # remove block comments
        cleaned = cleaned.strip()

        if not cleaned:
            raise UnsafeQueryException("SQL query cannot be empty.")

        # Must start with SELECT or WITH
        first_word = cleaned.split()[0].lower()
        if first_word not in ("select", "with", "explain"):
            raise UnsafeQueryException(f"Dangerous query rejected: Only SELECT queries are permitted. Found: '{first_word}'.")

        # Disallow multiple statements separated by semicolon (e.g. SELECT 1; DROP TABLE ...)
        statements = [s.strip() for s in cleaned.split(";") if s.strip()]
        if len(statements) > 1:
            raise UnsafeQueryException("Dangerous query rejected: Multiple statement chaining (semicolon) is not permitted.")

        # Check for forbidden mutation keywords
        words = re.findall(r"\b[a-zA-Z_]+\b", cleaned.lower())
        for forbidden in cls.FORBIDDEN_KEYWORDS:
            if forbidden in words:
                raise UnsafeQueryException(
                    f"Dangerous query rejected: Destructive keyword '{forbidden.upper()}' is forbidden in read-only validation."
                )
        return cleaned

    validate_read_only = validate_sql_read_only

    @classmethod
    def validate_table_and_columns(
        cls,
        table_name: str,
        column_names: List[str],
        discovered_tables: Dict[str, List[str]]
    ) -> None:
        """
        Ensures table and columns actually exist in discovered schema before query generation.
        """
        clean_table = table_name.lower().strip()
        if clean_table not in discovered_tables:
            raise ValueError(f"Table '{table_name}' does not exist in discovered database schema.")

        valid_columns = [c.lower() for c in discovered_tables[clean_table]]
        for col in column_names:
            if col.lower() not in valid_columns and col != "*":
                raise ValueError(f"Column '{col}' does not exist on table '{table_name}' in discovered schema.")

    @classmethod
    def sanitize_evidence_params(cls, parameters: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Redacts sensitive field values from evidence storage.
        """
        if not parameters:
            return {}
        sanitized = {}
        sensitive_patterns = ["password", "token", "secret", "auth", "key", "credential", "hash"]
        for k, v in parameters.items():
            if any(p in k.lower() for p in sensitive_patterns):
                sanitized[k] = "********"
            else:
                sanitized[k] = v
        return sanitized
