"""
Helper Script to Get Telegram Chat ID

Steps:
1. Make sure TELEGRAM_BOT_TOKEN is set in .env
2. Start a chat with your bot on Telegram
3. Send any message to the bot (e.g., "/start" or "Hello")
4. Run this script to retrieve your chat_id
"""

import os
from dotenv import load_dotenv
from notifications.telegram_notifier import TelegramNotifier

# Load environment variables
load_dotenv()

def get_chat_id():
    """Get Telegram chat ID from bot updates."""
    
    # Get bot token from environment
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not bot_token:
        print("❌ Error: TELEGRAM_BOT_TOKEN not found in .env file")
        print("\nPlease add your bot token to .env:")
        print("TELEGRAM_BOT_TOKEN=your_bot_token_here")
        return
    
    print("🤖 Telegram Bot Token found!")
    print(f"   Token: {bot_token[:10]}...{bot_token[-5:]}")
    print()
    
    # Create temporary notifier (chat_id not needed for this)
    notifier = TelegramNotifier(bot_token=bot_token, chat_id="0")
    
    print("📡 Fetching recent messages from your bot...")
    print()
    
    # Get chat ID
    chat_id = notifier.get_chat_id()
    
    if chat_id:
        print("✅ Success! Your chat ID is:")
        print(f"\n   {chat_id}\n")
        print("📝 Add this to your .env file:")
        print(f"   TELEGRAM_CHAT_ID={chat_id}")
        print()
        print("💡 Tip: You can now test the bot with:")
        print("   python test_telegram.py")
    else:
        print("❌ No chat ID found!")
        print()
        print("📋 Make sure you:")
        print("   1. Started a chat with your bot on Telegram")
        print("   2. Sent at least one message to the bot")
        print("   3. The bot token is correct")
        print()
        print("🔍 To find your bot:")
        print("   1. Open Telegram")
        print("   2. Search for your bot's username")
        print("   3. Click 'START' or send any message")
        print("   4. Run this script again")

if __name__ == "__main__":
    print("=" * 60)
    print("🔧 Telegram Chat ID Retriever")
    print("=" * 60)
    print()
    get_chat_id()
    print("=" * 60)
