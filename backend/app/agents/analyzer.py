import json
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session

from backend.app.database.repositories.page_repo import PageRepository
from backend.app.database.models.models import Page, Element
from backend.app.api.schemas.testcase import AIAnalysisOutput, AIWorkflowModel, AITestCaseModel, AITestStepModel, AIWorkflowStepModel
from backend.app.agents.ai_provider import get_ai_provider, GeminiProvider
from backend.app.core.logging import logger

SYSTEM_PROMPT = """
You are a Senior Principal QA Automation Engineer analyzing a real web application.
You are given the exact application map discovered by a real browser crawler:
- Pages (URLs, titles, status codes)
- Discovered interactive elements (selectors, tag names, types, labels, placeholders)

CRITICAL INSTRUCTIONS & ANTI-HALLUCINATION RULES:
1. NO HALLUCINATIONS: You MUST ONLY generate workflows and test cases based strictly on the observed pages and elements provided in the application map.
2. DO NOT invent nonexistent pages (e.g. do NOT invent payments, billing, subscriptions, invoices) unless they appear in the provided pages.
3. Every test step MUST reference a real `source_page_url` and `source_element_selector` from the map.
4. Categorize test cases appropriately:
   - 'smoke': Verifying core pages load and basic workflows succeed.
   - 'functional': Validating creation, view, update actions using real forms and buttons.
   - 'negative': Validating error handling, invalid inputs, unauthorized access.
   - 'boundary': Testing input limits, empty inputs, format constraints on real input fields.
   - 'form validation': Testing required fields on discovered forms.
5. Assign risk_level to workflows and priority to test cases: 'critical', 'high', 'medium', or 'low' based on QA risk analysis.
6. Return your response ONLY as valid JSON conforming strictly to the requested schema.

JSON SCHEMA:
{
  "summary": "High-level summary of application architecture and QA risk analysis",
  "workflows": [
    {
      "name": "Workflow Name",
      "description": "Workflow description",
      "risk_level": "critical | high | medium | low",
      "steps": [
        {
          "sequence": 1,
          "action": "action description",
          "expected_behavior": "expected behavior",
          "target_page_url": "http://...",
          "target_element_selector": "selector or null"
        }
      ]
    }
  ],
  "test_cases": [
    {
      "name": "TC-001 Test Case Name",
      "workflow_name": "Must match a workflow name above",
      "category": "smoke | functional | negative | boundary | form validation | e2e | authentication",
      "priority": "critical | high | medium | low",
      "description": "Test case description",
      "preconditions": ["Precondition 1"],
      "steps": [
        {
          "sequence": 1,
          "action": "navigate | click | fill | select | assert",
          "target": "selector or url",
          "value": "optional input value",
          "expected_result": "expected outcome",
          "source_page_url": "http://...",
          "source_element_selector": "selector or null"
        }
      ]
    }
  ]
}
"""

class ApplicationAnalyzer:
    """Extracts application knowledge from database and coordinates AI reasoning to generate workflows and test cases."""

    def __init__(self, db: Session):
        self.db = db
        self.page_repo = PageRepository(db)

    def build_application_context(self, application_id: int) -> Tuple[str, Dict[str, Page], Dict[str, Element]]:
        pages = self.page_repo.get_pages_by_app(application_id)
        if not pages:
            raise ValueError(f"No pages discovered for application #{application_id}. Run an exploration first.")

        url_page_map: Dict[str, Page] = {}
        selector_element_map: Dict[str, Element] = {}

        context_lines = [f"=== DISCOVERED APPLICATION MAP ({len(pages)} Pages) ==="]
        for p in pages:
            url_page_map[p.url.rstrip("/")] = p
            context_lines.append(f"\nPAGE: {p.url} (Title: '{p.title or 'Untitled'}', HTTP: {p.status_code or 200})")
            
            elements = self.page_repo.get_elements_by_page(p.id)
            if elements:
                context_lines.append(f"  Interactive Elements ({len(elements)}):")
                for el in elements:
                    selector_element_map[el.selector] = el
                    label = f"'{el.text}'" if el.text else (f"name='{el.name}'" if el.name else "")
                    context_lines.append(f"    - [{el.element_type}] selector='{el.selector}' {label} (tag: <{el.tag_name}>)")
            else:
                context_lines.append("  (No interactive controls found on this page)")

        return "\n".join(context_lines), url_page_map, selector_element_map

    def _generate_deterministic_analysis(
        self,
        app_context: str,
        url_page_map: Dict[str, Page],
        selector_element_map: Dict[str, Element]
    ) -> AIAnalysisOutput:
        """Deterministic QA reasoning fallback ensuring 100% reliable test generation from discovered application map."""
        workflows: List[AIWorkflowModel] = []
        test_cases: List[AITestCaseModel] = []

        # Analyze discovered pages
        pages = list(url_page_map.values())
        base_urls = [p.url for p in pages]

        # 1. Identify Authentication Workflow
        auth_page = next((p for p in pages if any(kw in p.url.lower() for kw in ["login", "signin", "auth"])), None)
        dashboard_page = next((p for p in pages if any(kw in p.url.lower() for kw in ["dashboard", "home", "admin"])), None)
        
        if auth_page:
            auth_elements = self.page_repo.get_elements_by_page(auth_page.id)
            user_input = next((e for e in auth_elements if "user" in (e.name or "").lower() or "email" in (e.name or "").lower() or e.element_type == "text"), None)
            pass_input = next((e for e in auth_elements if "pass" in (e.name or "").lower() or e.element_type == "password"), None)
            submit_btn = next((e for e in auth_elements if e.element_type in ("button", "submit")), None)

            auth_steps = [
                AIWorkflowStepModel(
                    sequence=1,
                    action="Open login page",
                    expected_behavior="Login interface loads with credentials inputs",
                    target_page_url=auth_page.url,
                    target_element_selector=None
                )
            ]
            if user_input:
                auth_steps.append(AIWorkflowStepModel(
                    sequence=2,
                    action=f"Enter credentials in {user_input.selector}",
                    expected_behavior="Inputs accept user text",
                    target_page_url=auth_page.url,
                    target_element_selector=user_input.selector
                ))
            if submit_btn:
                auth_steps.append(AIWorkflowStepModel(
                    sequence=3,
                    action=f"Click submit button {submit_btn.selector}",
                    expected_behavior="User is authenticated and redirected to dashboard",
                    target_page_url=auth_page.url,
                    target_element_selector=submit_btn.selector
                ))

            workflows.append(AIWorkflowModel(
                name="User Authentication",
                description="Verifies user identity verification, login credentials handling, and access control.",
                risk_level="critical",
                steps=auth_steps
            ))

            # Add Smoke Test: Valid Login
            test_cases.append(AITestCaseModel(
                name="TC-001 Smoke: Valid User Login",
                workflow_name="User Authentication",
                category="smoke",
                priority="critical",
                description="Ensure registered users can authenticate successfully and reach the dashboard.",
                preconditions=["Valid user credentials exist in database"],
                steps=[
                    AITestStepModel(
                        sequence=1,
                        action="navigate",
                        target=auth_page.url,
                        expected_result="Login page loads with status 200",
                        source_page_url=auth_page.url
                    ),
                    AITestStepModel(
                        sequence=2,
                        action="fill",
                        target=user_input.selector if user_input else "input[type='text']",
                        value="admin@example.com",
                        expected_result="Username is populated",
                        source_page_url=auth_page.url,
                        source_element_selector=user_input.selector if user_input else None
                    ),
                    AITestStepModel(
                        sequence=3,
                        action="fill",
                        target=pass_input.selector if pass_input else "input[type='password']",
                        value="validPassword123",
                        expected_result="Password is obfuscated",
                        source_page_url=auth_page.url,
                        source_element_selector=pass_input.selector if pass_input else None
                    ),
                    AITestStepModel(
                        sequence=4,
                        action="click",
                        target=submit_btn.selector if submit_btn else "button[type='submit']",
                        expected_result="User session established and redirected to dashboard",
                        source_page_url=auth_page.url,
                        source_element_selector=submit_btn.selector if submit_btn else None
                    )
                ]
            ))

            # Add Negative Test: Invalid Credentials
            test_cases.append(AITestCaseModel(
                name="TC-002 Negative: Invalid Password Rejection",
                workflow_name="User Authentication",
                category="negative",
                priority="high",
                description="Verify that access is rejected when an invalid password is provided.",
                preconditions=["User account exists"],
                steps=[
                    AITestStepModel(
                        sequence=1,
                        action="navigate",
                        target=auth_page.url,
                        expected_result="Login page rendered",
                        source_page_url=auth_page.url
                    ),
                    AITestStepModel(
                        sequence=2,
                        action="fill",
                        target=user_input.selector if user_input else "input[type='text']",
                        value="admin@example.com",
                        expected_result="Username accepted",
                        source_page_url=auth_page.url,
                        source_element_selector=user_input.selector if user_input else None
                    ),
                    AITestStepModel(
                        sequence=3,
                        action="fill",
                        target=pass_input.selector if pass_input else "input[type='password']",
                        value="wrong_password_xyz",
                        expected_result="Password field filled",
                        source_page_url=auth_page.url,
                        source_element_selector=pass_input.selector if pass_input else None
                    ),
                    AITestStepModel(
                        sequence=4,
                        action="click",
                        target=submit_btn.selector if submit_btn else "button[type='submit']",
                        expected_result="Access denied; authentication error displayed",
                        source_page_url=auth_page.url,
                        source_element_selector=submit_btn.selector if submit_btn else None
                    )
                ]
            ))

        # 2. Identify Product / Resource Management Workflows
        product_pages = [p for p in pages if "product" in p.url.lower()]
        if product_pages:
            prod_list_page = next((p for p in product_pages if "create" not in p.url.lower()), product_pages[0])
            prod_create_page = next((p for p in product_pages if "create" in p.url.lower()), None)
            
            p_steps = [
                AIWorkflowStepModel(
                    sequence=1,
                    action="Navigate to Product Catalog",
                    expected_behavior="Catalog renders with item rows and management controls",
                    target_page_url=prod_list_page.url
                )
            ]

            if prod_create_page:
                p_steps.append(AIWorkflowStepModel(
                    sequence=2,
                    action="Open Create Product Form",
                    expected_behavior="Form fields render (Title, Category, Price)",
                    target_page_url=prod_create_page.url
                ))

            workflows.append(AIWorkflowModel(
                name="Product Management",
                description="Manages product listings, catalog inspection, and creation of new product offerings.",
                risk_level="high",
                steps=p_steps
            ))

            # Functional test: View Catalog
            test_cases.append(AITestCaseModel(
                name="TC-003 Functional: Browse Products Catalog",
                workflow_name="Product Management",
                category="functional",
                priority="high",
                description="Verify that the products catalog displays available items with correct price and category columns.",
                preconditions=["Products exist in catalog"],
                steps=[
                    AITestStepModel(
                        sequence=1,
                        action="navigate",
                        target=prod_list_page.url,
                        expected_result="Product management catalog renders with HTTP 200",
                        source_page_url=prod_list_page.url
                    )
                ]
            ))

            # Form Validation & Boundary test on Create Product if available
            if prod_create_page:
                c_elements = self.page_repo.get_elements_by_page(prod_create_page.id)
                title_input = next((e for e in c_elements if "title" in (e.name or "").lower() or "name" in (e.name or "").lower()), None)
                save_btn = next((e for e in c_elements if e.element_type in ("button", "submit")), None)

                test_cases.append(AITestCaseModel(
                    name="TC-004 Form Validation: Required Fields on Product Creation",
                    workflow_name="Product Management",
                    category="form validation",
                    priority="medium",
                    description="Ensure submitting product creation form without title triggers HTML5 or application required validation.",
                    preconditions=["User is authorized to create products"],
                    steps=[
                        AITestStepModel(
                            sequence=1,
                            action="navigate",
                            target=prod_create_page.url,
                            expected_result="Create product form rendered",
                            source_page_url=prod_create_page.url
                        ),
                        AITestStepModel(
                            sequence=2,
                            action="click",
                            target=save_btn.selector if save_btn else "button[type='submit']",
                            expected_result="Browser prevents submission or displays required field error",
                            source_page_url=prod_create_page.url,
                            source_element_selector=save_btn.selector if save_btn else None
                        )
                    ]
                ))

        # 3. Identify Orders Workflow
        orders_page = next((p for p in pages if "order" in p.url.lower()), None)
        if orders_page:
            workflows.append(AIWorkflowModel(
                name="Order Processing & Tracking",
                description="Allows operators to review customer order statuses, transaction amounts, and fulfillments.",
                risk_level="high",
                steps=[
                    AIWorkflowStepModel(
                        sequence=1,
                        action="Access Order History",
                        expected_behavior="Order records table loaded with customer details and status indicators",
                        target_page_url=orders_page.url
                    )
                ]
            ))
            test_cases.append(AITestCaseModel(
                name="TC-005 Functional: Inspect Customer Orders History",
                workflow_name="Order Processing & Tracking",
                category="functional",
                priority="high",
                description="Verify that orders history renders valid order numbers, amounts, and statuses.",
                preconditions=["Customer orders exist"],
                steps=[
                    AITestStepModel(
                        sequence=1,
                        action="navigate",
                        target=orders_page.url,
                        expected_result="Orders table displays customer and transaction info",
                        source_page_url=orders_page.url
                    )
                ]
            ))

        # 4. Identify Profile Workflow
        profile_page = next((p for p in pages if "profile" in p.url.lower()), None)
        if profile_page:
            workflows.append(AIWorkflowModel(
                name="User Profile Management",
                description="Enables account holders to inspect and update their user credentials and preferences.",
                risk_level="medium",
                steps=[
                    AIWorkflowStepModel(
                        sequence=1,
                        action="Load User Profile Settings",
                        expected_behavior="Profile settings form renders current full name and email",
                        target_page_url=profile_page.url
                    )
                ]
            ))
            test_cases.append(AITestCaseModel(
                name="TC-006 Boundary: Profile Email Format Validation",
                workflow_name="User Profile Management",
                category="boundary",
                priority="medium",
                description="Verify boundary check when entering an invalid email format in profile update form.",
                preconditions=["Logged in user"],
                steps=[
                    AITestStepModel(
                        sequence=1,
                        action="navigate",
                        target=profile_page.url,
                        expected_result="Profile settings loaded",
                        source_page_url=profile_page.url
                    )
                ]
            ))

        # 5. Fallback for general navigation and interactive workflows if no specific domain keyword matched
        if not workflows and pages:
            primary_page = pages[0]
            primary_elements = self.page_repo.get_elements_by_page(primary_page.id)
            steps = [
                AIWorkflowStepModel(
                    sequence=1,
                    action=f"Navigate to {primary_page.title or 'Dashboard'}",
                    expected_behavior="Page loads successfully with HTTP 200",
                    target_page_url=primary_page.url
                )
            ]
            if primary_elements:
                interactive_el = next((e for e in primary_elements if e.is_interactive), primary_elements[0])
                steps.append(AIWorkflowStepModel(
                    sequence=2,
                    action=f"Interact with control {interactive_el.selector}",
                    expected_behavior=f"Element {interactive_el.selector} responds to user interaction",
                    target_page_url=primary_page.url,
                    target_element_selector=interactive_el.selector
                ))
            wf_name = f"{primary_page.title or 'Core Application'} Workflow"
            workflows.append(AIWorkflowModel(
                name=wf_name,
                description="Core application navigation and primary interactive feature flow.",
                risk_level="high",
                steps=steps
            ))
            test_cases.append(AITestCaseModel(
                name=f"TC-001 Smoke: Access {primary_page.title or 'Core View'}",
                workflow_name=wf_name,
                category="smoke",
                priority="critical",
                description="Verify that primary application view loads and interactive components are functional.",
                preconditions=["Application server is online"],
                steps=[
                    AITestStepModel(
                        sequence=1,
                        action="navigate",
                        target=primary_page.url,
                        expected_result="Page renders with status 200",
                        source_page_url=primary_page.url
                    )
                ]
            ))

        return AIAnalysisOutput(
            summary=f"Discovered {len(workflows)} high-confidence business workflows and generated {len(test_cases)} traceable test scenarios across {len(pages)} observed pages.",
            workflows=workflows,
            test_cases=test_cases
        )

    async def analyze(self, application_id: int) -> AIAnalysisOutput:
        """Executes full AI application understanding and test case generation with strict validation."""
        context_text, url_page_map, selector_element_map = self.build_application_context(application_id)
        provider = get_ai_provider()

        prompt = f"{SYSTEM_PROMPT}\n\n{context_text}"

        try:
            if isinstance(provider, GeminiProvider):
                raw_json = await provider.analyze_application_map(prompt)
                output = AIAnalysisOutput(**raw_json)
                logger.info(f"Gemini successfully generated {len(output.workflows)} workflows and {len(output.test_cases)} test cases.")
                return output
            else:
                return self._generate_deterministic_analysis(context_text, url_page_map, selector_element_map)
        except Exception as e:
            logger.warning(f"AI Provider call failed ({e}). Falling back to deterministic QA reasoning engine...")
            return self._generate_deterministic_analysis(context_text, url_page_map, selector_element_map)
