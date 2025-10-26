"""
Telegram Notifier for Trading Signals

Sends formatted trading signal notifications to Telegram via bot API.
Supports Markdown formatting for better readability.
"""

import requests
import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """
    Sends trading signal notifications to Telegram via bot API.
    
    Uses Telegram Bot API with Markdown formatting for structured messages.
    """
    
    # Signal type to emoji mapping
    SIGNAL_EMOJIS = {
        'LONG': '🚀',
        'SHORT': '📉',
        'EXIT LONG': '🛑',
        'EXIT SHORT': '✅'
    }
    
    def __init__(self, bot_token: str, chat_id: str):
        """
        Initialize Telegram notifier.
        
        Args:
            bot_token: Telegram bot token from BotFather
            chat_id: Telegram chat ID to send messages to
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}"
        logger.info(f"Initialized TelegramNotifier for chat {chat_id}")
    
    def send_signal(self,
                   symbol: str,
                   signal_type: str,
                   confidence: float,
                   price: float,
                   stop_loss: float,
                   ichimoku_values: Dict,
                   llm_analysis: Optional[str] = None,
                   timestamp: Optional[datetime] = None) -> bool:
        """
        Send trading signal notification to Telegram.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            signal_type: Signal type (LONG, SHORT, EXIT LONG, EXIT SHORT)
            confidence: Signal confidence (0.0 to 1.0)
            price: Current price
            stop_loss: Calculated stop loss price (4% from current)
            ichimoku_values: Dictionary with Ichimoku indicator values
            llm_analysis: Optional AI-generated analysis
            timestamp: Signal timestamp (defaults to now)
        
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            if timestamp is None:
                timestamp = datetime.utcnow()
            
            # Build message
            message = self._build_message(
                symbol=symbol,
                signal_type=signal_type,
                confidence=confidence,
                price=price,
                stop_loss=stop_loss,
                ichimoku_values=ichimoku_values,
                llm_analysis=llm_analysis,
                timestamp=timestamp
            )
            
            # Send to Telegram
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': True
            }
            
            response = requests.post(f"{self.api_url}/sendMessage", json=payload)
            response.raise_for_status()
            
            logger.info(f"Sent Telegram notification for {symbol} {signal_type}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Telegram notification: {e}")
            return False
    
    def _build_message(self,
                      symbol: str,
                      signal_type: str,
                      confidence: float,
                      price: float,
                      stop_loss: float,
                      ichimoku_values: Dict,
                      llm_analysis: Optional[str],
                      timestamp: datetime) -> str:
        """Build Telegram message with Markdown formatting."""
        
        emoji = self.SIGNAL_EMOJIS.get(signal_type, '📊')
        
        # Header
        message = f"{emoji} *{signal_type} Signal: {symbol}*\n"
        message += "━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # Price and confidence
        message += f"💰 *Price:* ${price:,.2f}\n"
        message += f"📊 *Confidence:* {confidence:.1%}\n"
        message += f"🛡️ *Stop Loss (4%):* ${stop_loss:,.2f}\n\n"
        
        # Ichimoku indicators
        tenkan = ichimoku_values.get('tenkan_sen')
        kijun = ichimoku_values.get('kijun_sen')
        cloud_color = ichimoku_values.get('cloud_color', 'unknown')
        
        if tenkan is not None and kijun is not None:
            message += "📈 *Ichimoku Indicators*\n"
            message += f"  • Tenkan-sen: ${tenkan:,.2f}\n"
            message += f"  • Kijun-sen: ${kijun:,.2f}\n"
            message += f"  • Cloud: {cloud_color.capitalize()}\n\n"
        
        # Cloud boundaries
        cloud_top = ichimoku_values.get('cloud_top')
        cloud_bottom = ichimoku_values.get('cloud_bottom')
        
        if cloud_top is not None and cloud_bottom is not None:
            message += "☁️ *Cloud Boundaries*\n"
            message += f"  • Top: ${cloud_top:,.2f}\n"
            message += f"  • Bottom: ${cloud_bottom:,.2f}\n\n"
        
        # LLM Analysis
        if llm_analysis:
            message += "🤖 *AI Analysis*\n"
            message += f"{llm_analysis}\n\n"
        
        # Timestamp
        time_str = timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')
        message += f"🕐 {time_str}"
        
        return message
    
    def send_test_message(self) -> bool:
        """
        Send a test message to verify bot is working.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            payload = {
                'chat_id': self.chat_id,
                'text': '✅ Telegram bot connection test successful!'
            }
            
            response = requests.post(f"{self.api_url}/sendMessage", json=payload)
            response.raise_for_status()
            
            logger.info("Telegram test message sent successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Telegram test message: {e}")
            return False
    
    def get_chat_id(self) -> Optional[str]:
        """
        Helper method to get chat ID from recent updates.
        Useful for initial bot setup.
        
        Returns:
            Most recent chat ID or None
        """
        try:
            response = requests.get(f"{self.api_url}/getUpdates")
            response.raise_for_status()
            
            data = response.json()
            if data.get('ok') and data.get('result'):
                updates = data['result']
                if updates:
                    chat_id = updates[-1]['message']['chat']['id']
                    logger.info(f"Found chat ID: {chat_id}")
                    return str(chat_id)
            
            logger.warning("No chat updates found")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get chat ID: {e}")
            return None
