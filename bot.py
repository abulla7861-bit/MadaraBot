import telebot
import requests
import schedule
import time
import threading
import os
from datetime import datetime, timedelta
import pytz
from collections import deque

# ==================== DETAILS ====================
BOT_TOKEN = os.getenv("BOT_TOKEN") or "8862228592:AAGHAAE71nqT9bSKE93DGF6ZYLf087Z3mVg"

CHANNEL_IDS = [
    "-1004448042734",
    "-1003800136238",
    "-1002597141644",
    "-1002598601395",
]
# ============================================================

# ==================== STICKER FILE IDs ====================
STICKER_SECTION_START = "CAACAgUAAxkBAAMEarGQw7i-pbl2L2mzt4Oy7A3JgrYAAlURAAIcF4BW0YVNawwjJLM9BA"
STICKER_WIN = "CAACAgUAAyEFAAMBCR--7gADdGqxkcBBnPXvHXtClEY9c8Jrd94XAAJoEQAC3PUYV1BXdO7P3kDsPQQ"
STICKER_LOSS = "CAACAgIAAxkBAAMNarGgwo8zyU5gcl2NcrRwi-YGWp4AAvNBAAJvs2hJX6Pg0NfEo3Y9BA"
STICKER_SECTION_END = "CAACAgUAAyEFAAMBCR--7gADdmqxkfD4onJjQYKlQpGsqJ2sabv2AAIVEwACEuaBVsBXC_A_xfmkPQQ"
# ============================================================

REGISTER_LINK = "https://www.veergame31.com/#/register?invitationCode=11327394097"

bot = telebot.TeleBot(BOT_TOKEN)
IST = pytz.timezone('Asia/Kolkata')

API_URL = "https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json"

result_history = deque(maxlen=60)
current_prediction = None
predictions_in_section = 0
MAX_PREDICTIONS = 6

SECTION_TIMES = ["09:30", "11:30", "15:00", "17:30", "19:20", "21:30"]

@bot.message_handler(content_types=['sticker'])
def get_sticker_id(message):
    file_id = message.sticker.file_id
    bot.reply_to(message, f"Sticker File ID:\n`{file_id}`", parse_mode="Markdown")
    print("\n===== STICKER FILE ID =====")
    print(file_id)
    print("===========================\n")

def send_to_all(text=None, sticker=None):
    for ch in CHANNEL_IDS:
        try:
            if sticker:
                bot.send_sticker(ch, sticker)
            if text:
                bot.send_message(ch, text)
            time.sleep(0.4)
        except Exception as e:
            print(f"Error sending to {ch}:", e)

# FIX 1: Headers and Safe JSON Handling Added
def fetch_results():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*"
    }
    try:
        r = requests.get(API_URL + f"?ts={int(time.time())}", headers=headers, timeout=10)
        if r.status_code == 200 and r.text.strip():
            data = r.json()
            return data.get("data", {}).get("list", [])
        else:
            print(f"API Returned empty or status {r.status_code}")
            return []
    except Exception as e:
        print("API Fetch Error:", e)
        return []

def update_history():
    lst = fetch_results()
    if not lst:
        return
    for item in reversed(lst):
        period = str(item.get("issueNumber", ""))
        number = item.get("number")
        if not period or number is None:
            continue
        number = int(number)
        if not any(x["period"] == period for x in result_history):
            result_history.append({
                "period": period,
                "number": number,
                "result": "BIG" if number >= 5 else "SMALL"
            })
    print(f"History updated. Total items: {len(result_history)}")

def predict(nums):
    if not nums or len(nums) < 3:
        return "BIG"

    latest = nums[-1]
    prevs = []
    for i in range(1, len(nums) - 1):
        if nums[i] == latest:
            prevs.append(nums[i+1])

    if not prevs:
        return "BIG"

    big = sum(1 for x in prevs if x >= 5)
    small = len(prevs) - big

    if big > small:
        return "BIG"
    if small > big:
        return "SMALL"
    return "SMALL" if latest >= 5 else "BIG"

def next_period(period):
    try:
        return str(int(period) + 1)
    except:
        return period

def get_next_section_time():
    now = datetime.now(IST)
    today = now.strftime("%Y-%m-%d")
    
    for t in SECTION_TIMES:
        dt = IST.localize(datetime.strptime(f"{today} {t}", "%Y-%m-%d %H:%M"))
        if dt > now + timedelta(minutes=1):
            return dt.strftime("%I:%M %p")
    
    return "09:30 AM (Kal)"

def send_one_prediction():
    global current_prediction, predictions_in_section

    if current_prediction is not None:
        return
    if predictions_in_section >= MAX_PREDICTIONS:
        return

    update_history()
    if len(result_history) < 5:
        return

    nums = [x["number"] for x in result_history]
    last_period = result_history[-1]["period"]
    period = next_period(last_period)
    pred = predict(nums)

    msg = f"""📆 PERIOD NO  :-  {period}
🎲 BET ON :-  {pred}
🎯 STATUS     :-  Pending"""

    send_to_all(text=msg)
    current_prediction = {"period": period, "prediction": pred}
    predictions_in_section += 1
    print(f"Prediction {predictions_in_section}/6 → {period} | {pred}")

def check_result():
    global current_prediction, predictions_in_section

    if current_prediction is None:
        return

    update_history()
    history_map = {x["period"]: x["result"] for x in result_history}
    period = current_prediction["period"]
    pred = current_prediction["prediction"]

    if period not in history_map:
        return

    actual = history_map[period]
    status = "WIN" if pred == actual else "LOSS"

    if status == "WIN":
        send_to_all(sticker=STICKER_WIN)
    else:
        send_to_all(sticker=STICKER_LOSS)

    print(f"Result: {period} → {status}")
    current_prediction = None

    if predictions_in_section >= MAX_PREDICTIONS:
        time.sleep(1.5)
        send_to_all(sticker=STICKER_SECTION_END)

        next_time = get_next_section_time()
        end_msg = f"""DOSTO UMEED HAI AAP KO SACTION PASAND AAYA HOGA 
OR AAP NE ACCHA PROFIT KIYA HOGA

NEXT SACTION TIMING :- {next_time}

JIS BHAI NE BHI ID NAHI BANAYA HAI WO JALDI SE REGISTER KARO
{REGISTER_LINK}"""
        send_to_all(text=end_msg)
        predictions_in_section = 0
        print("Section End")
    else:
        time.sleep(2)
        send_one_prediction()

def pre_section_message():
    msg = f"""DOSTO SACTION START HONA WALA HAI 
JALDI SE APNA NECHE DIYA GAYA LINK SE ID BANA KAR 
APNA WALLET ME DEPOSIT KAR LO

{REGISTER_LINK}"""
    send_to_all(text=msg)
    print("Pre-section message bhej diya")

def start_section():
    global predictions_in_section, current_prediction
    predictions_in_section = 0
    current_prediction = None

    print("Section Starting...")
    send_to_all(sticker=STICKER_SECTION_START)
    time.sleep(4)
    send_one_prediction()

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(3)

# ==================== SCHEDULE ====================
schedule.every().day.at("09:28").do(pre_section_message)
schedule.every().day.at("11:28").do(pre_section_message)
schedule.every().day.at("14:58").do(pre_section_message)
schedule.every().day.at("17:28").do(pre_section_message)
schedule.every().day.at("19:18").do(pre_section_message)
schedule.every().day.at("21:28").do(pre_section_message)

schedule.every().day.at("09:30").do(start_section)
schedule.every().day.at("11:30").do(start_section)
schedule.every().day.at("15:00").do(start_section)
schedule.every().day.at("17:30").do(start_section)
schedule.every().day.at("19:20").do(start_section)
schedule.every().day.at("21:30").do(start_section)

schedule.every(8).seconds.do(check_result)

print("Bot start ho gaya...")
update_history()

# Scheduler background mein chalao
scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
scheduler_thread.start()

# FIX 2: Webhook remove and Infinity Polling with robust options
try:
    bot.remove_webhook()
except Exception:
    pass

bot.infinity_polling(timeout=10, long_polling_timeout=5, skip_pending=True)
