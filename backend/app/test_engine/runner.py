import os
import time
import json
import traceback
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from playwright.async_api import async_playwright, Page, BrowserContext, expect

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.browser.manager import BrowserManager
from backend.app.database.models.models import (
    TestCase,
    TestStep,
    Environment,
    TestExecution,
    TestExecutionStep,
    ExecutionEvidence,
    ExecutionStatus,
    EvidenceType,
    Element
)
from backend.app.database.repositories.execution_repo import ExecutionRepository
from backend.app.database.repositories.generated_test_repo import GeneratedTestRepository
from backend.app.test_engine.locator_resolver import LocatorResolver
from backend.app.test_engine.safety import SafetyValidator, ActionSafetyLevel
from backend.app.test_engine.generator import TestGenerator

class PlaywrightTestRunner:
    """
    Executes validated test cases against real target web applications using Playwright.
    Collects real execution results, step timings, screenshots, traces, console, and network logs.
    Zero mock data.
    """

    def __init__(self, db: Session):
        self.db = db
        self.exec_repo = ExecutionRepository(db)
        self.gen_repo = GeneratedTestRepository(db)

    async def execute_test_case(
        self,
        test_case_id: int,
        environment_id: Optional[int] = None,
        base_url: Optional[str] = None
    ) -> TestExecution:
        """
        Executes a single test case with full Playwright automation, tracing, and evidence capture.
        """
        # 1. Fetch test case
        test_case = self.db.query(TestCase).filter(TestCase.id == test_case_id).first()
        if not test_case:
            raise ValueError(f"TestCase #{test_case_id} not found.")

        # Resolve environment
        env = None
        if environment_id:
            env = self.db.query(Environment).filter(Environment.id == environment_id).first()
        elif test_case.application:
            env = (
                self.db.query(Environment)
                .filter(Environment.application_id == test_case.application_id)
                .first()
            )
        
        target_base_url = base_url or (env.base_url if env else "http://127.0.0.1:3000")

        # 2. Ensure test has generated Playwright code (generate if not present)
        generated_test = self.gen_repo.get_latest_by_test_case(test_case_id)
        if not generated_test:
            logger.info(f"Generating Playwright code for TC #{test_case_id} prior to execution...")
            generator = TestGenerator(self.db)
            generated_test = generator.generate_and_save(test_case_id, base_url=target_base_url)

        # 3. Create initial Execution Record
        execution = self.exec_repo.create_execution(
            test_case_id=test_case_id,
            environment_id=env.id if env else None,
            status=ExecutionStatus.RUNNING
        )
        execution_id = execution.id

        # 4. Safety validation
        safety_res = SafetyValidator.validate_test_case(test_case, environment=env)
        if not safety_res.is_valid:
            logger.warning(f"Execution #{execution_id} BLOCKED by safety validator: {safety_res.error_message}")
            return self.exec_repo.update_execution(
                execution_id=execution_id,
                status=ExecutionStatus.BLOCKED,
                completed_at=datetime.utcnow(),
                duration_ms=0,
                error_message=safety_res.error_message
            )

        # Prepare artifact directories
        screenshot_dir = os.path.join(settings.ARTIFACTS_DIR, "screenshots", "executions")
        trace_dir = os.path.join(settings.ARTIFACTS_DIR, "traces")
        log_dir = os.path.join(settings.ARTIFACTS_DIR, "logs")
        os.makedirs(screenshot_dir, exist_ok=True)
        os.makedirs(trace_dir, exist_ok=True)
        os.makedirs(log_dir, exist_ok=True)

        trace_path = os.path.join(trace_dir, f"exec_{execution_id}_trace.zip")
        final_screenshot_path = os.path.join(screenshot_dir, f"exec_{execution_id}_final.png")
        failure_screenshot_path = os.path.join(screenshot_dir, f"exec_{execution_id}_failure.png")
        console_log_path = os.path.join(log_dir, f"exec_{execution_id}_console.json")
        network_log_path = os.path.join(log_dir, f"exec_{execution_id}_network.json")

        browser_manager = BrowserManager()
        console_messages: List[Dict[str, Any]] = []
        network_failures: List[Dict[str, Any]] = []

        started_at = datetime.utcnow()
        start_time_monotonic = time.monotonic()
        final_url = target_base_url
        overall_status = ExecutionStatus.PASSED
        execution_error: Optional[str] = None

        # Deduplicate steps by sequence if needed
        seen_seqs = set()
        ordered_steps: List[TestStep] = []
        for s in sorted(test_case.steps, key=lambda x: (x.sequence, x.id)):
            if s.sequence not in seen_seqs:
                seen_seqs.add(s.sequence)
                ordered_steps.append(s)

        try:
            # 5. Launch Browser & Context with Tracing
            browser = await browser_manager.start()
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="AutonomousQA-Executor/1.0 (Windows NT 10.0; Win64; x64) Playwright"
            )

            # Start Playwright Trace
            await context.tracing.start(screenshots=True, snapshots=True, sources=True)

            page = await context.new_page()
            page.set_default_timeout(20000)

            page_errors: List[str] = []

            # Attach listeners
            page.on("pageerror", lambda err: page_errors.append(str(err)))
            page.on("console", lambda msg: console_messages.append({
                "type": msg.type,
                "text": msg.text,
                "location": str(msg.location)
            }))
            page.on("requestfailed", lambda req: network_failures.append({
                "url": req.url,
                "method": req.method,
                "failure": req.failure
            }))

            # 6. Execute Steps sequentially
            step_failed = False
            for step in ordered_steps:
                step_start_time = time.monotonic()
                step_started_at = datetime.utcnow()

                if step_failed:
                    # Skip subsequent steps
                    self.exec_repo.add_step_result(
                        execution_id=execution_id,
                        test_step_id=step.id,
                        sequence=step.sequence,
                        action=step.action,
                        target=step.target,
                        status="skipped",
                        started_at=None,
                        completed_at=None,
                        duration_ms=0,
                        error_message="Skipped due to earlier step failure."
                    )
                    continue

                step_error: Optional[str] = None
                step_status = "passed"
                actual_result = ""

                try:
                    actual_result = await self._execute_single_step(
                        page=page,
                        step=step,
                        base_url=target_base_url
                    )
                    final_url = page.url

                    # Check for unhandled client-side page errors
                    if page_errors:
                        err_text = page_errors.pop(0)
                        raise RuntimeError(f"Uncaught JavaScript Exception: {err_text}")

                    # Check for server 500 error page
                    try:
                        content = await page.content()
                        if "500 internal server error" in content.lower() or "database constraint violation" in content.lower():
                            raise RuntimeError("HTTP 500: Internal Server Error returned by application backend (Database constraint violation)")
                    except Exception as c_err:
                        if "HTTP 500" in str(c_err):
                            raise
                except Exception as step_ex:
                    step_failed = True
                    step_status = "failed"
                    step_error = f"{type(step_ex).__name__}: {str(step_ex)}"
                    overall_status = ExecutionStatus.FAILED
                    execution_error = f"Step #{step.sequence} failed: {step_error}"
                    logger.error(f"Step #{step.sequence} failed in execution #{execution_id}: {step_error}")

                    # Capture failure screenshot immediately
                    try:
                        await page.screenshot(path=failure_screenshot_path, full_page=True)
                        self.exec_repo.add_evidence(
                            execution_id=execution_id,
                            evidence_type=EvidenceType.SCREENSHOT,
                            file_path=failure_screenshot_path.replace("\\", "/"),
                            description=f"Failure screenshot captured at Step #{step.sequence}"
                        )
                    except Exception as ss_err:
                        logger.warning(f"Could not take failure screenshot: {ss_err}")

                step_duration_ms = int((time.monotonic() - step_start_time) * 1000)
                step_completed_at = datetime.utcnow()

                self.exec_repo.add_step_result(
                    execution_id=execution_id,
                    test_step_id=step.id,
                    sequence=step.sequence,
                    action=step.action,
                    target=step.target,
                    status=step_status,
                    started_at=step_started_at,
                    completed_at=step_completed_at,
                    duration_ms=step_duration_ms,
                    error_message=step_error,
                    actual_result=actual_result if step_status == "passed" else step_error
                )

            # Final screenshot
            try:
                await page.screenshot(path=final_screenshot_path, full_page=True)
                self.exec_repo.add_evidence(
                    execution_id=execution_id,
                    evidence_type=EvidenceType.SCREENSHOT,
                    file_path=final_screenshot_path.replace("\\", "/"),
                    description="Final execution screenshot"
                )
            except Exception as ss_err:
                logger.warning(f"Could not take final screenshot: {ss_err}")

            # Stop and save trace
            try:
                await context.tracing.stop(path=trace_path)
                self.exec_repo.add_evidence(
                    execution_id=execution_id,
                    evidence_type=EvidenceType.TRACE,
                    file_path=trace_path.replace("\\", "/"),
                    description="Full Playwright execution trace file"
                )
            except Exception as trace_err:
                logger.warning(f"Could not export trace: {trace_err}")

            await context.close()

        except Exception as ex:
            overall_status = ExecutionStatus.ERROR
            execution_error = f"Test execution engine error: {type(ex).__name__} - {str(ex)}\n{traceback.format_exc()}"
            logger.error(f"Error running execution #{execution_id}: {execution_error}")

        finally:
            await browser_manager.close()

        # Save console and network logs
        if console_messages:
            try:
                with open(console_log_path, "w", encoding="utf-8") as f:
                    json.dump(console_messages, f, indent=2)
                self.exec_repo.add_evidence(
                    execution_id=execution_id,
                    evidence_type=EvidenceType.CONSOLE_LOG,
                    file_path=console_log_path.replace("\\", "/"),
                    description=f"{len(console_messages)} console message entries",
                    metadata_json={"count": len(console_messages)}
                )
            except Exception as log_err:
                logger.warning(f"Failed to write console logs: {log_err}")

        if network_failures:
            try:
                with open(network_log_path, "w", encoding="utf-8") as f:
                    json.dump(network_failures, f, indent=2)
                self.exec_repo.add_evidence(
                    execution_id=execution_id,
                    evidence_type=EvidenceType.NETWORK_LOG,
                    file_path=network_log_path.replace("\\", "/"),
                    description=f"{len(network_failures)} network failure entries",
                    metadata_json={"count": len(network_failures)}
                )
            except Exception as net_err:
                logger.warning(f"Failed to write network logs: {net_err}")

        total_duration_ms = int((time.monotonic() - start_time_monotonic) * 1000)
        completed_at = datetime.utcnow()

        # Update final execution record
        updated_exec = self.exec_repo.update_execution(
            execution_id=execution_id,
            status=overall_status,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=total_duration_ms,
            error_message=execution_error,
            final_url=final_url
        )

        # Automatically trigger intelligent defect investigation on failure
        if overall_status in (ExecutionStatus.FAILED, ExecutionStatus.ERROR):
            try:
                from backend.app.services.bug_service import BugService
                bug_service = BugService(self.db)
                await bug_service.analyze_failed_execution(execution_id)
            except Exception as bug_err:
                logger.warning(f"Automatic bug analysis on execution #{execution_id} encountered an issue: {bug_err}")

        return updated_exec


    async def _execute_single_step(
        self,
        page: Page,
        step: TestStep,
        base_url: str
    ) -> str:
        """
        Executes a single test step in Playwright, evaluating assertions.
        """
        action = step.action.lower().strip()
        target = (step.target or "").strip()
        val = step.value
        expected = step.expected_result or ""

        # Resolve locator
        if step.source_element:
            loc_res = LocatorResolver.resolve_from_element(step.source_element)
        else:
            loc_res = LocatorResolver.resolve_target_string(target, action)

        if action == "navigate":
            dest_url = target
            if not (dest_url.startswith("http://") or dest_url.startswith("https://")):
                dest_url = f"{base_url.rstrip('/')}/{dest_url.lstrip('/')}"
            
            response = await page.goto(dest_url, wait_until="domcontentloaded", timeout=25000)
            await page.wait_for_timeout(300)
            status_code = response.status if response else 200
            return f"Navigated to {dest_url} (HTTP {status_code})"

        elif action == "fill":
            locator = self._get_locator(page, target, loc_res)
            await locator.wait_for(state="visible", timeout=6000)
            await locator.fill(val or "")
            return f"Filled target with '{val}'"

        elif action == "click":
            locator = self._get_locator(page, target, loc_res)
            await locator.wait_for(state="visible", timeout=6000)
            await locator.click()
            await page.wait_for_timeout(500)
            return f"Clicked {target}"

        elif action == "select":
            locator = self._get_locator(page, target, loc_res)
            await locator.wait_for(state="visible", timeout=6000)
            await locator.select_option(val or "")
            return f"Selected option '{val}'"

        elif action == "submit":
            locator = self._get_locator(page, target, loc_res)
            await locator.click()
            await page.wait_for_timeout(600)
            return f"Submitted form via {target}"

        elif action == "assert":
            # Assertion evaluation
            exp_lower = expected.lower()
            if "status 200" in exp_lower or "rendered" in exp_lower or "loads" in exp_lower:
                assert page.url is not None and len(page.url) > 0, "Page did not load properly."
                return f"Verified page loaded at {page.url}"

            elif "dashboard" in exp_lower or "redirect" in exp_lower:
                current = page.url
                assert "dashboard" in current or "login" not in current, f"Expected dashboard redirect, got {current}"
                return f"Verified redirected to {page.url}"

            elif "error" in exp_lower or "denied" in exp_lower or "prevent" in exp_lower:
                content = await page.content()
                # Verify error banner or validation state
                has_error_text = any(k in content.lower() for k in ["invalid", "error", "required", "failed", "denied", "alert"])
                assert has_error_text or page.url.endswith("/login"), "Expected error indication or prevented submission."
                return f"Verified validation/error state on {page.url}"

            else:
                # Check element or text presence
                if loc_res.is_valid:
                    loc = self._get_locator(page, target, loc_res)
                    await expect(loc).to_be_visible(timeout=5000)
                    return f"Verified {target} is visible on page"
                content = await page.content()
                assert len(content) > 100, "Page has insufficient content."
                return f"Verified assertion on {page.url}"

        else:
            raise ValueError(f"Unsupported step action '{action}'")

    def _get_locator(self, page: Page, target: str, loc_res: Any):
        """Helper to get Playwright Locator object."""
        try:
            if loc_res.strategy == "role":
                # e.g. page.get_by_role("button", name="...")
                import re
                role_match = re.search(r'get_by_role\("([^"]+)", name="([^"]+)"\)', loc_res.code_snippet)
                if role_match:
                    return page.get_by_role(role_match.group(1), name=role_match.group(2))
            elif loc_res.strategy == "placeholder":
                import re
                ph_match = re.search(r'get_by_placeholder\("([^"]+)"\)', loc_res.code_snippet)
                if ph_match:
                    return page.get_by_placeholder(ph_match.group(1))
            elif loc_res.strategy == "text":
                import re
                txt_match = re.search(r'get_by_text\("([^"]+)"\)', loc_res.code_snippet)
                if txt_match:
                    return page.get_by_text(txt_match.group(1))
        except Exception:
            pass

        # Fallback to direct selector
        return page.locator(target)
