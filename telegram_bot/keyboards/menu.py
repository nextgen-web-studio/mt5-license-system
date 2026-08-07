from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Returns the main menu keyboard layout as requested."""
    keyboard = [
        [InlineKeyboardButton("🏠 Home", callback_data="home")],
        [InlineKeyboardButton("🛒 Buy EA", callback_data="buy_ea"), InlineKeyboardButton("💻 Buy VPS", callback_data="buy_vps")],
        [InlineKeyboardButton("🔄 Renew License", callback_data="renew_license")],
        [InlineKeyboardButton("📄 My Orders", callback_data="my_orders"), InlineKeyboardButton("📥 Downloads", callback_data="downloads")],
        [InlineKeyboardButton("☎ Support", callback_data="support")]
    ]
    return InlineKeyboardMarkup(keyboard)
