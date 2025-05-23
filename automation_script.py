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

                                # await page.click("button.ng-tns-c56-17.ui-confirmdialog-acceptbutton")

                                print(f"Booking initiated for train {target_train_number}")
                                return
        except Exception as e:
            print(f"Error processing train: {e}")
    
    # raise Exception(f"Train {target_train_number} with class {target_class} on date {formatted_date} not found.")


async def fill_passenger_details(page, passengers):
    """
    Adds passenger slots and fills passenger details on IRCTC booking page.

    Args:
    - page: Playwright page object
    - passengers: List of [Name, Age, Gender] entries
    """

    for idx, (name, age, gender) in enumerate(passengers):
        # Add new passenger slot if idx > 0
        if idx > 0:
            await page.click('div.zeroPadding.pull-left.ng-star-inserted')
            await page.wait_for_timeout(500)  # Small wait after adding


        name_input = page.locator("div.Layer_7.col-sm-3.col-xs-12").nth(idx)
        await name_input.click()
        # await name_input.fill('')  # Clear existing text if any
        await name_input.type(name, delay=150)

        # Fill Age
        age_input = page.locator("div.Layer_7.col-sm-1.col-xs-6").nth(idx)
        await age_input.click()
        # await age_input.fill('')
        await age_input.type(age, delay=150)

        # Fill Gender
        # await page.keyboard.press('Tab')
        gender_dropdown = page.locator("select[formcontrolname='passengerGender']").nth(idx)

        if gender.upper() == 'M':
            await gender_dropdown.select_option('M')
        elif gender.upper() == 'F':
            await gender_dropdown.select_option('F')
        elif gender.upper() == 'T':
            await gender_dropdown.select_option('T')
        else:
            raise ValueError(f"Unknown gender '{gender}' for passenger {name}")
        
        
        # (Country and berth preference are defaulted, not changed)

    radio_button = page.locator("p-radiobutton[id='2']")
    await radio_button.click() 
    await page.wait_for_timeout(500)

    await page.click('button.train_Search.btnDefault')
    await page.wait_for_timeout(500)

    print(f"✅ Successfully filled {len(passengers)} passengers.")




async def automate_booking(session_data):
    """
    Starts IRCTC booking automation, logs in, fills user ID and password,
    captures captcha, and returns captcha image path along with browser and page instances.
    """
    playwright = await async_playwright().start()

    # user_data_dir = "./playwright_user_data"
    # user_data_dir = "C:\\Users\\saish\\AppData\\Local\\Google\\Chrome\\User Data"
    # chrome_executable_path = "C:\\Users\\saish\\Downloads\\chrome-win64\\chrome.exe"

    browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
    page = await browser.new_page()

    # Navigate to IRCTC site
    await page.goto("https://www.irctc.co.in/nget/train-search")
    await page.wait_for_timeout(3000)


    # IF the page has menu button 
    await page.click('div.h_menu_drop_button')
    await page.wait_for_timeout(1000)
    await page.click('button.search_btn')


    # Click on Login button withno menu button
    # await page.click('a.search_btn.loginText')
    await page.wait_for_timeout(1000)

    # Fill login credentials
    # await page.fill("input[formcontrolname='userid']", session_data['credentials']['username'])
    # await page.fill("input[formcontrolname='password']", session_data['credentials']['password'])

    await page.wait_for_selector("input[formcontrolname='userid']")

    # Instead of fill, do human-like typing
    await page.click("input[formcontrolname='userid']")
    await page.keyboard.type(session_data['credentials']['username'], delay=150)

    await page.click("input[formcontrolname='password']")
    await page.keyboard.type(session_data['credentials']['password'], delay=150)

    # Wait for captcha to appear
    await page.wait_for_selector("img.captcha-img")

    # Save captcha image
    captcha_path = f"captcha_{session_data['credentials']['username']}.png"
    await page.locator("img.captcha-img").screenshot(path=captcha_path)

    return captcha_path, browser, page


async def handle_payment(session_data, browser, page):
    await page.click("input[formcontrolname='captcha']")
    await page.keyboard.type(session_data['captcha_2'], delay=150)

    await page.wait_for_timeout(500)
    await page.click("button[type='submit']")
    await page.wait_for_timeout(1000)

    await page.locator("img[src$='./assets/images/multiplepaymenticon.png']").click()
    await page.wait_for_timeout(2000)

    # await page.locator("div.col-pad.col-xs-12.bank-text").fourth().click()
    # await page.wait_for_timeout(500)

    # https://www.irctc.co.in/nget/assets/images/payment/116.png

    # await page.locator("img[src$='./assets/images/payment/116.png']").nth(3).click()
    # await page.wait_for_timeout(1000)

    await page.get_by_role("cell", name="Rail Icon Credit & Debit cards / Wallet / UPI (Powered by PhonePe)").get_by_role("img").click()
    await page.wait_for_timeout(1000)

    # get_by_role("cell", name="Rail Icon Credit & Debit cards / Wallet / UPI (Powered by PhonePe)").get_by_role("img")

    await page.click("button.btn.btn-primary")
    await page.wait_for_timeout(5000)

    qr_button = page.locator("button.showQRButton__1hkk9")
    await qr_button.click()
    await page.wait_for_timeout(1000)

    await page.wait_for_selector("img.qr__3q4Hu")

    # Save captcha image
    qr_path = f"qrCode_{session_data['credentials']['username']}.png"

    await page.locator("img.qr__3q4Hu").screenshot(path = qr_path)
    
    return qr_path, browser, page



async def complete_booking(session_data, browser, page):
    """
    After receiving captcha from user, fills captcha,
    searches train, selects class, fills passengers, and proceeds to booking.
    """
    # Fill captcha
    # await page.fill("input[formcontrolname='captcha']", session_data['captcha'])
    # await page.click("button.search_btn.train_Search.train_Search_custom_hover")
    # await page.wait_for_timeout(5000)

    await page.click("input[formcontrolname='captcha']")
    await page.keyboard.type(session_data['captcha'], delay=150)

    await page.wait_for_timeout(500)
    await page.click("button.search_btn.train_Search.train_Search_custom_hover")

    # Search for Trains
    # await page.fill("input.ng-tns-c57-8", session_data['from'])
    # await page.wait_for_timeout(500)
    # await page.keyboard.press("Enter")
    # await page.wait_for_timeout(1000)
    # await page.fill("input.ng-tns-c57-9", session_data['to'])
    # await page.wait_for_timeout(1000)
    # await page.keyboard.press("Enter")
    # await page.wait_for_timeout(1000)
    # await page.fill("input.ng-tns-c58-10", session_data['date'])
    # await page.wait_for_timeout(2000)
    # await page.keyboard.press("Enter")
    # await page.wait_for_timeout(1000)    

    await page.click("input.ng-tns-c57-8")
    await page.keyboard.type(session_data['from'], delay=150)
    await page.keyboard.press("Enter")
    await page.wait_for_timeout(1000)
    await page.click("input.ng-tns-c57-9")
    await page.keyboard.type(session_data['to'], delay=150)
    await page.keyboard.press("Enter")
    await page.wait_for_timeout(1000)
    await page.click("input.ng-tns-c58-10")
    await page.keyboard.press('Control+A')  # or 'Meta+A' on Mac
    await page.keyboard.press('Backspace')
    await page.keyboard.type(session_data['date'], delay=150)
    await page.keyboard.press("Enter")
    await page.wait_for_timeout(1000)

    # await page.click("button.search_btn.train_Search[type='submit']")
    # await page.wait_for_timeout(2000)

    await select_train_and_class_and_book(page, session_data)

    await fill_passenger_details(page, session_data['passengers'])

    # # Select desired Train
    # await page.get_by_text(session_data['train_type']).click()
    # await page.get_by_text(session_data['class']).click()

    # # Book Ticket
    # await page.click("button[label='Book Now']")
    # await page.wait_for_timeout(3000)

    # Wait for captcha to appear
    await page.wait_for_selector("img.captcha-img")

    # Save captcha image
    captcha_path = f"captcha_2_{session_data['credentials']['username']}.png"
    await page.locator("img.captcha-img").screenshot(path=captcha_path)

    return captcha_path, browser, page


