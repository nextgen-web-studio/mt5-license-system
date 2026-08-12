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
from utils.api_client import register_user, get_products, create_order, create_payment, get_user

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    db_user = await get_user(str(user.id))
    if db_user:
        context.user_data['db_user_id'] = db_user['id']
        context.user_data['db_user_phone'] = db_user.get('phone')
        context.user_data['db_user_name'] = db_user.get('name')
        await update.message.reply_text(
            f"Welcome back, {db_user['name']}!\n\nPlease select an option below:",
            reply_markup=get_main_menu_keyboard()
        )
        return ConversationHandler.END
        
    # Ask for full name explicitly
    await update.message.reply_text(
        f"Welcome to Infinity Trader!\n\nPlease enter your **Full Name** to register and continue:",
        parse_mode="Markdown"
    )
    context.user_data['awaiting_name'] = True
    context.user_data['temp_telegram_id'] = user.id
    context.user_data['temp_username'] = user.username
    return ConversationHandler.END

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data.startswith("approve_") or data.startswith("reject_"):
        admin_id = os.getenv("ADMIN_TELEGRAM_ID")
        if str(update.effective_user.id) != str(admin_id):
            await query.answer("You are not authorized to perform this action.", show_alert=True)
            return
            
        action = data.split("_")[0]
        order_id = int(data.split("_")[1])
        
        from utils.api_client import approve_order, reject_order
        
        if action == "approve":
            resp = await approve_order(order_id)
            if "error" not in resp:
                await query.edit_message_text(f"✅ Order #{order_id} has been APPROVED.")
                # Notify User
                try:
                    telegram_id = resp.get("telegram_id")
                    if telegram_id:
                        msg = (
                            f"✅ *Your order has been approved.*\n\n"
                            f"Order ID: #ORD-{order_id}\n\n"
                            f"Please enter your **MT5 ID** to continue:"
                        )
                        # We need to tell the user's state to wait for mt5_id
                        # This requires setting user_data for that user. In python-telegram-bot,
                        # accessing another user's user_data can be done via context.application.user_data[user_id]
                        # but we need the internal user id. For now we will just instruct them to enter it
                        # wait, the handle_text currently expects `awaiting_mt5_id_post_approval` to be true.
                        # Let's fetch the bot application's user_data dict for that telegram_id
                        user_data = context.application.user_data.get(int(telegram_id))
                        if user_data is not None:
                            user_data['awaiting_mt5_id_post_approval'] = True
                            user_data['approved_order_id'] = order_id
                            
                        await context.bot.send_message(chat_id=telegram_id, text=msg, parse_mode="Markdown")
                except Exception as e:
                    logging.error(f"Failed to notify user: {e}")
            else:
                await query.answer(f"Failed: {resp['error']}", show_alert=True)
                
        elif action == "reject":
            resp = await reject_order(order_id)
            if "error" not in resp:
                await query.edit_message_text(f"❌ Order #{order_id} has been REJECTED.")
                try:
                    telegram_id = resp.get("telegram_id")
                    if telegram_id:
                        msg = (
                            f"❌ *Your order has been rejected.*\n\n"
                            f"Order ID: #ORD-{order_id}\n\n"
                            f"Please contact the admin if you need more information."
                        )
                        await context.bot.send_message(chat_id=telegram_id, text=msg, parse_mode="Markdown")
                except:
                    pass
            else:
    if data == "confirm_mt5_id":
        mt5_id = context.user_data.get('pending_mt5_id')
        order_id = context.user_data.get('approved_order_id')
        
        await query.edit_message_text("Generating your Lifetime License and queueing compilation. Please wait...")
        from utils.api_client import generate_license
        resp = await generate_license(order_id, mt5_id)
        
        if "error" in resp:
            await query.edit_message_text(f"❌ *Error:*\n{resp['error']}", parse_mode="Markdown")
            return
            
        await query.edit_message_text(
            f"✅ *License Generated!*\n\n"
            f"Your Lifetime EA is now compiling. We will send you the file automatically once it's ready.\n"
            f"You can also check the 'Downloads' section.",
            parse_mode="Markdown"
        )
        context.user_data['pending_mt5_id'] = None
        context.user_data['approved_order_id'] = None
        return
        
    if data == "change_mt5_id":
        context.user_data['awaiting_mt5_id_post_approval'] = True
        await query.edit_message_text("Please enter your correct **MT5 ID**:")
        return

    if data == "broker_change":
        user_id = context.user_data.get('db_user_id')
        if not user_id:
            await query.edit_message_text("Session expired. Please send /start again.")
            return
            
        msg = (
            "🔄 *Changed your broker?*\n\n"
            "If your new broker has provided you with a new MT5 account/ID, you can submit a Broker Change request.\n\n"
            "Your existing Lifetime License is currently linked to your old MT5 ID.\n"
            "The old MT5 license will be deactivated when the broker change is approved."
        )
        kb = [[InlineKeyboardButton("📩 Request Broker Change", callback_data="start_broker_change")]]
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
        return
        
    if data == "start_broker_change":
        context.user_data['awaiting_new_mt5_id'] = True
        await query.edit_message_text("Please enter your **NEW MT5 ID**:")
        return

    if data.startswith("approve_change_") or data.startswith("reject_change_"):
        admin_id = os.getenv("ADMIN_TELEGRAM_ID")
        if str(update.effective_user.id) != str(admin_id):
            await query.answer("You are not authorized to perform this action.", show_alert=True)
            return
            
        action = data.split("_")[0]
        request_id = int(data.split("_")[2])
        
        from utils.api_client import approve_broker_change, reject_broker_change
        
        if action == "approve":
            resp = await approve_broker_change(request_id)
            if "error" not in resp:
                await query.edit_message_text(f"✅ Broker Change Request #{request_id} has been APPROVED. New EA is compiling.")
                # Notify User
                try:
                    telegram_id = resp.get("telegram_id")
                    if telegram_id:
                        msg = (
                            f"✅ *Your Broker Change has been approved.*\n\n"
                            f"Your old MT5 ID association has been deactivated.\n"
                            f"Your new Lifetime EA is now compiling and will be sent here shortly."
                        )
                        await context.bot.send_message(chat_id=telegram_id, text=msg, parse_mode="Markdown")
                except Exception as e:
                    logging.error(f"Failed to notify user: {e}")
            else:
                await query.answer(f"Failed: {resp['error']}", show_alert=True)
                
        elif action == "reject":
            resp = await reject_broker_change(request_id)
            if "error" not in resp:
                await query.edit_message_text(f"❌ Broker Change Request #{request_id} has been REJECTED.")
                try:
                    telegram_id = resp.get("telegram_id")
                    if telegram_id:
                        msg = (
                            f"❌ *Broker Change Request Rejected.*\n\n"
                            f"Your existing Lifetime EA remains associated with your current MT5 ID.\n"
                            f"Please contact the admin for assistance."
                        )
                        await context.bot.send_message(chat_id=telegram_id, text=msg, parse_mode="Markdown")
                except:
                    pass
            else:
                await query.answer(f"Failed: {resp['error']}", show_alert=True)
        return

    if data == "buy_ea":
        p_type = "EA"
        products = await get_products(product_type=p_type)
        if not products:
            try:
                await query.edit_message_text(f"No {p_type} products available.", reply_markup=get_main_menu_keyboard())
            except Exception:
                pass
            return
            
        product = products[0]
        product_id = product['id']
        
        user_id = context.user_data.get('db_user_id')
        if not user_id:
            await query.edit_message_text("Session expired. Please send /start again.")
            return
            
        context.user_data['pending_product_id'] = product_id
        context.user_data['pending_p_type'] = p_type
        
        if not context.user_data.get('db_user_phone'):
            await query.edit_message_text("Please enter your **Mobile Number** to continue with the order:", parse_mode="Markdown")
            context.user_data['awaiting_phone'] = True
            return
            
        await proceed_to_order_summary(update, context)
        
    elif data == "buy_vps":
        p_type = "VPS"
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
            
        context.user_data['pending_product_id'] = product_id
        context.user_data['pending_p_type'] = p_type
        
        if not context.user_data.get('db_user_phone'):
            await query.edit_message_text("Please enter your **Mobile Number** to continue with the order:", parse_mode="Markdown")
            context.user_data['awaiting_phone'] = True
            return
            
        # If they already have a phone, proceed directly to order summary
        # We need to simulate an update passing to proceed_to_order_summary
        await proceed_to_order_summary(update, context)
        
    elif data == "free_trial":
        user_id = context.user_data.get('db_user_id')
        if not user_id:
            await query.edit_message_text("Session expired. Please send /start again.")
            return
            
        context.user_data['awaiting_trial_mt5_id'] = True
        
        trial_msg = (
            "🆓 *FREE TRIAL*\n\n"
            "Try the EA before purchasing.\n\n"
            "Please enter your **MT5 ID**:"
        )
        try:
            await query.edit_message_text(trial_msg, parse_mode="Markdown")
        except Exception:
            pass
            
    elif data == "main_menu" or data == "home":
        try:
            await query.edit_message_text("Please select an option below:", reply_markup=get_main_menu_keyboard())
        except Exception:
            pass

async def proceed_to_order_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    product_id = context.user_data.get('pending_product_id')
    p_type = context.user_data.get('pending_p_type')
    user_id = context.user_data.get('db_user_id')
    
    if not user_id:
        if update.message:
            await update.message.reply_text("Session expired. Please /start again.")
        else:
            await update.callback_query.edit_message_text("Session expired. Please /start again.")
        return
        
    order = await create_order(user_id, product_id, p_type)
    if not order or "error" in order:
        err = order.get("error", "Unknown") if order else "Failed to create order"
        msg = f"❌ *Error:*\n```\n{err}\n```"
        if update.message:
            await update.message.reply_text(msg, parse_mode="Markdown")
        else:
            await update.callback_query.edit_message_text(msg, parse_mode="Markdown")
        return
        
    products = await get_products()
    product = next((p for p in products if p['id'] == product_id), None)
    
    admin_username = os.getenv("ADMIN_USERNAME", "@infinitytrader004")
    
    summary = (
        f"📋 *ORDER SUMMARY*\n\n"
        f"Order ID: #ORD-{order['id']}\n"
        f"👤 Name: {context.user_data.get('db_user_name', 'Unknown')}\n"
        f"📱 Phone: {context.user_data.get('db_user_phone', 'Unknown')}\n"
        f"📦 Plan: {product['name'] if product else 'Unknown'}\n"
        f"💰 Price: ₹{product['price'] if product else '0'}\n\n"
        f"Status: ⏳ Pending Admin Approval\n\n"
        f"Please contact the admin to discuss and confirm your order.\n"
        f"Your EA will only be generated after admin approval."
    )
    
    keyboard = [[InlineKeyboardButton("📞 Contact Admin", url=f"https://t.me/{admin_username.lstrip('@')}开展")]]
    
    if update.message:
        await update.message.reply_text(summary, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.callback_query.edit_message_text(summary, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        
    admin_chat_id = os.getenv("ADMIN_TELEGRAM_ID")
    if admin_chat_id:
        admin_msg = (
            f"🔔 *NEW EA ORDER*\n\n"
            f"Order ID: #ORD-{order['id']}\n"
            f"👤 Customer: {context.user_data.get('db_user_name', 'Unknown')}\n"
            f"📱 Phone: {context.user_data.get('db_user_phone', 'Unknown')}\n"
            f"💬 Telegram: @{update.effective_user.username or update.effective_user.id}\n"
            f"📦 Plan: {product['name'] if product else 'Unknown'}\n"
            f"💰 Price: ₹{product['price'] if product else '0'}\n\n"
            f"Status: ⏳ PENDING ADMIN APPROVAL"
        )
        admin_kb = [
            [
                InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{order['id']}"),
                InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{order['id']}")
            ]
        ]
        try:
            await context.bot.send_message(
                chat_id=admin_chat_id,
                text=admin_msg,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(admin_kb)
            )
        except Exception as e:
            logging.error(f"Failed to notify admin: {e}")
            
    context.user_data['pending_product_id'] = None

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if context.user_data.get('awaiting_name'):
        context.user_data['awaiting_name'] = False
        tid = context.user_data.get('temp_telegram_id')
        username = context.user_data.get('temp_username')
        
        db_user = await register_user(
            telegram_id=tid, name=text, username=username, phone=None
        )
        if db_user:
            context.user_data['db_user_id'] = db_user['id']
            context.user_data['db_user_name'] = db_user['name']
            
        await update.message.reply_text(f"Thank you, {text}.\n\nPlease enter your **Mobile Number**:", parse_mode="Markdown")
        context.user_data['awaiting_phone'] = True
        return

    if context.user_data.get('awaiting_phone'):
        context.user_data['awaiting_phone'] = False
        phone = text.strip()
        user_id = context.user_data.get('db_user_id')
        
        if user_id:
            from utils.api_client import update_user_phone
            await update_user_phone(user_id, phone)
            context.user_data['db_user_phone'] = phone
            
        # Check if they were in the middle of a purchase
        if context.user_data.get('pending_product_id'):
            await proceed_to_order_summary(update, context)
            return
            
        welcome_text = (
            f"Registration complete!\n\n"
            "Please select an option below:"
        )
        await update.message.reply_text(welcome_text, reply_markup=get_main_menu_keyboard())
        return

    if context.user_data.get('awaiting_mt5_id_post_approval'):
        context.user_data['awaiting_mt5_id_post_approval'] = False
        mt5_id = text.strip()
        order_id = context.user_data.get('approved_order_id')
        
        context.user_data['pending_mt5_id'] = mt5_id
        
        confirm_msg = (
            f"Please confirm your MT5 ID:\n\n"
            f"**MT5 ID:** `{mt5_id}`\n\n"
            f"This EA will be permanently associated with this MT5 account.\n"
            f"If you later change broker and receive a different MT5 ID, you will need to submit a Broker Change request."
        )
        
        keyboard = [
            [InlineKeyboardButton("✅ Confirm MT5 ID", callback_data=f"confirm_mt5_id")],
            [InlineKeyboardButton("✏️ Change MT5 ID", callback_data=f"change_mt5_id")]
        ]
        
        await update.message.reply_text(confirm_msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if context.user_data.get('awaiting_new_mt5_id'):
        context.user_data['awaiting_new_mt5_id'] = False
        new_mt5_id = text.strip()
        
        # We need to find their active license
        user_id = context.user_data.get('db_user_id')
        tid = update.effective_user.id
        
        await update.message.reply_text("Finding your active license...")
        
        base_url = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
        import httpx
        async with httpx.AsyncClient(verify=False, follow_redirects=True) as client:
            resp = await client.get(f"{base_url}/licenses/telegram/{tid}")
            if resp.status_code == 200:
                licenses = resp.json()
                active_licenses = [l for l in licenses if l['status'] == 'active' and l.get('license_type', 'paid') != 'trial']
                if not active_licenses:
                    await update.message.reply_text("You don't have any active paid EA licenses eligible for a broker change.")
                    return
                
                # Assume they only have one lifetime license as per rules
                lic = active_licenses[0]
                old_mt5_id = lic['mt5_id']
                license_id = lic['id']
                
                from utils.api_client import request_broker_change
                change_resp = await request_broker_change(license_id, new_mt5_id)
                if "error" in change_resp:
                    await update.message.reply_text(f"❌ Failed: {change_resp['error']}")
                    return
                    
                request_id = change_resp['request_id']
                
                # Notify User
                admin_username = os.getenv("ADMIN_USERNAME", "@infinitytrader004")
                summary = (
                    f"📋 *BROKER CHANGE REQUEST*\n\n"
                    f"Old MT5 ID: `{old_mt5_id}`\n"
                    f"New MT5 ID: `{new_mt5_id}`\n"
                    f"Product: Infinity Trader EA\n"
                    f"License: Lifetime\n\n"
                    f"Status: ⏳ Pending Admin Approval\n\n"
                    f"Please contact the admin to confirm your broker change."
                )
                
                kb = [[InlineKeyboardButton("📞 Contact Admin", url=f"https://t.me/{admin_username.lstrip('@')}开展")]]
                await update.message.reply_text(summary, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
                
                # Notify Admin
                admin_chat_id = os.getenv("ADMIN_TELEGRAM_ID")
                if admin_chat_id:
                    admin_msg = (
                        f"🔄 *BROKER CHANGE REQUEST*\n\n"
                        f"👤 Customer: {context.user_data.get('db_user_name', 'Unknown')}\n"
                        f"📱 Phone: {context.user_data.get('db_user_phone', 'Unknown')}\n"
                        f"💬 Telegram: @{update.effective_user.username or update.effective_user.id}\n"
                        f"Old MT5 ID: `{old_mt5_id}`\n"
                        f"New MT5 ID: `{new_mt5_id}`\n"
                        f"License: Lifetime\n\n"
                        f"Status: ⏳ PENDING APPROVAL"
                    )
                    admin_kb = [
                        [
                            InlineKeyboardButton("✅ APPROVE CHANGE", callback_data=f"approve_change_{request_id}"),
                            InlineKeyboardButton("❌ REJECT CHANGE", callback_data=f"reject_change_{request_id}")
                        ]
                    ]
                    try:
                        await context.bot.send_message(
                            chat_id=admin_chat_id,
                            text=admin_msg,
                            parse_mode="Markdown",
                            reply_markup=InlineKeyboardMarkup(admin_kb)
                        )
                    except Exception as e:
                        logging.error(f"Failed to notify admin: {e}")
            else:
                await update.message.reply_text("Failed to fetch your licenses.")
        return

    if context.user_data.get('awaiting_trial_mt5_id'):
        context.user_data['awaiting_trial_mt5_id'] = False
        mt5_id = text.strip()
        user_id = context.user_data.get('db_user_id')
        tid = update.effective_user.id
        
        from utils.api_client import request_free_trial
        
        await update.message.reply_text("Checking trial eligibility...")
        
        resp = await request_free_trial(tid, mt5_id)
        
        if "error" in resp:
            err_text = str(resp['error'])[:2000]
            await update.message.reply_text(f"❌ *Trial Request Failed:*\n\n{err_text}", parse_mode="Markdown")
            return
            
        success_msg = (
            f"✅ *{resp.get('message', 'Trial Approved!')}*\n\n"
            f"MT5 ID: `{mt5_id}`\n"
            f"Duration: {resp.get('duration_days', 2)} Days\n"
            f"Expires: {resp.get('expiry_date', 'Unknown')}\n\n"
            "⚙️ Please wait 1-2 minutes while we compile your trial EA. We will send the file here automatically."
        )
        await update.message.reply_text(success_msg, parse_mode="Markdown")
        return

    await update.message.reply_text("Please use the /start menu to select an option.")

async def mock_webhook(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # For testing only: mimics Razorpay webhook to activate license
    if not context.args:
        await update.message.reply_text("Usage: /mock_webhook <order_id>")
        return
        
    order_id = context.args[0]
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
    
    await update.message.reply_text(f"Mocking payment for Order #{order_id}...")
    
    # 1. Update order status to paid
    async with httpx.AsyncClient(verify=False) as client:
        await client.get(f"{base_url}/orders/{order_id}/mock-pay")
        
    # 2. Get the order to get the mt5_id
    async with httpx.AsyncClient(verify=False) as client:
        # We need a quick way to get the order, but the webhook logic hits start-fulfillment directly.
        # Let's hit the fulfillment directly with a dummy mt5_id (it will use the order's mt5_id internally in the new flow, actually we need to pass the MT5 ID in the request if the backend requires it).
        pass
        
    # We can just construct a fake Razorpay webhook payload and POST it to /payments/webhook
    payload = {
        "event": "payment_link.paid",
        "payload": {
            "payment_link": {
                "entity": {
                    "reference_id": f"order_{order_id}"
                }
            },
            "payment": {
                "entity": {
                    "id": "pay_mock123"
                }
            }
        }
    }
    
    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.post(f"{base_url}/payments/webhook", json=payload)
        if resp.status_code == 200:
            await update.message.reply_text("Webhook processed successfully! License should be compiling now.")
        else:
            await update.message.reply_text(f"Webhook error: {resp.text}")

async def licenses_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tid = str(update.effective_user.id)
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
    
    await update.message.reply_text("Fetching your active licenses...")
    
    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.get(f"{base_url}/licenses/telegram/{tid}")
        if resp.status_code == 200:
            licenses = resp.json()
            if not licenses:
                await update.message.reply_text("You don't have any active EA licenses.")
                return
                
            text = "🔑 *Your Licenses:*\n\n"
            for l in licenses:
                status_icon = "✅" if l['status'] == 'active' else "⏳" if l['status'] == 'generating' else "❌"
                expiry = l['expiry_date'].split('T')[0] if l['expiry_date'] else "Lifetime"
                text += f"{status_icon} *MT5 ID:* `{l['mt5_id']}`\n"
                text += f"   Type: {l.get('license_type', 'Paid').title()}\n"
                text += f"   Status: {l['status'].title()}\n"
                text += f"   Expires: {expiry}\n\n"
            
            await update.message.reply_text(text, parse_mode="Markdown")
        else:
            await update.message.reply_text("Failed to fetch licenses.")

async def downloads_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tid = str(update.effective_user.id)
        
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
    await update.message.reply_text("Fetching your downloads...")
    
    async with httpx.AsyncClient(verify=False, follow_redirects=True) as client:
        resp = await client.get(f"{base_url}/licenses/telegram/{tid}")
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
                    doc.name = f"InfinityTrader_{l['mt5_id']}.ex5"
                    await update.message.reply_document(document=doc, caption=f"📦 EA for MT5 ID: {l['mt5_id']}")
                else:
                    await update.message.reply_text(f"Could not retrieve file for MT5 ID {l['mt5_id']}. It might still be compiling.")
        else:
            await update.message.reply_text("Failed to fetch downloads.")

import json

class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")
        
    def do_POST(self):
        if self.path == "/internal/delivery":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                license_id = data.get('license_id')
                if license_id:
                    # We need to trigger an async task to send the document
                    # Since we are in a sync thread, we use asyncio.run_coroutine_threadsafe if we had the event loop
                    # But the simplest way is to use a background thread and requests or httpx to fetch the document
                    # and send it via Telegram API directly.
                    threading.Thread(target=self.send_delivery, args=(license_id,), daemon=True).start()
                    
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status":"ok"}')
            except Exception as e:
                logging.error(f"Internal delivery error: {e}")
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"Error")
        else:
            self.send_response(404)
            self.end_headers()

    def send_delivery(self, license_id):
        import asyncio
        asyncio.run(self.async_send_delivery(license_id))
        
    async def async_send_delivery(self, license_id):
        base_url = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        try:
            async with httpx.AsyncClient(verify=False, follow_redirects=True) as client:
                resp = await client.get(f"{base_url}/licenses/{license_id}/delivery-info")
                if resp.status_code == 200:
                    info = resp.json()
                    chat_id = info.get("telegram_id")
                    mt5_id = info.get("mt5_id")
                    download_url = info.get("download_url")
                    
                    if chat_id and download_url:
                        # Send file via telegram
                        # Since it's a URL to a zip, we can just send the URL or download and send
                        # Supabase public URLs can be sent as documents to Telegram directly!
                        msg = f"✅ *Compilation Complete!*\n\nYour EA for MT5 ID `{mt5_id}` is ready."
                        await client.post(
                            f"https://api.telegram.org/bot{token}/sendMessage",
                            json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}
                        )
                        
                        file_resp = await client.get(download_url)
                        if file_resp.status_code == 200:
                            files = {
                                "document": (f"InfinityTrader_{mt5_id}.ex5", file_resp.content, "application/octet-stream")
                            }
                            data = {
                                "chat_id": chat_id,
                                "caption": f"📦 InfinityTrader_{mt5_id}.ex5"
                            }
                            resp = await client.post(
                                f"https://api.telegram.org/bot{token}/sendDocument",
                                data=data,
                                files=files
                            )
                            if resp.status_code != 200:
                                err_msg = f"Failed to attach file. Telegram API Error: {resp.text}"
                                await client.post(
                                    f"https://api.telegram.org/bot{token}/sendMessage",
                                    json={"chat_id": chat_id, "text": err_msg}
                                )
                                logging.error(err_msg)
                        else:
                            logging.error(f"Failed to download EX5: {file_resp.status_code}")
        except Exception as e:
            logging.error(f"Delivery failed: {e}")

def start_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), DummyHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    logging.info(f"Webhook server started on port {port}")

from telegram import BotCommand

async def post_init(application):
    commands = [
        BotCommand("start", "Start the bot and see the main menu"),
        BotCommand("licenses", "View your active MT5 licenses"),
        BotCommand("downloads", "Download your compiled EA files")
    ]
    await application.bot.set_my_commands(commands)

def main():
    start_dummy_server()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    application = ApplicationBuilder().token(token).post_init(post_init).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("licenses", licenses_command))
    application.add_handler(CommandHandler("downloads", downloads_command))
    application.add_handler(CommandHandler("mock_webhook", mock_webhook))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    logging.info("Starting Infinity Trader Bot...")
    application.run_polling()

if __name__ == '__main__':
    main()
