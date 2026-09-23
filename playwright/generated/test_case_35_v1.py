"""
Generated Playwright Test Case #35: TC-007 Boundary: Product Price Negative Value Validation
Category: BOUNDARY | Priority: CRITICAL
Target Base URL: http://127.0.0.1:3000
"""
import asyncio
from playwright.async_api import Page, expect

async def test_case_35(page: Page, base_url: str = "http://127.0.0.1:3000"):
    """Executes the test steps for TC #35."""
    page.set_default_timeout(10000)

    # Step 1: NAVIGATE on http://127.0.0.1:3000/products/create
    # Expected: 
    await page.goto("http://127.0.0.1:3000/products/create", wait_until="domcontentloaded")
    await page.wait_for_load_state("networkidle")

    # Step 2: FILL on input[name="title"]
    # Expected: 
    await page.locator("input[name=\"title\"]").fill("Defect Boundary Widget")

    # Step 3: FILL on input[name="price"]
    # Expected: 
    await page.locator("input[name=\"price\"]").fill("-5.00")

    # Step 4: CLICK on #btn-save-product
    # Expected: 
    await page.locator("#btn-save-product").click()
    await page.wait_for_timeout(500)  # settle

# Standalone execution helper
async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await test_case_35(page)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
