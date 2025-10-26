#!/usr/bin/env python3
"""
Test script to send a simple message to Discord and/or Telegram.

Usage examples:
- python scripts/test_notifications.py --discord
- python scripts/test_notifications.py --telegram
- python scripts/test_notifications.py --both

Environment variables expected:
- DISCORD_WEBHOOK_URL
- TELEGRAM_BOT_TOKEN
- TELEGRAM_CHAT_ID
"""

import os
import sys
import argparse
from dotenv import load_dotenv

# Allow importing project modules when run as a script
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from notifications.discord_notifier import DiscordNotifier  # noqa: E402
from notifications.telegram_notifier import TelegramNotifier  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Send test message to Discord and/or Telegram")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--discord", action="store_true", help="Send only to Discord")
    group.add_argument("--telegram", action="store_true", help="Send only to Telegram")
    group.add_argument("--both", action="store_true", help="Send to both Discord and Telegram (default)")
    args = parser.parse_args()

    # Load .env if present
    load_dotenv()

    sent_any = False
    errors = []

    # Decide targets
    targets = ["discord", "telegram"] if (args.both or (not args.discord and not args.telegram)) else (
        ["discord"] if args.discord else ["telegram"]
    )

    if "discord" in targets:
        webhook = os.getenv("DISCORD_WEBHOOK_URL")
        if webhook:
            notifier = DiscordNotifier(webhook)
            ok = notifier.send_test_message()
            print("Discord: OK" if ok else "Discord: FAILED")
            sent_any = sent_any or ok
            if not ok:
                errors.append("Discord webhook request failed")
        else:
            print("Discord: SKIPPED (DISCORD_WEBHOOK_URL not set)")

    if "telegram" in targets:
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if token and chat_id:
            notifier = TelegramNotifier(token, chat_id)
            ok = notifier.send_test_message()
            print("Telegram: OK" if ok else "Telegram: FAILED")
            sent_any = sent_any or ok
            if not ok:
                errors.append("Telegram sendMessage request failed")
        else:
            missing = []
            if not token:
                missing.append("TELEGRAM_BOT_TOKEN")
            if not chat_id:
                missing.append("TELEGRAM_CHAT_ID")
            print(f"Telegram: SKIPPED ({' & '.join(missing)} not set)")

    if not sent_any and errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
