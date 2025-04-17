import telebot
from telebot import types
import os

BOT_TOKEN = '7763648932:AAFftMRo1CwkTtMZqAGtbgzIK0qNNiqriwA'
ADMIN_ID = 1237991597
ADMIN_USERNAME = 'sarvesh492'
BINANCE_ID = '766254967'
UPI_ID = '9049275529-5@ybl'
UPI_QR_PATH = 'qr.png'
INR_CONVERSION_RATE = 89

PRODUCTS = {
    'DigitalOcean': {'price': 6, 'file': 'digitalocean.txt'},
    'ChatGPT Plus': {'price': 7, 'file': 'chatgpt.txt'},
    'Google Cloud': {'price': 10, 'file': 'googlecloud.txt'}
}

bot = telebot.TeleBot(BOT_TOKEN)

pending_orders = {}
pending_stock_uploads = {}
pending_refunds = {}
known_users = set()

# Load users from file
if os.path.exists("users.txt"):
    with open("users.txt", "r") as f:
        known_users = set(int(line.strip()) for line in f if line.strip().isdigit())

@bot.message_handler(commands=['start'])
def start(msg):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Buy", callback_data="menu_buy"))
    kb.add(types.InlineKeyboardButton("My Orders", callback_data="menu_orders"))
    kb.add(types.InlineKeyboardButton("Contact Admin", url=f"https://t.me/{ADMIN_USERNAME}"))
    bot.send_message(msg.chat.id, "Welcome! Please choose an option:", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data == "menu_buy")
def show_buy_from_menu(call):
    show_products(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "menu_orders")
def show_my_orders(call):
    bot.send_message(call.message.chat.id, "Coming soon: Your order history.")

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

@bot.message_handler(commands=['broadcast'])
def broadcast(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    parts = msg.text.split(maxsplit=1)
    if len(parts) != 2:
        bot.send_message(msg.chat.id, "Usage: /broadcast <message>")
        return
    text = parts[1]
    sent = 0
    failed = 0
    for uid in known_users:
        try:
            bot.send_message(uid, f"📢 *Admin Broadcast:*\n{text}", parse_mode="Markdown")
            sent += 1
        except:
            failed += 1
    bot.send_message(msg.chat.id, f"✅ Broadcast sent to {sent} user(s), {failed} failed.")

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
    pending_orders[uid] = {'product': product, 'quantity': 1}
    kb = types.InlineKeyboardMarkup()
    for i in range(1, 6):
        kb.add(types.InlineKeyboardButton(str(i), callback_data=f"qty_{i}"))
    bot.send_message(uid, f"{product} is available ({count} in stock). How many do you want?", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("qty_"))
def select_quantity(call):
    uid = call.message.chat.id
    q = int(call.data.split("_")[1])
    if uid not in pending_orders:
        return
    pending_orders[uid]['quantity'] = q
    product = pending_orders[uid]['product']
    total = PRODUCTS[product]['price'] * q
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Pay with Binance", callback_data='pay_binance'))
    kb.add(types.InlineKeyboardButton("Pay with UPI", callback_data='pay_upi'))
    bot.send_message(uid, f"You selected {q} x {product} = ${total}", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_"))
def handle_payment_method(call):
    uid = call.message.chat.id
    method = call.data.split("_")[1]
    if uid not in pending_orders:
        return
    pending_orders[uid]['last_method'] = method
    order = pending_orders[uid]
    p = order['product']
    q = order['quantity']
    usd = PRODUCTS[p]['price'] * q
    inr = usd * INR_CONVERSION_RATE
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Contact Admin", url=f"https://t.me/{ADMIN_USERNAME}"))
    if method == 'binance':
        bot.send_message(uid, f"Send *${usd}* to Binance ID: `{BINANCE_ID}`", parse_mode='Markdown', reply_markup=markup)
    else:
        with open(UPI_QR_PATH, 'rb') as qr:
            bot.send_photo(uid, qr, caption=f"Send ₹{inr} (≈ ${usd}) to `{UPI_ID}`", parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(content_types=['text', 'photo'])
def handle_payment_proof(msg):
    uid = msg.chat.id
    if uid not in pending_orders:
        return
    order = pending_orders[uid]
    method = order.get('last_method', 'upi')
    bot.send_message(uid, f"⏳ Checking your transaction with {'Binance' if method == 'binance' else 'UPI'}...")
    product = order['product']
    quantity = order['quantity']
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Approve", callback_data=f"approve_{uid}"),
        types.InlineKeyboardButton("❌ Decline", callback_data=f"decline_{uid}"),
        types.InlineKeyboardButton("🔁 Refund", callback_data=f"refund_{uid}")
    )
    caption = f"New order!\nUser: @{msg.from_user.username or uid}\nProduct: {product}\nQty: {quantity}"
    if msg.photo:
        bot.send_photo(ADMIN_ID, msg.photo[-1].file_id, caption=caption, reply_markup=markup)
    else:
        bot.send_message(ADMIN_ID, caption + f"\nProof: {msg.text}", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_"))
def approve_order(call):
    uid = int(call.data.split("_")[1])
    if uid not in pending_orders: return
    o = pending_orders[uid]
    path = PRODUCTS[o['product']]['file']
    with open(path, 'r') as f:
        lines = f.readlines()
    if len(lines) < o['quantity']:
        bot.send_message(call.message.chat.id, "Not enough stock.")
        return
    accounts = lines[:o['quantity']]
    with open(path, 'w') as f:
        f.writelines(lines[o['quantity']:])
    reply = types.InlineKeyboardMarkup()
    reply.add(types.InlineKeyboardButton("Buy Again", callback_data="menu_buy"))
    bot.send_message(uid, "✅ Your accounts:\n" + "\n".join(f"`{a.strip()}`" for a in accounts), parse_mode='Markdown', reply_markup=reply)
    bot.send_message(call.message.chat.id, "Delivered.")
    del pending_orders[uid]

@bot.callback_query_handler(func=lambda call: call.data.startswith("decline_"))
def decline(call):
    uid = int(call.data.split("_")[1])
    if uid in pending_orders:
        bot.send_message(uid, "❌ Your payment was declined.")
        del pending_orders[uid]
    bot.send_message(call.message.chat.id, "Declined.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("refund_"))
def refund(call):
    uid = int(call.data.split("_")[1])
    pending_refunds[uid] = True
    bot.send_message(uid, "🔁 Please send your Refund ID.")
    bot.send_message(call.message.chat.id, "Waiting for refund info.")

@bot.message_handler(func=lambda m: m.chat.id in pending_refunds)
def handle_refund(m):
    bot.send_message(ADMIN_ID, f"🔁 Refund from @{m.from_user.username or m.chat.id}:\n{m.text}")
    bot.send_message(m.chat.id, "Refund request submitted.")
    del pending_refunds[m.chat.id]

@bot.message_handler(func=lambda m: True)
def track_users(m):
    if m.chat.id != ADMIN_ID:
        if m.chat.id not in known_users:
            known_users.add(m.chat.id)
            with open("users.txt", "a") as f:
                f.write(str(m.chat.id) + "\n")

def show_products(msg):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for product in PRODUCTS:
        kb.add(product)
    bot.send_message(msg.chat.id, "Select the account you want to buy:", reply_markup=kb)

print("Bot is running...")
bot.infinity_polling()


