"""
Market Data Fetcher for Live Monitoring

Fetches real-time OHLCV data from Binance for signal analysis.
Optimized for 4-hour timeframe monitoring with 300 candles.
"""

import ccxt
import pandas as pd
from datetime import datetime
from typing import Optional
import logging
import time
import random

logger = logging.getLogger(__name__)


class MarketDataFetcher:
    """
    Fetches real-time market data from Binance for live monitoring.
    Focused on 4h timeframe with sufficient historical data for Ichimoku calculation.
    """
    
    def __init__(self, exchange_name: str = 'binance', *, max_retries: int = 0, retry_delay_seconds: int = 5, backoff_factor: float = 2.0):
        """
        Initialize market data fetcher.
        
        Args:
            exchange_name: Name of the exchange (default: binance)
            max_retries: Number of retries on transient network errors
            retry_delay_seconds: Base delay between retries
            backoff_factor: Exponential backoff multiplier
        """
        self.exchange = getattr(ccxt, exchange_name)({
            'timeout': 30000,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
            }
        })
        self.max_retries = max(0, int(max_retries))
        self.retry_delay_seconds = max(0, int(retry_delay_seconds))
        self.backoff_factor = float(backoff_factor) if backoff_factor > 0 else 1.0
        
        logger.info(f"Initialized MarketDataFetcher with {exchange_name}")
    
    def fetch_latest_data(self, 
                         symbol: str, 
                         timeframe: str = '4h', 
                         limit: int = 300) -> pd.DataFrame:
        """
        Fetch the latest OHLCV data for a trading pair.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT', 'ETH/USDT', 'SOL/USDT')
            timeframe: Timeframe for candles (default: '4h')
            limit: Number of candles to fetch (default: 300)
                   300 x 4h = 50 days, sufficient for Senkou Span B (52 periods)
        
        Returns:
            DataFrame with OHLCV data and timestamp index
        """
        attempt = 0
        last_err = None
        while True:
            try:
                logger.info(f"Fetching {limit} candles of {timeframe} data for {symbol}")
                
                # Fetch OHLCV data
                ohlcv = self.exchange.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    limit=limit
                )
                
                if not ohlcv:
                    logger.warning(f"No data received for {symbol}")
                    return pd.DataFrame()
                
                # Convert to DataFrame
                df = pd.DataFrame(
                    ohlcv,
                    columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
                )
                
                # Convert timestamp to datetime
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                
                # Add symbol identifier
                df['symbol'] = symbol
                
                logger.info(f"Successfully fetched {len(df)} candles for {symbol}")
                logger.debug(f"Data range: {df.index[0]} to {df.index[-1]}")
                
                return df
                
            except (ccxt.NetworkError, ccxt.ExchangeNotAvailable, ccxt.DDoSProtection) as e:
                last_err = e
                if attempt < self.max_retries:
                    delay = self.retry_delay_seconds * (self.backoff_factor ** attempt)
                    delay += random.uniform(0, max(0.5, 0.5 * self.retry_delay_seconds))
                    attempt += 1
                    logger.warning(
                        f"Transient error fetching {symbol} OHLCV (attempt {attempt}/{self.max_retries}): {e}. "
                        f"Retrying in {delay:.1f}s"
                    )
                    time.sleep(delay)
                    continue
                logger.error(f"Network error fetching data for {symbol}: {e}")
                raise
            except ccxt.ExchangeError as e:
                # Do not retry on immediate exchange errors (bad params, etc.)
                logger.error(f"Exchange error fetching data for {symbol}: {e}")
                raise
            except Exception as e:
                # Some network stacks propagate different exceptions
                last_err = e
                if attempt < self.max_retries:
                    delay = self.retry_delay_seconds * (self.backoff_factor ** attempt)
                    delay += random.uniform(0, max(0.5, 0.5 * self.retry_delay_seconds))
                    attempt += 1
                    logger.warning(
                        f"Error fetching {symbol} OHLCV (attempt {attempt}/{self.max_retries}): {e}. "
                        f"Retrying in {delay:.1f}s"
                    )
                    time.sleep(delay)
                    continue
                logger.error(f"Unexpected error fetching data for {symbol}: {e}")
                raise
    
    def fetch_multiple_symbols(self, 
                              symbols: list[str], 
                              timeframe: str = '4h', 
                              limit: int = 300) -> dict[str, pd.DataFrame]:
        """
        Fetch data for multiple symbols.
        
        Args:
            symbols: List of trading pairs (e.g., ['BTC/USDT', 'ETH/USDT', 'SOL/USDT'])
            timeframe: Timeframe for candles (default: '4h')
            limit: Number of candles to fetch (default: 300)
        
        Returns:
            Dictionary mapping symbol to DataFrame
        """
        results = {}
        
        for symbol in symbols:
            try:
                df = self.fetch_latest_data(symbol, timeframe, limit)
                if not df.empty:
                    results[symbol] = df
            except Exception as e:
                logger.error(f"Failed to fetch data for {symbol}: {e}")
                # Continue with other symbols
                continue
        
        return results
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """
        Get the latest ticker price for a symbol.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
        
        Returns:
            Latest price or None if error
        """
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker.get('last')
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {e}")
            return None
    
    def validate_symbols(self, symbols: list[str]) -> dict[str, bool]:
        """
        Validate that trading pairs exist on the exchange.
        
        Args:
            symbols: List of trading pairs to validate
        
        Returns:
            Dictionary mapping symbol to validity status
        """
        try:
            markets = self.exchange.load_markets()
            results = {}
            
            for symbol in symbols:
                results[symbol] = symbol in markets
                if not results[symbol]:
                    logger.warning(f"Symbol {symbol} not found on exchange")
            
            return results
            
        except Exception as e:
            logger.error(f"Error validating symbols: {e}")
            return {symbol: False for symbol in symbols}
