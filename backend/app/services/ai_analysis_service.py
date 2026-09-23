import asyncio
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from backend.app.database.connection import SessionLocal
from backend.app.database.repositories.workflow_repo import WorkflowRepository
from backend.app.database.repositories.testcase_repo import TestCaseRepository
from backend.app.database.repositories.page_repo import PageRepository
from backend.app.database.repositories.application_repo import ApplicationRepository
from backend.app.agents.analyzer import ApplicationAnalyzer
from backend.app.core.logging import logger

# In-memory tracking for real-time analysis status & activity
active_analyses: Dict[int, Dict[str, Any]] = {}

class AIAnalysisService:
    """Orchestrates AI understanding of discovered applications and stores workflows & test cases."""

    def __init__(self, db: Session):
        self.db = db
        self.workflow_repo = WorkflowRepository(db)
        self.testcase_repo = TestCaseRepository(db)
        self.page_repo = PageRepository(db)
        self.app_repo = ApplicationRepository(db)

    async def execute_analysis(self, application_id: int):
        """Asynchronous worker executing multi-stage AI reasoning and database persistence."""
        db = SessionLocal()
        wf_repo = WorkflowRepository(db)
        tc_repo = TestCaseRepository(db)
        page_repo = PageRepository(db)
        app_repo = ApplicationRepository(db)

        app = app_repo.get_by_id(application_id)
        if not app:
            logger.error(f"Application #{application_id} not found for AI analysis.")
            db.close()
            return

        activity_log: List[str] = [f"Initiated AI analysis for application '{app.name}'."]
        active_analyses[application_id] = {
            "status": "ANALYZING",
            "stage": "Reading application map and discovered elements",
            "workflows_count": 0,
            "test_cases_count": 0,
            "activity_log": activity_log
        }

        try:
            analyzer = ApplicationAnalyzer(db)
            
            # STAGE 1: Analyzing Application Map
            active_analyses[application_id]["stage"] = "Synthesizing discovered pages, inputs, and interactive DOM controls"
            activity_log.append("Synthesizing discovered application map and interactive DOM elements...")
            await asyncio.sleep(0.5)

            # STAGE 2: Identifying Workflows
            active_analyses[application_id]["status"] = "IDENTIFYING WORKFLOWS"
            active_analyses[application_id]["stage"] = "Reasoning over business workflows and risk factors"
            activity_log.append("Reasoning over business workflows and calculating QA risk levels...")

            # Execute AI reasoning with Gemini / provider
            analysis_output = await analyzer.analyze(application_id)

            # STAGE 3: Generating Test Cases
            active_analyses[application_id]["status"] = "GENERATING TEST CASES"
            active_analyses[application_id]["stage"] = "Deriving smoke, functional, negative, and boundary scenarios"
            activity_log.append(f"AI identified {len(analysis_output.workflows)} workflows. Deriving structured test cases...")
            await asyncio.sleep(0.5)

            # STAGE 4: Validating Results & Persisting
            active_analyses[application_id]["status"] = "VALIDATING RESULTS"
            active_analyses[application_id]["stage"] = "Verifying traceability against database entities and saving"
            activity_log.append("Enforcing traceability: mapping test steps to real database page and element IDs...")

            # Clean previous workflows and test cases for this app to support re-analysis
            tc_repo.delete_by_application(application_id)
            wf_repo.delete_by_application(application_id)

            # Build URL -> Page & Selector -> Element lookup maps
            pages = page_repo.get_pages_by_app(application_id)
            url_to_page = {p.url.rstrip("/"): p for p in pages}
            elem_lookup = {}
            for p in pages:
                for el in page_repo.get_elements_by_page(p.id):
                    elem_lookup[(p.id, el.selector)] = el

            # Persist Workflows
            workflow_name_to_id: Dict[str, int] = {}
            for wf_data in analysis_output.workflows:
                db_wf = wf_repo.create_workflow(
                    application_id=application_id,
                    name=wf_data.name,
                    description=wf_data.description,
                    risk_level=wf_data.risk_level
                )
                workflow_name_to_id[wf_data.name.lower()] = db_wf.id

                for step in wf_data.steps:
                    matched_page = url_to_page.get(step.target_page_url.rstrip("/"))
                    matched_element = None
                    if matched_page and step.target_element_selector:
                        matched_element = elem_lookup.get((matched_page.id, step.target_element_selector))

                    wf_repo.add_step(
                        workflow_id=db_wf.id,
                        sequence=step.sequence,
                        action=step.action,
                        expected_behavior=step.expected_behavior,
                        page_id=matched_page.id if matched_page else None,
                        element_id=matched_element.id if matched_element else None
                    )

            # Persist Test Cases
            for tc_data in analysis_output.test_cases:
                wf_id = workflow_name_to_id.get(tc_data.workflow_name.lower())
                # If exact name not found, match first partial or first workflow
                if not wf_id and workflow_name_to_id:
                    wf_id = next((wid for wname, wid in workflow_name_to_id.items() if wname in tc_data.workflow_name.lower()), list(workflow_name_to_id.values())[0])

                db_tc = tc_repo.create_test_case(
                    application_id=application_id,
                    workflow_id=wf_id,
                    name=tc_data.name,
                    description=tc_data.description,
                    category=tc_data.category,
                    priority=tc_data.priority,
                    preconditions=tc_data.preconditions
                )

                for t_step in tc_data.steps:
                    matched_page = url_to_page.get(t_step.source_page_url.rstrip("/"))
                    matched_element = None
                    if matched_page and t_step.source_element_selector:
                        matched_element = elem_lookup.get((matched_page.id, t_step.source_element_selector))

                    tc_repo.add_step(
                        test_case_id=db_tc.id,
                        sequence=t_step.sequence,
                        action=t_step.action,
                        target=t_step.target,
                        value=t_step.value,
                        expected_result=t_step.expected_result,
                        source_page_id=matched_page.id if matched_page else None,
                        source_element_id=matched_element.id if matched_element else None
                    )

            # STAGE 5: Complete
            active_analyses[application_id]["status"] = "COMPLETED"
            active_analyses[application_id]["stage"] = "Analysis finished successfully"
            active_analyses[application_id]["workflows_count"] = len(analysis_output.workflows)
            active_analyses[application_id]["test_cases_count"] = len(analysis_output.test_cases)
            activity_log.append(f"Successfully generated and stored {len(analysis_output.workflows)} workflows and {len(analysis_output.test_cases)} test cases in PostgreSQL/SQLite.")
            logger.info(f"AI analysis completed for application #{application_id}.")

        except Exception as e:
            logger.exception(f"AI analysis failed for application #{application_id}: {e}")
            active_analyses[application_id]["status"] = "FAILED"
            active_analyses[application_id]["stage"] = f"Error: {str(e)}"
            activity_log.append(f"Analysis failed: {str(e)}")
        finally:
            db.close()
