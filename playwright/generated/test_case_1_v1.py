"""
Generated Playwright Test Case #1: TC-001 Smoke: Valid User Login
Category: SMOKE | Priority: CRITICAL
Target Base URL: http://127.0.0.1:3000
Preconditions:
  - Valid user credentials exist in database
"""
import asyncio
from playwright.async_api import Page, expect

async def test_case_1(page: Page, base_url: str = "http://127.0.0.1:3000"):
    """Executes the test steps for TC #1."""
    page.set_default_timeout(10000)

    # Step 1: NAVIGATE on http://127.0.0.1:3000/products
    # Expected: Page loaded with status 200
    await page.goto("http://127.0.0.1:3000/products", wait_until="domcontentloaded")
    await page.wait_for_load_state("networkidle")

    # Step 2: FILL on #input-username
    # Expected: Username is populated
    await page.get_by_placeholder("Enter username").fill("admin@example.com")

    # Step 3: FILL on #input-password
    # Expected: Password is obfuscated
    await page.get_by_placeholder("Enter password").fill("validPassword123")

    # Step 4: CLICK on #btn-login-submit
    # Expected: User session established and redirected to dashboard
    await page.get_by_role("button", name="Sign In").click()
    await page.wait_for_timeout(500)  # settle

# Standalone execution helper
async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await test_case_1(page)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
