"""
Signal Detector for Live Monitoring

Calculates Ichimoku indicators and detects trading signals based on the default Ichimoku strategy (ichimoku_default).
Supports LONG, SHORT, EXIT LONG, and EXIT SHORT signal detection.
"""

import pandas as pd
import yaml
from pathlib import Path
from typing import Dict, Optional, Tuple, List
import logging
from dataclasses import dataclass

from strategy.ichimoku_strategy import (
    UnifiedIchimokuAnalyzer,
    IchimokuParameters,
    SignalType,
    StrategyRules
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
    
    Implements ichimoku_default logic with explicit long/short entry/exit:
    - LONG: All long_entry conditions met
    - SHORT: All short_entry conditions met
    - EXIT LONG: All long_exit conditions met
    - EXIT SHORT: All short_exit conditions met
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
        
        # Parse strategy rules (long/short entry/exit)
        self.strategy_rules = self._parse_strategy_rules()
        
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
    
    def _parse_strategy_rules(self) -> StrategyRules:
        """Parse strategy rules (long/short entry/exit) from config."""
        conditions = self.strategy['signal_conditions']
        
        # Convert string conditions to SignalType enums
        long_entry = [
            SignalType(cond) for cond in conditions['long_entry']
        ]
        short_entry = [
            SignalType(cond) for cond in conditions['short_entry']
        ]
        long_exit = [
            SignalType(cond) for cond in conditions['long_exit']
        ]
        short_exit = [
            SignalType(cond) for cond in conditions['short_exit']
        ]
        
        return StrategyRules(
            long_entry=long_entry,
            short_entry=short_entry,
            long_exit=long_exit,
            short_exit=short_exit,
            long_entry_logic=conditions.get('long_entry_logic', 'AND'),
            short_entry_logic=conditions.get('short_entry_logic', 'AND'),
            long_exit_logic=conditions.get('long_exit_logic', 'AND'),
            short_exit_logic=conditions.get('short_exit_logic', 'AND')
        )
    
    def detect_signal(self, data: pd.DataFrame, symbol: str) -> SignalResult:
        """
        Detect trading signal from OHLCV data using StrategyRules.
        
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
            
            # Use check_position_signals to evaluate all entry/exit conditions
            position_signals = self.analyzer.check_position_signals(
                signals_df, self.strategy_rules
            )
            
            # Get latest completed bar (second to last)
            latest_idx = -2 if len(signals_df) > 1 else -1
            latest = signals_df.iloc[latest_idx]
            
            # Determine signal type from position signals
            signal_type, confidence = self._determine_signal_type(
                position_signals, latest
            )
            
            # Extract Ichimoku values for reporting
            ichimoku_values = self._extract_ichimoku_values(latest)
            
            result = SignalResult(
                signal_type=signal_type,
                symbol=symbol,
                timestamp=position_signals['timestamp'],
                confidence=confidence,
                details=position_signals,
                ichimoku_values=ichimoku_values
            )
            
            logger.debug(f"Detected {signal_type} signal for {symbol} with confidence {confidence:.2%}")
            return result
            
        except Exception as e:
            logger.error(f"Error detecting signal for {symbol}: {e}")
            raise
    
    def _determine_signal_type(self, 
                               position_signals: Dict, 
                               latest_row: pd.Series) -> Tuple[str, float]:
        """
        Determine signal type from position_signals (long/short entry/exit).
        
        Logic:
        - LONG: long_entry is True
        - SHORT: short_entry is True
        - EXIT LONG: long_exit is True
        - EXIT SHORT: short_exit is True
        - NONE: No conditions met
        
        Returns:
            Tuple of (signal_type, confidence)
        """
        # Priority: Entry signals first, then exit signals
        if position_signals['long_entry']:
            confidence = self._calculate_confidence(
                self.strategy_rules.long_entry, latest_row
            )
            return "LONG", confidence
        
        elif position_signals['short_entry']:
            confidence = self._calculate_confidence(
                self.strategy_rules.short_entry, latest_row
            )
            return "SHORT", confidence
        
        elif position_signals['long_exit']:
            confidence = self._calculate_confidence(
                self.strategy_rules.long_exit, latest_row
            )
            return "EXIT LONG", confidence
        
        elif position_signals['short_exit']:
            confidence = self._calculate_confidence(
                self.strategy_rules.short_exit, latest_row
            )
            return "EXIT SHORT", confidence
        
        else:
            # No actionable signal
            return "NONE", 0.0
    
    def _calculate_confidence(self, conditions: List[SignalType], latest_row: pd.Series) -> float:
        """Calculate confidence based on percentage of conditions met."""
        if not conditions:
            return 0.0
        
        met = 0
        for condition in conditions:
            column_name = self.analyzer.signal_mapping.get(condition)
            if column_name and latest_row.get(column_name, False):
                met += 1
        
        return met / len(conditions)
    
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
            'long_entry_conditions': [cond.value for cond in self.strategy_rules.long_entry],
            'short_entry_conditions': [cond.value for cond in self.strategy_rules.short_entry],
            'long_exit_conditions': [cond.value for cond in self.strategy_rules.long_exit],
            'short_exit_conditions': [cond.value for cond in self.strategy_rules.short_exit],
            'long_entry_logic': self.strategy_rules.long_entry_logic,
            'short_entry_logic': self.strategy_rules.short_entry_logic,
            'long_exit_logic': self.strategy_rules.long_exit_logic,
            'short_exit_logic': self.strategy_rules.short_exit_logic,
            'ichimoku_parameters': {
                'tenkan_period': self.parameters.tenkan_period,
                'kijun_period': self.parameters.kijun_period,
                'senkou_b_period': self.parameters.senkou_b_period,
                'chikou_offset': self.parameters.chikou_offset,
                'senkou_offset': self.parameters.senkou_offset
            }
        }
