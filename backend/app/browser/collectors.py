from typing import List, Dict, Any, Optional
from datetime import datetime
from playwright.async_api import Page, ConsoleMessage, Request, Response
from backend.app.browser.events import ConsoleMessageEvent, NetworkRequestEvent
from backend.app.core.logging import logger

class PageEventCollector:
    """Attaches runtime listeners to a Playwright Page to capture real network and console activity."""

    def __init__(self):
        self.console_events: List[ConsoleMessageEvent] = []
        self.network_events: List[NetworkRequestEvent] = []
        self._request_start_times: Dict[str, datetime] = {}

    def attach_to_page(self, page: Page):
        page.on("console", self._handle_console)
        page.on("pageerror", self._handle_page_error)
        page.on("request", self._handle_request)
        page.on("response", self._handle_response)
        page.on("requestfailed", self._handle_request_failed)

    def _handle_console(self, msg: ConsoleMessage):
        try:
            event = ConsoleMessageEvent(
                timestamp=datetime.utcnow(),
                type=msg.type,
                text=msg.text,
                location=msg.location
            )
            self.console_events.append(event)
        except Exception as e:
            logger.debug(f"Error handling console event: {e}")

    def _handle_page_error(self, error: Exception):
        try:
            event = ConsoleMessageEvent(
                timestamp=datetime.utcnow(),
                type="error",
                text=str(error)
            )
            self.console_events.append(event)
        except Exception as e:
            logger.debug(f"Error handling page error: {e}")

    def _handle_request(self, req: Request):
        try:
            self._request_start_times[req.url] = datetime.utcnow()
        except Exception as e:
            logger.debug(f"Error handling request event: {e}")

    def _handle_response(self, res: Response):
        try:
            start_time = self._request_start_times.pop(res.url, None)
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000 if start_time else None

            event = NetworkRequestEvent(
                timestamp=datetime.utcnow(),
                url=res.url,
                method=res.request.method,
                resource_type=res.request.resource_type,
                status=res.status,
                status_text=res.status_text,
                failed=(res.status >= 400),
                duration_ms=duration_ms
            )
            self.network_events.append(event)
        except Exception as e:
            logger.debug(f"Error handling response event: {e}")

    def _handle_request_failed(self, req: Request):
        try:
            start_time = self._request_start_times.pop(req.url, None)
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000 if start_time else None

            failure = req.failure
            error_text = failure if isinstance(failure, str) else str(failure)

            event = NetworkRequestEvent(
                timestamp=datetime.utcnow(),
                url=req.url,
                method=req.method,
                resource_type=req.resource_type,
                failed=True,
                failure_error=error_text,
                duration_ms=duration_ms
            )
            self.network_events.append(event)
        except Exception as e:
            logger.debug(f"Error handling failed request event: {e}")

    def get_console_errors(self) -> List[ConsoleMessageEvent]:
        return [e for e in self.console_events if e.type in ("error", "assert")]

    def get_failed_requests(self) -> List[NetworkRequestEvent]:
        return [e for e in self.network_events if e.failed]

    def clear(self):
        self.console_events.clear()
        self.network_events.clear()
        self._request_start_times.clear()
