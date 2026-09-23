import os
import pytest
import asyncio
from datetime import datetime

from backend.app.database.connection import SessionLocal
from backend.app.database.models.models import (
    Application,
    Environment,
    EnvironmentType,
    TestCase as DBTestCase,
    TestStep as DBTestStep,
    Element,
    Page,
    ExecutionStatus,
    EvidenceType,
    ExecutionEvidence
)
from backend.app.test_engine.locator_resolver import LocatorResolver
from backend.app.test_engine.safety import SafetyValidator, ActionSafetyLevel
from backend.app.test_engine.generator import TestGenerator as AppTestGenerator
from backend.app.test_engine.runner import PlaywrightTestRunner
from backend.app.database.repositories.execution_repo import ExecutionRepository


def test_locator_resolver_hierarchy():
    # 1. Role with text
    elem_role = Element(role="button", text="Submit Order", selector="#submit", tag_name="button")
    res1 = LocatorResolver.resolve_from_element(elem_role)
    assert res1.strategy == "role"
    assert 'page.get_by_role("button", name="Submit Order")' in res1.code_snippet

    # 2. Input placeholder
    elem_ph = Element(tag_name="input", placeholder="Enter Email", selector="#email")
    res2 = LocatorResolver.resolve_from_element(elem_ph)
    assert res2.strategy == "placeholder"
    assert 'page.get_by_placeholder("Enter Email")' in res2.code_snippet

    # 3. Input name
    elem_name = Element(tag_name="input", name="username", selector="input[name='username']")
    res3 = LocatorResolver.resolve_from_element(elem_name)
    assert res3.strategy == "css"
    assert 'input[name="username"]' in res3.code_snippet

    # 4. Data test id
    elem_test = Element(tag_name="div", selector='button[data-testid="save-btn"]')
    res4 = LocatorResolver.resolve_from_element(elem_test)
    assert res4.strategy == "test_id"
    assert 'page.get_by_test_id("save-btn")' in res4.code_snippet

def test_safety_validator_policies():
    # 1. Safe step
    step_safe = DBTestStep(sequence=1, action="navigate", target="http://127.0.0.1:3000/dashboard")
    level, _ = SafetyValidator.classify_step(step_safe)
    assert level == ActionSafetyLevel.SAFE

    # 2. Destructive step
    step_destructive = DBTestStep(sequence=2, action="click", target="#btn-delete-all-records")
    level, reason = SafetyValidator.classify_step(step_destructive)
    assert level == ActionSafetyLevel.DESTRUCTIVE
    assert "delete" in reason.lower()

    # 3. Blocked high-risk payment step
    step_payment = DBTestStep(sequence=3, action="fill", target="#credit_card_input", value="4111222233334444")
    level, reason = SafetyValidator.classify_step(step_payment)
    assert level == ActionSafetyLevel.BLOCKED
    assert "credit_card" in reason.lower()

    # 4. Production guard
    env_prod = Environment(name="Prod", base_url="https://prod.mycompany.com", environment_type=EnvironmentType.PROD)
    tc = DBTestCase(name="Smoke", steps=[step_safe])
    res = SafetyValidator.validate_test_case(tc, environment=env_prod)
    assert res.is_valid is False
    assert res.safety_level == ActionSafetyLevel.BLOCKED

def test_test_generator_ir_and_code():
    db = SessionLocal()
    try:
        # Create test case in memory
        app = Application(name="Phase 3 Test App")
        db.add(app)
        db.commit()
        db.refresh(app)

        tc = DBTestCase(
            application_id=app.id,
            name="TC-P3-001 Navigation and Fill",
            category="functional",
            priority="high",
            description="Testing generator IR conversion"
        )
        db.add(tc)
        db.commit()
        db.refresh(tc)

        s1 = DBTestStep(test_case_id=tc.id, sequence=1, action="navigate", target="http://127.0.0.1:3000/login", expected_result="Page loaded")
        s2 = DBTestStep(test_case_id=tc.id, sequence=2, action="fill", target="input[name='username']", value="test@example.com", expected_result="Filled")
        db.add_all([s1, s2])
        db.commit()

        generator = AppTestGenerator(db)
        ir = generator.generate_intermediate_representation(tc)
        assert ir["test_case_id"] == tc.id
        assert len(ir["steps"]) == 2
        assert ir["steps"][0]["action"] == "navigate"
        assert ir["steps"][1]["action"] == "fill"

        generated = generator.generate_and_save(tc.id, base_url="http://127.0.0.1:3000")
        assert generated.generation_version >= 1
        assert os.path.exists(generated.file_path)
        assert "async def test_case_" in generated.generated_code
    finally:
        db.close()

def test_execution_summary_zero_mock():
    db = SessionLocal()
    try:
        repo = ExecutionRepository(db)
        # Summary for non-existent app should return has_executions=False, zeros
        summary = repo.get_summary_by_application(999999)
        assert summary["has_executions"] is False
        assert summary["total_executions"] == 0
        assert summary["pass_rate"] == 0.0
    finally:
        db.close()

@pytest.mark.asyncio
async def test_real_playwright_execution_against_crm():
    """
    Executes a real test case against http://127.0.0.1:3000 and verifies
    real Playwright browser execution, real trace creation, and screenshots.
    """
    db = SessionLocal()
    try:
        app = db.query(Application).filter(Application.id == 2).first()
        assert app is not None, "Application #2 must exist in test database"

        tc = db.query(DBTestCase).filter(DBTestCase.application_id == 2).first()
        assert tc is not None, "Test case for application #2 must exist in test database"

        runner = PlaywrightTestRunner(db)
        execution = await runner.execute_test_case(test_case_id=tc.id)

        assert execution.id is not None
        assert execution.status in (ExecutionStatus.PASSED, ExecutionStatus.FAILED)
        assert execution.duration_ms is not None and execution.duration_ms > 0
        assert execution.completed_at is not None

        # Verify evidence files exist on disk
        evidence_list = db.query(ExecutionEvidence).filter(ExecutionEvidence.execution_id == execution.id).all()
        assert len(evidence_list) >= 1

        screenshot_evidence = [e for e in evidence_list if e.type == EvidenceType.SCREENSHOT]
        assert len(screenshot_evidence) > 0
        assert os.path.exists(screenshot_evidence[0].file_path)
        assert os.path.getsize(screenshot_evidence[0].file_path) > 1000

        trace_evidence = [e for e in evidence_list if e.type == EvidenceType.TRACE]
        if trace_evidence:
            assert os.path.exists(trace_evidence[0].file_path)
            assert os.path.getsize(trace_evidence[0].file_path) > 1000
    finally:
        db.close()

