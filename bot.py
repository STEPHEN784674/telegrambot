import telebot
from telebot import types
import os

BOT_TOKEN = '7763648932:AAFftMRo1CwkTtMZqAGtbgzIK0qNNiqriwA'
ADMIN_ID = 1237991597  # Replace with your Telegram user ID
ADMIN_USERNAME = 'sarvesh492'  # For contact buttons
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

pending_orders = {}  # user_id: {product, quantity}
known_users = set()
pending_stock_uploads = {}  # admin_id: product name
pending_refunds = {}  # user_id: True if refund expected

@bot.message_handler(commands=['start'])
def start(msg):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add('Buy', 'My Orders', 'Contact Admin')
    bot.send_message(msg.chat.id, "Welcome! What would you like to do?", reply_markup=kb)

@bot.message_handler(commands=['id'])
def get_user_id(msg):
    bot.reply_to(msg, f"Your user ID is: `{msg.from_user.id}`", parse_mode="Markdown")

@bot.message_handler(commands=['stock'])
def stock_count(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    response = "*Stock Summary:*\n"
    for name, info in PRODUCTS.items():
        count = 0
        if os.path.exists(info['file']):
            with open(info['file'], 'r') as f:
                count = len([line for line in f if line.strip()])
        response += f"{name}: {count} in stock\n"
    bot.send_message(msg.chat.id, response, parse_mode="Markdown")

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

@bot.message_handler(func=lambda m: m.text == 'Buy')
def show_products(msg):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for product in PRODUCTS:
        kb.add(product)
    bot.send_message(msg.chat.id, "Select the account you want to buy:", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == 'My Orders')
def show_orders(msg):
    bot.send_message(msg.chat.id, "Coming soon: Your order history.")

@bot.message_handler(func=lambda m: m.text == 'Contact Admin')
def contact_admin(msg):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Message Admin", url=f"https://t.me/{ADMIN_USERNAME}"))
    bot.send_message(msg.chat.id, "You can contact the admin here:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in PRODUCTS)
def handle_product_selection(msg):
    user_id = msg.chat.id
    product = msg.text
    filepath = PRODUCTS[product]['file']
    count = 0
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            count = len([line for line in f if line.strip()])

    if count == 0:
        bot.send_message(user_id, f"Sorry, *{product}* is currently *out of stock*.", parse_mode='Markdown')
        return

    pending_orders[user_id] = {'product': product, 'quantity': 1}

    qty_markup = types.InlineKeyboardMarkup()
    for i in range(1, 6):
        qty_markup.add(types.InlineKeyboardButton(str(i), callback_data=f"qty_{i}"))

    bot.send_message(user_id, f"*{product}* is available. ({count} in stock)\nHow many accounts would you like to buy?", parse_mode='Markdown', reply_markup=qty_markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('qty_'))
def select_quantity(call):
    user_id = call.message.chat.id
    quantity = int(call.data.split('_')[1])
    if user_id not in pending_orders:
        return

    pending_orders[user_id]['quantity'] = quantity
    product = pending_orders[user_id]['product']
    total = PRODUCTS[product]['price'] * quantity

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Pay with Binance", callback_data='pay_binance'))
    markup.add(types.InlineKeyboardButton("Pay with UPI", callback_data='pay_upi'))
    markup.add(types.InlineKeyboardButton("Contact Admin", url=f"https://t.me/{ADMIN_USERNAME}"))

    bot.send_message(user_id, f"You selected *{quantity}* x {product} = *${total}*\nChoose a payment method:", parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ['pay_binance', 'pay_upi'])
def handle_payment_choice(call):
    user_id = call.message.chat.id
    if user_id not in pending_orders:
        return

    order = pending_orders[user_id]
    product = order['product']
    quantity = order['quantity']
    total_usd = PRODUCTS[product]['price'] * quantity
    total_inr = total_usd * INR_CONVERSION_RATE
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Contact Admin", url=f"https://t.me/{ADMIN_USERNAME}"))

    if call.data == 'pay_binance':
        bot.send_message(user_id, f"Send *${total_usd}* to Binance ID: `{BINANCE_ID}`\nAfter payment, send a screenshot or transaction ID here.", parse_mode='Markdown', reply_markup=markup)
    elif call.data == 'pay_upi':
        with open(UPI_QR_PATH, 'rb') as qr:
            bot.send_photo(user_id, qr, caption=f"Send ₹{total_inr} (≈ ${total_usd}) to UPI ID: `{UPI_ID}`\nAfter payment, send a screenshot or transaction ID here.", parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(content_types=['text', 'photo'])
def handle_payment_proof(msg):
    user_id = msg.chat.id
    if user_id not in pending_orders:
        return

    order = pending_orders[user_id]
    product = order['product']
    quantity = order['quantity']
    caption = f"New order!\nUser: @{msg.from_user.username or msg.from_user.id}\nProduct: {product}\nQuantity: {quantity}\nChoose action:"
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}"),
        types.InlineKeyboardButton("❌ Decline", callback_data=f"decline_{user_id}"),
        types.InlineKeyboardButton("🔁 Refund", callback_data=f"refund_{user_id}")
    )

    if msg.photo:
        file_id = msg.photo[-1].file_id
        bot.send_photo(ADMIN_ID, file_id, caption=caption, reply_markup=markup)
    else:
        bot.send_message(ADMIN_ID, caption + f"\nProof: {msg.text}", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_'))
def approve_order(call):
    target_id = int(call.data.split('_')[1])
    if target_id not in pending_orders:
        bot.send_message(call.message.chat.id, "Order not found or already processed.")
        return

    order = pending_orders[target_id]
    product = order['product']
    quantity = order['quantity']
    filepath = PRODUCTS[product]['file']

    if not os.path.exists(filepath):
        bot.send_message(call.message.chat.id, f"Stock file missing for {product}!")
        return

    with open(filepath, 'r') as f:
        lines = f.readlines()

    if len(lines) < quantity:
        bot.send_message(call.message.chat.id, f"Not enough {product} accounts in stock!")
        return

    accounts = [lines[i].strip() for i in range(quantity)]
    with open(filepath, 'w') as f:
        f.writelines(lines[quantity:])

    reply_markup = types.InlineKeyboardMarkup()
    reply_markup.add(
        types.InlineKeyboardButton("Buy Again", callback_data="buy_again"),
        types.InlineKeyboardButton("Contact Admin", url=f"https://t.me/{ADMIN_USERNAME}")
    )

    bot.send_message(target_id, f"✅ Your {product} accounts:\n" + '\n'.join(f"`{acc}`" for acc in accounts), parse_mode='Markdown', reply_markup=reply_markup)
    bot.send_message(call.message.chat.id, "Account(s) delivered successfully.")
    del pending_orders[target_id]

@bot.callback_query_handler(func=lambda call: call.data.startswith('decline_'))
def decline_order(call):
    target_id = int(call.data.split('_')[1])
    if target_id in pending_orders:
        bot.send_message(target_id, "❌ Your payment was declined by the admin.")
        del pending_orders[target_id]
    bot.send_message(call.message.chat.id, "Order declined.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('refund_'))
def refund_order(call):
    target_id = int(call.data.split('_')[1])
    pending_refunds[target_id] = True
    bot.send_message(target_id, "🔁 Please send your UPI or Binance Refund ID.")
    bot.send_message(call.message.chat.id, "Waiting for refund details from user...")

@bot.message_handler(func=lambda m: m.chat.id in pending_refunds)
def handle_refund_id(msg):
    bot.send_message(ADMIN_ID, f"🔁 Refund request from @{msg.from_user.username or msg.from_user.id}:\n{msg.text}")
    bot.send_message(msg.chat.id, "Thank you. Your refund request has been submitted to the admin.")
    del pending_refunds[msg.chat.id]

@bot.callback_query_handler(func=lambda call: call.data == 'buy_again')
def handle_buy_again(call):
    show_products(call.message)

print("Bot is running...")
bot.infinity_polling()


