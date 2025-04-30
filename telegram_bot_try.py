# booking_bot.py
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes
import os

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# States for ConversationHandler
FROM, TO, DATE, CLASS, TRAIN_TYPE, NUM_PASSENGERS, PASSENGER_DETAILS, CREDENTIALS, CAPTCHA, CAPTCHA_2 = range(10)

# Temporary storage for user session
user_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to the IRCTC Ticket Bot! Let's start your booking.\nFrom which station are you traveling?")
    return FROM

async def from_station(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_sessions[update.effective_user.id] = {'from': update.message.text}
    await update.message.reply_text("To which station are you going?")
    return TO

async def to_station(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_sessions[update.effective_user.id]['to'] = update.message.text
    await update.message.reply_text("Enter date of journey (dd/mm/yyyy):")
    return DATE

async def date_of_journey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_sessions[update.effective_user.id]['date'] = update.message.text
    await update.message.reply_text("Which class? (SL, 3AC, 2AC, 2S, etc):")
    return CLASS

async def travel_class(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_sessions[update.effective_user.id]['class'] = update.message.text
    await update.message.reply_text("Train type or train number?")
    return TRAIN_TYPE

async def train_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_sessions[update.effective_user.id]['train_type'] = update.message.text
    await update.message.reply_text("How many passengers?")
    return NUM_PASSENGERS

async def num_passengers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_sessions[update.effective_user.id]['num_passengers'] = int(update.message.text)
    await update.message.reply_text("Enter passenger details in format: Name,Age,Gender (one per line)")
    return PASSENGER_DETAILS

async def passenger_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    passengers = update.message.text.split('\n')
    user_sessions[update.effective_user.id]['passengers'] = [p.split(',') for p in passengers]
    await update.message.reply_text("Enter your IRCTC username and password (comma separated):")
    return CREDENTIALS

async def credentials(update: Update, context: ContextTypes.DEFAULT_TYPE):
    creds = update.message.text.split(', ')
    user_sessions[update.effective_user.id]['credentials'] = {'username': creds[0], 'password': creds[1]}
    await update.message.reply_text("Thanks! We're starting the booking process now... 🚀")

    from automation_script import automate_booking
    captcha_image_path, browser, page = await automate_booking(user_sessions[update.effective_user.id])

    # Save browser and page inside user session
    user_sessions[update.effective_user.id]['browser'] = browser
    user_sessions[update.effective_user.id]['page'] = page
    user_sessions[update.effective_user.id]['captcha_image_path'] = captcha_image_path

    # Send captcha to user
    with open(captcha_image_path, 'rb') as captcha_file:
        await update.message.reply_photo(captcha_file, caption="🛡 Please enter the captcha text:")

    return CAPTCHA

async def handle_captcha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_sessions[user_id]['captcha'] = update.message.text

    from automation_script import complete_booking
    browser = user_sessions[user_id]['browser']
    page = user_sessions[user_id]['page']

    captcha_image_path_2, browser, page = await complete_booking(user_sessions[user_id], browser, page)

    user_sessions[update.effective_user.id]['browser'] = browser
    user_sessions[update.effective_user.id]['page'] = page
    user_sessions[update.effective_user.id]['captcha_image_path'] = captcha_image_path_2

    # Send captcha to user
    with open(captcha_image_path_2, 'rb') as captcha_file:
        await update.message.reply_photo(captcha_file, caption="🛡 Please enter the captcha text:")

    return CAPTCHA_2


async def handle_captcha_2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_sessions[user_id]['captcha_2'] = update.message.text

    from automation_script import complete_booking
    browser = user_sessions[user_id]['browser']
    page = user_sessions[user_id]['page']

    from automation_script import handle_payment
    qr_path, browser, page = await handle_payment(user_sessions[user_id], browser, page)

    user_sessions[update.effective_user.id]['browser'] = browser
    user_sessions[update.effective_user.id]['page'] = page
    user_sessions[update.effective_user.id]['qr_path'] = qr_path

    with open(qr_path, 'rb') as qr_file:
        await update.message.reply_photo(qr_file, caption="🛡 Scan QR to Pay")

    print("QR code has been sent to the user.")

    # await update.message.reply_document(InputFile(ticket_pdf_path), caption="✅ Here is your booked ticket! Safe travels!")

    # # Cleanup session
    # await browser.close()
    # del user_sessions[user_id]

    # return ConversationHandler.END

# Bot Setup
app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    states={
        FROM: [MessageHandler(filters.TEXT & ~filters.COMMAND, from_station)],
        TO: [MessageHandler(filters.TEXT & ~filters.COMMAND, to_station)],
        DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, date_of_journey)],
        CLASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, travel_class)],
        TRAIN_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, train_type)],
        NUM_PASSENGERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, num_passengers)],
        PASSENGER_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, passenger_details)],
        CREDENTIALS: [MessageHandler(filters.TEXT & ~filters.COMMAND, credentials)],
        CAPTCHA: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_captcha)],
        CAPTCHA_2: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_captcha_2)],
        
    },
    fallbacks=[]
)

app.add_handler(conv_handler)

if __name__ == '__main__':
    app.run_polling()
