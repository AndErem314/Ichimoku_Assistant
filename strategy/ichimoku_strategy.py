"""
Unified Ichimoku Cloud Analysis System - Strategy-Oriented Version

This module provides a comprehensive calculator and signal detection system
for the Ichimoku Cloud indicator, designed to work with strategy configurations.
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
    """Enumeration of available Ichimoku signal types."""
    PRICE_ABOVE_CLOUD = "PriceAboveCloud"
    PRICE_BELOW_CLOUD = "PriceBelowCloud"
    TENKAN_ABOVE_KIJUN = "TenkanAboveKijun"
    TENKAN_BELOW_KIJUN = "TenkanBelowKijun"
    SPAN_A_ABOVE_SPAN_B = "SpanAaboveSpanB"
    SPAN_A_BELOW_SPAN_B = "SpanAbelowSpanB"
    CHIKOU_ABOVE_PRICE = "ChikouAbovePrice"
    CHIKOU_BELOW_PRICE = "ChikouBelowPrice"
    CHIKOU_ABOVE_CLOUD = "ChikouAboveCloud"
    CHIKOU_BELOW_CLOUD = "ChikouBelowCloud"


@dataclass
class IchimokuParameters:
    """Ichimoku calculation parameters."""
    tenkan_period: int = 9
    kijun_period: int = 26
    senkou_b_period: int = 52
    chikou_offset: int = 26
    senkou_offset: int = 26


@dataclass
class SignalConditions:
    """Signal conditions for strategy (legacy buy/sell)."""
    buy_conditions: List[SignalType]
    sell_conditions: List[SignalType]
    buy_logic: str = "AND"  # AND or OR
    sell_logic: str = "AND"  # AND or OR


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

    def check_strategy_signals(self,
                               df: pd.DataFrame,
                               signal_conditions: SignalConditions) -> Dict[str, Any]:
        """
        Check buy/sell signals based on strategy conditions.

        Args:
            df: DataFrame with Ichimoku signals
            signal_conditions: Strategy signal conditions

        Returns:
            Dictionary with signal results
        """
        if len(df) == 0:
            return {"buy_signal": False, "sell_signal": False, "active_signals": {}}

        # Get the latest completed bar
        latest_idx = -2 if len(df) > 1 else -1
        latest = df.iloc[latest_idx]

        # Check buy conditions
        buy_signals = self._check_signal_conditions(latest, signal_conditions.buy_conditions,
                                                    signal_conditions.buy_logic)

        # Check sell conditions
        sell_signals = self._check_signal_conditions(latest, signal_conditions.sell_conditions,
                                                     signal_conditions.sell_logic)

        # Get active signals for monitoring
        active_signals = self._get_active_signals(latest, signal_conditions)

        return {
            "buy_signal": buy_signals["all_conditions_met"],
            "sell_signal": sell_signals["all_conditions_met"],
            "buy_conditions_met": buy_signals["conditions_met"],
            "sell_conditions_met": sell_signals["conditions_met"],
            "active_signals": active_signals,
            "timestamp": df.index[latest_idx]
        }

    def _check_signal_conditions(self,
                                 latest_row: pd.Series,
                                 conditions: List[SignalType],
                                 logic: str) -> Dict[str, Any]:
        """Check individual signal conditions with specified logic."""
        if not conditions:
            return {"all_conditions_met": False, "conditions_met": []}

        conditions_met = []
        conditions_not_met = []

        for condition in conditions:
            column_name = self.signal_mapping.get(condition)
            if column_name and column_name in latest_row:
                if latest_row[column_name]:
                    conditions_met.append(condition.value)
                else:
                    conditions_not_met.append(condition.value)

        # Apply logic (AND or OR)
        if logic.upper() == "AND":
            all_met = len(conditions_met) == len(conditions)
        elif logic.upper() == "OR":
            all_met = len(conditions_met) > 0
        else:
            all_met = False

        return {
            "all_conditions_met": all_met,
            "conditions_met": conditions_met,
            "conditions_not_met": conditions_not_met,
            "total_conditions": len(conditions)
        }

    def _get_active_signals(self, latest_row: pd.Series, signal_conditions: SignalConditions) -> Dict[str, bool]:
        """Get all active signals for monitoring."""
        active_signals = {}

        # Combine all buy and sell conditions
        all_conditions = signal_conditions.buy_conditions + signal_conditions.sell_conditions

        for condition in all_conditions:
            column_name = self.signal_mapping.get(condition)
            if column_name and column_name in latest_row:
                active_signals[condition.value] = bool(latest_row[column_name])

        return active_signals

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

    def generate_strategy_analysis(self,
                                   df: pd.DataFrame,
                                   parameters: IchimokuParameters,
                                   signal_conditions: SignalConditions) -> Dict[str, Any]:
        """
        Generate comprehensive analysis for strategy evaluation.

        Args:
            df: DataFrame with OHLCV data
            parameters: Ichimoku parameters
            signal_conditions: Strategy signal conditions

        Returns:
            Comprehensive analysis dictionary
        """
        # Calculate Ichimoku components
        ichimoku_df = self.calculate_ichimoku_components(df, parameters)

        # Detect boolean signals
        signals_df = self.detect_boolean_signals(ichimoku_df, parameters)

        # Check strategy signals
        signal_results = self.check_strategy_signals(signals_df, signal_conditions)

        # Get current market state
        market_state = self._get_market_state(signals_df)

        # Combine all analysis
        analysis = {
            "signal_results": signal_results,
            "market_state": market_state,
            "ichimoku_parameters": {
                "tenkan_period": parameters.tenkan_period,
                "kijun_period": parameters.kijun_period,
                "senkou_b_period": parameters.senkou_b_period,
                "chikou_offset": parameters.chikou_offset,
                "senkou_offset": parameters.senkou_offset
            },
            "signal_conditions": {
                "buy_conditions": [cond.value for cond in signal_conditions.buy_conditions],
                "sell_conditions": [cond.value for cond in signal_conditions.sell_conditions],
                "buy_logic": signal_conditions.buy_logic,
                "sell_logic": signal_conditions.sell_logic
            }
        }

        return analysis

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
    def create_signal_conditions(buy_conditions: List[SignalType],
                                 sell_conditions: List[SignalType],
                                 buy_logic: str = "AND",
                                 sell_logic: str = "AND") -> SignalConditions:
        """Create signal conditions object (legacy buy/sell)."""
        return SignalConditions(
            buy_conditions=buy_conditions,
            sell_conditions=sell_conditions,
            buy_logic=buy_logic,
            sell_logic=sell_logic
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
        """Parse a list of signal names (case- and style-insensitive) into SignalType enums."""
        name_map = {
            "priceabovecloud": SignalType.PRICE_ABOVE_CLOUD,
            "price_below_cloud": SignalType.PRICE_BELOW_CLOUD,
            "pricebelowcloud": SignalType.PRICE_BELOW_CLOUD,
            "tenkanabovekijun": SignalType.TENKAN_ABOVE_KIJUN,
            "tenkan_below_kijun": SignalType.TENKAN_BELOW_KIJUN,
            "tenkanbelowkijun": SignalType.TENKAN_BELOW_KIJUN,
            "spanaabovespanb": SignalType.SPAN_A_ABOVE_SPAN_B,
            "span_a_above_span_b": SignalType.SPAN_A_ABOVE_SPAN_B,
            "spanabelowspanb": SignalType.SPAN_A_BELOW_SPAN_B,
            "span_a_below_span_b": SignalType.SPAN_A_BELOW_SPAN_B,
            "chikouaboveprice": SignalType.CHIKOU_ABOVE_PRICE,
            "chikou_above_price": SignalType.CHIKOU_ABOVE_PRICE,
            "chikoubelowprice": SignalType.CHIKOU_BELOW_PRICE,
            "chikou_below_price": SignalType.CHIKOU_BELOW_PRICE,
            "chikouabovecloud": SignalType.CHIKOU_ABOVE_CLOUD,
            "chikou_above_cloud": SignalType.CHIKOU_ABOVE_CLOUD,
            "chikoubelowcloud": SignalType.CHIKOU_BELOW_CLOUD,
            "chikou_below_cloud": SignalType.CHIKOU_BELOW_CLOUD,
        }
        parsed: List[SignalType] = []
        for n in signal_names:
            key = n.replace(" ", "").replace("-", "_").replace("__", "_").lower().replace("_", "")
            if key in name_map:
                parsed.append(name_map[key])
        return parsed


# Example usage with strategy configurations
if __name__ == "__main__":
    # Create sample data
    np.random.seed(42)
    dates = pd.date_range(start='2024-01-01', end='2024-03-01', freq='1h')
    close_prices = 50000 + np.cumsum(np.random.normal(0, 100, len(dates)))

    sample_data = pd.DataFrame({
        'timestamp': dates,
        'close': close_prices,
        'high': close_prices + np.random.uniform(0, 200, len(dates)),
        'low': close_prices - np.random.uniform(0, 200, len(dates)),
        'open': close_prices + np.random.uniform(-100, 100, len(dates)),
        'volume': np.random.uniform(100, 1000, len(dates))
    })

    # Initialize analyzer
    analyzer = UnifiedIchimokuAnalyzer()

    # Default strategy: Cloud-TK Base TK Exit
    default_params = IchimokuStrategyConfig.create_parameters()
    default_conditions = IchimokuStrategyConfig.create_signal_conditions(
        buy_conditions=[
            SignalType.PRICE_ABOVE_CLOUD,
            SignalType.TENKAN_ABOVE_KIJUN
        ],
        sell_conditions=[
            SignalType.TENKAN_BELOW_KIJUN
        ]
    )

    # Strategy 02: Cloud-TK-SpanA Base TK Exit
    strategy_02_conditions = IchimokuStrategyConfig.create_signal_conditions(
        buy_conditions=[
            SignalType.PRICE_ABOVE_CLOUD,
            SignalType.TENKAN_ABOVE_KIJUN,
            SignalType.SPAN_A_ABOVE_SPAN_B
        ],
        sell_conditions=[
            SignalType.TENKAN_BELOW_KIJUN
        ]
    )

    # Analyze default strategy
    print("Analyzing ichimoku_default: Cloud-TK Base TK Exit")
    analysis_01 = analyzer.generate_strategy_analysis(
        sample_data, default_params, default_conditions
    )

    print(f"Buy Signal: {analysis_01['signal_results']['buy_signal']}")
    print(f"Sell Signal: {analysis_01['signal_results']['sell_signal']}")
    print(f"Buy Conditions Met: {analysis_01['signal_results']['buy_conditions_met']}")
    print(f"Market State: {analysis_01['market_state']['cloud_color']} cloud")

    # Analyze Strategy 02
    print("\nAnalyzing Strategy 02: Cloud-TK-SpanA Base TK Exit")
    analysis_02 = analyzer.generate_strategy_analysis(
        sample_data, default_params, strategy_02_conditions
    )

    print(f"Buy Signal: {analysis_02['signal_results']['buy_signal']}")
    print(f"Sell Signal: {analysis_02['signal_results']['sell_signal']}")
    print(f"Buy Conditions Met: {analysis_02['signal_results']['buy_conditions_met']}")