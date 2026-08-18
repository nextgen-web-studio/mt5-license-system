from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_main_menu_keyboard(show_installment: bool = False, show_free_trial: bool = True) -> InlineKeyboardMarkup:
    """Returns the main menu keyboard layout.

    show_installment: only True for customers who have an eligible
    installment arrangement. Normal customers must never see this button
    (see spec section 20 - Installment Menu Visibility).
    """
    keyboard = [
        [InlineKeyboardButton("🏠 Home", callback_data="home")],
        [InlineKeyboardButton("🛒 Buy EA", callback_data="buy_ea"), InlineKeyboardButton("🔄 Broker Change", callback_data="broker_change")]
    ]
    
    if show_free_trial:
        keyboard.append([InlineKeyboardButton("🆓 Free Trial", callback_data="free_trial")])
        
    keyboard.append([InlineKeyboardButton("📞 Support", callback_data="support")])

    if show_installment:
        keyboard.append([InlineKeyboardButton("💸 My Installment", callback_data="my_installment")])

    return InlineKeyboardMarkup(keyboard)
