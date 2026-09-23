import pytest
import asyncio
from backend.app.database.connection import SessionLocal
from backend.app.database.repositories.application_repo import ApplicationRepository
from backend.app.database.repositories.workflow_repo import WorkflowRepository
from backend.app.database.repositories.testcase_repo import TestCaseRepository
from backend.app.database.repositories.page_repo import PageRepository
from backend.app.services.ai_analysis_service import AIAnalysisService
from backend.app.api.schemas.testcase import AIAnalysisOutput, AIWorkflowModel, AITestCaseModel, AITestStepModel
from backend.app.agents.analyzer import ApplicationAnalyzer
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_ai_schema_validation():
    # Valid output
    valid_data = {
        "summary": "Application contains authentication and product catalog.",
        "workflows": [
            {
                "name": "Authentication",
                "description": "User login flow",
                "risk_level": "critical",
                "steps": [
                    {
                        "sequence": 1,
                        "action": "Navigate to login",
                        "expected_behavior": "Login page rendered",
                        "target_page_url": "http://localhost:3000/login"
                    }
                ]
            }
        ],
        "test_cases": [
            {
                "name": "TC-001 Smoke: Valid Login",
                "workflow_name": "Authentication",
                "category": "smoke",
                "priority": "critical",
                "description": "Test valid login",
                "preconditions": ["User exists"],
                "steps": [
                    {
                        "sequence": 1,
                        "action": "navigate",
                        "target": "http://localhost:3000/login",
                        "expected_result": "Status 200",
                        "source_page_url": "http://localhost:3000/login"
                    }
                ]
            }
        ]
    }
    output = AIAnalysisOutput(**valid_data)
    assert len(output.workflows) == 1
    assert len(output.test_cases) == 1

def test_invalid_ai_schema_rejection():
    # Missing required 'steps' in test case
    invalid_data = {
        "summary": "Invalid test",
        "workflows": [],
        "test_cases": [
            {
                "name": "Broken Test",
                "workflow_name": "Auth",
                "category": "smoke",
                "priority": "high",
                "description": "Missing steps field",
                "preconditions": []
            }
        ]
    }
    with pytest.raises(Exception):
        AIAnalysisOutput(**invalid_data)

@pytest.mark.asyncio
async def test_full_phase2_ai_analysis_pipeline():
    """Validates real AI understanding and test case generation on the explored target application."""
    db = SessionLocal()
    app_repo = ApplicationRepository(db)
    wf_repo = WorkflowRepository(db)
    tc_repo = TestCaseRepository(db)
    service = AIAnalysisService(db)

    try:
        # Find the application explored in Phase 1
        apps = app_repo.get_all()
        target_app = next((a for a in apps if "Target Test Application" in a.name or len(a.pages) > 0), apps[0] if apps else None)
        assert target_app is not None, "A target application with discovered pages must exist from Phase 1."

        # Execute AI analysis
        await service.execute_analysis(target_app.id)

        # Verify Workflows generated and persisted in DB
        db.expire_all()
        workflows = wf_repo.get_by_application(target_app.id)
        assert len(workflows) > 0, "AI must generate at least one workflow from observed application pages."
        print(f"\nDiscovered {len(workflows)} Real Workflows in DB:")
        for wf in workflows:
            steps = wf_repo.get_steps(wf.id)
            print(f"  - [{wf.risk_level.upper()}] {wf.name} ({len(steps)} steps)")
            assert len(steps) > 0

        # Verify Test Cases generated and persisted in DB
        test_cases = tc_repo.get_by_application(target_app.id)
        assert len(test_cases) > 0, "AI must generate structured test cases."
        print(f"\nGenerated {len(test_cases)} Real Test Cases in DB:")
        for tc in test_cases:
            steps = tc_repo.get_steps(tc.id)
            print(f"  - [{tc.category.upper()} | {tc.priority.upper()}] {tc.name} ({len(steps)} steps)")
            assert len(steps) > 0

            # Traceability check: Each step must have a source page URL
            for step in steps:
                assert step.target is not None
                assert step.expected_result is not None

        # Verify API Endpoints return the generated records
        wf_res = client.get(f"/api/applications/{target_app.id}/workflows")
        assert wf_res.status_code == 200
        assert len(wf_res.json()) == len(workflows)

        tc_res = client.get(f"/api/applications/{target_app.id}/test-cases")
        assert tc_res.status_code == 200
        assert len(tc_res.json()) == len(test_cases)

    finally:
        db.close()
