from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Returns the main menu keyboard layout as requested."""
    keyboard = [
        [InlineKeyboardButton("🏠 Home", callback_data="home")],
        [InlineKeyboardButton("🛒 Buy EA", callback_data="buy_ea"), InlineKeyboardButton("🔄 Broker Change", callback_data="broker_change")],
        [InlineKeyboardButton("📥 Downloads", callback_data="downloads"), InlineKeyboardButton("🎫 License Details", callback_data="license_details")],
        [InlineKeyboardButton("📄 My Orders", callback_data="my_orders"), InlineKeyboardButton("🆓 Free Trial", callback_data="free_trial")],
        [InlineKeyboardButton("☎️ Support", callback_data="support")]
    ]
    return InlineKeyboardMarkup(keyboard)
