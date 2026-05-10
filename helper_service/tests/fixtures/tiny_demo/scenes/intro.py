async def record(page):
    await page.goto("about:blank")
    await page.wait_for_timeout(2000)
