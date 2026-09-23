import pytest
from backend.app.browser.explorer import PageExplorer
from backend.app.browser.collectors import PageEventCollector
from backend.app.browser.events import ConsoleMessageEvent, NetworkRequestEvent

def test_url_normalization():
    explorer = PageExplorer(run_id=999)
    base_url = "http://localhost:3000"

    # Same domain valid
    norm1 = explorer.normalize_url(base_url, "/products")
    assert norm1 == "http://localhost:3000/products"

    # With hash should be stripped
    norm2 = explorer.normalize_url(base_url, "/dashboard#overview")
    assert norm2 == "http://localhost:3000/dashboard"

    # Query param preserved
    norm3 = explorer.normalize_url(base_url, "/search?q=test")
    assert norm3 == "http://localhost:3000/search?q=test"

    # External domain rejected
    norm4 = explorer.normalize_url(base_url, "https://google.com/search")
    assert norm4 is None

def test_safety_action_policy():
    explorer = PageExplorer(run_id=999)

    # Safe interactions
    assert explorer.is_safe_action("View Products", "button") is True
    assert explorer.is_safe_action("Next Page", "link") is True
    assert explorer.is_safe_action("Submit Filter", "button") is True

    # Destructive interactions
    assert explorer.is_safe_action("Delete Customer", "button") is False
    assert explorer.is_safe_action("Remove Item", "button") is False
    assert explorer.is_safe_action("Pay Now", "button") is False
    assert explorer.is_safe_action("Logout", "button") is False

def test_collector_event_filtering():
    collector = PageEventCollector()

    # Add dummy console events
    collector.console_events.append(ConsoleMessageEvent(type="log", text="info msg"))
    collector.console_events.append(ConsoleMessageEvent(type="error", text="Uncaught TypeError"))

    # Add network events
    collector.network_events.append(NetworkRequestEvent(url="http://localhost:3000/api/ok", method="GET", status=200, failed=False))
    collector.network_events.append(NetworkRequestEvent(url="http://localhost:3000/api/fail", method="POST", status=500, failed=True))

    errors = collector.get_console_errors()
    assert len(errors) == 1
    assert errors[0].text == "Uncaught TypeError"

    failed_reqs = collector.get_failed_requests()
    assert len(failed_reqs) == 1
    assert failed_reqs[0].status == 500
