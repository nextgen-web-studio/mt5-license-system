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
from utils.api_client import register_user, get_products, create_order, get_user

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
    
    if data.startswith("approve_") and not data.startswith("approve_change_"):
        admin_id = os.getenv("ADMIN_CHAT_ID")
        if str(update.effective_user.id) != str(admin_id):
            await query.answer("You are not authorized to perform this action.", show_alert=True)
            return
            
        order_id = int(data.split("_")[1])
        
        from utils.api_client import approve_order, reject_order
        
        resp = await approve_order(order_id)
        if "error" not in resp:
            kb = [[InlineKeyboardButton("💳 Create Installment Arrangement", callback_data=f"create_installment_{order_id}")]]
            await query.edit_message_text(f"✅ Order #{order_id} has been APPROVED.\n\nThe customer has been asked to provide their MT5 ID.", reply_markup=InlineKeyboardMarkup(kb))
            
            # Notify Customer
            try:
                telegram_id = resp.get("telegram_id")
                if telegram_id:
                    msg = (
                        f"✅ *YOUR ORDER HAS BEEN APPROVED*\n\n"
                        f"Your EA Lifetime License order (ORD-{order_id}) has been approved.\n\n"
                        f"Please enter your **MT5 ID** to continue with license generation:"
                    )
                    await context.bot.send_message(chat_id=telegram_id, text=msg, parse_mode="Markdown")
                    # We can't set user_data of another user directly without a persistence backend that shares state perfectly,
                    # but python-telegram-bot allows context.application.user_data[int(telegram_id)] if memory is shared.
                    # We will update the user data for the specific user.
                    context.application.user_data[int(telegram_id)]['awaiting_approved_mt5_id'] = True
                    context.application.user_data[int(telegram_id)]['pending_order_id'] = order_id
            except Exception as e:
                logging.error(f"Failed to notify user: {e}")
        else:
            await query.answer(f"Failed: {resp['error']}", show_alert=True)
        return

    if data.startswith("reject_") and not data.startswith("reject_change_"):
        admin_id = os.getenv("ADMIN_CHAT_ID")
        if str(update.effective_user.id) != str(admin_id):
            await query.answer("You are not authorized to perform this action.", show_alert=True)
            return
            
        order_id = int(data.split("_")[1])
        from utils.api_client import reject_order
        
        resp = await reject_order(order_id)
        if "error" not in resp:
            await query.edit_message_text(f"❌ Order #{order_id} has been REJECTED.")
            try:
                telegram_id = resp.get("telegram_id")
                if telegram_id:
                    msg = (
                        f"❌ *ORDER NOT APPROVED*\n\n"
                        f"Your EA order (ORD-{order_id}) has not been approved by the administrator.\n\n"
                        f"Please contact support for more information."
                    )
                    await context.bot.send_message(chat_id=telegram_id, text=msg, parse_mode="Markdown")
            except:
                pass
        else:
            await query.answer(f"Failed: {resp['error']}", show_alert=True)
        return

    if data.startswith("create_installment_"):
        admin_id = os.getenv("ADMIN_CHAT_ID")
        if str(update.effective_user.id) != str(admin_id):
            await query.answer("You are not authorized to perform this action.", show_alert=True)
            return
            
        order_id = int(data.split("_")[2])
        context.user_data['install_order_id'] = order_id
        context.user_data['install_step'] = 'total_amount'
        
        await query.edit_message_text(f"💳 *Create Installment Arrangement for Order #{order_id}*\n\nPlease enter the **Total agreed amount** (e.g. 20000):", parse_mode="Markdown")
        return

    if data.startswith("manage_installment_"):
        admin_id = os.getenv("ADMIN_CHAT_ID")
        if str(update.effective_user.id) != str(admin_id):
            await query.answer("You are not authorized to perform this action.", show_alert=True)
            return
            
        order_id = int(data.split("_")[2])
        base_url = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
        import httpx
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.get(f"{base_url}/installments/admin/{order_id}")
            if resp.status_code == 200:
                data_json = resp.json()
                msg = (
                    f"💳 *INSTALLMENT*\n\n"
                    f"Order: ORD-{order_id}\n\n"
                    f"MT5 ID: `{data_json['mt5_id']}`\n\n"
                    f"Total: ₹{data_json['total_amount']:,.0f}\n"
                    f"Installment: ₹{data_json['installment_amount']:,.0f}\n\n"
                    f"Paid: ₹{data_json['amount_paid']:,.0f}\n"
                    f"Remaining: ₹{data_json['amount_remaining']:,.0f}\n\n"
                    f"Progress:\n{data_json['installments_paid']}/{data_json['installment_count']}\n\n"
                    f"License:\n{data_json['license_status'].title()}\n\n"
                    f"Expires:\n{data_json['license_expiry'].split('T')[0] if data_json['license_expiry'] else 'Never'}"
                )
                kb = [
                    [InlineKeyboardButton("Mark Payment Received", callback_data=f"mark_install_paid_{order_id}")],
                    [InlineKeyboardButton("Payment History", callback_data=f"install_history_{order_id}")],
                    [InlineKeyboardButton("Disable Arrangement", callback_data=f"disable_install_{order_id}")]
                ]
                await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
            else:
                await query.answer("Installment arrangement not found.", show_alert=True)
        return

    if data.startswith("mark_install_paid_"):
        admin_id = os.getenv("ADMIN_CHAT_ID")
        if str(update.effective_user.id) != str(admin_id):
            await query.answer("You are not authorized to perform this action.", show_alert=True)
            return
            
        order_id = int(data.split("_")[3])
        # In a real app we'd confirm, but for now we'll just process it
        base_url = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
        import httpx
        async with httpx.AsyncClient(verify=False) as client:
            # First fetch installment_amount
            resp = await client.get(f"{base_url}/installments/admin/{order_id}")
            if resp.status_code == 200:
                amount = resp.json()['installment_amount']
                pay_resp = await client.post(f"{base_url}/installments/pay", json={"order_id": order_id, "amount": amount})
                if pay_resp.status_code == 200:
                    await query.edit_message_text(f"✅ Payment of ₹{amount:,.0f} recorded for Order #{order_id}.\n\nLicense extended and compilation queued.")
                else:
                    await query.answer("Failed to record payment.", show_alert=True)
        return

    if data == "license_details":
        await render_licenses(update, context)
        return
        
    if data.startswith("view_license_"):
        lic_id = int(data.split("_")[2])
        tid = str(update.effective_user.id)
        base_url = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
        
        async with httpx.AsyncClient(verify=False, follow_redirects=True) as client:
            resp = await client.get(f"{base_url}/licenses/telegram/{tid}")
            if resp.status_code == 200:
                licenses = resp.json()
                lic = next((l for l in licenses if l['id'] == lic_id), None)
                if lic:
                    status_icon = "🟢" if lic['status'] == 'active' else "🔴" if lic['status'] == 'expired' else "⚫"
                    expiry = lic['expiry_date'].split('T')[0] if lic['expiry_date'] else "Never"
                    activated = lic['purchase_date'].split('T')[0] if lic['purchase_date'] else "Unknown"
                    ltype = "Trial" if lic.get('license_type') == 'trial' else "Lifetime"
                    
                    text = (
                        f"📋 *LICENSE DETAILS*\n\n"
                        f"MT5 ID: `{lic['mt5_id']}`\n\n"
                        f"Type:\n{ltype}\n\n"
                        f"Status:\n{status_icon} {lic['status'].title()}\n\n"
                        f"Expiry:\n{expiry}"
                    )
                    
                    kb = []
                    if ltype == "Lifetime":
                        kb.append([InlineKeyboardButton("🔄 Broker Change", callback_data="broker_change")])
                    kb.append([InlineKeyboardButton("🏠 Home", callback_data="home")])
                    
                    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
                    return
        await query.edit_message_text("❌ License not found.")
        return

    if data == "my_orders":
        await render_orders(update, context)
        return
        
    if data == "downloads":
        await render_downloads(update, context)
        return
        
    if data.startswith("download_ea_"):
        parts = data.split("_")
        lic_id = int(parts[2])
        mt5_id = parts[3]
        base_url = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
        
        await query.edit_message_text(f"⏳ Retrieving your EA file for MT5 ID {mt5_id}...")
        
        async with httpx.AsyncClient(verify=False, follow_redirects=True) as client:
            # We add a security check: ensure the license actually belongs to the user by querying their licenses first
            tid = str(update.effective_user.id)
            resp = await client.get(f"{base_url}/licenses/telegram/{tid}")
            if resp.status_code == 200:
                licenses = resp.json()
                if not any(l['id'] == lic_id for l in licenses):
                    await query.edit_message_text("❌ Access denied. This file does not belong to you.")
                    return
            else:
                await query.edit_message_text("❌ Authorization failed.")
                return
                
            download_url = f"{base_url}/licenses/{lic_id}/download"
            file_resp = await client.get(download_url)
            if file_resp.status_code == 200:
                import io
                doc = io.BytesIO(file_resp.content)
                doc.name = f"InfinityTrader_{mt5_id}.ex5"
                await query.message.reply_document(document=doc, caption=f"📦 Here is your EA for MT5 ID: {mt5_id}")
                await query.edit_message_text("✅ File sent below!")
            else:
                await query.edit_message_text(f"❌ Could not retrieve file for MT5 ID {mt5_id}.\nIt might still be compiling or there is an issue with the storage.")
        return
    if data == "broker_change":
        user_id = context.user_data.get('db_user_id')
        tid = update.effective_user.id
        if not user_id:
            await query.edit_message_text("Session expired. Please send /start again.")
            return
            
        await query.edit_message_text("Fetching your active licenses...")
        base_url = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
        import httpx
        async with httpx.AsyncClient(verify=False, follow_redirects=True) as client:
            resp = await client.get(f"{base_url}/licenses/telegram/{tid}")
            
        if resp.status_code != 200:
            await query.edit_message_text("Failed to fetch your licenses. Please contact support.")
            return
            
        licenses = resp.json()
        active_licenses = [lic for lic in licenses if lic['status'] == 'active' and lic.get('license_type') == 'paid']
        
        if not active_licenses:
            await query.edit_message_text("You do not have any active Lifetime licenses eligible for a broker change.")
            return
            
        if len(active_licenses) == 1:
            lic = active_licenses[0]
            context.user_data['bc_license_id'] = lic['id']
            context.user_data['bc_old_mt5_id'] = lic['mt5_id']
            context.user_data['bc_old_broker'] = lic.get('broker', 'Unknown')
            
            context.user_data['awaiting_broker_change_mt5_id'] = True
            await query.edit_message_text(
                f"🔄 *Broker Change*\n\nSelected License:\nMT5 ID: `{lic['mt5_id']}`\nBroker: `{lic.get('broker', 'Unknown')}`\n\nPlease enter your **NEW MT5 ID**:",
                parse_mode="Markdown"
            )
            return
            
        msg = (
            "🔄 *BROKER CHANGE*\n\n"
            "You have multiple active EA licenses.\n"
            "Please select the license for which you want to change the broker."
        )
        kb = []
        for lic in active_licenses:
            broker_name = lic.get('broker', 'Unknown')
            kb.append([InlineKeyboardButton(f"🔄 MT5 {lic['mt5_id']} - {broker_name}", callback_data=f"bc_select_{lic['id']}_{lic['mt5_id']}_{broker_name}")])
        kb.append([InlineKeyboardButton("⬅️ Back", callback_data="main_menu")])
        
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
        return
        
    if data.startswith("bc_select_"):
        parts = data.split("_")
        lic_id = parts[2]
        old_mt5 = parts[3]
        old_broker = "_".join(parts[4:])
        
        context.user_data['bc_license_id'] = lic_id
        context.user_data['bc_old_mt5_id'] = old_mt5
        context.user_data['bc_old_broker'] = old_broker
        
        context.user_data['awaiting_broker_change_mt5_id'] = True
        await query.edit_message_text(
            f"🔄 *Broker Change*\n\nSelected License:\nMT5 ID: `{old_mt5}`\nBroker: `{old_broker}`\n\nPlease enter your **NEW MT5 ID**:",
            parse_mode="Markdown"
        )
        return

    if data == "cancel_broker_change":
        context.user_data['bc_license_id'] = None
        context.user_data['bc_new_mt5_id'] = None
        context.user_data['bc_new_broker'] = None
        await query.edit_message_text("❌ Broker change request cancelled.")
        return
        
    if data == "submit_broker_change":
        lic_id = context.user_data.get('bc_license_id')
        new_mt5 = context.user_data.get('bc_new_mt5_id')
        new_broker = context.user_data.get('bc_new_broker')
        tid = update.effective_user.id
        
        if not lic_id or not new_mt5 or not new_broker:
            await query.edit_message_text("Session data lost. Please try again.")
            return
            
        await query.edit_message_text("Submitting your request...")
        from utils.api_client import request_broker_change
        resp = await request_broker_change(lic_id, new_mt5, new_broker, tid)
        
        if "error" in resp:
            await query.edit_message_text(f"❌ Failed: {resp['error']}")
            return
            
        request_id = resp['request_id']
        
        # Notify Admin
        admin_chat_id = os.getenv("ADMIN_CHAT_ID")
        if admin_chat_id:
            admin_msg = (
                f"🔄 *BROKER CHANGE REQUEST*\n\n"
                f"Request ID: BCR-{request_id}\n"
                f"Customer: {context.user_data.get('db_user_name', 'Unknown')}\n"
                f"Telegram ID: `{tid}`\n\n"
                f"Selected License ID: {lic_id}\n"
                f"Old MT5 ID: `{context.user_data.get('bc_old_mt5_id')}`\n"
                f"Old Broker: `{context.user_data.get('bc_old_broker')}`\n\n"
                f"Requested Change:\n"
                f"New MT5 ID: `{new_mt5}`\n"
                f"New Broker: `{new_broker}`\n\n"
                f"Status: Pending Admin Approval"
            )
            kb = [
                [InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_change_{request_id}"),
                 InlineKeyboardButton("❌ REJECT", callback_data=f"reject_change_{request_id}")]
            ]
            try:
                await context.bot.send_message(chat_id=admin_chat_id, text=admin_msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
            except Exception as e:
                logging.error(f"Failed to notify admin: {e}")
                
        await query.edit_message_text("✅ Your broker change request has been submitted and is pending admin approval.")
        
        # Clear state
        context.user_data['bc_license_id'] = None
        context.user_data['bc_new_mt5_id'] = None
        context.user_data['bc_new_broker'] = None
        return

    if data.startswith("approve_change_") or data.startswith("reject_change_"):
        admin_id = os.getenv("ADMIN_CHAT_ID")
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

    if data.startswith("admin_edit_"):
        admin_id = os.getenv("ADMIN_CHAT_ID")
        if str(update.effective_user.id) != str(admin_id):
            await query.answer("Unauthorized.", show_alert=True)
            return
            
        setting_key = data.replace("admin_edit_", "")
        context.user_data['awaiting_admin_setting_key'] = setting_key
        await query.edit_message_text(f"Please enter the new value for `{setting_key}`:", parse_mode="Markdown")
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
    
    from utils.api_client import get_settings
    settings = await get_settings()
    admin_username = settings.get("support_username", os.getenv("ADMIN_USERNAME", "@infinitytrader004"))
    if not admin_username.startswith("@"):
        admin_username = f"@{admin_username}"
    
    summary = (
        f"📋 *ORDER SUMMARY*\n\n"
        f"Order ID: #ORD-{order['id']}\n"
        f"👤 Name: {context.user_data.get('db_user_name', 'Unknown')}\n"
        f"📱 Phone: {context.user_data.get('db_user_phone', 'Unknown')}\n"
        f"📦 Plan: {product['name'] if product else 'Unknown'}\n\n"
        f"Status: ⏳ Pending Admin Approval\n\n"
        f"Please contact the admin to discuss and confirm your order.\n"
        f"Your EA will only be generated after admin approval."
    )
    
    keyboard = [[InlineKeyboardButton("📞 Contact Admin", url=f"https://t.me/{admin_username.lstrip('@')}")] ]
    
    if update.message:
        await update.message.reply_text(summary, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.callback_query.edit_message_text(summary, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        
    admin_chat_id = os.getenv("ADMIN_CHAT_ID")
    if admin_chat_id:
        admin_msg = (
            f"🆕 *NEW EA ORDER*\n\n"
            f"Order ID: ORD-{order['id']}\n"
            f"Customer Name: {context.user_data.get('db_user_name', 'Unknown')}\n"
            f"Phone: {context.user_data.get('db_user_phone', 'Unknown')}\n"
            f"Telegram ID: `{update.effective_user.id}`\n"
            f"Plan: {product['name'] if product else 'Unknown'}\n"
            f"Status: Pending Admin Approval"
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
    
    install_step = context.user_data.get('install_step')
    if install_step:
        order_id = context.user_data.get('install_order_id')
        if install_step == 'total_amount':
            context.user_data['install_total_amount'] = float(text)
            context.user_data['install_step'] = 'installment_amount'
            await update.message.reply_text("Please enter the **Installment amount** (e.g. 5000):", parse_mode="Markdown")
            return
        elif install_step == 'installment_amount':
            context.user_data['install_amount'] = float(text)
            context.user_data['install_step'] = 'installments'
            await update.message.reply_text("Please enter the **Number of installments** (e.g. 4):", parse_mode="Markdown")
            return
        elif install_step == 'installments':
            context.user_data['install_count'] = int(text)
            context.user_data['install_step'] = 'first_payment'
            await update.message.reply_text("Please enter the **First payment amount** (e.g. 5000):", parse_mode="Markdown")
            return
        elif install_step == 'first_payment':
            context.user_data['install_first_payment'] = float(text)
            context.user_data['install_step'] = 'license_duration'
            await update.message.reply_text("Please enter the **License duration per payment in days** (e.g. 35):", parse_mode="Markdown")
            return
        elif install_step == 'license_duration':
            duration = int(text)
            context.user_data['install_step'] = None
            
            payload = {
                "order_id": order_id,
                "total_amount": context.user_data['install_total_amount'],
                "installment_amount": context.user_data['install_amount'],
                "installment_count": context.user_data['install_count'],
                "first_payment_amount": context.user_data['install_first_payment'],
                "license_period_days": duration
            }
            
            base_url = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
            import httpx
            async with httpx.AsyncClient(verify=False) as client:
                resp = await client.post(f"{base_url}/installments/create", json=payload)
                if resp.status_code == 200:
                    await update.message.reply_text("✅ Installment arrangement created and first payment recorded!")
                else:
                    await update.message.reply_text(f"❌ Error creating arrangement: {resp.text}")
            return

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

    if context.user_data.get('awaiting_approved_mt5_id'):
        context.user_data['awaiting_approved_mt5_id'] = False
        mt5_id = text.strip()
        order_id = context.user_data.get('pending_order_id')
        
        await update.message.reply_text("🔄 Verifying your MT5 ID...")
        await update.message.reply_text("🔐 Creating your Lifetime License...\n📦 Preparing your EA...\n⚙️ Compilation started...")
        
        from utils.api_client import generate_license
        resp = await generate_license(order_id, mt5_id)
        
        if "error" in resp:
            await update.message.reply_text(f"❌ *Error:*\n{resp['error']}", parse_mode="Markdown")
            return
            
        success_msg = (
            f"✅ *Compilation Complete!*\n\n"
            f"Your personalized EA is ready.\n\n"
            f"MT5 ID: `{mt5_id}`\n"
            f"License: Lifetime\n"
            f"Status: Active\n\n"
            f"The compiled EA file is attached below."
        )
        await update.message.reply_text(success_msg, parse_mode="Markdown")
        
        context.user_data['pending_order_id'] = None
        return
        
    setting_key = context.user_data.get('awaiting_admin_setting_key')
    if setting_key:
        context.user_data['awaiting_admin_setting_key'] = None
        new_val = text.strip()
        
        from utils.api_client import update_setting
        success = await update_setting(setting_key, new_val)
        if success:
            await update.message.reply_text(f"✅ Setting `{setting_key}` updated to `{new_val}`.", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"❌ Failed to update `{setting_key}`.")
        return

    if context.user_data.get('awaiting_broker_change_mt5_id'):
        context.user_data['awaiting_broker_change_mt5_id'] = False
        new_mt5_id = text.strip()
        context.user_data['bc_new_mt5_id'] = new_mt5_id
        
        context.user_data['awaiting_broker_change_broker_name'] = True
        await update.message.reply_text("Please enter your **NEW BROKER NAME**:", parse_mode="Markdown")
        return

    if context.user_data.get('awaiting_broker_change_broker_name'):
        context.user_data['awaiting_broker_change_broker_name'] = False
        new_broker = text.strip()
        
        lic_id = context.user_data.get('bc_license_id')
        old_mt5 = context.user_data.get('bc_old_mt5_id')
        old_broker = context.user_data.get('bc_old_broker')
        new_mt5_id = context.user_data.get('bc_new_mt5_id')
        
        msg = (
            "📋 *BROKER CHANGE REQUEST*\n\n"
            f"Current MT5 ID: `{old_mt5}`\n"
            f"Current Broker: `{old_broker}`\n\n"
            f"New MT5 ID: `{new_mt5_id}`\n"
            f"New Broker: `{new_broker}`\n\n"
            "License: Lifetime\n"
            "Status: Pending Admin Approval"
        )
        
        context.user_data['bc_new_broker'] = new_broker
        
        kb = [
            [InlineKeyboardButton("📨 Submit Request", callback_data="submit_broker_change")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_broker_change")]
        ]
        
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
        return

    if context.user_data.get('awaiting_trial_mt5_id'):
        context.user_data['awaiting_trial_mt5_id'] = False
        mt5_id = text.strip()
        user_id = context.user_data.get('db_user_id')
        tid = str(update.effective_user.id)
        
        from utils.api_client import request_free_trial
        
        await update.message.reply_text("Checking trial eligibility...")
        
        resp = await request_free_trial(tid, mt5_id)
        
        if "error" in resp:
            if resp['error'] == "ALREADY_CLAIMED":
                import datetime
                month_name = datetime.datetime.now().strftime("%B %Y")
                err_msg = (
                    f"⚠️ *FREE TRIAL ALREADY USED*\n\n"
                    f"You have already used your free trial for this month.\n\n"
                    f"Free Trial:\n3 Days\n\n"
                    f"Trial Used:\n{month_name}\n\n"
                    f"You can request another free trial next month."
                )
                kb = [[InlineKeyboardButton("🏠 Home", callback_data="home")]]
                await update.message.reply_text(err_msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
            else:
                err_text = str(resp['error'])[:2000]
                await update.message.reply_text(f"❌ *Trial Request Failed:*\n\n{err_text}", parse_mode="Markdown")
            return
            
        success_msg = (
            f"🎁 *FREE TRIAL ACTIVATED*\n\n"
            f"MT5 ID: `{mt5_id}`\n\n"
            f"Trial Duration: 3 Days\n\n"
            f"Expires:\n{resp.get('expiry_date', 'Unknown')}\n\n"
            f"You may use the trial once this calendar month.\n\n"
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

async def render_licenses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tid = str(update.effective_user.id)
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
    
    msg_target = update.message if update.message else update.callback_query
    await msg_target.reply_text("Fetching your licenses...")
    
    async with httpx.AsyncClient(verify=False, follow_redirects=True) as client:
        resp = await client.get(f"{base_url}/licenses/telegram/{tid}")
        if resp.status_code == 200:
            licenses = resp.json()
            home_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Home", callback_data="home")]])
            if not licenses:
                await msg_target.reply_text("❌ *No licenses found.*\n\nYou don't currently have any EA licenses.", parse_mode="Markdown", reply_markup=home_kb)
                return
                
            if len(licenses) == 1:
                l = licenses[0]
                status_icon = "🟢" if l['status'] == 'active' else "🔴" if l['status'] == 'expired' else "⚫"
                expiry = l['expiry_date'].split('T')[0] if l['expiry_date'] else "Never"
                activated = l['purchase_date'].split('T')[0] if l['purchase_date'] else "Unknown"
                ltype = "Trial" if l.get('license_type') == 'trial' else "Lifetime"
                
                text = (
                    f"🔐 *LICENSE DETAILS*\n\n"
                    f"MT5 ID: `{l['mt5_id']}`\n"
                    f"License Type: {ltype}\n"
                    f"Status: {status_icon} {l['status'].title()}\n"
                    f"Activated: {activated}\n"
                    f"Expires: {expiry}"
                )
                await msg_target.reply_text(text, parse_mode="Markdown", reply_markup=home_kb)
                return
                
            # Multiple licenses
            text = "📋 *Your Licenses:*\n\nPlease select a license below to view details or manage it."
            kb = []
            for idx, l in enumerate(licenses, 1):
                status_icon = "🟢" if l['status'] == 'active' else "🔴" if l['status'] == 'expired' else "⚫"
                ltype = "Trial" if l.get('license_type') == 'trial' else "Lifetime"
                button_text = f"MT5 {l['mt5_id']} — {ltype} — {status_icon} {l['status'].title()}"
                
                kb.append([InlineKeyboardButton(button_text, callback_data=f"view_license_{l['id']}")])
                
            kb.append([InlineKeyboardButton("🏠 Home", callback_data="home")])
            await msg_target.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
        else:
            await msg_target.reply_text("❌ Unable to load your licenses right now.\nPlease try again or contact support.")

async def render_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tid = str(update.effective_user.id)
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
    
    msg_target = update.message if update.message else update.callback_query
    await msg_target.reply_text("Fetching your orders...")
    
    async with httpx.AsyncClient(verify=False, follow_redirects=True) as client:
        resp = await client.get(f"{base_url}/orders/telegram/{tid}")
        if resp.status_code == 200:
            orders = resp.json()
            home_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Home", callback_data="home")]])
            if not orders:
                await msg_target.reply_text("📭 *You don't have any orders yet.*", parse_mode="Markdown", reply_markup=home_kb)
                return
                
            text = "🧾 *MY ORDERS*\n\n"
            for order in orders:
                status = order['status']
                if status == "approved" or "approved" in status:
                    status_display = "✅ Approved"
                elif status == "pending_admin_approval":
                    status_display = "⏳ Pending Admin Approval"
                elif status == "rejected":
                    status_display = "❌ Rejected"
                else:
                    status_display = f"ℹ️ {status.replace('_', ' ').title()}"
                    
                created = order['created_at'].split('T')[0] if order.get('created_at') else "Unknown"
                price_str = f"₹{order.get('price', 0):,.0f}" if order.get('price') else "Free"
                
                text += (
                    f"Order #ORD-{order['id']}\n"
                    f"Plan: {order.get('product_name', 'Unknown')}\n"
                    f"Price: {price_str}\n"
                    f"Status: {status_display}\n"
                    f"Created: {created}\n\n"
                )
            
            await msg_target.reply_text(text, parse_mode="Markdown", reply_markup=home_kb)
        else:
            await msg_target.reply_text("❌ Unable to load your orders right now.\nPlease try again or contact support.")

async def orders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await render_orders(update, context)

async def licenses_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await render_licenses(update, context)

async def render_downloads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tid = str(update.effective_user.id)
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
    msg_target = update.message if update.message else update.callback_query
    await msg_target.reply_text("Fetching your downloads...")
    
    async with httpx.AsyncClient(verify=False, follow_redirects=True) as client:
        resp = await client.get(f"{base_url}/licenses/telegram/{tid}")
        if resp.status_code == 200:
            licenses = resp.json()
            active_licenses = [l for l in licenses if l['status'] == 'active']
            home_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Home", callback_data="home")]])
            if not active_licenses:
                await msg_target.reply_text("❌ *No files available.*\n\nYou don't have any active EA licenses to download.", parse_mode="Markdown", reply_markup=home_kb)
                return
                
            text = "📥 *YOUR DOWNLOADS*\n\n"
            kb = []
            
            for idx, l in enumerate(active_licenses, 1):
                ltype = "Trial" if l.get('license_type') == 'trial' else "Lifetime"
                gen = l['purchase_date'].split('T')[0] if l['purchase_date'] else "Unknown"
                
                text += (
                    f"{idx}️⃣ InfinityTrader_{l['mt5_id']}.ex5\n"
                    f"   MT5 ID: {l['mt5_id']}\n"
                    f"   License: {ltype}\n"
                    f"   Generated: {gen}\n\n"
                )
                
                kb.append([InlineKeyboardButton(f"⬇️ Download EA (MT5 {l['mt5_id']})", callback_data=f"download_ea_{l['id']}_{l['mt5_id']}")])
                
            kb.append([InlineKeyboardButton("🏠 Home", callback_data="home")])
            await msg_target.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
        else:
            await msg_target.reply_text("❌ Unable to load your downloads right now.\nPlease try again or contact support.")

async def downloads_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await render_downloads(update, context)

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

async def myid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Your Telegram Chat ID is: `{update.effective_user.id}`", parse_mode="Markdown")

async def admintest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = os.getenv("ADMIN_CHAT_ID")
    if str(update.effective_user.id) != str(admin_id):
        return
    await update.message.reply_text("✅ Admin notification test successful")

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = os.getenv("ADMIN_CHAT_ID")
    if str(update.effective_user.id) != str(admin_id):
        await update.message.reply_text("❌ You are not authorized to access the admin panel.")
        return
        
    from utils.api_client import get_settings
    settings = await get_settings()
    
    msg = (
        "⚙️ *Admin Configuration Panel*\n\n"
        f"Free Trial Enabled: `{settings.get('free_trial_enabled', 'Not Set')}`\n"
        f"Trial Duration (Days): `{settings.get('trial_duration', 'Not Set')}`\n"
        f"Max Trials / Month: `{settings.get('max_trials', 'Not Set')}`\n"
        f"Broker Change Fee: `{settings.get('broker_change_fee', 'Not Set')}`\n"
        f"Support Username: `{settings.get('support_username', 'Not Set')}`\n\n"
        "Click a button below to change a setting:"
    )
    
    kb = [
        [InlineKeyboardButton("Edit Trial Status", callback_data="admin_edit_free_trial_enabled"), InlineKeyboardButton("Edit Trial Duration", callback_data="admin_edit_trial_duration")],
        [InlineKeyboardButton("Edit Max Trials", callback_data="admin_edit_max_trials"), InlineKeyboardButton("Edit Change Fee", callback_data="admin_edit_broker_change_fee")],
        [InlineKeyboardButton("Edit Support Username", callback_data="admin_edit_support_username")]
    ]
    
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

async def installment_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tid = str(update.effective_user.id)
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
    
    import httpx
    async with httpx.AsyncClient(verify=False, follow_redirects=True) as client:
        resp = await client.get(f"{base_url}/installments/customer/{tid}")
        if resp.status_code == 404:
            await update.message.reply_text("❌ You don't have an active installment arrangement.")
            return
        elif resp.status_code != 200:
            await update.message.reply_text("❌ Unable to fetch installment info.")
            return
            
        data = resp.json()
        
        status_icon = "🟢" if data['license_status'] == 'active' else "🔴" if data['license_status'] == 'expired' else "⚫"
        expiry_str = data['license_expiry'].split('T')[0] if data['license_expiry'] else "Never"
        next_due_str = data['next_due_date'].split('T')[0] if data['next_due_date'] else "Completed"
        
        # Calculate days to next due date to show warning
        payment_warning = ""
        if data['installment_status'] != 'completed' and data['next_due_date']:
            from datetime import datetime, timezone
            try:
                next_due = datetime.strptime(data['next_due_date'].split('T')[0], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                days_left = (next_due - now).days
                if days_left <= 5:
                    payment_warning = "\nStatus:\n⚠️ Payment Due Soon"
                else:
                    payment_warning = "\nStatus:\n✅ Active"
            except:
                pass
                
        msg = (
            "💳 *YOUR INSTALLMENT PLAN*\n\n"
            f"Plan: {data['product_name']}\n\n"
            f"MT5 ID: `{data['mt5_id']}`\n\n"
            f"Total Amount: ₹{data['total_amount']:,.0f}\n"
            f"Installment: ₹{data['installment_amount']:,.0f}\n\n"
            f"Paid: ₹{data['amount_paid']:,.0f}\n"
            f"Remaining: ₹{data['amount_remaining']:,.0f}\n\n"
            f"Payment:\n{data['installments_paid']}/{data['installment_count']}\n\n"
            f"License:\n{status_icon} {data['license_status'].title()}\n\n"
            f"Expires:\n{expiry_str}\n\n"
            f"Next Payment:\n₹{data['installment_amount']:,.0f} (Due: {next_due_str}){payment_warning}"
        )
        
        kb = [
            [InlineKeyboardButton("Contact Admin", url="https://t.me/InfinityTraderSupport"), InlineKeyboardButton("🏠 Home", callback_data="home")]
        ]
        
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

def main():
    start_dummy_server()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    application = ApplicationBuilder().token(token).post_init(post_init).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("licenses", licenses_command))
    application.add_handler(CommandHandler("downloads", downloads_command))
    application.add_handler(CommandHandler("installment", installment_command))
    application.add_handler(CommandHandler("myid", myid_command))
    application.add_handler(CommandHandler("admintest", admintest_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("mock_webhook", mock_webhook))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    logging.info("Starting Infinity Trader Bot...")
    application.run_polling()

if __name__ == '__main__':

