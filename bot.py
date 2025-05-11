# Telegram Wallet Bot with Binance UID Payment Integration and Enhanced Balance Warning
import telebot
from telebot import types
import os
import json
import re

BOT_TOKEN = '7763648932:AAFdovWm-l8DZ0r9QMgUZ1MW6TUTAjiDtIE'
ADMIN_ID = 1237991597
ADMIN_USERNAME = 'sarvesh492'
BINANCE_UID = '766254967'

PRODUCTS_FILE = 'products.json'
WALLETS_FILE = 'wallets.json'

DEFAULT_PRODUCTS = {
    'DigitalOcean': {'price': 6, 'file': 'digitalocean.txt'},
    'ChatGPT Plus': {'price': 7, 'file': 'chatgpt.txt'},
    'Google Cloud': {'price': 10, 'file': 'googlecloud.txt'},
    'Microsoft365': {'price': 7, 'file': 'microsoft365.txt'}
}

if os.path.exists(PRODUCTS_FILE):
    with open(PRODUCTS_FILE, 'r') as f:
        PRODUCTS = json.load(f)
else:
    PRODUCTS = DEFAULT_PRODUCTS

if os.path.exists(WALLETS_FILE):
    with open(WALLETS_FILE, 'r') as f:
        WALLETS = json.load(f)
else:
    WALLETS = {}

bot = telebot.TeleBot(BOT_TOKEN)
pending_stock_uploads = {}
known_users = set()

if os.path.exists("users.txt"):
    with open("users.txt", "r") as f:
        known_users = set(int(line.strip()) for line in f if line.strip().isdigit())

def save_wallets():
    with open('wallets_backup.json', 'w') as backup:
        json.dump(WALLETS, backup, indent=2)
    with open(WALLETS_FILE, 'w') as f:
        json.dump(WALLETS, f, indent=2)

def get_wallet(uid):
    if str(uid) not in WALLETS:
        WALLETS[str(uid)] = {'balance': 0.0, 'spent': 0.0}
    return WALLETS[str(uid)]

@bot.message_handler(commands=['start'])
def start(msg):

@bot.message_handler(commands=['wallet'])
def wallet_cmd(msg):
    wallet(msg)

@bot.message_handler(commands=['addfunds'])
def addfunds_cmd(msg):
    add_funds(msg)

@bot.message_handler(commands=['buy'])
def buy_cmd(msg):
    show_products(msg)
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Buy", callback_data="menu_buy"))
    kb.add(types.InlineKeyboardButton("My Wallet", callback_data="menu_wallet"))
    kb.add(types.InlineKeyboardButton("Add Funds", callback_data="menu_addfunds"))
    kb.add(types.InlineKeyboardButton("Contact Admin", url=f"https://t.me/{ADMIN_USERNAME}"))
    bot.send_message(msg.chat.id, "Welcome! Please choose an option:", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data == "menu_wallet")
def wallet(call):
    user_wallet = get_wallet(call.from_user.id)
    msg = f"\U0001F511 Wallet\nBalance: ${user_wallet['balance']:.2f}\nTotal Spent: ${user_wallet['spent']:.2f}"
    bot.send_message(call.message.chat.id, msg)

@bot.callback_query_handler(func=lambda call: call.data == "menu_addfunds")
def add_funds(call):
    msg = f"\U0001F4B5 Add Funds via Binance Internal Transfer\n\nSend USDT to Binance UID:\n🔸 UID: {BINANCE_UID}\n\nAfter sending, reply here with the transaction screenshot or ID. Admin will verify and credit your wallet."
    bot.send_message(call.message.chat.id, msg)

@bot.message_handler(commands=['addbal'])
def add_balance(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    try:
        parts = msg.text.split()
        target_uid = parts[1].replace('@', '')
        amount = float(parts[2])
        for uid, data in WALLETS.items():
            if data.get('username') == target_uid or uid == target_uid:
                data['balance'] += amount
                save_wallets()
                bot.send_message(msg.chat.id, f"Added ${amount:.2f} to @{target_uid}'s wallet.")
                return
        bot.send_message(msg.chat.id, f"User @{target_uid} not found.")
    except:
        bot.reply_to(msg, "Usage: /addbal @username amount")

@bot.callback_query_handler(func=lambda call: call.data == "menu_buy")
def show_buy_from_menu(call):
    show_products(call.message)

@bot.message_handler(func=lambda m: m.text in PRODUCTS)
def handle_product_selection(msg):
    uid = msg.chat.id
    product = msg.text
    path = PRODUCTS[product]['file']
    count = 0
    if os.path.exists(path):
        with open(path, 'r') as f:
            count = len([line for line in f if line.strip()])
    if count == 0:
        bot.send_message(uid, f"*{product}* is currently *out of stock*.", parse_mode='Markdown')
        return
    kb = types.InlineKeyboardMarkup()
    for i in range(1, 6):
        kb.add(types.InlineKeyboardButton(f"Buy {i} - ${PRODUCTS[product]['price']*i:.2f}", callback_data=f"buy_{product}_{i}"))
    bot.send_message(uid, f"{product} is available ({count} in stock). Choose quantity:", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def handle_buy(call):
    _, product, qty = call.data.split("_")
    qty = int(qty)
    uid = call.message.chat.id
    wallet = get_wallet(uid)
    total = PRODUCTS[product]['price'] * qty
    if wallet['balance'] < total:
        short = total - wallet['balance']
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("➕ Add Funds", callback_data="menu_addfunds"))
        kb.add(types.InlineKeyboardButton("📞 Contact Admin", url=f"https://t.me/{ADMIN_USERNAME}"))
        bot.send_message(uid, f"❌ You have insufficient balance.\n\n💸 Price: ${total:.2f}\n💰 Your Balance: ${wallet['balance']:.2f}\n🧾 You are short by: ${short:.2f}\n\nPlease top up your wallet:", reply_markup=kb)
        return
    path = PRODUCTS[product]['file']
    with open(path, 'r') as f:
        lines = f.readlines()
    if len(lines) < qty:
        bot.send_message(uid, "❌ Not enough stock.")
        return
    accounts = lines[:qty]
    with open(path, 'w') as f:
        f.writelines(lines[qty:])
    wallet['balance'] -= total
    wallet['spent'] += total
    save_wallets()
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Buy Again", callback_data="menu_buy"))
    bot.send_message(uid, "✅ Your accounts:\n" + "\n".join(f"`{a.strip()}`" for a in accounts), parse_mode='Markdown', reply_markup=kb)

@bot.message_handler(commands=['setprice'])
def set_price(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    match = re.match(r'^/setprice\s+(.+?)\s+(\d+(\.\d+)?)$', msg.text)
    if not match:
        bot.reply_to(msg, "Usage: /setprice <ProductName> <NewPrice>\nExample: /setprice Google Cloud 12")
        return
    product = match.group(1).strip()
    new_price = match.group(2)
    if product not in PRODUCTS:
        bot.reply_to(msg, f"❌ Product not found: {product}")
        return
    try:
        PRODUCTS[product]['price'] = float(new_price)
        with open('products_backup.json', 'w') as backup:
            json.dump(PRODUCTS, backup, indent=2)
        with open(PRODUCTS_FILE, 'w') as f:
            json.dump(PRODUCTS, f, indent=2)
        bot.send_message(msg.chat.id, f"✅ Price for *{product}* updated to *${new_price}*", parse_mode='Markdown')
    except ValueError:
        bot.reply_to(msg, "❌ Invalid price. Please enter a number.")

@bot.message_handler(commands=['addstock'])
def add_stock_prompt(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    args = msg.text.split(maxsplit=1)
    if len(args) != 2 or args[1] not in PRODUCTS:
        bot.reply_to(msg, "Usage: /addstock <ProductName>\nExample: /addstock DigitalOcean")
        return
    product = args[1]
    pending_stock_uploads[msg.from_user.id] = product
    bot.send_message(msg.chat.id, f"Please upload a .txt file with accounts for {product}.")

@bot.message_handler(content_types=['document'])
def handle_stock_file(msg):
    if msg.from_user.id not in pending_stock_uploads:
        return
    product = pending_stock_uploads[msg.from_user.id]
    file_info = bot.get_file(msg.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    with open(PRODUCTS[product]['file'], 'a') as f:
        f.write(downloaded_file.decode('utf-8'))
    bot.send_message(msg.chat.id, f"✅ Stock updated for {product}.")
    del pending_stock_uploads[msg.from_user.id]

@bot.message_handler(content_types=['text', 'photo'])
def handle_addfund_proof(msg):
    if msg.text or msg.photo:
        caption = f"💸 New add funds request from @{msg.from_user.username or msg.chat.id}
User ID: `{msg.chat.id}`
"
        if msg.photo:
            file_id = msg.photo[-1].file_id
            kb = types.InlineKeyboardMarkup()
            kb.add(
                types.InlineKeyboardButton("✅ Approve", callback_data=f"approvefund_{msg.chat.id}"),
                types.InlineKeyboardButton("❌ Decline", callback_data=f"declinefund_{msg.chat.id}")
            )
            bot.send_photo(ADMIN_ID, file_id, caption=caption, parse_mode='Markdown', reply_markup=kb)
        else:
            bot.send_message(ADMIN_ID, caption + f"Proof: {msg.text}", parse_mode='Markdown')


@bot.callback_query_handler(func=lambda call: call.data.startswith("approvefund_"))
def approve_fund(call):
    uid = call.data.split("_")[1]
    try:
        uid = int(uid)
        amount = 0  # You can replace this with fixed amount logic or prompt manually
        bot.send_message(uid, f"✅ Your payment has been approved. Please wait while your balance is updated.")
        bot.send_message(ADMIN_ID, f"Now run: /addbal @{WALLETS[str(uid)].get('username', uid)} <amount>")
    except Exception as e:
        bot.send_message(ADMIN_ID, f"Failed to process approval: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("declinefund_"))
def decline_fund(call):
    uid = call.data.split("_")[1]
    try:
        uid = int(uid)
        bot.send_message(uid, "❌ Your payment has been declined. Please contact admin.")
        bot.send_message(ADMIN_ID, f"User {uid} has been notified about decline.")
    except:
        pass

def track_users(m):
    if m.chat.id != ADMIN_ID:
        if m.chat.id not in known_users:
            known_users.add(m.chat.id)
            with open("users_backup.txt", "w") as backup:
                backup.write("
".join(map(str, known_users)))
            with open("users.txt", "a") as f:
                f.write(str(m.chat.id) + "\n")

    # Optionally store username
    uid = str(m.chat.id)
    if uid not in WALLETS:
        WALLETS[uid] = {'balance': 0.0, 'spent': 0.0, 'username': m.from_user.username or str(uid)}
        save_wallets()

def show_products(msg):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for product in PRODUCTS:
        kb.add(product)
    bot.send_message(msg.chat.id, "Select the account you want to buy:", reply_markup=kb)

from telebot.types import BotCommand

commands = [
    BotCommand("start", "Show main menu"),
    BotCommand("wallet", "View your balance"),
    BotCommand("addfunds", "Add funds via Binance UID"),
    BotCommand("buy", "Browse and buy accounts"),
    BotCommand("addbal", "Admin: Add funds to user wallet"),
    BotCommand("addstock", "Admin: Upload stock"),
    BotCommand("setprice", "Admin: Update product price")
]
bot.set_my_commands(commands)

print("Bot is running...")
bot.infinity_polling()
