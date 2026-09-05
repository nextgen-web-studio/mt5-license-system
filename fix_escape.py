with open("telegram_bot/bot.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix invalid escape sequences - these are inside f-strings for MarkdownV2
# \. and \! are valid in MarkdownV2 but Python warns about them in f-strings
# Fix by using raw strings or doubling the backslash
content = content.replace(
    r'f"Payment of ₹{amount:,.0f} has been received\.\n\n"',
    r'f"Payment of ₹{amount:,.0f} has been received\\.\n\n"'
)
content = content.replace(
    r'f"🎉 *FINAL PAYMENT CONFIRMED\!*\n\n"',
    r'f"🎉 *FINAL PAYMENT CONFIRMED\\!*\n\n"'
)
content = content.replace(
    r'f"All payments complete\! Your lifetime EA is being compiled\.\n\n"',
    r'f"All payments complete\\! Your lifetime EA is being compiled\\.\n\n"'
)

# More targeted fix - replace the actual garbled bytes
import re

# Fix the \. and \! patterns that Python warns about  
content = re.sub(r"received\\\.", "received\\\\.", content)
content = re.sub(r"CONFIRMED\\!", "CONFIRMED\\\\!", content)
content = re.sub(r"complete\\!", "complete\\\\!", content)
content = re.sub(r"compiled\\.", "compiled\\\\.", content)

with open("telegram_bot/bot.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed escape sequences")
