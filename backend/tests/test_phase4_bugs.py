import pytest
from datetime import datetime
from backend.app.database.connection import SessionLocal
from backend.app.database.models.models import (
    Application,
    Environment,
    TestCase as DBTestCase,
    TestStep as DBTestStep,
    TestExecution,
    TestExecutionStep,
    ExecutionEvidence,
    ExecutionStatus,
    EvidenceType,
    Bug
)
from backend.app.bug_engine.classifier import FailureClassifier
from backend.app.bug_engine.root_cause_analyzer import RootCauseAnalyzer
from backend.app.services.bug_service import BugService
from backend.app.database.repositories.bug_repo import BugRepository

def test_failure_classifier_distinctions():
    # 1. Infrastructure failure: browser crash
    res_infra = FailureClassifier.classify(
        application_id=1,
        error_message="Target page, context or browser has been closed"
    )
    assert res_infra.classification == "INFRASTRUCTURE_FAILURE"
    assert res_infra.is_application_defect is False

    # 2. Environment failure: connection refused
    res_env = FailureClassifier.classify(
        application_id=1,
        error_message="page.goto: net::ERR_CONNECTION_REFUSED at http://127.0.0.1:3000"
    )
    assert res_env.classification == "ENVIRONMENT_FAILURE"
    assert res_env.is_application_defect is False

    # 3. Test Bug: selector mismatch
    res_test = FailureClassifier.classify(
        application_id=1,
        error_message="waiting for locator(\"button#save-product-nonexistent\") failed: timeout 10000ms exceeded",
        failed_step_target="button#save-product-nonexistent"
    )
    assert res_test.classification == "TEST_BUG"
    assert res_test.is_application_defect is False

    # 4. Application Bug: uncaught JS exception in page console
    res_js = FailureClassifier.classify(
        application_id=1,
        error_message="Step failed during form submission",
        console_logs=[
            {"type": "error", "text": "Uncaught TypeError: Cannot read properties of undefined (reading 'submit')"}
        ]
    )
    assert res_js.classification == "APPLICATION_BUG"
    assert res_js.category == "JAVASCRIPT"
    assert res_js.is_application_defect is True

    # 5. Application Bug: server responded with HTTP 500
    res_api = FailureClassifier.classify(
        application_id=1,
        error_message="Failed to submit form: HTTP 500 Internal Server Error",
        network_failures=[{"url": "http://127.0.0.1:3000/api/products", "failure": "status 500"}]
    )
    assert res_api.classification == "APPLICATION_BUG"
    assert res_api.category == "API"
    assert res_api.is_application_defect is True

    # 6. Application Bug: assertion mismatch
    res_assert = FailureClassifier.classify(
        application_id=1,
        error_message="AssertionError: Expected dashboard redirect, got http://127.0.0.1:3000/login",
        failed_step_action="assert"
    )
    assert res_assert.classification == "APPLICATION_BUG"
    assert res_assert.is_application_defect is True

def test_root_cause_analyzer_calibration():
    analyzer = RootCauseAnalyzer()

    # Direct JS error must yield CONFIRMED confidence
    res_js = analyzer._deterministic_analysis(
        test_case_name="TC-004 Form Submit",
        failed_step_action="click",
        failed_step_target="#btn-save-product",
        expected_result="Product saved",
        error_message="Error clicking button",
        final_url="http://127.0.0.1:3000/products/create",
        console_logs=[{"type": "error", "text": "Uncaught ReferenceError: validateForm is not defined"}],
        network_failures=[],
        preliminary_category="JAVASCRIPT"
    )
    assert res_js.category == "JAVASCRIPT"
    assert res_js.confidence_level == "CONFIRMED"
    assert res_js.confidence_score >= 90
    assert "ReferenceError" in res_js.root_cause

    # Functional assertion yields LIKELY confidence
    res_func = analyzer._deterministic_analysis(
        test_case_name="TC-001 Login",
        failed_step_action="assert",
        failed_step_target="url",
        expected_result="User session established and redirected to dashboard",
        error_message="AssertionError: Expected dashboard redirect, got http://127.0.0.1:3000/login",
        final_url="http://127.0.0.1:3000/login",
        console_logs=[],
        network_failures=[],
        preliminary_category="FUNCTIONAL"
    )
    assert res_func.confidence_level == "LIKELY"
    assert res_func.confidence_score < 90

def test_bug_repository_and_summary_zero_mock():
    db = SessionLocal()
    try:
        repo = BugRepository(db)

        # Summary for clean app must return has_bugs=False, zero counts
        clean_summary = repo.get_summary_by_application(999998)
        assert clean_summary["has_bugs"] is False
        assert clean_summary["total_bugs"] == 0
        assert clean_summary["open_bugs"] == 0

        # Create bug
        app = Application(name="P4 Test App")
        db.add(app)
        db.commit()
        db.refresh(app)

        bug = repo.create_bug(
            application_id=app.id,
            title="Product price validation missing",
            summary="Application accepts negative price values without validation.",
            description="Entering -50.00 creates a product successfully without server rejection.",
            category="VALIDATION",
            severity="HIGH",
            status="OPEN",
            failure_signature="sig_p4_test_123"
        )
        assert bug.id is not None
        assert bug.status == "OPEN"

        # Check summary reflects the real bug
        app_summary = repo.get_summary_by_application(app.id)
        assert app_summary["has_bugs"] is True
        assert app_summary["total_bugs"] == 1
        assert app_summary["open_bugs"] == 1
        assert app_summary["high_bugs"] == 1

        # Status transition
        updated = repo.update_status(bug.id, "TRIAGED")
        assert updated.status == "TRIAGED"

        updated = repo.update_status(bug.id, "FIXED")
        assert updated.status == "FIXED"

        app_summary2 = repo.get_summary_by_application(app.id)
        assert app_summary2["open_bugs"] == 0
        assert app_summary2["resolved_bugs"] == 1
    finally:
        db.close()

@pytest.mark.asyncio
async def test_duplicate_bug_deduplication():
    db = SessionLocal()
    try:
        app = Application(name="P4 Deduplication App")
        db.add(app)
        db.commit()
        db.refresh(app)

        tc = DBTestCase(
            application_id=app.id,
            name="TC-DEDUP Form Submit",
            category="functional",
            priority="high"
        )
        db.add(tc)
        db.commit()
        db.refresh(tc)

        step = DBTestStep(
            test_case_id=tc.id,
            sequence=1,
            action="click",
            target="#btn-submit",
            expected_result="Form submitted successfully"
        )
        db.add(step)
        db.commit()
        db.refresh(step)

        # Execution 1: fails with an uncaught JS error
        exec1 = TestExecution(
            test_case_id=tc.id,
            status=ExecutionStatus.FAILED,
            error_message="Step #1 failed: Uncaught TypeError: submitHandler is not a function",
            final_url="http://127.0.0.1:3000/products/create"
        )
        db.add(exec1)
        db.commit()
        db.refresh(exec1)

        step1 = TestExecutionStep(
            execution_id=exec1.id,
            test_step_id=step.id,
            sequence=1,
            action="click",
            target="#btn-submit",
            status="failed",
            error_message="Uncaught TypeError: submitHandler is not a function"
        )
        db.add(step1)
        db.commit()

        service = BugService(db)
        bug1 = await service.analyze_failed_execution(exec1.id)
        assert bug1 is not None
        assert bug1.occurrence_count == 1
        initial_bug_id = bug1.id

        # Execution 2: fails with the exact same error on the same page
        exec2 = TestExecution(
            test_case_id=tc.id,
            status=ExecutionStatus.FAILED,
            error_message="Step #1 failed: Uncaught TypeError: submitHandler is not a function",
            final_url="http://127.0.0.1:3000/products/create"
        )
        db.add(exec2)
        db.commit()
        db.refresh(exec2)

        step2 = TestExecutionStep(
            execution_id=exec2.id,
            test_step_id=step.id,
            sequence=1,
            action="click",
            target="#btn-submit",
            status="failed",
            error_message="Uncaught TypeError: submitHandler is not a function"
        )
        db.add(step2)
        db.commit()

        bug2 = await service.analyze_failed_execution(exec2.id)
        assert bug2 is not None
        # Must be the SAME bug with incremented occurrence count
        assert bug2.id == initial_bug_id
        assert bug2.occurrence_count == 2
    finally:
        db.close()
