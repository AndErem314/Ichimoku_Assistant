"""
Message Formatter with LLM Support

Formats trading signals with AI-enhanced analysis using Gemini or OpenAI.
Calculates stop loss levels and generates actionable trading insights.
"""

import logging
from typing import Dict, Optional, Tuple
from datetime import datetime

from llm_analysis.llm_client import LLMClient
from llm_analysis.env_loader import LLMConfig

logger = logging.getLogger(__name__)


class MessageFormatter:
    """
    Formats trading signal notifications with LLM-enhanced analysis.
    
    Supports both Gemini and OpenAI for generating insights.
    Calculates stop loss levels and prepares data for notifications.
    """
    
    def __init__(self, llm_provider: str = "gemini", enable_llm: bool = True):
        """
        Initialize message formatter.
        
        Args:
            llm_provider: LLM provider to use ("gemini" or "openai")
            enable_llm: Enable LLM analysis (set False to skip AI insights)
        """
        self.llm_provider = llm_provider.lower()
        self.enable_llm = enable_llm
        
        if self.enable_llm:
            # Load LLM configuration
            config = LLMConfig.from_env()
            self.llm_client = LLMClient(config)
            logger.info(f"Initialized MessageFormatter with {self.llm_provider} LLM")
        else:
            self.llm_client = None
            logger.info("Initialized MessageFormatter without LLM")
    
    def format_signal(self,
                     symbol: str,
                     signal_type: str,
                     confidence: float,
                     ichimoku_values: Dict,
                     timestamp: Optional[datetime] = None) -> Dict:
        """
        Format trading signal with all required information.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            signal_type: Signal type (LONG, SHORT, EXIT LONG, EXIT SHORT)
            confidence: Signal confidence (0.0 to 1.0)
            ichimoku_values: Dictionary with Ichimoku indicator values
            timestamp: Signal timestamp (defaults to now)
        
        Returns:
            Dictionary with formatted signal data including:
            - symbol, signal_type, confidence
            - price, stop_loss
            - ichimoku_values
            - llm_analysis (if enabled)
            - timestamp
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        price = ichimoku_values.get('close', 0)
        
        # Calculate stop loss (4% from current price)
        stop_loss = self._calculate_stop_loss(price, signal_type)
        
        # Generate LLM analysis if enabled
        llm_analysis = None
        if self.enable_llm and self.llm_client:
            llm_analysis = self._generate_llm_analysis(
                symbol=symbol,
                signal_type=signal_type,
                price=price,
                stop_loss=stop_loss,
                ichimoku_values=ichimoku_values,
                confidence=confidence
            )
        
        return {
            'symbol': symbol,
            'signal_type': signal_type,
            'confidence': confidence,
            'price': price,
            'stop_loss': stop_loss,
            'ichimoku_values': ichimoku_values,
            'llm_analysis': llm_analysis,
            'timestamp': timestamp
        }
    
    def _calculate_stop_loss(self, price: float, signal_type: str) -> float:
        """
        Calculate stop loss at 4% from current price.
        
        Args:
            price: Current price
            signal_type: Signal type (LONG/SHORT determines direction)
        
        Returns:
            Stop loss price
        """
        if signal_type in ['LONG', 'EXIT SHORT']:
            # For LONG positions, stop loss is 4% below
            return price * 0.96
        else:
            # For SHORT positions, stop loss is 4% above
            return price * 1.04
    
    def _generate_llm_analysis(self,
                              symbol: str,
                              signal_type: str,
                              price: float,
                              stop_loss: float,
                              ichimoku_values: Dict,
                              confidence: float) -> Optional[str]:
        """
        Generate LLM-enhanced analysis of the trading signal.
        
        Creates a concise, actionable analysis explaining:
        - Why the signal is significant
        - Key support/resistance levels
        - Risk considerations
        
        Args:
            symbol: Trading pair
            signal_type: Signal type
            price: Current price
            stop_loss: Calculated stop loss
            ichimoku_values: Ichimoku indicator values
            confidence: Signal confidence
        
        Returns:
            AI-generated analysis string or None if failed
        """
        try:
            # Build prompt
            prompt = self._build_llm_prompt(
                symbol=symbol,
                signal_type=signal_type,
                price=price,
                stop_loss=stop_loss,
                ichimoku_values=ichimoku_values,
                confidence=confidence
            )
            
            # Generate analysis using specified provider
            analysis = self.llm_client.generate(
                prompt=prompt,
                provider=self.llm_provider
            )
            
            # Trim to reasonable length (Discord/Telegram limits)
            if analysis and len(analysis) > 800:
                analysis = analysis[:797] + "..."
            
            logger.info(f"Generated LLM analysis for {symbol} using {self.llm_provider}")
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to generate LLM analysis: {e}")
            return None
    
    def _build_llm_prompt(self,
                         symbol: str,
                         signal_type: str,
                         price: float,
                         stop_loss: float,
                         ichimoku_values: Dict,
                         confidence: float) -> str:
        """Build prompt for LLM analysis."""
        
        tenkan = ichimoku_values.get('tenkan_sen', 'N/A')
        kijun = ichimoku_values.get('kijun_sen', 'N/A')
        cloud_color = ichimoku_values.get('cloud_color', 'unknown')
        cloud_top = ichimoku_values.get('cloud_top', 'N/A')
        cloud_bottom = ichimoku_values.get('cloud_bottom', 'N/A')
        
        # Format values
        if isinstance(tenkan, (int, float)):
            tenkan = f"${tenkan:,.2f}"
        if isinstance(kijun, (int, float)):
            kijun = f"${kijun:,.2f}"
        if isinstance(cloud_top, (int, float)):
            cloud_top = f"${cloud_top:,.2f}"
        if isinstance(cloud_bottom, (int, float)):
            cloud_bottom = f"${cloud_bottom:,.2f}"
        
        prompt = f"""You are a crypto trading assistant. A {signal_type} signal has been detected for {symbol} on the 4-hour timeframe.

Market Data:
- Current Price: ${price:,.2f}
- Stop Loss (4%): ${stop_loss:,.2f}
- Tenkan-sen (Conversion Line): {tenkan}
- Kijun-sen (Base Line): {kijun}
- Cloud Status: {cloud_color.capitalize()}
- Cloud Top: {cloud_top}
- Cloud Bottom: {cloud_bottom}
- Signal Confidence: {confidence:.1%}

Provide a concise 2-3 sentence analysis explaining:
1) Why this {signal_type} signal is significant based on Ichimoku indicators
2) Key support/resistance levels to watch
3) One brief risk consideration

Keep it actionable and trader-friendly. Maximum 150 words."""
        
        return prompt
    
    def set_llm_provider(self, provider: str):
        """
        Switch LLM provider.
        
        Args:
            provider: "gemini" or "openai"
        """
        self.llm_provider = provider.lower()
        logger.info(f"Switched LLM provider to {self.llm_provider}")
    
    def get_llm_provider(self) -> str:
        """Get current LLM provider."""
        return self.llm_provider
