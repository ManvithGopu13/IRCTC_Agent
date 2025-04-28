# automation_script.py
from playwright.async_api import async_playwright
import asyncio
import os
from datetime import datetime

async def select_train_and_class_and_book(page, session_data):
    """
    After search, finds the correct train number, selects class, selects date, and clicks Book Now.
    """
    await page.wait_for_timeout(3000)  # Let search results load

    # Find all train containers (Each train block on the page)
    trains = await page.query_selector_all("div.form-group.no-pad.col-xs-12")

    
    target_train_number = session_data['train_type'].strip()
    target_class = session_data['class'].strip()
    print(f"{trains}, {target_train_number}, {target_class}")

    # Convert session_data['date'] ("29/04/2025") --> "Tue, 29 Apr"
    date_obj = datetime.strptime(session_data['date'], "%d/%m/%Y")
    formatted_date = date_obj.strftime("%a, %d %b")  # "Tue, 29 Apr"

    for train in trains:
        try:
            # Find the train number in this block
            train_number_element = await train.query_selector("div.col-sm-5.col-xs-11.train-heading")
            train_number_text = await train_number_element.inner_text()
            
            if target_train_number in train_number_text:
                print(f"Found train {target_train_number}")

                # Select Class inside that train block
                class_buttons = await train.query_selector_all("div.pre-avl")
                
                for class_button in class_buttons:
                    class_text = await class_button.inner_text()
                    if target_class.upper() in class_text.upper():
                        print(f"Found {target_class}")
                        await class_button.click()
                        await page.wait_for_timeout(1500)

                        # Select Date inside availability
                        date_buttons = await train.query_selector_all("div.pre-avl")
                        
                        for date_button in date_buttons:
                            date_text = await date_button.inner_text()
                            if formatted_date.lower() in date_text.lower():
                                await date_button.click()
                                await page.wait_for_timeout(1500)

                                # Click Book Now
                                book_now_button = await train.query_selector("button.btnDefault.train_Search.ng-star-inserted")
                                await book_now_button.click()
                                await page.wait_for_timeout(1000)

                                await page.click("button.ng-tns-c56-17.ui-confirmdialog-acceptbutton")

                                print(f"Booking initiated for train {target_train_number}")
                                return
        except Exception as e:
            print(f"Error processing train: {e}")
    
    # raise Exception(f"Train {target_train_number} with class {target_class} on date {formatted_date} not found.")


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
    await page.wait_for_timeout(2000)
    await page.keyboard.press("Enter")
    await page.wait_for_timeout(1000)

    # await page.click("button.search_btn.train_Search[type='submit']")
    # await page.wait_for_timeout(2000)

    await select_train_and_class_and_book(page, session_data)

    # # Select desired Train
    # await page.get_by_text(session_data['train_type']).click()
    # await page.get_by_text(session_data['class']).click()

    # # Book Ticket
    # await page.click("button[label='Book Now']")
    # await page.wait_for_timeout(3000)

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
