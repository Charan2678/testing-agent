import os
import pytest
from backend.app.database.connection import SessionLocal
from backend.app.database.repositories.application_repo import ApplicationRepository
from backend.app.database.repositories.exploration_repo import ExplorationRepository
from backend.app.database.repositories.page_repo import PageRepository
from backend.app.api.schemas.application import ApplicationCreate
from backend.app.api.schemas.environment import EnvironmentCreate
from backend.app.api.schemas.exploration import ExplorationCreate
from backend.app.services.exploration_service import ExplorationService
from backend.app.database.models.models import ExplorationStatus, EvidenceType

@pytest.mark.asyncio
async def test_e2e_custom_url_passed_to_playwright():
    """
    Validates end-to-end that a custom user-entered Target Application URL
    takes precedence over the environment base_url and is genuinely used by Playwright.
    """
    db = SessionLocal()
    app_repo = ApplicationRepository(db)
    expl_repo = ExplorationRepository(db)
    page_repo = PageRepository(db)
    service = ExplorationService(db)

    try:
        # 1. Create Application
        app = app_repo.create(ApplicationCreate(
            name="Custom Target URL App",
            description="Tests custom URL precedence over predefined environment URL"
        ))

        # 2. Configure environment with a DUMMY/UNREACHABLE URL
        # Proving that if Playwright used the environment URL, it would fail or navigate elsewhere
        env = app_repo.create_environment(app.id, EnvironmentCreate(
            name="Dummy Base Environment",
            base_url="http://unreachable-dummy-env.local",
            environment_type="development"
        ))

        # 3. Create exploration with the REAL target CRM URL passed as custom target_url
        CUSTOM_TARGET_URL = "http://127.0.0.1:3000"
        run = expl_repo.create_run(ExplorationCreate(
            application_id=app.id,
            environment_id=env.id,
            target_url=CUSTOM_TARGET_URL,
            max_pages=10,
            max_depth=2
        ))
        assert run.id is not None
        assert run.target_url == CUSTOM_TARGET_URL

        # 4. Execute Playwright exploration
        await service.execute_exploration(run.id, max_pages=10, max_depth=2)

        # 5. Verify results: Playwright navigated to the custom URL, NOT the dummy environment URL
        db.expire_all()
        completed_run = expl_repo.get_run(run.id)
        assert completed_run.status == ExplorationStatus.COMPLETED
        assert completed_run.target_url == CUSTOM_TARGET_URL
        assert completed_run.pages_discovered > 0
        assert completed_run.actions_discovered > 0

        # Discovered pages MUST belong to the custom target URL origin (127.0.0.1:3000)
        pages = page_repo.get_pages_by_app(app.id)
        assert len(pages) > 0
        for p in pages:
            assert p.url.startswith(CUSTOM_TARGET_URL), f"Page URL {p.url} did not start with custom target URL {CUSTOM_TARGET_URL}"

        # Real screenshots exist on disk
        evidence_list = expl_repo.get_evidence_by_run(run.id)
        screenshots = [e for e in evidence_list if e.type == EvidenceType.SCREENSHOT]
        assert len(screenshots) > 0
        for s in screenshots:
            assert os.path.exists(s.file_path)
            assert os.path.getsize(s.file_path) > 1000

        print(f"\nSuccessfully proved Playwright crawled custom URL {CUSTOM_TARGET_URL} across {len(pages)} pages.")

    finally:
        db.close()
