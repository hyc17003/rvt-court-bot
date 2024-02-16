import httpx
import logging
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackContext, CallbackQueryHandler

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Welcome to the RV Tennis Court Bot! \nSend /next to get the next booking(s).")

async def fetch_next_booking():
    url = "https://reboks.nus.edu.sg/nus_public_web/public/index.php/facilities/booking_schedule"
    
    params = {
        'venue_id': '6', 
        'date_from': datetime.now().strftime("%a, %d %b %Y"), 
        'date_to': (datetime.now() + timedelta(days=7)).strftime("%a, %d %b %Y") 
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
    
    soup = BeautifulSoup(response.text, 'html.parser')
    print(response.text)
    table = soup.find('table', {'id': 'user_list_result'})
    if not table:
        return "Error! Looks like website formatting has changed, inform bot creator."
    
    booking_info = []
    rows = table.find_all('tr')[1:]
    for row in rows:
        columns = row.find_all('td')
        if 'Ridge View Residential College' in columns[1].text:
            subvenue = columns[4].text.strip()
            date = columns[5].text.strip()
            time = columns[7].text.strip()
            booking_details = f"Venue: {subvenue}\nDate: {date}\nTimeslot: {time}"
            booking_info.append(booking_details)
    
    return '\n\n\n'.join(booking_info) if booking_info else "No upcoming bookings :(."

async def next_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    booking_info = await fetch_next_booking()
    await update.message.reply_text(booking_info) 

async def check_routine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_date = datetime.now() + timedelta(days=2)
    target_date_str = target_date.strftime("%Y-%m-%d")
    booking = await fetch_next_booking()

    if target_date_str in booking:
        court_extraction_pattern = rf"Venue: Tennis Court (\d+)\nDate: {target_date_str}\n"
    
        courts = set(re.findall(court_extraction_pattern, booking))

        timeslot_pattern = rf"Date: {target_date_str}\nTimeslot: (\d{{2}}:\d{{2}}:\d{{2}})-(\d{{2}}:\d{{2}}:\d{{2}})"
        timeslots = re.findall(timeslot_pattern, booking)
    
        if timeslots:
            earliest_start, latest_end = min(timeslot[0] for timeslot in timeslots), max(timeslot[1] for timeslot in timeslots)
            message_text= f"There are courts on {target_date_str}: Courts {', '.join(sorted(courts))}, from {earliest_start[:5]}-{latest_end[:5]}"
            keyboard = [[InlineKeyboardButton("Make Poll", callback_data='make_poll')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(chat_id=update.effective_chat.id, text=message_text, reply_markup=reply_markup)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="No bookings 2 days later.")

async def make_poll_button_handler(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    # can replace with callback_data
    if query.data == "make_poll":
        target_date = datetime.now() + timedelta(days=2)
        target_date_str = target_date.strftime("%Y-%m-%d")
        booking = await fetch_next_booking()

        if target_date_str in booking:
            court_extraction_pattern = rf"Venue: Tennis Court (\d+)\nDate: {target_date_str}\n"
    
            courts = set(re.findall(court_extraction_pattern, booking))

            timeslot_pattern = rf"Date: {target_date_str}\nTimeslot: (\d{{2}}:\d{{2}}:\d{{2}})-(\d{{2}}:\d{{2}}:\d{{2}})"
            timeslots = re.findall(timeslot_pattern, booking)
    
            if timeslots:
                earliest_start, latest_end = min(timeslot[0] for timeslot in timeslots), max(timeslot[1] for timeslot in timeslots)
                question = f"Tennis on {target_date_str} @ Courts {', '.join(sorted(courts))}, {earliest_start[:5]}-{latest_end[:5]}"
                options = ["Coming!", "Coming, and I need a racket!", "Not coming this time :("]
                await context.bot.send_poll(chat_id=update.effective_chat.id, question=question, options=options, is_anonymous=False)

if __name__ == '__main__':
    application = ApplicationBuilder().token(TELEGRAM_SECRET_TOKEN).build()
    
    start_handler = CommandHandler('start', start)
    next_handler = CommandHandler('next', next_booking)
    check_routine = CommandHandler('check_routine', check_routine)

    application.add_handler(start_handler)
    application.add_handler(next_handler)
    application.add_handler(check_routine)
    application.add_handler(CallbackQueryHandler(make_poll_button_handler))
    
    application.run_polling()
