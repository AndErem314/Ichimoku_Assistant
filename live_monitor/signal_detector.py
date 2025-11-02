"""
Signal Detector for Live Monitoring

Calculates Ichimoku indicators and detects trading signals based on the default Ichimoku strategy (ichimoku_default).
Supports LONG, SHORT, EXIT LONG, and EXIT SHORT signal detection.
"""

import pandas as pd
import yaml
from pathlib import Path
from typing import Dict, Optional, Tuple
import logging
from dataclasses import dataclass

from strategy.ichimoku_strategy import (
    UnifiedIchimokuAnalyzer,
    IchimokuParameters,
    SignalType,
    SignalConditions
)

logger = logging.getLogger(__name__)


@dataclass
class SignalResult:
    """Result of signal detection."""
    signal_type: str  # "LONG", "SHORT", "EXIT LONG", "EXIT SHORT", "NONE"
    symbol: str
    timestamp: pd.Timestamp
    confidence: float  # Number of conditions met / total conditions
    details: Dict
    ichimoku_values: Dict


class SignalDetector:
    """
    Detects trading signals using Ichimoku Cloud indicators.
    
    Implements ichimoku_default logic:
    - LONG: All buy conditions met
    - EXIT LONG: Sell conditions met (exit long position)
    - SHORT: All inverse conditions met
    - EXIT SHORT: Buy conditions met (exit short position)
    """
    
    def __init__(self, strategy_config_path: Optional[str] = None):
        """
        Initialize signal detector.
        
        Args:
            strategy_config_path: Path to strategy.yaml file
                                 If None, uses default config/strategy.yaml
        """
        self.analyzer = UnifiedIchimokuAnalyzer()
        
        # Load strategy configuration
        if strategy_config_path is None:
            config_dir = Path(__file__).parent.parent / 'config'
            strategy_config_path = config_dir / 'strategy.yaml'
        
        self.strategy_config = self._load_strategy_config(strategy_config_path)
        
        # Use ichimoku_default by default
        self.strategy = self.strategy_config['strategies']['ichimoku_default']
        
        # Parse Ichimoku parameters
        self.parameters = self._parse_ichimoku_parameters()
        
        # Parse signal conditions
        self.signal_conditions = self._parse_signal_conditions()
        
        logger.info(f"Initialized SignalDetector with strategy: {self.strategy['name']}")
    
    def _load_strategy_config(self, config_path: Path) -> Dict:
        """Load strategy configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded strategy configuration from {config_path}")
            return config
        except Exception as e:
            logger.error(f"Error loading strategy config: {e}")
            raise
    
    def _parse_ichimoku_parameters(self) -> IchimokuParameters:
        """Parse Ichimoku parameters from strategy config."""
        params = self.strategy['ichimoku_parameters']
        return IchimokuParameters(
            tenkan_period=params['tenkan_period'],
            kijun_period=params['kijun_period'],
            senkou_b_period=params['senkou_b_period'],
            chikou_offset=params['chikou_offset'],
            senkou_offset=params['senkou_offset']
        )
    
    def _parse_signal_conditions(self) -> SignalConditions:
        """Parse signal conditions from strategy config."""
        conditions = self.strategy['signal_conditions']
        
        # Convert string conditions to SignalType enums
        buy_conditions = [
            SignalType(cond) for cond in conditions['buy_conditions']
        ]
        sell_conditions = [
            SignalType(cond) for cond in conditions['sell_conditions']
        ]
        
        return SignalConditions(
            buy_conditions=buy_conditions,
            sell_conditions=sell_conditions,
            buy_logic=conditions['buy_logic'],
            sell_logic=conditions['sell_logic']
        )
    
    def detect_signal(self, data: pd.DataFrame, symbol: str) -> SignalResult:
        """
        Detect trading signal from OHLCV data.
        
        Args:
            data: DataFrame with OHLCV data
            symbol: Trading pair symbol
        
        Returns:
            SignalResult with detected signal type and details
        """
        try:
            # Calculate Ichimoku components
            ichimoku_df = self.analyzer.calculate_ichimoku_components(
                data, self.parameters
            )
            
            # Detect boolean signals
            signals_df = self.analyzer.detect_boolean_signals(
                ichimoku_df, self.parameters
            )
            
            # Check strategy signals
            signal_results = self.analyzer.check_strategy_signals(
                signals_df, self.signal_conditions
            )
            
            # Get latest completed bar (second to last)
            latest_idx = -2 if len(signals_df) > 1 else -1
            latest = signals_df.iloc[latest_idx]
            
            # Determine signal type
            signal_type, confidence = self._determine_signal_type(
                signal_results, latest
            )
            
            # Extract Ichimoku values for reporting
            ichimoku_values = self._extract_ichimoku_values(latest)
            
            result = SignalResult(
                signal_type=signal_type,
                symbol=symbol,
                timestamp=signals_df.index[latest_idx],
                confidence=confidence,
                details=signal_results,
                ichimoku_values=ichimoku_values
            )
            
            logger.debug(f"Detected {signal_type} signal for {symbol} with confidence {confidence:.2%}")
            return result
            
        except Exception as e:
            logger.error(f"Error detecting signal for {symbol}: {e}")
            raise
    
    def _determine_signal_type(self, 
                               signal_results: Dict, 
                               latest_row: pd.Series) -> Tuple[str, float]:
        """
        Determine signal type based on buy/sell conditions.
        
        Logic:
        - LONG: All buy conditions met
        - EXIT LONG: Sell conditions met
        - SHORT: All inverse (bearish) conditions met
        - EXIT SHORT: Buy conditions met while in bearish setup
        
        Returns:
            Tuple of (signal_type, confidence)
        """
        buy_signal = signal_results['buy_signal']
        sell_signal = signal_results['sell_signal']
        
        # Calculate confidence (percentage of conditions met)
        buy_conditions_met = len(signal_results['buy_conditions_met'])
        total_buy_conditions = len(self.signal_conditions.buy_conditions)
        buy_confidence = buy_conditions_met / total_buy_conditions if total_buy_conditions > 0 else 0
        
        sell_conditions_met = len(signal_results['sell_conditions_met'])
        total_sell_conditions = len(self.signal_conditions.sell_conditions)
        sell_confidence = sell_conditions_met / total_sell_conditions if total_sell_conditions > 0 else 0
        
        # Detect SHORT conditions (inverse of LONG)
        short_signal = self._check_short_conditions(latest_row)
        
        # Determine signal type
        if buy_signal:
            # Check if this is EXIT SHORT or new LONG
            if short_signal:
                return "EXIT SHORT", buy_confidence
            else:
                return "LONG", buy_confidence
        
        elif sell_signal:
            # This is EXIT LONG
            return "EXIT LONG", sell_confidence
        
        elif short_signal:
            # Pure SHORT signal (all bearish conditions met)
            short_confidence = self._calculate_short_confidence(latest_row)
            return "SHORT", short_confidence
        
        else:
            # No actionable signal
            return "NONE", 0.0
    
    def _check_short_conditions(self, latest_row: pd.Series) -> bool:
        """
        Check if SHORT conditions are met (inverse of LONG conditions).
        
        SHORT conditions:
        - Price below cloud
        - Tenkan below Kijun
        - Span A below Span B
        - Chikou below cloud
        - Chikou below price
        """
        try:
            conditions = [
                latest_row.get('price_below_cloud', False),
                latest_row.get('tenkan_below_kijun', False),
                latest_row.get('SpanAbelowSpanB', False),
                latest_row.get('chikou_below_cloud', False),
                latest_row.get('chikou_below_price', False)
            ]
            
            # All conditions must be True for SHORT signal
            return all(conditions)
            
        except Exception as e:
            logger.error(f"Error checking SHORT conditions: {e}")
            return False
    
    def _calculate_short_confidence(self, latest_row: pd.Series) -> float:
        """Calculate confidence for SHORT signal."""
        short_conditions = [
            latest_row.get('price_below_cloud', False),
            latest_row.get('tenkan_below_kijun', False),
            latest_row.get('SpanAbelowSpanB', False),
            latest_row.get('chikou_below_cloud', False),
            latest_row.get('chikou_below_price', False)
        ]
        
        met = sum(short_conditions)
        total = len(short_conditions)
        
        return met / total if total > 0 else 0.0
    
    def _extract_ichimoku_values(self, latest_row: pd.Series) -> Dict:
        """Extract Ichimoku indicator values for reporting."""
        return {
            'close': float(latest_row['close']),
            'tenkan_sen': float(latest_row['tenkan_sen']) if pd.notna(latest_row['tenkan_sen']) else None,
            'kijun_sen': float(latest_row['kijun_sen']) if pd.notna(latest_row['kijun_sen']) else None,
            'senkou_span_a': float(latest_row['senkou_span_a']) if pd.notna(latest_row['senkou_span_a']) else None,
            'senkou_span_b': float(latest_row['senkou_span_b']) if pd.notna(latest_row['senkou_span_b']) else None,
            'chikou_span': float(latest_row['chikou_span']) if pd.notna(latest_row['chikou_span']) else None,
            'cloud_color': latest_row.get('cloud_color', 'unknown'),
            'cloud_top': float(latest_row['cloud_top']) if pd.notna(latest_row.get('cloud_top')) else None,
            'cloud_bottom': float(latest_row['cloud_bottom']) if pd.notna(latest_row.get('cloud_bottom')) else None,
        }
    
    def get_strategy_info(self) -> Dict:
        """Get information about the current strategy being used."""
        return {
            'name': self.strategy['name'],
            'description': self.strategy['description'],
            'timeframes': self.strategy['timeframes'],
            'symbols': self.strategy['symbols'],
            'buy_conditions': [cond.value for cond in self.signal_conditions.buy_conditions],
            'sell_conditions': [cond.value for cond in self.signal_conditions.sell_conditions],
            'buy_logic': self.signal_conditions.buy_logic,
            'sell_logic': self.signal_conditions.sell_logic,
            'ichimoku_parameters': {
                'tenkan_period': self.parameters.tenkan_period,
                'kijun_period': self.parameters.kijun_period,
                'senkou_b_period': self.parameters.senkou_b_period,
                'chikou_offset': self.parameters.chikou_offset,
                'senkou_offset': self.parameters.senkou_offset
            }
        }
