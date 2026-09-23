import re
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class FailureClassificationResult:
    classification: str       # APPLICATION_BUG, TEST_BUG, ENVIRONMENT_FAILURE, INFRASTRUCTURE_FAILURE, TIMEOUT, UNKNOWN
    category: str             # JAVASCRIPT, API, FUNCTIONAL, VALIDATION, UI, NAVIGATION, etc.
    is_application_defect: bool
    reason: str
    failure_signature: str

class FailureClassifier:
    """
    Distinguishes genuine application defects from test authoring, environment,
    and infrastructure failures using raw Playwright execution evidence.
    """

    @classmethod
    def classify(
        cls,
        application_id: int,
        error_message: str,
        failed_step_action: Optional[str] = None,
        failed_step_target: Optional[str] = None,
        console_logs: Optional[List[Dict[str, Any]]] = None,
        network_failures: Optional[List[Dict[str, Any]]] = None,
        final_url: Optional[str] = None
    ) -> FailureClassificationResult:
        err_lower = (error_message or "").lower()
        step_action = (failed_step_action or "").lower()
        step_target = (failed_step_target or "").lower()
        logs = console_logs or []
        net_fails = network_failures or []

        # 1. INFRASTRUCTURE FAILURE
        infra_keywords = [
            "browser closed", "target page, context or browser has been closed",
            "failed to launch", "executable doesn't exist", "process exited with code",
            "crashed"
        ]
        if any(k in err_lower for k in infra_keywords):
            sig = cls._make_signature(application_id, final_url, "infra", err_lower)
            return FailureClassificationResult(
                classification="INFRASTRUCTURE_FAILURE",
                category="UNKNOWN",
                is_application_defect=False,
                reason="Browser automation crash or Playwright process terminated unexpectedly.",
                failure_signature=sig
            )

        # 2. ENVIRONMENT FAILURE
        env_keywords = [
            "net::err_connection_refused", "connection refused", "err_name_not_resolved",
            "502 bad gateway", "503 service unavailable", "connectionreseterror",
            "host is unreachable"
        ]
        if any(k in err_lower for k in env_keywords):
            sig = cls._make_signature(application_id, final_url, "env", err_lower)
            return FailureClassificationResult(
                classification="ENVIRONMENT_FAILURE",
                category="NETWORK",
                is_application_defect=False,
                reason="Target environment or host is unreachable / connection refused.",
                failure_signature=sig
            )

        # 3. APPLICATION BUG - JAVASCRIPT ERROR IN CONSOLE OR ERROR MESSAGE
        js_error_entries = [
            l for l in logs
            if l.get("type") == "error" and any(k in l.get("text", "").lower() for k in ["uncaught", "typeerror", "referenceerror", "syntaxerror", "exception"])
        ]
        has_js_in_err = any(k in err_lower for k in ["uncaught", "typeerror", "referenceerror", "syntaxerror", "unhandledrejection"])
        if js_error_entries or has_js_in_err:
            err_text = js_error_entries[0].get("text", "") if js_error_entries else error_message
            sig = cls._make_signature(application_id, final_url, "js", err_text)
            return FailureClassificationResult(
                classification="APPLICATION_BUG",
                category="JAVASCRIPT",
                is_application_defect=True,
                reason=f"Uncaught JavaScript exception in target application: {err_text[:120]}",
                failure_signature=sig
            )

        # 4. APPLICATION BUG - API / HTTP 500
        http_500_net = [
            n for n in net_fails
            if "500" in str(n.get("failure", "")) or "500" in str(n.get("url", ""))
        ]
        if http_500_net or "500 internal server error" in err_lower or "500: internal server error" in err_lower or "http 500" in err_lower or "status code 500" in err_lower:
            sig = cls._make_signature(application_id, final_url, "api500", step_target)
            return FailureClassificationResult(
                classification="APPLICATION_BUG",
                category="API",
                is_application_defect=True,
                reason="Server responded with HTTP 500 Internal Server Error during test workflow execution.",
                failure_signature=sig
            )

        # 5. TEST BUG - LOCATOR FAILURE
        # If waiting for locator timed out, but there were no server 500s or JS errors
        if "waiting for locator" in err_lower or "element has no valid locator" in err_lower:
            sig = cls._make_signature(application_id, final_url, "bad_locator", step_target)
            return FailureClassificationResult(
                classification="TEST_BUG",
                category="UI",
                is_application_defect=False,
                reason=f"Playwright locator '{step_target}' could not be matched in DOM. Likely selector mismatch or missing DOM element.",
                failure_signature=sig
            )

        # 6. APPLICATION BUG - ASSERTION FAILURE
        if "assertionerror" in err_lower or "expected" in err_lower or step_action == "assert":
            category = "VALIDATION" if "validation" in err_lower or "error" in err_lower else "FUNCTIONAL"
            sig = cls._make_signature(application_id, final_url, "assertion", err_lower)
            return FailureClassificationResult(
                classification="APPLICATION_BUG",
                category=category,
                is_application_defect=True,
                reason="Application state failed verification: expected behavior did not materialize.",
                failure_signature=sig
            )

        # 7. TIMEOUT
        if "timeout" in err_lower:
            sig = cls._make_signature(application_id, final_url, "timeout", step_target)
            return FailureClassificationResult(
                classification="TIMEOUT",
                category="PERFORMANCE",
                is_application_defect=False,
                reason="Operation exceeded timeout limit without receiving expected page state.",
                failure_signature=sig
            )

        # 8. FALLBACK / UNKNOWN
        sig = cls._make_signature(application_id, final_url, "unknown", err_lower)
        return FailureClassificationResult(
            classification="UNKNOWN",
            category="UNKNOWN",
            is_application_defect=False,
            reason="Failure signature did not match known application or test defect patterns.",
            failure_signature=sig
        )

    @classmethod
    def _make_signature(cls, app_id: int, url: Optional[str], kind: str, detail: str) -> str:
        clean_url = (url or "").split("?")[0].rstrip("/")
        clean_detail = re.sub(r'\s+', ' ', detail[:100].strip())
        raw = f"{app_id}:{clean_url}:{kind}:{clean_detail}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
