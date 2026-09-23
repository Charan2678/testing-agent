import asyncio
from datetime import datetime
from typing import Set, Tuple, List, Optional
from collections import deque
from sqlalchemy.orm import Session

from backend.app.database.connection import SessionLocal
from backend.app.database.repositories.exploration_repo import ExplorationRepository
from backend.app.database.repositories.page_repo import PageRepository
from backend.app.database.repositories.application_repo import ApplicationRepository
from backend.app.database.models.models import (
    ExplorationStatus, EvidenceType, ActionType
)
from backend.app.api.schemas.page import ElementBase
from backend.app.browser.manager import BrowserManager
from backend.app.browser.collectors import PageEventCollector
from backend.app.browser.explorer import PageExplorer
from backend.app.core.config import settings
from backend.app.core.logging import logger

# Active exploration memory store for real-time activity streaming / status
active_explorations = {}

class ExplorationService:
    """Orchestrates deterministic real-application exploration with Playwright and records all discoveries."""

    def __init__(self, db: Session):
        self.db = db
        self.exploration_repo = ExplorationRepository(db)
        self.page_repo = PageRepository(db)
        self.app_repo = ApplicationRepository(db)

    async def execute_exploration(self, run_id: int, max_pages: int = 30, max_depth: int = 3):
        """Asynchronously executes the autonomous crawler workflow against the target environment."""
        # Use a fresh DB session for the background task
        db = SessionLocal()
        expl_repo = ExplorationRepository(db)
        page_repo = PageRepository(db)
        app_repo = ApplicationRepository(db)

        activity_log: List[str] = []
        active_explorations[run_id] = {
            "status": ExplorationStatus.RUNNING,
            "current_url": None,
            "pages_discovered": 0,
            "actions_discovered": 0,
            "error_count": 0,
            "activity_log": activity_log
        }

        run = expl_repo.get_run(run_id)
        if not run:
            logger.error(f"Exploration run {run_id} not found.")
            db.close()
            return

        env = app_repo.get_environment_by_id(run.environment_id)
        if not env:
            logger.error(f"Environment {run.environment_id} not found for run {run_id}.")
            expl_repo.complete_run(run_id, status=ExplorationStatus.FAILED)
            db.close()
            return

        # Resolve target URL: Custom user-provided target_url takes precedence over environment base_url
        if run.target_url and run.target_url.strip():
            raw_url = run.target_url.strip()
            url_source = "custom target URL"
        else:
            raw_url = env.base_url.strip()
            url_source = "predefined environment URL"

        base_url = raw_url.rstrip("/")
        if not run.target_url:
            run.target_url = base_url
            db.commit()

        active_explorations[run_id]["target_url"] = base_url
        active_explorations[run_id]["url_source"] = url_source

        expl_repo.start_run(run_id)
        activity_log.append(f"Started exploration for application #{run.application_id} using {url_source}: {base_url}")
        logger.info(f"[Run #{run_id}] Starting exploration using {url_source} on {base_url}")

        browser_mgr = BrowserManager()
        collector = PageEventCollector()
        explorer = PageExplorer(run_id=run_id)

        visited_urls: Set[str] = set()
        queue: deque[Tuple[str, int]] = deque([(base_url, 0)])

        pages_count = 0
        actions_count = 0
        error_count = 0

        try:
            await browser_mgr.start()
            context = await browser_mgr.create_context()
            page = await context.new_page()
            collector.attach_to_page(page)

            while queue and pages_count < max_pages:
                current_url, depth = queue.popleft()
                norm_current = current_url.rstrip("/")

                if norm_current in visited_urls:
                    continue

                if depth > max_depth:
                    continue

                visited_urls.add(norm_current)
                active_explorations[run_id]["current_url"] = current_url
                activity_log.append(f"Navigating to {current_url} (depth={depth})")
                logger.info(f"[Run #{run_id}] Visiting ({pages_count + 1}/{max_pages}): {current_url}")

                collector.clear()
                status_code = None

                try:
                    response = await page.goto(current_url, wait_until="load", timeout=settings.CRAWL_TIMEOUT_SECONDS * 1000)
                    if response:
                        status_code = response.status
                    # Small grace period for dynamic hydration / AJAX
                    await asyncio.sleep(1)
                except Exception as nav_err:
                    error_count += 1
                    logger.warning(f"[Run #{run_id}] Navigation error on {current_url}: {nav_err}")
                    activity_log.append(f"Navigation warning: {str(nav_err)[:100]}")
                    expl_repo.add_evidence(
                        run_id=run_id,
                        evidence_type=EvidenceType.CONSOLE_LOG,
                        url=current_url,
                        description=f"Navigation failure: {str(nav_err)}"
                    )

                # Inspect page DOM, extract elements, screenshot
                discovered = await explorer.inspect_page(page, base_url)
                
                # Persist discovered page
                db_page = page_repo.get_or_create(
                    application_id=run.application_id,
                    environment_id=run.environment_id,
                    url=current_url,
                    title=discovered.title,
                    status_code=status_code or discovered.status_code
                )
                pages_count += 1
                active_explorations[run_id]["pages_discovered"] = pages_count
                activity_log.append(f"Discovered page: '{discovered.title or current_url}' ({len(discovered.elements)} elements)")

                # Persist elements and discovered actions
                for el in discovered.elements:
                    db_element = page_repo.add_element(
                        page_id=db_page.id,
                        element_data=ElementBase(
                            element_type=el.element_type,
                            tag_name=el.tag_name,
                            selector=el.selector,
                            text=el.text,
                            name=el.name,
                            placeholder=el.placeholder,
                            role=el.role,
                            is_interactive=el.is_interactive
                        )
                    )
                    
                    if el.is_interactive:
                        # Determine action type
                        act_type = ActionType.CLICK if el.element_type in ("button", "link") else ActionType.FILL
                        page_repo.add_action(
                            page_id=db_page.id,
                            element_id=db_element.id,
                            action_type=act_type,
                            action_data={"selector": el.selector, "text": el.text},
                            result="discovered"
                        )
                        actions_count += 1

                active_explorations[run_id]["actions_discovered"] = actions_count

                # Persist screenshot evidence
                if discovered.screenshot_path:
                    expl_repo.add_evidence(
                        run_id=run_id,
                        evidence_type=EvidenceType.SCREENSHOT,
                        file_path=discovered.screenshot_path,
                        url=current_url,
                        description=f"Screenshot of {discovered.title or current_url}"
                    )

                # Persist console errors
                for c_err in collector.get_console_errors():
                    error_count += 1
                    expl_repo.add_evidence(
                        run_id=run_id,
                        evidence_type=EvidenceType.CONSOLE_LOG,
                        url=current_url,
                        description=f"Console [{c_err.type}]: {c_err.text}",
                        metadata_json=c_err.model_dump(mode="json")
                    )

                # Persist failed network requests
                for n_err in collector.get_failed_requests():
                    error_count += 1
                    expl_repo.add_evidence(
                        run_id=run_id,
                        evidence_type=EvidenceType.NETWORK_LOG,
                        url=n_err.url,
                        description=f"Failed network request {n_err.method} {n_err.url} ({n_err.status or n_err.failure_error})",
                        metadata_json=n_err.model_dump(mode="json")
                    )

                active_explorations[run_id]["error_count"] = error_count
                expl_repo.update_metrics(run_id, pages_count, actions_count, error_count)

                # Enqueue new links within domain
                for link in discovered.internal_links:
                    norm_link = link.rstrip("/")
                    if norm_link not in visited_urls and all(norm_link != q[0].rstrip("/") for q in queue):
                        queue.append((link, depth + 1))

            activity_log.append(f"Exploration completed: {pages_count} pages, {actions_count} actions, {error_count} errors.")
            active_explorations[run_id]["status"] = ExplorationStatus.COMPLETED
            expl_repo.complete_run(run_id, status=ExplorationStatus.COMPLETED)
            logger.info(f"[Run #{run_id}] Exploration completed successfully.")

        except Exception as e:
            logger.exception(f"[Run #{run_id}] Critical failure during exploration: {e}")
            activity_log.append(f"Fatal error: {str(e)}")
            active_explorations[run_id]["status"] = ExplorationStatus.FAILED
            expl_repo.complete_run(run_id, status=ExplorationStatus.FAILED)
        finally:
            await browser_mgr.close()
            db.close()
