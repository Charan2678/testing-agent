import os
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright
from backend.app.core.config import settings
from backend.app.core.logging import logger

class BrowserManager:
    """Manages the lifecycle of Playwright Chromium instances and browser contexts."""

    def __init__(self, headless: Optional[bool] = None):
        self.headless = headless if headless is not None else settings.PLAYWRIGHT_HEADLESS
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None

    async def start(self) -> Browser:
        if self._browser is not None:
            return self._browser

        logger.info(f"Starting Playwright browser (headless={self.headless})...")
        self._playwright = await async_playwright().start()

        # Try launching installed Chrome first, fallback to standard chromium or msedge
        try:
            self._browser = await self._playwright.chromium.launch(
                channel="chrome",
                headless=self.headless,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            logger.info(f"Successfully launched real Google Chrome (v{self._browser.version})")
        except Exception as chrome_err:
            logger.warning(f"Failed to launch with channel='chrome': {chrome_err}. Trying msedge...")
            try:
                self._browser = await self._playwright.chromium.launch(
                    channel="msedge",
                    headless=self.headless
                )
                logger.info(f"Successfully launched Microsoft Edge (v{self._browser.version})")
            except Exception as edge_err:
                logger.warning(f"Failed to launch with channel='msedge': {edge_err}. Trying default chromium...")
                self._browser = await self._playwright.chromium.launch(
                    headless=self.headless
                )
                logger.info(f"Successfully launched Chromium (v{self._browser.version})")

        return self._browser

    async def create_context(self) -> BrowserContext:
        if not self._browser:
            await self.start()
        
        context = await self._browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="AutonomousQA-Explorer/1.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        return context

    async def close(self):
        if self._browser:
            logger.info("Closing Playwright browser...")
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
