import os
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# Allowed admin and group IDs
ADMIN_ID = 5727413041
GROUP_ID = -1002139907201

# Storage for words (can be replaced with DB later)
flagged_words = set()
banned_words = set()

# /flag <word>
async def flag_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != GROUP_ID:
        return
    if update.effective_user.id != ADMIN_ID:
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /flag <word>")
        return
    
    word = " ".join(context.args).lower()
    flagged_words.add(word)
    await update.message.reply_text(f"✅ Flagged word added: {word}")

# /ban <word>
async def ban_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != GROUP_ID:
        return
    if update.effective_user.id != ADMIN_ID:
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /ban <word>")
        return
    
    word = " ".join(context.args).lower()
    banned_words.add(word)
    await update.message.reply_text(f"🚫 Banned word added: {word}")

# Delete flagged/banned messages
async def check_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != GROUP_ID:
        return
    if not update.message or not update.message.text:
        return
    
    text = update.message.text.lower()
    for word in flagged_words.union(banned_words):
        if word in text:
            try:
                await update.message.delete()
                print(f"🗑 Deleted message with banned/flagged word: {word}")
                return
            except Exception as e:
                print(f"❌ Failed to delete: {e}")

def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("❌ BOT_TOKEN not found in environment variables")
        return

    app = Application.builder().token(token).build()

    # Handlers
    app.add_handler(CommandHandler("flag", flag_word))
    app.add_handler(CommandHandler("ban", ban_word))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_messages))

    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
