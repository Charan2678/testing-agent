from typing import Optional, Dict, Any, Tuple
from backend.app.database.models.models import Element

class LocatorResolutionResult:
    def __init__(
        self,
        strategy: str,
        code_snippet: str,
        is_valid: bool = True,
        error: Optional[str] = None
    ):
        self.strategy = strategy  # role, label, placeholder, text, test_id, css
        self.code_snippet = code_snippet
        self.is_valid = is_valid
        self.error = error

class LocatorResolver:
    """
    Resolves targets to resilient Playwright locators using the preferred hierarchy:
    1. getByRole
    2. getByLabel
    3. getByPlaceholder
    4. getByText (for buttons/links/headings)
    5. getByTestId (data-testid, data-test)
    6. CSS Selector fallback
    7. XPath (last resort)
    
    If the target cannot be safely identified, marks as invalid.
    Never invents locators.
    """

    @classmethod
    def resolve_from_element(cls, elem: Element) -> LocatorResolutionResult:
        """Resolves locator code for a known DB Element."""
        # 1. Role with accessible name / text
        if elem.role and elem.text and elem.text.strip():
            clean_text = elem.text.strip().replace('"', '\\"')
            return LocatorResolutionResult(
                strategy="role",
                code_snippet=f'page.get_by_role("{elem.role}", name="{clean_text}")'
            )

        # 2. Placeholder for inputs
        if elem.placeholder and elem.placeholder.strip():
            clean_ph = elem.placeholder.strip().replace('"', '\\"')
            return LocatorResolutionResult(
                strategy="placeholder",
                code_snippet=f'page.get_by_placeholder("{clean_ph}")'
            )

        # 3. Input name attribute
        if elem.name and elem.name.strip():
            clean_name = elem.name.strip().replace('"', '\\"')
            if elem.tag_name == "input":
                return LocatorResolutionResult(
                    strategy="css",
                    code_snippet=f'page.locator(\'input[name="{clean_name}"]\')'
                )
            elif elem.tag_name in ("select", "textarea"):
                return LocatorResolutionResult(
                    strategy="css",
                    code_snippet=f'page.locator(\'{elem.tag_name}[name="{clean_name}"]\')'
                )

        # 4. Text for buttons/links
        if elem.tag_name in ("button", "a") and elem.text and elem.text.strip():
            clean_text = elem.text.strip().replace('"', '\\"')
            if elem.tag_name == "button":
                return LocatorResolutionResult(
                    strategy="role",
                    code_snippet=f'page.get_by_role("button", name="{clean_text}")'
                )
            return LocatorResolutionResult(
                strategy="text",
                code_snippet=f'page.get_by_text("{clean_text}")'
            )

        # 5. Stable ID or CSS selector from DOM extraction
        if elem.selector and elem.selector.strip():
            clean_sel = elem.selector.strip()
            # If selector has data-testid
            if "data-testid=" in clean_sel:
                import re
                match = re.search(r'data-testid=["\']([^"\']+)["\']', clean_sel)
                if match:
                    return LocatorResolutionResult(
                        strategy="test_id",
                        code_snippet=f'page.get_by_test_id("{match.group(1)}")'
                    )
            return LocatorResolutionResult(
                strategy="css",
                code_snippet=f'page.locator("{clean_sel}")'
            )

        return LocatorResolutionResult(
            strategy="unknown",
            code_snippet="",
            is_valid=False,
            error=f"Element #{elem.id} has no valid locator parameters."
        )

    @classmethod
    def resolve_target_string(cls, target: str, action: str) -> LocatorResolutionResult:
        """
        Resolves an arbitrary target string from a test step.
        Supports CSS selectors, URLs for navigation, and textual targets.
        """
        if not target or not target.strip():
            return LocatorResolutionResult(
                strategy="invalid",
                code_snippet="",
                is_valid=False,
                error="Target string cannot be empty."
            )

        target = target.strip()

        # If action is navigate or target is an HTTP URL
        if action.lower() == "navigate" or target.startswith("http://") or target.startswith("https://") or target.startswith("/"):
            return LocatorResolutionResult(
                strategy="url",
                code_snippet=target
            )

        # CSS selector with ID (#) or class (.) or attribute ([])
        if target.startswith("#") or target.startswith(".") or "[" in target or ">" in target:
            clean_sel = target.replace('"', '\\"')
            return LocatorResolutionResult(
                strategy="css",
                code_snippet=f'page.locator("{clean_sel}")'
            )

        # XPath
        if target.startswith("//") or target.startswith(".//"):
            clean_xpath = target.replace('"', '\\"')
            return LocatorResolutionResult(
                strategy="xpath",
                code_snippet=f'page.locator("xpath={clean_xpath}")'
            )

        # By text or role fallback
        clean_target = target.replace('"', '\\"')
        return LocatorResolutionResult(
            strategy="text",
            code_snippet=f'page.get_by_text("{clean_target}")'
        )
