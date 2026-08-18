import os

filepath = 'telegram_bot/keyboards/menu.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    'def get_main_menu_keyboard(show_installment: bool = False) -> InlineKeyboardMarkup:',
    'def get_main_menu_keyboard(show_installment: bool = False, show_free_trial: bool = True) -> InlineKeyboardMarkup:'
)

lines = content.split('\n')
new_lines = []
for line in lines:
    if 'callback_data="free_trial"' in line:
        parts = line.split('), ')
        downloads_part = parts[1].replace('],', ']')
        # The line is something like: [InlineKeyboardButton("Free Trial", callback_data="free_trial"), InlineKeyboardButton("Downloads", callback_data="downloads")],
        new_line = f'        {line.strip()} if show_free_trial else [{downloads_part},'
        new_lines.append(new_line)
    else:
        new_lines.append(line)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write('\n'.join(new_lines))
