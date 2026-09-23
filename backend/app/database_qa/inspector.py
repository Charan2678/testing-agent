import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from backend.app.database_qa.validator import DatabaseSafetyValidator

logger = logging.getLogger("autonomous-qa-agent.db_inspector")

class DatabaseInspector:
    """
    Safely inspects target database structure without modifying any records.
    Discovers schemas, tables, columns, primary keys, foreign keys, and indexes.
    """

    @classmethod
    def discover_database(cls, engine: Engine, max_tables: int = 100) -> List[Dict[str, Any]]:
        inspector = inspect(engine)
        discovered_schemas: List[Dict[str, Any]] = []

        # Determine schema names
        try:
            raw_schemas = inspector.get_schema_names()
        except Exception as e:
            logger.warning(f"Could not retrieve schema names, defaulting to public/main: {e}")
            raw_schemas = ["main"] if "sqlite" in engine.dialect.name else ["public"]

        # Filter internal system schemas (pg_catalog, information_schema, sys, etc.)
        system_schemas = {"pg_catalog", "information_schema", "pg_toast", "sys", "mysql", "performance_schema"}
        active_schemas = [s for s in raw_schemas if s.lower() not in system_schemas]
        if not active_schemas and raw_schemas:
            active_schemas = [raw_schemas[0]]

        for schema_name in active_schemas:
            schema_dict: Dict[str, Any] = {
                "schema_name": schema_name,
                "tables": []
            }

            try:
                table_names = inspector.get_table_names(schema=schema_name if schema_name != "main" else None)
            except Exception as e:
                logger.warning(f"Error fetching tables for schema '{schema_name}': {e}")
                table_names = []

            for t_name in table_names[:max_tables]:
                # Skip internal SQLite sequence tables
                if t_name.startswith("sqlite_"):
                    continue

                table_data: Dict[str, Any] = {
                    "name": t_name,
                    "row_count": 0,
                    "description": f"Target table '{t_name}' in schema '{schema_name}'",
                    "columns": [],
                    "relationships": []
                }

                # 1. Fetch Primary Keys
                try:
                    pk_constraint = inspector.get_pk_constraint(t_name, schema=schema_name if schema_name != "main" else None)
                    pks = set(pk_constraint.get("constrained_columns", []) or [])
                except Exception:
                    pks = set()

                # 2. Fetch Columns
                try:
                    cols = inspector.get_columns(t_name, schema=schema_name if schema_name != "main" else None)
                    for col in cols:
                        col_name = col.get("name")
                        table_data["columns"].append({
                            "name": col_name,
                            "type": str(col.get("type", "TEXT")),
                            "nullable": col.get("nullable", True),
                            "is_primary_key": col_name in pks,
                            "is_foreign_key": False,  # Updated below
                            "default": str(col.get("default")) if col.get("default") is not None else None
                        })
                except Exception as col_err:
                    logger.warning(f"Error inspecting columns for '{t_name}': {col_err}")

                # 3. Fetch Foreign Keys & Relationships
                try:
                    fks = inspector.get_foreign_keys(t_name, schema=schema_name if schema_name != "main" else None)
                    fk_col_names = set()
                    for fk in fks:
                        referred_table = fk.get("referred_table")
                        constrained_cols = fk.get("constrained_columns", [])
                        referred_cols = fk.get("referred_columns", [])

                        for s_col, t_col in zip(constrained_cols, referred_cols):
                            fk_col_names.add(s_col)
                            table_data["relationships"].append({
                                "source_column": s_col,
                                "related_table": referred_table,
                                "target_column": t_col,
                                "relationship_type": "foreign_key"
                            })

                    # Mark is_foreign_key flag on columns
                    for c in table_data["columns"]:
                        if c["name"] in fk_col_names:
                            c["is_foreign_key"] = True
                except Exception as fk_err:
                    logger.warning(f"Error inspecting foreign keys for '{t_name}': {fk_err}")

                # 4. Safe Row Count
                try:
                    with engine.connect() as connection:
                        count_sql = f"SELECT COUNT(*) FROM {t_name}"
                        DatabaseSafetyValidator.validate_sql_read_only(count_sql)
                        row = connection.execute(text(count_sql)).fetchone()
                        if row:
                            table_data["row_count"] = int(row[0])
                except Exception as cnt_err:
                    logger.debug(f"Count query skipped for '{t_name}': {cnt_err}")

                schema_dict["tables"].append(table_data)

            discovered_schemas.append(schema_dict)

        return discovered_schemas
