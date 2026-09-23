import os
import json
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from backend.app.database.models.models import TestCase, TestStep, GeneratedTest, Environment
from backend.app.database.repositories.generated_test_repo import GeneratedTestRepository
from backend.app.test_engine.locator_resolver import LocatorResolver
from backend.app.test_engine.safety import SafetyValidator, ActionSafetyLevel
from backend.app.core.config import settings
from backend.app.core.logging import logger

GENERATED_TESTS_DIR = os.path.join("playwright", "generated")

class TestGenerator:
    """
    Generates standalone, versioned Playwright test scripts from stored TestCase models
    using a controlled Intermediate Representation (IR).
    """

    def __init__(self, db: Session):
        self.db = db
        self.repo = GeneratedTestRepository(db)

    def generate_intermediate_representation(
        self,
        test_case: TestCase,
        base_url: str = "http://127.0.0.1:3000"
    ) -> Dict[str, Any]:
        """
        Builds the controlled intermediate representation (IR) from the stored test case.
        """
        # Deduplicate steps by sequence if there were duplicates stored
        seen_seqs = set()
        ordered_steps: List[TestStep] = []
        for s in sorted(test_case.steps, key=lambda x: (x.sequence, x.id)):
            if s.sequence not in seen_seqs:
                seen_seqs.add(s.sequence)
                ordered_steps.append(s)

        steps_ir = []
        for s in ordered_steps:
            target_str = s.target or ""
            # Resolve URL if navigate
            if s.action.lower() == "navigate":
                if not (target_str.startswith("http://") or target_str.startswith("https://")):
                    target_str = f"{base_url.rstrip('/')}/{target_str.lstrip('/')}"

            # Locator resolution
            if s.source_element:
                loc_res = LocatorResolver.resolve_from_element(s.source_element)
            else:
                loc_res = LocatorResolver.resolve_target_string(target_str, s.action)

            steps_ir.append({
                "sequence": s.sequence,
                "action": s.action.lower(),
                "target": target_str,
                "value": s.value,
                "expected": s.expected_result,
                "locator_strategy": loc_res.strategy,
                "locator_code": loc_res.code_snippet
            })

        return {
            "test_case_id": test_case.id,
            "name": test_case.name,
            "description": test_case.description,
            "category": test_case.category,
            "priority": test_case.priority,
            "preconditions": test_case.preconditions or [],
            "target_base_url": base_url,
            "steps": steps_ir
        }

    def convert_ir_to_playwright_code(self, ir: Dict[str, Any]) -> str:
        """
        Converts the controlled IR into executable Python Playwright test code.
        """
        tc_id = ir["test_case_id"]
        tc_name = ir["name"].replace('"', '\\"')
        category = ir["category"]
        priority = ir["priority"]
        base_url = ir["target_base_url"]
        preconditions = ir.get("preconditions", [])

        code_lines = [
            f'"""',
            f'Generated Playwright Test Case #{tc_id}: {tc_name}',
            f'Category: {category.upper()} | Priority: {priority.upper()}',
            f'Target Base URL: {base_url}',
        ]
        if preconditions:
            code_lines.append("Preconditions:")
            for p in preconditions:
                code_lines.append(f"  - {p}")
        code_lines.extend([
            f'"""',
            f'import asyncio',
            f'from playwright.async_api import Page, expect',
            f'',
            f'async def test_case_{tc_id}(page: Page, base_url: str = "{base_url}"):',
            f'    """Executes the test steps for TC #{tc_id}."""',
            f'    page.set_default_timeout(10000)',
            f'',
        ])

        for step in ir["steps"]:
            seq = step["sequence"]
            action = step["action"]
            target = step["target"]
            val = step["value"]
            expected = step["expected"].replace('"', '\\"') if step["expected"] else ""
            loc_code = step["locator_code"]

            code_lines.append(f'    # Step {seq}: {action.upper()} on {target}')
            code_lines.append(f'    # Expected: {expected}')

            if action == "navigate":
                # Ensure full URL
                dest = target if (target.startswith("http://") or target.startswith("https://")) else f'{base_url.rstrip("/")}/{target.lstrip("/")}'
                code_lines.append(f'    await page.goto("{dest}", wait_until="domcontentloaded")')
                code_lines.append(f'    await page.wait_for_load_state("networkidle")')

            elif action == "fill":
                clean_val = (val or "").replace('"', '\\"')
                if loc_code:
                    code_lines.append(f'    await {loc_code}.fill("{clean_val}")')
                else:
                    code_lines.append(f'    await page.locator("{target}").fill("{clean_val}")')

            elif action == "click":
                if loc_code:
                    code_lines.append(f'    await {loc_code}.click()')
                else:
                    code_lines.append(f'    await page.locator("{target}").click()')
                code_lines.append(f'    await page.wait_for_timeout(500)  # settle')

            elif action == "select":
                clean_val = (val or "").replace('"', '\\"')
                if loc_code:
                    code_lines.append(f'    await {loc_code}.select_option("{clean_val}")')
                else:
                    code_lines.append(f'    await page.locator("{target}").select_option("{clean_val}")')

            elif action == "assert":
                # If checking URL or status
                if "status 200" in expected.lower() or "page loads" in expected.lower():
                    code_lines.append(f'    assert page.url is not None, "Page URL should be valid"')
                elif "dashboard" in expected.lower():
                    code_lines.append(f'    await expect(page).to_have_url(lambda u: "dashboard" in u or "login" not in u, timeout=5000)')
                elif loc_code:
                    code_lines.append(f'    await expect({loc_code}).to_be_visible(timeout=5000)')
                else:
                    clean_exp = expected.split(";")[0].strip()
                    code_lines.append(f'    assert "{clean_exp}" in await page.content() or len(page.url) > 0')

            elif action == "submit":
                if loc_code:
                    code_lines.append(f'    await {loc_code}.click()')
                else:
                    code_lines.append(f'    await page.locator("{target}").click()')
                code_lines.append(f'    await page.wait_for_load_state("networkidle")')

            code_lines.append('')

        code_lines.extend([
            f'# Standalone execution helper',
            f'async def main():',
            f'    from playwright.async_api import async_playwright',
            f'    async with async_playwright() as p:',
            f'        browser = await p.chromium.launch(headless=False)',
            f'        context = await browser.new_context()',
            f'        page = await context.new_page()',
            f'        await test_case_{tc_id}(page)',
            f'        await browser.close()',
            f'',
            f'if __name__ == "__main__":',
            f'    asyncio.run(main())',
            f''
        ])

        return "\n".join(code_lines)

    def generate_and_save(
        self,
        test_case_id: int,
        base_url: Optional[str] = None
    ) -> GeneratedTest:
        """
        Generates and saves Playwright test file and DB record for a test case.
        """
        test_case = self.db.query(TestCase).filter(TestCase.id == test_case_id).first()
        if not test_case:
            raise ValueError(f"TestCase #{test_case_id} not found.")

        # Determine target base URL from environment if available
        if not base_url:
            env = (
                self.db.query(Environment)
                .filter(Environment.application_id == test_case.application_id)
                .first()
            )
            base_url = env.base_url if env else "http://127.0.0.1:3000"

        # Validate safety
        safety_res = SafetyValidator.validate_test_case(test_case)
        if not safety_res.is_valid:
            logger.warning(f"Safety check warning for TC #{test_case_id}: {safety_res.error_message}")

        # Build IR
        ir = self.generate_intermediate_representation(test_case, base_url=base_url)

        # Convert to Playwright Python code
        code = self.convert_ir_to_playwright_code(ir)

        # Prepare directory
        os.makedirs(GENERATED_TESTS_DIR, exist_ok=True)

        # Determine version
        latest = self.repo.get_latest_by_test_case(test_case_id)
        version = (latest.generation_version + 1) if latest else 1

        file_name = f"test_case_{test_case_id}_v{version}.py"
        file_path = os.path.join(GENERATED_TESTS_DIR, file_name)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code)

        logger.info(f"Generated Playwright test written to {file_path}")

        # Save to DB
        return self.repo.save_generated_test(
            test_case_id=test_case_id,
            file_path=file_path.replace("\\", "/"),
            generated_code=code,
            framework="playwright",
            language="python"
        )
