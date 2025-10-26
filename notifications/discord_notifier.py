"""
Discord Notifier for Trading Signals

Sends formatted trading signal notifications to Discord via webhooks.
Supports rich formatting with embeds for better visualization.
"""

import requests
import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class DiscordNotifier:
    """
    Sends trading signal notifications to Discord via webhook.
    
    Uses Discord embeds for rich, color-coded messages with structured data.
    """
    
    # Signal type to color mapping (Discord embed colors in decimal)
    SIGNAL_COLORS = {
        'LONG': 0x00FF00,      # Green
        'SHORT': 0xFF0000,     # Red
        'EXIT LONG': 0xFFA500, # Orange
        'EXIT SHORT': 0x00CED1 # Dark Turquoise
    }
    
    # Signal type to emoji mapping
    SIGNAL_EMOJIS = {
        'LONG': '🚀',
        'SHORT': '📉',
        'EXIT LONG': '🛑',
        'EXIT SHORT': '✅'
    }
    
    def __init__(self, webhook_url: str):
        """
        Initialize Discord notifier.
        
        Args:
            webhook_url: Discord webhook URL
        """
        self.webhook_url = webhook_url
        logger.info("Initialized DiscordNotifier")
    
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
        Send trading signal notification to Discord.
        
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
            
            # Build embed
            embed = self._build_embed(
                symbol=symbol,
                signal_type=signal_type,
                confidence=confidence,
                price=price,
                stop_loss=stop_loss,
                ichimoku_values=ichimoku_values,
                llm_analysis=llm_analysis,
                timestamp=timestamp
            )
            
            # Send to Discord
            payload = {
                'embeds': [embed]
            }
            
            response = requests.post(self.webhook_url, json=payload)
            response.raise_for_status()
            
            logger.info(f"Sent Discord notification for {symbol} {signal_type}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Discord notification: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Discord notification: {e}")
            return False
    
    def _build_embed(self,
                    symbol: str,
                    signal_type: str,
                    confidence: float,
                    price: float,
                    stop_loss: float,
                    ichimoku_values: Dict,
                    llm_analysis: Optional[str],
                    timestamp: datetime) -> Dict:
        """Build Discord embed for signal notification."""
        
        emoji = self.SIGNAL_EMOJIS.get(signal_type, '📊')
        color = self.SIGNAL_COLORS.get(signal_type, 0x3498db)
        
        # Title
        title = f"{emoji} {signal_type} Signal: {symbol}"
        
        # Description with price and confidence
        description = (
            f"**Price:** ${price:,.2f}\n"
            f"**Confidence:** {confidence:.1%}\n"
            f"**Stop Loss (4%):** ${stop_loss:,.2f}"
        )
        
        # Build fields for Ichimoku data
        fields = []
        
        # Ichimoku indicators
        tenkan = ichimoku_values.get('tenkan_sen')
        kijun = ichimoku_values.get('kijun_sen')
        cloud_color = ichimoku_values.get('cloud_color', 'unknown')
        
        if tenkan is not None and kijun is not None:
            fields.append({
                'name': '📊 Ichimoku Indicators',
                'value': (
                    f"**Tenkan-sen:** ${tenkan:,.2f}\n"
                    f"**Kijun-sen:** ${kijun:,.2f}\n"
                    f"**Cloud:** {cloud_color.capitalize()}"
                ),
                'inline': True
            })
        
        # Cloud boundaries
        cloud_top = ichimoku_values.get('cloud_top')
        cloud_bottom = ichimoku_values.get('cloud_bottom')
        
        if cloud_top is not None and cloud_bottom is not None:
            fields.append({
                'name': '☁️ Cloud Boundaries',
                'value': (
                    f"**Top:** ${cloud_top:,.2f}\n"
                    f"**Bottom:** ${cloud_bottom:,.2f}"
                ),
                'inline': True
            })
        
        # LLM Analysis (if available)
        if llm_analysis:
            fields.append({
                'name': '🤖 AI Analysis',
                'value': llm_analysis,
                'inline': False
            })
        
        # Build embed
        embed = {
            'title': title,
            'description': description,
            'color': color,
            'fields': fields,
            'footer': {
                'text': 'Ichimoku Trading Assistant'
            },
            'timestamp': timestamp.isoformat()
        }
        
        return embed
    
    def send_test_message(self) -> bool:
        """
        Send a test message to verify webhook is working.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            payload = {
                'content': '✅ Discord webhook connection test successful!'
            }
            
            response = requests.post(self.webhook_url, json=payload)
            response.raise_for_status()
            
            logger.info("Discord test message sent successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Discord test message: {e}")
            return False
