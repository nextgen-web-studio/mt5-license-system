import os
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from dotenv import load_dotenv

import httpx
# Monkey patch httpx to disable SSL verification due to local proxy/certificate issues
_original_init = httpx.AsyncClient.__init__
def _patched_init(self, *args, **kwargs):
    kwargs['verify'] = False
    _original_init(self, *args, **kwargs)
httpx.AsyncClient.__init__ = _patched_init

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters, ConversationHandler

from keyboards.menu import get_main_menu_keyboard
from utils.api_client import register_user, get_products, create_order, create_payment

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

WAITING_FOR_MT5_ID = 1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = await register_user(
        telegram_id=user.id, name=user.first_name, username=user.username, phone=None
    )
    if db_user:
        context.user_data['db_user_id'] = db_user['id']

    welcome_text = (
        f"Hello {user.first_name}! Welcome to Infinity Trader.\n\n"
        "Please select an option below:"
    )
    await update.message.reply_text(welcome_text, reply_markup=get_main_menu_keyboard())
    return ConversationHandler.END

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "buy_ea" or data == "buy_vps":
        p_type = "EA" if data == "buy_ea" else "VPS"
        products = await get_products(product_type=p_type)
        if not products:
            try:
                await query.edit_message_text(f"No {p_type} products available.", reply_markup=get_main_menu_keyboard())
            except Exception:
                pass
            return
            
        keyboard = []
        for p in products:
            keyboard.append([InlineKeyboardButton(f"{p['name']} - ₹{p['price']}", callback_data=f"buy_product_{p['id']}_{p_type}")])
        keyboard.append([InlineKeyboardButton("« Back to Menu", callback_data="main_menu")])
        
        try:
            await query.edit_message_text(f"Please select a {p_type} Plan:", reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            pass
        
    elif data.startswith("buy_product_"):
        parts = data.split("_")
        product_id = int(parts[2])
        p_type = parts[3]
        user_id = context.user_data.get('db_user_id')
        
        if not user_id:
            await query.edit_message_text("Session expired. Please send /start again.")
            return
            
        order = await create_order(user_id, product_id, p_type)
        if not order:
            await query.edit_message_text("Failed to create order.")
            return
            
        products = await get_products()
        product = next((p for p in products if p['id'] == product_id), None)
        if not product:
            await query.edit_message_text("Product not found.")
            return
            
        amount = product['price']
        payment = await create_payment(order['id'], amount)
        if not payment:
            await query.edit_message_text("Failed to generate payment link.")
            return
            
        payment_url = payment['payment_link_url']
        keyboard = [[InlineKeyboardButton(f"💳 Pay ₹{amount}", url=payment_url)]]
        
        await query.edit_message_text(
            text=f"Order #{order['id']} created!\n\nPlease click the button below to complete your payment securely via Razorpay.\n\n_You will be automatically notified here once the payment is successful._",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        if p_type == "EA":
            return WAITING_FOR_MT5_ID
        return ConversationHandler.END
            
    elif data == "main_menu" or data == "home":
        try:
            await query.edit_message_text("Please select an option below:", reply_markup=get_main_menu_keyboard())
        except Exception:
            pass
    return ConversationHandler.END

async def handle_mt5_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mt5_id = update.message.text
    order_id = context.user_data.get('current_order_id')
    
    await update.message.reply_text(f"⏳ *Creating License* for MT5 ID: `{mt5_id}`...", parse_mode="Markdown")
    
    # Trigger fulfillment
    async with httpx.AsyncClient(verify=False) as client:
        # Hack to mark paid (since Razorpay webhook isn't here yet)
        await client.get(f"http://localhost:8000/api/v1/orders/{order_id}/mock-pay") # I will add this endpoint!
        
        resp = await client.post(f"http://localhost:8000/api/v1/orders/{order_id}/start-fulfillment", json={"mt5_id": mt5_id})
        
    if resp.status_code == 200:
        await update.message.reply_text("📦 *Compiling EA...* (This takes a few seconds)", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"Error: {resp.text}")
        
    return ConversationHandler.END

class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

def start_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), DummyHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    logging.info(f"Dummy web server started on port {port}")

def main():
    start_dummy_server()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    application = ApplicationBuilder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler)],
        states={
            WAITING_FOR_MT5_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_mt5_id)]
        },
        fallbacks=[CommandHandler("start", start)]
    )
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    
    logging.info("Starting Infinity Trader Bot...")
    application.run_polling()

if __name__ == '__main__':
    main()
