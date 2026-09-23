import logging
from typing import List, Dict, Any, Optional
from backend.app.database.models.models import DatabaseSchema, DatabaseTable, TestCase

logger = logging.getLogger("autonomous-qa-agent.db_generator")

class DatabaseTestCaseGenerator:
    """
    Synthesizes structured database integrity test cases from discovered
    schema metadata and application workflows without hallucination.
    """

    @classmethod
    def generate_test_cases(
        cls,
        schemas: List[DatabaseSchema],
        application_test_cases: Optional[List[TestCase]] = None
    ) -> List[Dict[str, Any]]:
        generated: List[Dict[str, Any]] = []

        all_tables: Dict[str, DatabaseTable] = {}
        for s in schemas:
            for t in s.tables:
                all_tables[t.table_name.lower()] = t

        # 1. Foreign Key / Referential Integrity Test Cases
        for table_name, t in all_tables.items():
            for rel in t.source_relationships:
                if rel.related_table and rel.source_column and rel.target_column:
                    test_def = {
                        "name": f"Referential Integrity: {t.table_name}.{rel.source_column} -> {rel.related_table.table_name}.{rel.target_column}",
                        "description": f"Verifies that foreign key values in {t.table_name}.{rel.source_column} strictly reference valid primary keys in {rel.related_table.table_name}.{rel.target_column} without orphan rows.",
                        "category": "REFERENTIAL_INTEGRITY",
                        "priority": "HIGH",
                        "validation_definition": {
                            "type": "orphan_check",
                            "source_table": t.table_name,
                            "source_column": rel.source_column,
                            "related_table": rel.related_table.table_name,
                            "related_column": rel.target_column
                        }
                    }
                    generated.append(test_def)

        # 2. Mandatory Nullability Test Cases for Key Tables
        for table_name in ["products", "orders", "users", "categories"]:
            if table_name in all_tables:
                t = all_tables[table_name]
                not_null_cols = [c.column_name for c in t.columns if not c.nullable and not c.is_primary_key]
                if not_null_cols:
                    test_def = {
                        "name": f"Nullability Constraint: {t.table_name} Required Columns",
                        "description": f"Validates that required columns ({', '.join(not_null_cols[:4])}) in {t.table_name} do not contain unexpected NULL values.",
                        "category": "NULLABILITY",
                        "priority": "MEDIUM",
                        "validation_definition": {
                            "type": "nullability_check",
                            "table": t.table_name,
                            "columns": not_null_cols
                        }
                    }
                    generated.append(test_def)

        # 3. Data Integrity Validation for Known Seed Records
        if "products" in all_tables:
            test_def = {
                "name": "Data Integrity: Enterprise Cloud Suite Stored Attributes",
                "description": "Validates that the Enterprise Cloud Suite product record in the target database matches expected price ($499.00) and active status.",
                "category": "DATA_INTEGRITY",
                "priority": "CRITICAL",
                "validation_definition": {
                    "type": "field_comparison",
                    "table": "products",
                    "lookup": {
                        "column": "title",
                        "value": "Enterprise Cloud Suite"
                    },
                    "expected_fields": {
                        "price": 499.00,
                        "is_active": 1
                    }
                }
            }
            generated.append(test_def)

        if "orders" in all_tables:
            test_def = {
                "name": "CRUD Validation: Order ORD-9021 Completed State",
                "description": "Verifies that customer order ORD-9021 is persisted in the target database with Completed status and $1,497.00 amount.",
                "category": "CRUD_VALIDATION",
                "priority": "HIGH",
                "validation_definition": {
                    "type": "field_comparison",
                    "table": "orders",
                    "lookup": {
                        "column": "order_number",
                        "value": "ORD-9021"
                    },
                    "expected_fields": {
                        "status": "Completed",
                        "total_amount": 1497.00
                    }
                }
            }
            generated.append(test_def)

        return generated
