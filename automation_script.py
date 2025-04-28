# automation_script.py
from playwright.async_api import async_playwright
import asyncio
import os


async def automate_booking(session_data):
    """
    Starts IRCTC booking automation, logs in, fills user ID and password,
    captures captcha, and returns captcha image path along with browser and page instances.
    """
    playwright = await async_playwright().start()

    user_data_dir = "./playwright_user_data"

    browser = await playwright.chromium.launch_persistent_context(
        user_data_dir,
        headless=False,  # show browser
        slow_mo=50,      # slow actions to mimic human
        args=[
            "--start-maximized",
            "--disable-blink-features=AutomationControlled",
        ],
        viewport={"width": 1920, "height": 1080}
    )
    page = await browser.new_page()

    # Navigate to IRCTC site
    await page.goto("https://www.irctc.co.in/nget/train-search")
    await page.wait_for_timeout(3000)

    # Click on Login button
    await page.click('a.search_btn.loginText')
    await page.wait_for_timeout(1000)

    # Fill login credentials
    await page.fill("input[formcontrolname='userid']", session_data['credentials']['username'])
    await page.fill("input[formcontrolname='password']", session_data['credentials']['password'])

    # Wait for captcha to appear
    await page.wait_for_selector("img.captcha-img")

    # Save captcha image
    captcha_path = f"captcha_{session_data['credentials']['username']}.png"
    await page.locator("img.captcha-img").screenshot(path=captcha_path)

    return captcha_path, browser, page


async def complete_booking(session_data, browser, page):
    """
    After receiving captcha from user, fills captcha,
    searches train, selects class, fills passengers, and proceeds to booking.
    """
    # Fill captcha
    await page.fill("input[formcontrolname='captcha']", session_data['captcha'])
    await page.click("button.search_btn.train_Search.train_Search_custom_hover")
    await page.wait_for_timeout(5000)

    # Search for Trains
    await page.fill("input.ng-tns-c57-8", session_data['from'])
    await page.wait_for_timeout(500)
    await page.keyboard.press("Enter")
    await page.wait_for_timeout(1000)
    await page.fill("input.ng-tns-c57-9", session_data['to'])
    await page.wait_for_timeout(500)
    await page.keyboard.press("Enter")
    await page.wait_for_timeout(1000)
    await page.fill("input.ng-tns-c58-10", session_data['date'])
    await page.wait_for_timeout(500)
    # await page.keyboard.press("Enter")
    await page.wait_for_timeout(1000)

    await page.click("button.search_btn.train_Search")
    await page.wait_for_timeout(5000)

    # Select desired Train
    await page.get_by_text(session_data['train_type']).click()
    await page.get_by_text(session_data['class']).click()

    # Book Ticket
    await page.click("button[label='Book Now']")
    await page.wait_for_timeout(3000)

    # Fill Passenger Details
    for idx, (name, age, gender) in enumerate(session_data['passengers']):
        await page.fill(f"input[formcontrolname='passengerName{idx}']", name.strip())
        await page.fill(f"input[formcontrolname='passengerAge{idx}']", age.strip())
        await page.select_option(f"select[formcontrolname='passengerGender{idx}']", gender.strip().upper())

    # Continue to booking
    await page.click("button[label='Continue Booking']")
    await page.wait_for_timeout(5000)

    # IMPORTANT: Payment must be done manually by user.

    # For demo: we assume booking is successful
    # Save dummy ticket PDF
    ticket_pdf_path = f"ticket_{session_data['credentials']['username']}.pdf"

    with open(ticket_pdf_path, "wb") as f:
        f.write(b"%PDF-1.4\n% Dummy Ticket PDF\n")  # simple placeholder content

    return ticket_pdf_path
