import os
import hashlib
from typing import List, Tuple, Optional
from urllib.parse import urlparse, urljoin
from playwright.async_api import Page
from backend.app.browser.events import DiscoveredElement, DiscoveredPage
from backend.app.core.config import settings
from backend.app.core.logging import logger

DOM_EXTRACTION_SCRIPT = """
() => {
    function generateSelector(el) {
        if (el.id) {
            return '#' + CSS.escape(el.id);
        }
        if (el.getAttribute('data-testid')) {
            return `[data-testid="${CSS.escape(el.getAttribute('data-testid'))}"]`;
        }
        if (el.name && ['INPUT', 'SELECT', 'TEXTAREA', 'BUTTON'].includes(el.tagName)) {
            return `${el.tagName.toLowerCase()}[name="${CSS.escape(el.name)}"]`;
        }
        if (el.tagName === 'A' && el.getAttribute('href')) {
            const href = el.getAttribute('href');
            if (href.length < 50 && !href.includes('"')) {
                return `a[href="${href}"]`;
            }
        }
        // Path fallback
        let path = [];
        let curr = el;
        while (curr && curr.nodeType === Node.ELEMENT_NODE && curr.tagName !== 'BODY' && curr.tagName !== 'HTML') {
            let selector = curr.tagName.toLowerCase();
            if (curr.className && typeof curr.className === 'string') {
                const classes = curr.className.trim().split(/\\s+/).filter(c => c && !c.includes(':'));
                if (classes.length > 0) {
                    selector += '.' + CSS.escape(classes[0]);
                }
            }
            let siblingIndex = 1;
            let sibling = curr.previousElementSibling;
            while (sibling) {
                if (sibling.tagName === curr.tagName) siblingIndex++;
                sibling = sibling.previousElementSibling;
            }
            selector += `:nth-of-type(${siblingIndex})`;
            path.unshift(selector);
            curr = curr.parentElement;
        }
        return path.join(' > ');
    }

    const elements = [];
    const internalLinks = [];

    // Extract links
    document.querySelectorAll('a[href]').forEach(a => {
        const href = a.getAttribute('href');
        if (href && !href.startsWith('#') && !href.startsWith('javascript:') && !href.startsWith('mailto:')) {
            internalLinks.push(a.href);
        }
        elements.push({
            element_type: 'link',
            tag_name: 'a',
            selector: generateSelector(a),
            text: (a.innerText || a.textContent || '').trim().slice(0, 150),
            name: a.getAttribute('name') || null,
            placeholder: null,
            role: a.getAttribute('role') || 'link',
            is_interactive: true
        });
    });

    // Extract buttons
    document.querySelectorAll('button, input[type="button"], input[type="submit"], [role="button"]').forEach(btn => {
        elements.push({
            element_type: 'button',
            tag_name: btn.tagName.toLowerCase(),
            selector: generateSelector(btn),
            text: (btn.innerText || btn.value || btn.textContent || '').trim().slice(0, 150),
            name: btn.getAttribute('name') || null,
            placeholder: null,
            role: btn.getAttribute('role') || 'button',
            is_interactive: !btn.disabled
        });
    });

    // Extract inputs
    document.querySelectorAll('input:not([type="button"]):not([type="submit"]):not([type="hidden"]), textarea').forEach(input => {
        elements.push({
            element_type: input.type || 'input',
            tag_name: input.tagName.toLowerCase(),
            selector: generateSelector(input),
            text: null,
            name: input.getAttribute('name') || null,
            placeholder: input.getAttribute('placeholder') || null,
            role: input.getAttribute('role') || 'textbox',
            is_interactive: !input.disabled
        });
    });

    // Extract selects
    document.querySelectorAll('select').forEach(sel => {
        elements.push({
            element_type: 'select',
            tag_name: 'select',
            selector: generateSelector(sel),
            text: null,
            name: sel.getAttribute('name') || null,
            placeholder: null,
            role: sel.getAttribute('role') || 'combobox',
            is_interactive: !sel.disabled
        });
    });

    // Extract forms
    document.querySelectorAll('form').forEach(f => {
        elements.push({
            element_type: 'form',
            tag_name: 'form',
            selector: generateSelector(f),
            text: null,
            name: f.getAttribute('name') || null,
            placeholder: null,
            role: 'form',
            is_interactive: true
        });
    });

    return {
        elements: elements,
        internalLinks: internalLinks
    };
}
"""

class PageExplorer:
    """Inspects a Playwright Page, extracts DOM elements, collects internal links, and takes screenshots."""

    def __init__(self, run_id: int):
        self.run_id = run_id
        self.screenshots_dir = os.path.join(settings.ARTIFACTS_DIR, "screenshots", f"run_{run_id}")
        os.makedirs(self.screenshots_dir, exist_ok=True)

    def is_safe_action(self, text: str, element_type: str) -> bool:
        """Determines if an interactive control is safe for automated Phase 1 exploration."""
        destructive_keywords = [
            "delete", "remove", "destroy", "drop", "terminate",
            "logout", "signout", "sign out", "log out",
            "pay", "payment", "purchase", "buy", "checkout",
            "change password", "reset password", "password change",
            "modify account", "delete account", "close account", "cancel account"
        ]
        normalized = (text or "").lower()
        for kw in destructive_keywords:
            if kw in normalized:
                return False
        return True

    def normalize_url(self, base_url: str, target_url: str) -> Optional[str]:
        """Normalizes and ensures target URL belongs to the same domain as base_url."""
        try:
            full_url = urljoin(base_url, target_url)
            parsed_base = urlparse(base_url)
            parsed_target = urlparse(full_url)

            # Restrict strictly to same origin (hostname + port)
            if parsed_base.netloc.lower() != parsed_target.netloc.lower():
                return None

            # Ignore non-http/https schemes
            if parsed_target.scheme not in ("http", "https"):
                return None

            # Strip fragments / hashes
            normalized = f"{parsed_target.scheme}://{parsed_target.netloc}{parsed_target.path}"
            if parsed_target.query:
                normalized += f"?{parsed_target.query}"

            return normalized.rstrip("/")
        except Exception:
            return None

    async def inspect_page(self, page: Page, base_url: str) -> DiscoveredPage:
        """Analyzes the current page state, extracts elements, takes screenshot."""
        current_url = page.url
        title = await page.title()

        # Execute extraction script in browser context
        try:
            raw_data = await page.evaluate(DOM_EXTRACTION_SCRIPT)
        except Exception as e:
            logger.error(f"Failed to evaluate DOM extraction script on {current_url}: {e}")
            raw_data = {"elements": [], "internalLinks": []}

        # Filter internal links
        internal_links = []
        for raw_link in raw_data.get("internalLinks", []):
            norm = self.normalize_url(base_url, raw_link)
            if norm and norm not in internal_links and norm != current_url.rstrip("/"):
                internal_links.append(norm)

        # Parse discovered elements
        discovered_elements = []
        for el in raw_data.get("elements", []):
            discovered_elements.append(
                DiscoveredElement(
                    element_type=el.get("element_type", "unknown"),
                    tag_name=el.get("tag_name", "div"),
                    selector=el.get("selector", ""),
                    text=el.get("text"),
                    name=el.get("name"),
                    placeholder=el.get("placeholder"),
                    role=el.get("role"),
                    is_interactive=el.get("is_interactive", True)
                )
            )

        # Take page screenshot
        url_hash = hashlib.md5(current_url.encode("utf-8")).hexdigest()[:10]
        screenshot_filename = f"page_{url_hash}.png"
        screenshot_path = os.path.join(self.screenshots_dir, screenshot_filename)
        
        try:
            await page.screenshot(path=screenshot_path, full_page=True)
            logger.info(f"Captured screenshot for {current_url} -> {screenshot_path}")
        except Exception as e:
            logger.warning(f"Could not take full page screenshot of {current_url}: {e}")
            screenshot_path = None

        return DiscoveredPage(
            url=current_url,
            title=title,
            status_code=200,
            screenshot_path=screenshot_path,
            elements=discovered_elements,
            internal_links=internal_links
        )
