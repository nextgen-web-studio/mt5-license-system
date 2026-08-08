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
            text=f"Order #{order['id']} created!\n\nPlease click the button below to complete your payment securely via Razorpay.\n\n*(For Testing: Since webhooks aren't configured yet, just type any MT5 ID here in the chat to simulate a successful payment!)*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        context.user_data['current_order_id'] = order['id']
            
    elif data == "main_menu" or data == "home":
        try:
            await query.edit_message_text("Please select an option below:", reply_markup=get_main_menu_keyboard())
        except Exception:
            pass

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = context.user_data.get('db_user_id')
    if not user_id:
        return
        
    text = update.message.text
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
    
    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.get(f"{base_url}/orders/user/{user_id}")
        if resp.status_code == 200:
            orders = resp.json()
            # Find the most recent 'paid' EA order that hasn't been fulfilled
            paid_order = next((o for o in sorted(orders, key=lambda x: x['id'], reverse=True) if o['status'] == 'paid' and o['order_type'] == 'EA'), None)
            
            if paid_order:
                order_id = paid_order['id']
                await update.message.reply_text(f"⏳ *Creating License* for MT5 ID: `{text}`...", parse_mode="Markdown")
                
                start_resp = await client.post(f"{base_url}/orders/{order_id}/start-fulfillment", json={"mt5_id": text})
                if start_resp.status_code == 200:
                    await update.message.reply_text("📦 *Compiling EA...* (This takes a few seconds)", parse_mode="Markdown")
                else:
                    await update.message.reply_text(f"Error starting fulfillment: {start_resp.text}")
                return
                
    await update.message.reply_text("Please use the /start menu to select an option.")

async def licenses_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = context.user_data.get('db_user_id')
    if not user_id:
        await update.message.reply_text("Please use /start to initialize your session.")
        return
        
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.get(f"{base_url}/licenses/user/{user_id}")
        if resp.status_code == 200:
            licenses = resp.json()
            if not licenses:
                await update.message.reply_text("You don't have any licenses yet.")
                return
                
            text = "🔑 *Your MT5 Licenses:*\n\n"
            for l in licenses:
                text += f"• *MT5 ID:* `{l['mt5_id']}`\n"
                text += f"  Status: {l['status']}\n"
                text += f"  Expires: {l['expiry_date'][:10] if l['expiry_date'] else 'N/A'}\n\n"
            
            await update.message.reply_text(text, parse_mode="Markdown")
        else:
            await update.message.reply_text("Failed to fetch licenses.")

async def downloads_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = context.user_data.get('db_user_id')
    if not user_id:
        await update.message.reply_text("Please use /start to initialize your session.")
        return
        
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
    await update.message.reply_text("Fetching your downloads...")
    
    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.get(f"{base_url}/licenses/user/{user_id}")
        if resp.status_code == 200:
            licenses = resp.json()
            active_licenses = [l for l in licenses if l['status'] == 'active']
            if not active_licenses:
                await update.message.reply_text("You don't have any active EA licenses to download.")
                return
                
            for l in active_licenses:
                download_url = f"{base_url}/licenses/{l['id']}/download"
                file_resp = await client.get(download_url)
                if file_resp.status_code == 200:
                    import io
                    doc = io.BytesIO(file_resp.content)
                    doc.name = f"InfinityTrader_{l['mt5_id']}.zip"
                    await update.message.reply_document(document=doc, caption=f"📦 EA for MT5 ID: {l['mt5_id']}")
                else:
                    await update.message.reply_text(f"Could not retrieve file for MT5 ID {l['mt5_id']}. It might still be compiling.")
        else:
            await update.message.reply_text("Failed to fetch downloads.")

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
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("licenses", licenses_command))
    application.add_handler(CommandHandler("downloads", downloads_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    logging.info("Starting Infinity Trader Bot...")
    application.run_polling()

if __name__ == '__main__':
    main()
