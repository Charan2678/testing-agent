from backend.app.browser.manager import BrowserManager
from backend.app.browser.collectors import PageEventCollector
from backend.app.browser.explorer import PageExplorer
from backend.app.browser.events import (
    ConsoleMessageEvent,
    NetworkRequestEvent,
    DiscoveredElement,
    DiscoveredPage
)

__all__ = [
    "BrowserManager",
    "PageEventCollector",
    "PageExplorer",
    "ConsoleMessageEvent",
    "NetworkRequestEvent",
    "DiscoveredElement",
    "DiscoveredPage"
]
