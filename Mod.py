from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from datetime import datetime, timedelta
import pytz
import asyncio
import re

# Telegram ID of the bot admin (replace with your admin ID)
ADMIN_ID = 6357920694

# Approved users with expiration times
approved_users = {}

def parse_duration(duration_str):
    """Parse duration string into timedelta"""
    if not duration_str:
        return timedelta(days=1)  # Default 1 day

    match = re.match(r'(\d+)(mins|m|h)$', duration_str)
    if not match:
        return timedelta(days=1)

    amount = int(match.group(1))
    unit = match.group(2)

    if unit == 'mins':
        return timedelta(minutes=amount)
    elif unit == 'm':
        return timedelta(days=amount * 30)  # Approximate month
    elif unit == 'h':
        return timedelta(hours=amount)

    return timedelta(days=1)

def is_user_authorized(user_id):
    """Check if user is authorized and not expired, returns (bool, str)"""
    if str(user_id) == str(ADMIN_ID):
        return True, None

    if user_id not in approved_users:
        return False, "🚫 You are not authorized. 🔄 Use /start to request access."

    expiration_time = approved_users[user_id]
    current_time = datetime.now(pytz.UTC)
    if current_time >= expiration_time:
        del approved_users[user_id]  # Remove expired user
        return False, "⏳ Your authorization has expired. 🔄 Use /start to request new access."

    return True, None

async def delete_unauthorized_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete messages from unauthorized users"""
    user_id = str(update.message.chat_id)
    is_authorized, _ = is_user_authorized(user_id)

    if not is_authorized:
        warning_message = await update.message.reply_text("🚫 Contact Admin for Authorization!")
        await asyncio.sleep(1)
        try:
            await update.message.delete()
            await warning_message.delete()
        except:
            pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.chat_id)
    username = update.message.chat.username

    if user_id in approved_users or user_id == str(ADMIN_ID):
        await update.message.reply_text("✅ You are already authorized!", parse_mode="HTML")
        return

    message = f"New user requests access: @{username} (ID: {user_id})\nApprove? Use /approve {user_id}"
    await context.bot.send_message(chat_id=ADMIN_ID, text=message)

    await update.message.reply_text("☑ Request sent to admin.")

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if str(update.message.chat_id) != str(ADMIN_ID):
        await update.message.reply_text("🚫 Not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("✅ Use: /approve USER_ID DURATION\nExample: /approve 123456 1m")
        return

    user_id = context.args[0]
    duration_str = context.args[1] if len(context.args) > 1 else None
    duration = parse_duration(duration_str)
    expiration_time = datetime.now(pytz.UTC) + duration

    approved_users[user_id] = expiration_time

    ist_tz = pytz.timezone('Asia/Kolkata')
    ist_expiration = expiration_time.astimezone(ist_tz)
    expiration_str = ist_expiration.strftime("%Y-%m-%d %I:%M:%S %p IST")

    await context.bot.send_message(chat_id=user_id, text=f"🤖 Authorized until {expiration_str}", parse_mode="HTML")
    await update.message.reply_text(f"✨ Authorized {user_id} until {expiration_str}")

async def deny(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if str(update.message.chat_id) != str(ADMIN_ID):
        await update.message.reply_text("🚫 Not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("❌ Provide user ID to deny.")
        return

    user_id = context.args[0]
    await context.bot.send_message(chat_id=user_id, text="❌ Request denied by admin.")

async def any_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete messages from unauthorized users"""
    await delete_unauthorized_message(update, context)

if __name__ == "__main__":
    application = Application.builder().token("YOUR_BOT_TOKEN").build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("approve", approve))
    application.add_handler(CommandHandler("deny", deny))

    # ✅ Delete normal messages from unauthorized users
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, any_message_handler))

    print("Bot started. Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
