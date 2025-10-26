"""
Live Crypto Trading Monitor - Main Entry Point

Monitors BTC/USDT, ETH/USDT, and SOL/USDT every 4 hours.
Detects Ichimoku signals and sends notifications via Discord/Telegram.
"""

import os
import sys
import yaml
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

from live_monitor import MarketDataFetcher, SignalDetector, StateManager, MonitorScheduler
from notifications import DiscordNotifier, TelegramNotifier, MessageFormatter


class CryptoMonitor:
    """
    Main orchestrator for crypto trading monitor.
    
    Coordinates data fetching, signal detection, and notifications.
    """
    
    def __init__(self, config_path: str = "config/monitor_config.yaml"):
        """Initialize monitor with configuration."""
        self.config = self._load_config(config_path)
        self._setup_logging()
        self._initialize_components()
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("=" * 70)
        self.logger.info("Crypto Trading Monitor Initialized")
        self.logger.info("=" * 70)
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    
    def _setup_logging(self):
        """Setup logging configuration."""
        log_config = self.config.get('logging', {})
        log_level = getattr(logging, log_config.get('level', 'INFO'))
        
        # Create logs directory
        log_file_config = log_config.get('file', {})
        if log_file_config.get('enabled', True):
            log_path = Path(log_file_config.get('path', 'logs/monitor.log'))
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Setup file handler with rotation
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                log_path,
                maxBytes=log_file_config.get('max_size_mb', 10) * 1024 * 1024,
                backupCount=log_file_config.get('backup_count', 5)
            )
            file_handler.setLevel(log_level)
            
            # Setup console handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(log_level)
            
            # Configure logging
            logging.basicConfig(
                level=log_level,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[file_handler, console_handler]
            )
        else:
            logging.basicConfig(
                level=log_level,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
    
    def _initialize_components(self):
        """Initialize all monitoring components."""
        # Market data fetcher
        self.data_fetcher = MarketDataFetcher()
        
        # Signal detector
        self.signal_detector = SignalDetector()
        
        # State manager
        state_path = self.config.get('state', {}).get('file_path', 'data/state/signal_states.json')
        self.state_manager = StateManager(state_path)
        
        # Message formatter
        llm_config = self.config.get('llm', {})
        llm_provider = llm_config.get('provider', 'gemini')
        llm_enabled = llm_config.get('enabled', True)
        self.message_formatter = MessageFormatter(
            llm_provider=llm_provider,
            enable_llm=llm_enabled
        )
        
        # Initialize notifiers
        self._initialize_notifiers()
    
    def _initialize_notifiers(self):
        """Initialize notification services."""
        notification_config = self.config.get('notifications', {})
        
        self.notifiers = []
        
        # Discord
        if notification_config.get('discord', {}).get('enabled', False):
            webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
            if webhook_url:
                discord = DiscordNotifier(webhook_url)
                self.notifiers.append(('Discord', discord))
                self.logger.info("Discord notifier enabled")
            else:
                self.logger.warning("Discord enabled but DISCORD_WEBHOOK_URL not found in .env")
        
        # Telegram
        if notification_config.get('telegram', {}).get('enabled', False):
            bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
            chat_id = os.getenv('TELEGRAM_CHAT_ID')
            if bot_token and chat_id:
                telegram = TelegramNotifier(bot_token, chat_id)
                self.notifiers.append(('Telegram', telegram))
                self.logger.info("Telegram notifier enabled")
            else:
                self.logger.warning("Telegram enabled but TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not found in .env")
        
        if not self.notifiers:
            self.logger.warning("No notifiers enabled! Signals will be logged but not sent.")
        
        # Send test messages if configured
        if notification_config.get('test_on_startup', False):
            self._send_test_notifications()
    
    def _send_test_notifications(self):
        """Send test notifications on startup."""
        self.logger.info("Sending test notifications...")
        for name, notifier in self.notifiers:
            try:
                notifier.send_test_message()
                self.logger.info(f"✓ {name} test message sent")
            except Exception as e:
                self.logger.error(f"✗ {name} test failed: {e}")
    
    def analyze_and_notify(self):
        """Main analysis loop - runs every 4 hours."""
        monitoring_config = self.config.get('monitoring', {})
        symbols = monitoring_config.get('symbols', ['BTC/USDT', 'ETH/USDT', 'SOL/USDT'])
        timeframe = monitoring_config.get('timeframe', '4h')
        data_points = monitoring_config.get('data_points', 300)
        
        self.logger.info(f"Starting analysis cycle at {datetime.utcnow().isoformat()}")
        
        for symbol in symbols:
            try:
                self.logger.info(f"Analyzing {symbol}...")
                
                # 1. Fetch market data
                data = self.data_fetcher.fetch_latest_data(
                    symbol=symbol,
                    timeframe=timeframe,
                    limit=data_points
                )
                
                if data.empty:
                    self.logger.warning(f"No data received for {symbol}, skipping")
                    continue
                
                # 2. Detect signal
                signal_result = self.signal_detector.detect_signal(data, symbol)
                
                self.logger.info(
                    f"{symbol}: {signal_result.signal_type} "
                    f"(confidence: {signal_result.confidence:.1%})"
                )
                
                # 3. Check if signal changed
                if self.state_manager.has_signal_changed(symbol, signal_result.signal_type):
                    self.logger.info(f"New signal for {symbol}: {signal_result.signal_type}")
                    
                    # 4. Format message with LLM analysis
                    formatted = self.message_formatter.format_signal(
                        symbol=symbol,
                        signal_type=signal_result.signal_type,
                        confidence=signal_result.confidence,
                        ichimoku_values=signal_result.ichimoku_values,
                        timestamp=signal_result.timestamp
                    )
                    
                    # 5. Send notifications
                    self._send_notifications(formatted)
                    
                    # 6. Update state
                    self.state_manager.update_state(
                        symbol=symbol,
                        signal_type=signal_result.signal_type,
                        confidence=signal_result.confidence,
                        timestamp=signal_result.timestamp.isoformat()
                    )
                else:
                    self.logger.debug(f"No signal change for {symbol}")
                
            except Exception as e:
                self.logger.error(f"Error analyzing {symbol}: {e}", exc_info=True)
                
                # Continue with other symbols if configured
                if not self.config.get('error_handling', {}).get('continue_on_error', True):
                    raise
        
        self.logger.info("Analysis cycle completed")
        self.logger.info("-" * 70)
    
    def _send_notifications(self, formatted: Dict):
        """Send notifications via all enabled channels."""
        for name, notifier in self.notifiers:
            try:
                success = notifier.send_signal(
                    symbol=formatted['symbol'],
                    signal_type=formatted['signal_type'],
                    confidence=formatted['confidence'],
                    price=formatted['price'],
                    stop_loss=formatted['stop_loss'],
                    ichimoku_values=formatted['ichimoku_values'],
                    llm_analysis=formatted.get('llm_analysis'),
                    timestamp=formatted['timestamp']
                )
                
                if success:
                    self.logger.info(f"✓ {name} notification sent for {formatted['symbol']}")
                else:
                    self.logger.warning(f"✗ {name} notification failed for {formatted['symbol']}")
                    
            except Exception as e:
                self.logger.error(f"Error sending {name} notification: {e}")
    
    def start(self):
        """Start the monitoring service."""
        if not self.config.get('monitoring', {}).get('enabled', True):
            self.logger.warning("Monitoring is disabled in configuration")
            return
        
        # Show configuration
        self._show_configuration()
        
        # Run immediately if configured
        if self.config.get('monitoring', {}).get('run_on_startup', True):
            self.logger.info("Running initial analysis...")
            try:
                self.analyze_and_notify()
            except Exception as e:
                self.logger.error(f"Error in initial analysis: {e}", exc_info=True)
        
        # Setup scheduler
        scheduler = MonitorScheduler(self.analyze_and_notify)
        
        # Start scheduled monitoring
        try:
            self.logger.info("Starting scheduled monitoring...")
            scheduler.start(run_immediately=False)  # Already ran above if configured
        except KeyboardInterrupt:
            self.logger.info("Shutting down monitor...")
            scheduler.stop()
        except Exception as e:
            self.logger.error(f"Fatal error: {e}", exc_info=True)
            raise
    
    def _show_configuration(self):
        """Display current configuration."""
        monitoring = self.config.get('monitoring', {})
        notifications = self.config.get('notifications', {})
        llm = self.config.get('llm', {})
        
        self.logger.info("Configuration:")
        self.logger.info(f"  Symbols: {', '.join(monitoring.get('symbols', []))}")
        self.logger.info(f"  Timeframe: {monitoring.get('timeframe', '4h')}")
        self.logger.info(f"  Data points: {monitoring.get('data_points', 300)}")
        self.logger.info(f"  Discord: {'Enabled' if notifications.get('discord', {}).get('enabled') else 'Disabled'}")
        self.logger.info(f"  Telegram: {'Enabled' if notifications.get('telegram', {}).get('enabled') else 'Disabled'}")
        self.logger.info(f"  LLM: {llm.get('provider', 'gemini')} ({'Enabled' if llm.get('enabled') else 'Disabled'})")
        self.logger.info("-" * 70)


def main():
    """Main entry point."""
    try:
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        # Create and start monitor
        monitor = CryptoMonitor()
        monitor.start()
        
    except KeyboardInterrupt:
        print("\n✓ Monitor stopped by user")
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
