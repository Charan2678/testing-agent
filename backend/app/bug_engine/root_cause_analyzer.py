import json
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.agents.ai_provider import GeminiProvider, get_ai_provider

class AIBugAnalysisResult(BaseModel):
    title: str = Field(..., description="Concise bug title")
    summary: str = Field(..., description="1-2 sentence executive summary of the issue")
    description: str = Field(..., description="Detailed technical description of the defect")
    category: str = Field(default="FUNCTIONAL", description="FUNCTIONAL, VALIDATION, UI, API, JAVASCRIPT, etc.")
    severity: str = Field(default="HIGH", description="CRITICAL, HIGH, MEDIUM, LOW")
    priority: str = Field(default="HIGH", description="CRITICAL, HIGH, MEDIUM, LOW")
    expected_behavior: str = Field(..., description="What the application should have done")
    actual_behavior: str = Field(..., description="What the application actually did")
    root_cause: str = Field(..., description="Inferred technical root cause")
    confidence_level: str = Field(default="LIKELY", description="CONFIRMED, LIKELY, POSSIBLE, UNKNOWN")
    confidence_score: int = Field(default=80, ge=0, le=100, description="Percentage confidence 0-100")
    severity_explanation: str = Field(..., description="Justification for the assigned severity")
    reasoning_summary: str = Field(..., description="Summary of evidence supporting this conclusion")

class RootCauseAnalyzer:
    """
    Analyzes failed execution evidence using structured LLM reasoning and
    strict calibration to deduce root causes without hallucination.
    """

    SYSTEM_PROMPT = """
You are a Principal Software Quality Engineer and Failure Analysis Expert.
Analyze the provided Playwright test execution failure and browser evidence.
Generate a structured, evidence-based bug analysis report.

CRITICAL RULES:
1. STRICT ANTI-HALLUCINATION: Base your conclusions ONLY on the provided test steps, console messages, network failures, error messages, and URL.
2. ROOT CAUSE CONFIDENCE:
   - Use 'CONFIRMED' ONLY if direct evidence (e.g. an uncaught JavaScript TypeError, an explicit HTTP 500 response from an endpoint) proves the exact line or subsystem that broke.
   - Use 'LIKELY' when symptoms strongly point to a specific frontend or form handler failure.
   - Use 'POSSIBLE' when multiple plausible causes exist.
   - Use 'UNKNOWN' if browser evidence is insufficient to diagnose the backend. If so, state: "Exact root cause cannot be determined from browser evidence alone."
   - NEVER invent database, SQL, or internal server code causes without evidence.
3. SEVERITY RULES:
   - CRITICAL: App-wide blocking or major security/authentication failure.
   - HIGH: Core business workflow (e.g. creating products, orders, auth) cannot be completed.
   - MEDIUM: Important functionality broken, but workaround exists.
   - LOW: Minor validation, cosmetic, or text issue.
4. Output must strictly be a single JSON object with these EXACT keys (all string/number values, no nested objects):
{
  "title": "Concise defect title (e.g. HTTP 500 on Negative Product Price)",
  "summary": "One sentence summary of the issue",
  "description": "Detailed explanation of the failure and steps observed",
  "classification": "APPLICATION_BUG",
  "category": "API",
  "severity": "CRITICAL",
  "priority": "HIGH",
  "expected_behavior": "Expected behavior according to QA requirements",
  "actual_behavior": "Actual observed failure behavior",
  "root_cause": "Plain text technical explanation of the root cause",
  "confidence_level": "CONFIRMED",
  "confidence_score": 95,
  "severity_explanation": "Justification for severity level",
  "reasoning_summary": "Summary of evidence supporting conclusion"
}
"""

    def __init__(self):
        self.provider = get_ai_provider()

    async def analyze(
        self,
        test_case_name: str,
        test_category: str,
        failed_step_sequence: int,
        failed_step_action: str,
        failed_step_target: str,
        failed_step_value: Optional[str],
        expected_result: str,
        error_message: str,
        final_url: str,
        console_logs: List[Dict[str, Any]],
        network_failures: List[Dict[str, Any]],
        preliminary_classification: str,
        preliminary_category: str
    ) -> AIBugAnalysisResult:
        """
        Executes AI root-cause analysis on real execution evidence.
        """
        # Prepare context payload
        evidence_summary = {
            "test_case": test_case_name,
            "test_category": test_category,
            "failed_step": {
                "sequence": failed_step_sequence,
                "action": failed_step_action,
                "target": failed_step_target,
                "value": failed_step_value,
                "expected": expected_result
            },
            "error_message": error_message,
            "final_url": final_url,
            "console_errors": [l for l in console_logs if l.get("type") == "error"][:10],
            "network_failures": network_failures[:10],
            "preliminary_classification": preliminary_classification,
            "preliminary_category": preliminary_category
        }

        prompt = f"{self.SYSTEM_PROMPT}\n\nEVIDENCE TO ANALYZE:\n{json.dumps(evidence_summary, indent=2)}"

        if isinstance(self.provider, GeminiProvider):
            try:
                raw_json = await self.provider.analyze_application_map(prompt)
                validated = AIBugAnalysisResult.model_validate(raw_json)
                logger.info(f"AI Root-Cause Analysis succeeded: '{validated.title}' (confidence: {validated.confidence_level})")
                return validated
            except Exception as e:
                logger.warning(f"Gemini AI bug analysis call failed: {e}. Falling back to deterministic engine.")

        # Deterministic Rule-Based Analyzer
        return self._deterministic_analysis(
            test_case_name=test_case_name,
            failed_step_action=failed_step_action,
            failed_step_target=failed_step_target,
            expected_result=expected_result,
            error_message=error_message,
            final_url=final_url,
            console_logs=console_logs,
            network_failures=network_failures,
            preliminary_category=preliminary_category
        )

    def _deterministic_analysis(
        self,
        test_case_name: str,
        failed_step_action: str,
        failed_step_target: str,
        expected_result: str,
        error_message: str,
        final_url: str,
        console_logs: List[Dict[str, Any]],
        network_failures: List[Dict[str, Any]],
        preliminary_category: str
    ) -> AIBugAnalysisResult:
        """High-precision deterministic rule-based analysis when LLM is unavailable."""
        err_lower = error_message.lower()

        # Check for JS uncaught errors
        js_errors = [l.get("text", "") for l in console_logs if l.get("type") == "error"]
        if js_errors:
            title = f"Uncaught JavaScript exception during {failed_step_action} on {failed_step_target}"
            summary = f"Execution halted due to unhandled JavaScript error: '{js_errors[0][:80]}'."
            description = (
                f"During test '{test_case_name}', step {failed_step_action.upper()} on target '{failed_step_target}' "
                f"triggered an unhandled JavaScript error in page code.\nException: {js_errors[0]}"
            )
            return AIBugAnalysisResult(
                title=title,
                summary=summary,
                description=description,
                category="JAVASCRIPT",
                severity="HIGH",
                priority="HIGH",
                expected_behavior=expected_result or "Page should handle action gracefully without client exceptions.",
                actual_behavior=f"Triggered uncaught exception: {js_errors[0]}",
                root_cause=f"Client-side script exception in application logic: {js_errors[0]}",
                confidence_level="CONFIRMED",
                confidence_score=95,
                severity_explanation="Unhandled client-side exception breaks user interaction on this view.",
                reasoning_summary=f"Direct console error log confirms client exception on {final_url}."
            )

        # Check for API 500 error
        if "500" in err_lower or any("500" in str(n) for n in network_failures):
            title = f"HTTP 500 Server Error encountered on {failed_step_target}"
            summary = "Target server responded with an internal server error status 500 during form or action execution."
            description = (
                f"Test '{test_case_name}' failed at step {failed_step_action.upper()} '{failed_step_target}'. "
                f"The backend API endpoint returned HTTP 500 Internal Server Error."
            )
            return AIBugAnalysisResult(
                title=title,
                summary=summary,
                description=description,
                category="API",
                severity="HIGH",
                priority="HIGH",
                expected_behavior=expected_result or "Server should process request and return HTTP 200/201.",
                actual_behavior="Server returned HTTP 500 Internal Server Error.",
                root_cause="Backend endpoint encountered an unhandled server-side failure during processing.",
                confidence_level="CONFIRMED",
                confidence_score=92,
                severity_explanation="HTTP 500 blocks users from completing server-side transactions.",
                reasoning_summary="Direct network status code 500 captured in HTTP traffic."
            )

        # Functional / Validation Assertion Failure
        title = f"Validation or functional requirement failure on {failed_step_target}"
        summary = f"Expected behavior '{expected_result[:60]}' was not satisfied after {failed_step_action}."
        description = (
            f"Test '{test_case_name}' failed step assertion on '{failed_step_target}'.\n"
            f"Expected: {expected_result}\nActual: {error_message}"
        )
        return AIBugAnalysisResult(
            title=title,
            summary=summary,
            description=description,
            category=preliminary_category or "FUNCTIONAL",
            severity="MEDIUM",
            priority="MEDIUM",
            expected_behavior=expected_result,
            actual_behavior=error_message,
            root_cause="Application state transition or validation response did not match expected business rule.",
            confidence_level="LIKELY",
            confidence_score=78,
            severity_explanation="Core functional assertion failed; user does not reach expected post-condition.",
            reasoning_summary=f"Assertion failed on target '{failed_step_target}' at final URL '{final_url}'."
        )
