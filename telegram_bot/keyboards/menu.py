from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_main_menu_keyboard(show_installment: bool = False, show_free_trial: bool = True) -> InlineKeyboardMarkup:
    "Returns the main menu keyboard layout."
    keyboard = [
        [InlineKeyboardButton("🏠 Home", callback_data="home")],
        [InlineKeyboardButton("🛒 Buy EA", callback_data="buy_ea"), InlineKeyboardButton("🖥️ Buy VPS", callback_data="buy_vps")],
        [InlineKeyboardButton("🔄 Broker Change", callback_data="broker_change")]
    ]
    
    if show_free_trial:
        keyboard.append([InlineKeyboardButton("🆓 Free Trial", callback_data="free_trial")])
        
    keyboard.append([InlineKeyboardButton("📞 Support", callback_data="support")])

    if show_installment:
        keyboard.append([InlineKeyboardButton("💳 My Installment", callback_data="my_installment")])

    return InlineKeyboardMarkup(keyboard)
