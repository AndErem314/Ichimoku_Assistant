"""
Unified Ichimoku Cloud Analysis System - Strategy-Oriented Version

This module provides a comprehensive calculator and signal detection system
for the Ichimoku Cloud indicator, designed to work with strategy configurations.

Signal Architecture:
- Uses StrategyRules with explicit long_entry/short_entry/long_exit/short_exit
- All signals use snake_case naming (e.g., price_above_cloud, tenkan_above_kijun)
- Supports AND/OR logic for combining multiple conditions
- Designed for monitoring/alerting (not automated trading)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union, Any
import logging
from dataclasses import dataclass
from enum import Enum

# Configure logging
logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Enumeration of available Ichimoku signal types (snake_case for consistency)."""
    PRICE_ABOVE_CLOUD = "price_above_cloud"
    PRICE_BELOW_CLOUD = "price_below_cloud"
    TENKAN_ABOVE_KIJUN = "tenkan_above_kijun"
    TENKAN_BELOW_KIJUN = "tenkan_below_kijun"
    SPAN_A_ABOVE_SPAN_B = "span_a_above_span_b"
    SPAN_A_BELOW_SPAN_B = "span_a_below_span_b"
    CHIKOU_ABOVE_PRICE = "chikou_above_price"
    CHIKOU_BELOW_PRICE = "chikou_below_price"
    CHIKOU_ABOVE_CLOUD = "chikou_above_cloud"
    CHIKOU_BELOW_CLOUD = "chikou_below_cloud"


@dataclass
class IchimokuParameters:
    """Ichimoku calculation parameters."""
    tenkan_period: int = 9
    kijun_period: int = 26
    senkou_b_period: int = 52
    chikou_offset: int = 26
    senkou_offset: int = 26


@dataclass
class StrategyRules:
    """Explicit long/short entry/exit rules."""
    long_entry: List[SignalType]
    short_entry: List[SignalType]
    long_exit: List[SignalType]
    short_exit: List[SignalType]
    long_entry_logic: str = "AND"
    short_entry_logic: str = "AND"
    long_exit_logic: str = "AND"
    short_exit_logic: str = "AND"


class UnifiedIchimokuAnalyzer:
    """
    Unified Ichimoku Cloud analysis system designed for strategy configurations.

    This class provides:
    - Complete Ichimoku indicator calculation with configurable parameters
    - Boolean signal detection for strategy conditions
    - Signal combination logic for buy/sell conditions
    - Comprehensive analysis for strategy evaluation
    """

    def __init__(self):
        """Initialize the analyzer with default parameters."""
        self.signal_mapping = {
            SignalType.PRICE_ABOVE_CLOUD: 'price_above_cloud',
            SignalType.PRICE_BELOW_CLOUD: 'price_below_cloud',
            SignalType.TENKAN_ABOVE_KIJUN: 'tenkan_above_kijun',
            SignalType.TENKAN_BELOW_KIJUN: 'tenkan_below_kijun',
            SignalType.SPAN_A_ABOVE_SPAN_B: 'span_a_above_span_b',
            SignalType.SPAN_A_BELOW_SPAN_B: 'span_a_below_span_b',
            SignalType.CHIKOU_ABOVE_PRICE: 'chikou_above_price',
            SignalType.CHIKOU_BELOW_PRICE: 'chikou_below_price',
            SignalType.CHIKOU_ABOVE_CLOUD: 'chikou_above_cloud',
            SignalType.CHIKOU_BELOW_CLOUD: 'chikou_below_cloud'
        }

    def calculate_ichimoku_components(self,
                                      df: pd.DataFrame,
                                      parameters: IchimokuParameters) -> pd.DataFrame:
        """
        Calculate all Ichimoku Cloud components with given parameters.

        Args:
            df: DataFrame with OHLCV data
            parameters: Ichimoku calculation parameters

        Returns:
            DataFrame with Ichimoku components added
        """
        # Input validation
        required_columns = ['high', 'low', 'close']
        missing_columns = set(required_columns) - set(df.columns)
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        result_df = df.copy()

        # Calculate core components
        # Tenkan-sen
        high_tenkan = result_df['high'].rolling(window=parameters.tenkan_period, min_periods=1).max()
        low_tenkan = result_df['low'].rolling(window=parameters.tenkan_period, min_periods=1).min()
        result_df['tenkan_sen'] = (high_tenkan + low_tenkan) / 2

        # Kijun-sen
        high_kijun = result_df['high'].rolling(window=parameters.kijun_period, min_periods=1).max()
        low_kijun = result_df['low'].rolling(window=parameters.kijun_period, min_periods=1).min()
        result_df['kijun_sen'] = (high_kijun + low_kijun) / 2

        # Senkou Span A
        senkou_a_raw = (result_df['tenkan_sen'] + result_df['kijun_sen']) / 2
        result_df['senkou_span_a'] = senkou_a_raw.shift(parameters.senkou_offset)

        # Senkou Span B
        high_senkou = result_df['high'].rolling(window=parameters.senkou_b_period, min_periods=1).max()
        low_senkou = result_df['low'].rolling(window=parameters.senkou_b_period, min_periods=1).min()
        senkou_b_raw = (high_senkou + low_senkou) / 2
        result_df['senkou_span_b'] = senkou_b_raw.shift(parameters.senkou_offset)

        # Chikou Span
        # Chikou Span (lagging): past close at current index
        result_df['chikou_span'] = result_df['close'].shift(parameters.chikou_offset)

        # Calculate derived metrics
        result_df = self._calculate_derived_metrics(result_df)

        logger.info(f"Calculated Ichimoku indicators for {len(result_df)} data points")
        return result_df

    def _calculate_derived_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate derived Ichimoku metrics."""
        result_df = df.copy()

        # Cloud boundaries
        result_df['cloud_top'] = result_df[['senkou_span_a', 'senkou_span_b']].max(axis=1)
        result_df['cloud_bottom'] = result_df[['senkou_span_a', 'senkou_span_b']].min(axis=1)
        result_df['cloud_thickness'] = abs(result_df['senkou_span_a'] - result_df['senkou_span_b'])

        # Cloud color for visualization
        result_df['cloud_color'] = np.where(
            result_df['senkou_span_a'] >= result_df['senkou_span_b'], 'green', 'red'
        )

        # Span relationships for strategies (normalized to snake_case)
        result_df['span_a_above_span_b'] = result_df['senkou_span_a'] > result_df['senkou_span_b']
        result_df['span_a_below_span_b'] = result_df['senkou_span_a'] < result_df['senkou_span_b']

        return result_df

    def detect_boolean_signals(self, df: pd.DataFrame, parameters: IchimokuParameters) -> pd.DataFrame:
        """
        Detect all boolean Ichimoku signals for strategy conditions.

        Args:
            df: DataFrame with Ichimoku components
            parameters: Ichimoku parameters for signal detection

        Returns:
            DataFrame with boolean signal columns added
        """
        if not self._has_ichimoku_columns(df):
            raise ValueError("DataFrame must contain Ichimoku indicators")

        signal_df = df.copy()

        # Use all rows except the last one (current incomplete bar)
        closed_bars_mask = pd.Series(True, index=signal_df.index)
        if len(signal_df) > 0:
            closed_bars_mask.iloc[-1] = False

        # Price vs Cloud signals
        signal_df['price_above_cloud'] = self._detect_price_above_cloud(signal_df, closed_bars_mask)
        signal_df['price_below_cloud'] = self._detect_price_below_cloud(signal_df, closed_bars_mask)

        # Tenkan vs Kijun signals
        signal_df['tenkan_above_kijun'] = self._detect_tenkan_above_kijun(signal_df, closed_bars_mask)
        signal_df['tenkan_below_kijun'] = self._detect_tenkan_below_kijun(signal_df, closed_bars_mask)

        # Chikou signals (only for closed bars)
        signal_df['chikou_above_price'] = self._detect_chikou_above_price(signal_df, closed_bars_mask, parameters)
        signal_df['chikou_below_price'] = self._detect_chikou_below_price(signal_df, closed_bars_mask, parameters)
        signal_df['chikou_above_cloud'] = self._detect_chikou_above_cloud(signal_df, closed_bars_mask, parameters)
        signal_df['chikou_below_cloud'] = self._detect_chikou_below_cloud(signal_df, closed_bars_mask, parameters)

        return signal_df

    def _detect_price_above_cloud(self, df: pd.DataFrame, mask: pd.Series) -> pd.Series:
        """Detect when price is above the cloud (uses precomputed cloud_top)."""
        signal = (df["close"] > df["cloud_top"]) & mask
        return signal.astype(bool)

    def _detect_price_below_cloud(self, df: pd.DataFrame, mask: pd.Series) -> pd.Series:
        """Detect when price is below the cloud (uses precomputed cloud_bottom)."""
        signal = (df["close"] < df["cloud_bottom"]) & mask
        return signal.astype(bool)

    def _detect_tenkan_above_kijun(self, df: pd.DataFrame, mask: pd.Series) -> pd.Series:
        """Detect when Tenkan is above Kijun."""
        signal = (df["tenkan_sen"] > df["kijun_sen"]) & mask
        return signal.astype(bool)

    def _detect_tenkan_below_kijun(self, df: pd.DataFrame, mask: pd.Series) -> pd.Series:
        """Detect when Tenkan is below Kijun."""
        signal = (df["tenkan_sen"] < df["kijun_sen"]) & mask
        return signal.astype(bool)

    def _detect_chikou_above_price(self, df: pd.DataFrame, mask: pd.Series,
                                   parameters: IchimokuParameters) -> pd.Series:
        """Detect when current close is above price at chikou_offset ago."""
        hist_price = df['close'].shift(parameters.chikou_offset)
        signal = (df['close'] > hist_price) & mask
        return signal.astype(bool)

    def _detect_chikou_below_price(self, df: pd.DataFrame, mask: pd.Series,
                                   parameters: IchimokuParameters) -> pd.Series:
        """Detect when current close is below price at chikou_offset ago."""
        hist_price = df['close'].shift(parameters.chikou_offset)
        signal = (df['close'] < hist_price) & mask
        return signal.astype(bool)

    def _detect_chikou_above_cloud(self, df: pd.DataFrame, mask: pd.Series,
                                   parameters: IchimokuParameters) -> pd.Series:
        """Detect when current close is above cloud at chikou_offset ago."""
        hist_cloud_top = df['cloud_top'].shift(parameters.chikou_offset)
        signal = (df['close'] > hist_cloud_top) & mask
        return signal.astype(bool)

    def _detect_chikou_below_cloud(self, df: pd.DataFrame, mask: pd.Series,
                                   parameters: IchimokuParameters) -> pd.Series:
        """Detect when current close is below cloud at chikou_offset ago."""
        hist_cloud_bottom = df['cloud_bottom'].shift(parameters.chikou_offset)
        signal = (df['close'] < hist_cloud_bottom) & mask
        return signal.astype(bool)

    def check_position_signals(self,
                               df: pd.DataFrame,
                               rules: 'StrategyRules') -> Dict[str, Any]:
        """Evaluate long/short entry/exit signals on the latest closed bar."""
        if len(df) == 0:
            return {"long_entry": False, "short_entry": False, "long_exit": False, "short_exit": False, "timestamp": None}

        # Use latest completed bar
        latest_idx = -2 if len(df) > 1 else -1
        latest = df.iloc[latest_idx]

        def _eval(conds: List[SignalType], logic: str) -> bool:
            if not conds:
                return False
            values = []
            for c in conds:
                col = self.signal_mapping.get(c)
                values.append(bool(latest.get(col, False)))
            return all(values) if logic.upper() == "AND" else any(values)

        return {
            "long_entry": _eval(rules.long_entry, rules.long_entry_logic),
            "short_entry": _eval(rules.short_entry, rules.short_entry_logic),
            "long_exit": _eval(rules.long_exit, rules.long_exit_logic),
            "short_exit": _eval(rules.short_exit, rules.short_exit_logic),
            "timestamp": df.index[latest_idx]
        }

    def _get_market_state(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get current market state from Ichimoku data."""
        if len(df) == 0:
            return {}

        latest = df.iloc[-1]

        return {
            "close_price": float(latest['close']) if pd.notna(latest['close']) else None,
            "tenkan_sen": float(latest['tenkan_sen']) if pd.notna(latest['tenkan_sen']) else None,
            "kijun_sen": float(latest['kijun_sen']) if pd.notna(latest['kijun_sen']) else None,
            "senkou_span_a": float(latest['senkou_span_a']) if pd.notna(latest['senkou_span_a']) else None,
            "senkou_span_b": float(latest['senkou_span_b']) if pd.notna(latest['senkou_span_b']) else None,
            "cloud_top": float(latest['cloud_top']) if pd.notna(latest['cloud_top']) else None,
            "cloud_bottom": float(latest['cloud_bottom']) if pd.notna(latest['cloud_bottom']) else None,
            "cloud_color": latest.get('cloud_color', 'unknown'),
            "price_above_cloud": latest.get('price_above_cloud', False),
            "price_below_cloud": latest.get('price_below_cloud', False),
            "tenkan_above_kijun": latest.get('tenkan_above_kijun', False),
            "tenkan_below_kijun": latest.get('tenkan_below_kijun', False),
            "span_a_above_span_b": latest.get('span_a_above_span_b', latest.get('SpanAaboveSpanB', False))
        }

    def _has_ichimoku_columns(self, df: pd.DataFrame) -> bool:
        """Check if DataFrame has required Ichimoku columns."""
        required = ['tenkan_sen', 'kijun_sen', 'senkou_span_a', 'senkou_span_b', 'chikou_span']
        return all(col in df.columns for col in required)


# Strategy Configuration Helper
class IchimokuStrategyConfig:
    """Helper class for creating strategy configurations."""

    @staticmethod
    def create_parameters(tenkan_period: int = 9,
                         kijun_period: int = 26,
                         senkou_b_period: int = 52,
                         chikou_offset: int = 26,
                         senkou_offset: int = 26) -> IchimokuParameters:
        """Create Ichimoku parameters object."""
        return IchimokuParameters(
            tenkan_period=tenkan_period,
            kijun_period=kijun_period,
            senkou_b_period=senkou_b_period,
            chikou_offset=chikou_offset,
            senkou_offset=senkou_offset
        )

    @staticmethod
    def create_strategy_rules(long_entry: List[SignalType],
                              short_entry: List[SignalType],
                              long_exit: List[SignalType],
                              short_exit: List[SignalType],
                              long_entry_logic: str = "AND",
                              short_entry_logic: str = "AND",
                              long_exit_logic: str = "AND",
                              short_exit_logic: str = "AND") -> StrategyRules:
        """Create StrategyRules for explicit long/short entries and exits."""
        return StrategyRules(
            long_entry=long_entry,
            short_entry=short_entry,
            long_exit=long_exit,
            short_exit=short_exit,
            long_entry_logic=long_entry_logic,
            short_entry_logic=short_entry_logic,
            long_exit_logic=long_exit_logic,
            short_exit_logic=short_exit_logic,
        )

    @staticmethod
    def parse_signal_list(signal_names: List[str]) -> List[SignalType]:
        """Parse a list of signal names (snake_case standard) into SignalType enums."""
        # Direct mapping for snake_case signals (standard format)
        name_map = {
            "price_above_cloud": SignalType.PRICE_ABOVE_CLOUD,
            "price_below_cloud": SignalType.PRICE_BELOW_CLOUD,
            "tenkan_above_kijun": SignalType.TENKAN_ABOVE_KIJUN,
            "tenkan_below_kijun": SignalType.TENKAN_BELOW_KIJUN,
            "span_a_above_span_b": SignalType.SPAN_A_ABOVE_SPAN_B,
            "span_a_below_span_b": SignalType.SPAN_A_BELOW_SPAN_B,
            "chikou_above_price": SignalType.CHIKOU_ABOVE_PRICE,
            "chikou_below_price": SignalType.CHIKOU_BELOW_PRICE,
            "chikou_above_cloud": SignalType.CHIKOU_ABOVE_CLOUD,
            "chikou_below_cloud": SignalType.CHIKOU_BELOW_CLOUD,
        }
        
        parsed: List[SignalType] = []
        for n in signal_names:
            # Normalize to snake_case
            normalized = n.lower().replace(" ", "_").replace("-", "_")
            # Remove duplicate underscores
            while "__" in normalized:
                normalized = normalized.replace("__", "_")
            
            if normalized in name_map:
                parsed.append(name_map[normalized])
            else:
                logger.warning(f"Unknown signal name: {n} (normalized: {normalized})")
        
        return parsed

