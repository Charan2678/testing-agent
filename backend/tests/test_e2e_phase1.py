import asyncio
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
async def test_full_phase1_crawler_pipeline():
    """Validates real end-to-end exploration against the local target test application."""
    db = SessionLocal()
    app_repo = ApplicationRepository(db)
    expl_repo = ExplorationRepository(db)
    page_repo = PageRepository(db)
    service = ExplorationService(db)

    try:
        # 1. Register Application
        app = app_repo.create(ApplicationCreate(
            name="Target Test Application",
            description="Autonomous crawl validation target app"
        ))
        assert app.id is not None

        # 2. Register Environment (pointing to test-app on port 3000)
        env = app_repo.create_environment(app.id, EnvironmentCreate(
            name="Local Test Server",
            base_url="http://127.0.0.1:3000",
            environment_type="development"
        ))
        assert env.id is not None

        # 3. Create Exploration Run
        run = expl_repo.create_run(ExplorationCreate(
            application_id=app.id,
            environment_id=env.id,
            max_pages=15,
            max_depth=3
        ))
        assert run.id is not None

        # 4. Execute real Playwright crawler
        await service.execute_exploration(run.id, max_pages=15, max_depth=3)

        # 5. Verify Database Records (NO DUMMY DATA)
        db.expire_all()
        completed_run = expl_repo.get_run(run.id)
        assert completed_run.status == ExplorationStatus.COMPLETED
        assert completed_run.pages_discovered > 0
        assert completed_run.actions_discovered > 0

        # Verify pages discovered
        pages = page_repo.get_pages_by_app(app.id)
        assert len(pages) >= 4
        urls = [p.url.rstrip("/") for p in pages]
        print("\nDiscovered real URLs in database:", urls)

        # Verify element extraction on the discovered pages
        total_elements = 0
        for p in pages:
            elements = page_repo.get_elements_by_page(p.id)
            total_elements += len(elements)
            assert len(elements) > 0  # Each page must have real discovered elements

        print(f"Total real elements discovered across pages: {total_elements}")
        assert total_elements >= 10

        # Verify Evidence: Real screenshots exist on disk
        evidence_list = expl_repo.get_evidence_by_run(run.id)
        screenshots = [e for e in evidence_list if e.type == EvidenceType.SCREENSHOT]
        assert len(screenshots) > 0

        for s in screenshots:
            assert s.file_path is not None
            assert os.path.exists(s.file_path), f"Screenshot file does not exist: {s.file_path}"
            assert os.path.getsize(s.file_path) > 1000  # Non-empty valid image file

        print(f"Verified {len(screenshots)} valid physical screenshot files on disk.")

        # Verify Console Logs captured
        console_logs = [e for e in evidence_list if e.type == EvidenceType.CONSOLE_LOG]
        print(f"Captured {len(console_logs)} console log entries from the target application.")

    finally:
        db.close()
