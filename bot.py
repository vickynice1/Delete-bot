import os
import re
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ChatMemberStatus

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = [5727413041, -1002139907201]  # Your admin IDs

# Storage for flagged and banned words
flagged_words = set()
banned_words = set()
auto_delete_links = False
auto_delete_joins = True  # New: Auto delete join messages
auto_delete_promotions = True  # New: Auto delete promotional messages

class MessageDeleterBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()
        # Add error handler
        self.application.add_error_handler(self.error_handler)
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Exception while handling an update: {context.error}")
    
    def setup_handlers(self):
        """Setup command and message handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("flag", self.flag_command))
        self.application.add_handler(CommandHandler("ban", self.ban_command))
        self.application.add_handler(CommandHandler("unflag", self.unflag_command))
        self.application.add_handler(CommandHandler("unban", self.unban_command))
        self.application.add_handler(CommandHandler("list", self.list_words))
        self.application.add_handler(CommandHandler("links", self.toggle_links))
        self.application.add_handler(CommandHandler("joins", self.toggle_joins))  # New command
        self.application.add_handler(CommandHandler("promos", self.toggle_promotions))  # New command
        self.application.add_handler(CommandHandler("help", self.help_command))
        
        # Message handlers
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.monitor_messages)
        )
        # New: Handler for service messages (join/leave)
        self.application.add_handler(
            MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, self.delete_join_message)
        )
        self.application.add_handler(
            MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, self.delete_leave_message)
        )
    
    async def is_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Check if user is admin"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Check if user is in our admin list
        if user_id in ADMIN_IDS:
            return True
        
        # Check if user is admin/creator in the group
        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
        except:
            return False
    
    async def is_bot_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Check if bot is admin in the group"""
        try:
            bot_member = await context.bot.get_chat_member(
                update.effective_chat.id, 
                context.bot.id
            )
            return bot_member.status == ChatMemberStatus.ADMINISTRATOR
        except:
            return False
    
    def is_promotional_message(self, text: str) -> bool:
        """Check if message is promotional based on patterns"""
        text_lower = text.lower()
        
        # Promotional keywords
        promo_keywords = [
            'airdrop', 'drop', 'token', 'coin', 'crypto', 'free', 'earn', 'profit',
            'refer', 'referral', 'bonus', 'reward', 'withdrawal', 'withdraw',
            'meta core', 'metacore', 'base', 'network issue', 'server issue',
            'notice from', 'dear users', 'currently experiencing', 'team is working',
            'continue referring', 'more you refer', 'thanks for your patience'
        ]
        
        # Bot mentions pattern
        bot_mention_pattern = r'@\w*bot\b'
        
        # Excessive emoji patterns
        excessive_emoji_pattern = r'[❗️🔥✅➡️]{5,}'
        
        # Check for promotional keywords (at least 2 matches)
        keyword_matches = sum(1 for keyword in promo_keywords if keyword in text_lower)
        
        # Check patterns
        has_bot_mentions = bool(re.search(bot_mention_pattern, text, re.IGNORECASE))
        has_excessive_emojis = bool(re.search(excessive_emoji_pattern, text))
        
        # Promotional message criteria
        if keyword_matches >= 2:  # At least 2 promotional keywords
            return True
        
        if has_bot_mentions and keyword_matches >= 1:  # Bot mention + 1 keyword
            return True
        
        if has_excessive_emojis and keyword_matches >= 1:  # Excessive emojis + 1 keyword
            return True
        
        # Check for specific promotional patterns
        promotional_patterns = [
            r'notice from.*core',
            r'dear users.*experiencing',
            r'server.*issue.*withdrawal',
            r'continue.*referring.*friends',
            r'more you refer.*profit',
            r'thanks.*patience.*support',
            r'[❗️]{3,}.*@\w*bot.*[❗️]{3,}',
            r'✅@\w*bot\s*➡️@\w*bot\s*✅@\w*bot'
        ]
        
        for pattern in promotional_patterns:
            if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                return True
        
        return False
    
    async def delete_join_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Delete join messages"""
        if auto_delete_joins and await self.is_bot_admin(update, context):
            try:
                await update.message.delete()
                logger.info("Deleted join message")
            except Exception as e:
                logger.error(f"Failed to delete join message: {e}")
    
    async def delete_leave_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Delete leave messages"""
        if auto_delete_joins and await self.is_bot_admin(update, context):
            try:
                await update.message.delete()
                logger.info("Deleted leave message")
            except Exception as e:
                logger.error(f"Failed to delete leave message: {e}")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command - only respond to admins"""
        if not await self.is_admin(update, context):
            return  # Don't reply if not admin
        
        # Fix the string formatting issue
        link_status = "ON" if auto_delete_links else "OFF"
        join_status = "ON" if auto_delete_joins else "OFF"
        promo_status = "ON" if auto_delete_promotions else "OFF"
        
        welcome_message = f"""🤖 **Hello Admin! Message Deleter Bot is now enabled!**

**Available Commands:**
• `/flag <word>` - Add word to flag list (auto-delete)
• `/ban <word>` - Add word to ban list (auto-delete)
• `/unflag <word>` - Remove word from flag list
• `/unban <word>` - Remove word from ban list
• `/list` - Show all flagged and banned words
• `/links on/off` - Toggle automatic link deletion
• `/joins on/off` - Toggle join/leave message deletion
• `/promos on/off` - Toggle promotional message deletion
• `/help` - Show this help message

**Current Status:**
• Flagged words: {len(flagged_words)}
• Banned words: {len(banned_words)}
• Link deletion: {link_status}
• Join message deletion: {join_status}
• Promotional message deletion: {promo_status}

Send me flagged or banned words to start protecting your group! 🛡️"""
        
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def toggle_joins(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Toggle automatic join/leave message deletion"""
        if not await self.is_admin(update, context):
            await update.message.reply_text("❌ Only admins can use this command!")
            return
        
        global auto_delete_joins
        
        if context.args:
            arg = context.args[0].lower()
            if arg in ['on', 'enable', '1', 'true']:
                auto_delete_joins = True
                await update.message.reply_text("✅ Automatic join/leave message deletion is now ON!")
            elif arg in ['off', 'disable', '0', 'false']:
                auto_delete_joins = False
                await update.message.reply_text("✅ Automatic join/leave message deletion is now OFF!")
            else:
                await update.message.reply_text("❌ Use: `/joins on` or `/joins off`", parse_mode='Markdown')
        else:
            auto_delete_joins = not auto_delete_joins
            status = "ON" if auto_delete_joins else "OFF"
            await update.message.reply_text(f"✅ Automatic join/leave message deletion is now {status}!")
    
    async def toggle_promotions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Toggle automatic promotional message deletion"""
        if not await self.is_admin(update, context):
            await update.message.reply_text("❌ Only admins can use this command!")
            return
        
        global auto_delete_promotions
        
        if context.args:
            arg = context.args[0].lower()
            if arg in ['on', 'enable', '1', 'true']:
                auto_delete_promotions = True
                await update.message.reply_text("✅ Automatic promotional message deletion is now ON!")
            elif arg in ['off', 'disable', '0', 'false']:
                auto_delete_promotions = False
                await update.message.reply_text("✅ Automatic promotional message deletion is now OFF!")
            else:
                await update.message.reply_text("❌ Use: `/promos on` or `/promos off`", parse_mode='Markdown')
        else:
            auto_delete_promotions = not auto_delete_promotions
            status = "ON" if auto_delete_promotions else "OFF"
            await update.message.reply_text(f"✅ Automatic promotional message deletion is now {status}!")
    
    async def flag_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /flag command"""
        if not await self.is_admin(update, context):
            await update.message.reply_text("❌ Only admins can use this command!")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Please provide a word to flag!\nExample: `/flag scam`", parse_mode='Markdown')
            return
        
        word = ' '.join(context.args).lower()
        flagged_words.add(word)
        await update.message.reply_text(f"✅ Word '{word}' has been flagged! Messages containing this word will be deleted.")
    
    async def ban_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ban command"""
        if not await self.is_admin(update, context):
            await update.message.reply_text("❌ Only admins can use this command!")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Please provide a word to ban!\nExample: `/ban scam`", parse_mode='Markdown')
            return
        
        word = ' '.join(context.args).lower()
        banned_words.add(word)
        await update.message.reply_text(f"✅ Word '{word}' has been banned! Messages containing this word will be deleted.")
    
    async def unflag_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /unflag command"""
        if not await self.is_admin(update, context):
            await update.message.reply_text("❌ Only admins can use this command!")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Please provide a word to unflag!")
            return
        
        word = ' '.join(context.args).lower()
        if word in flagged_words:
            flagged_words.remove(word)
            await update.message.reply_text(f"✅ Word '{word}' has been unflagged!")
        else:
            await update.message.reply_text(f"❌ Word '{word}' is not in the flagged list!")
    
    async def unban_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /unban command"""
        if not await self.is_admin(update, context):
            await update.message.reply_text("❌ Only admins can use this command!")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Please provide a word to unban!")
            return
        
        word = ' '.join(context.args).lower()
        if word in banned_words:
            banned_words.remove(word)
            await update.message.reply_text(f"✅ Word '{word}' has been unbanned!")
        else:
            await update.message.reply_text(f"❌ Word '{word}' is not in the banned list!")
    
    async def list_words(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List all flagged and banned words"""
        if not await self.is_admin(update, context):
            await update.message.reply_text("❌ Only admins can use this command!")
            return
        
        message = "📋 **Current Settings:**\n\n"
        
        if flagged_words:
            message += "🚩 **Flagged Words:**\n"
            for word in sorted(flagged_words):
                message += f"• {word}\n"
        else:
            message += "🚩 **Flagged Words:** None\n"
        
        message += "\n"
        
        if banned_words:
            message += "🚫 **Banned Words:**\n"
            for word in sorted(banned_words):
                message += f"• {word}\n"
        else:
            message += "🚫 **Banned Words:** None\n"
        
        link_status = "ON" if auto_delete_links else "OFF"
        join_status = "ON" if auto_delete_joins else "OFF"
        promo_status = "ON" if auto_delete_promotions else "OFF"
        
        message += f"\n🔗 **Link Deletion:** {link_status}"
        message += f"\n👋 **Join Message Deletion:** {join_status}"
        message += f"\n📢 **Promotional Message Deletion:** {promo_status}"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def toggle_links(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Toggle automatic link deletion"""
        if not await self.is_admin(update, context):
            await update.message.reply_text("❌ Only admins can use this command!")
            return
        
        global auto_delete_links
        
        if context.args:
            arg = context.args[0].lower()
            if arg in ['on', 'enable', '1', 'true']:
                auto_delete_links = True
                await update.message.reply_text("✅ Automatic link deletion is now ON!")
            elif arg in ['off', 'disable', '0', 'false']:
                auto_delete_links = False
                await update.message.reply_text("✅ Automatic link deletion is now OFF!")
            else:
                await update.message.reply_text("❌ Use: `/links on` or `/links off`", parse_mode='Markdown')
        else:
            auto_delete_links = not auto_delete_links
            status = "ON" if auto_delete_links else "OFF"
            await update.message.reply_text(f"✅ Automatic link deletion is now {status}!")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help message"""
        if not await self.is_admin(update, context):
            return  # Don't reply if not admin
        
        help_text = """🤖 **Message Deleter Bot Help**

**Commands:**
• `/start` - Initialize bot and show status
• `/flag <word>` - Add word to auto-delete list
• `/ban <word>` - Add word to ban list (same as flag)
• `/unflag <word>` - Remove word from flag list
• `/unban <word>` - Remove word from ban list
• `/list` - Show all settings and word lists
• `/links on/off` - Toggle automatic link deletion
• `/joins on/off` - Toggle join/leave message deletion
• `/promos on/off` - Toggle promotional message deletion
• `/help` - Show this help message

**Examples:**
• `/flag scam` - Delete messages containing "scam"
• `/ban help` - Delete messages containing "help"
• `/links on` - Enable automatic link deletion
• `/joins on` - Enable join message deletion
• `/promos on` - Enable promotional message deletion

**Features:**
• Automatically deletes messages with flagged/banned words
• Can delete messages containing links (when enabled)
• Deletes join/leave messages (when enabled)
• Detects and deletes promotional/spam messages (when enabled)
• Only admins can control the bot
• Works only when bot has admin privileges

**Promotional Message Detection:**
The bot can detect promotional messages by looking for:
• Airdrop/token/crypto related keywords
• Bot mentions with promotional content
• Excessive emoji usage with promotional content
• Specific spam patterns

**Note:** Bot must be admin in the group to delete messages!"""
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def monitor_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Monitor messages for flagged/banned words, links, and promotional content"""
        try:
            # Skip if no message text
            if not update.message or not update.message.text:
                return
            
            # Skip if bot is not admin
            if not await self.is_bot_admin(update, context):
                return
            
            # Skip admin messages
            if await self.is_admin(update, context):
                return
            
            message_text = update.message.text.lower()
            original_text = update.message.text
            should_delete = False
            reason = ""
            
            # Check for flagged words
            for word in flagged_words:
                if word in message_text:
                    should_delete = True
                    reason = f"flagged word: '{word}'"
                    break
            
            # Check for banned words
            if not should_delete:
                for word in banned_words:
                    if word in message_text:
                        should_delete = True
                        reason = f"banned word: '{word}'"
                        break
            
            # Check for promotional messages
            if not should_delete and auto_delete_promotions:
                if self.is_promotional_message(original_text):
                    should_delete = True
                    reason = "promotional/spam content"
            
            # Check for links if enabled
            if not should_delete and auto_delete_links:
                # Enhanced regex pattern for URLs and common link formats
                url_patterns = [
                    r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
                    r'www\.(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
                    r'(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}',
                    r't\.me/\w+',
                    r'@\w+\.\w+'
                ]
                
                for pattern in url_patterns:
                    if re.search(pattern, original_text, re.IGNORECASE):
                        should_delete = True
                        reason = "contains link"
                        break
            
            # Delete message if needed
            if should_delete:
                try:
                    await update.message.delete()
                    username = update.effective_user.username or update.effective_user.first_name or "Unknown"
                    logger.info(f"Deleted message from {username} - {reason}")
                except Exception as e:
                    logger.error(f"Failed to delete message: {e}")
                    
        except Exception as e:
            logger.error(f"Error in monitor_messages: {e}")
    
    def run(self):
        """Start the bot"""
        logger.info("Starting Message Deleter Bot...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN environment variable is required!")
        exit(1)
    
    bot = MessageDeleterBot()
    bot.run()
