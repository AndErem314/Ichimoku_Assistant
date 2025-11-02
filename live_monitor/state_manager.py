"""
State Manager for Live Monitoring

Tracks signal states for each symbol to avoid duplicate notifications.
Persists state to disk for Docker container restarts.
"""

import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class StateManager:
    """
    Manages signal states for each trading pair.
    
    Tracks:
    - Current signal type (LONG, SHORT, EXIT LONG, EXIT SHORT, NONE)
    - Last signal change timestamp
    - Signal confidence
    
    Persists state to JSON file to survive restarts.
    """
    
    def __init__(self, state_file_path: Optional[str] = None):
        """
        Initialize state manager.
        
        Args:
            state_file_path: Path to state JSON file
                           If None, uses data/state/signal_states.json
        """
        if state_file_path is None:
            state_dir = Path(__file__).parent.parent / 'data' / 'state'
            state_dir.mkdir(parents=True, exist_ok=True)
            state_file_path = state_dir / 'signal_states.json'
        
        self.state_file = Path(state_file_path)
        self.states = self._load_states()
        
        logger.info(f"Initialized StateManager with state file: {self.state_file}")
    
    def _load_states(self) -> Dict:
        """Load states from JSON file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    states = json.load(f)
                logger.info(f"Loaded states for {len(states)} symbols")
                return states
            except Exception as e:
                logger.error(f"Error loading states: {e}")
                return {}
        else:
            logger.info("No existing state file found, starting fresh")
            return {}
    
    def _save_states(self):
        """Save states to JSON file."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.states, f, indent=2, default=str)
            logger.debug(f"Saved states to {self.state_file}")
        except Exception as e:
            logger.error(f"Error saving states: {e}")
    
    def get_state(self, symbol: str) -> Optional[Dict]:
        """
        Get current state for a symbol.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
        
        Returns:
            State dictionary or None if no state exists
        """
        return self.states.get(symbol)
    
    def update_state(self, 
                    symbol: str, 
                    signal_type: str, 
                    confidence: float = 1.0,
                    timestamp: Optional[str] = None,
                    details: Optional[Dict] = None):
        """
        Update state for a symbol.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            signal_type: Signal type (LONG, SHORT, EXIT LONG, EXIT SHORT, NONE)
            confidence: Signal confidence (0.0 to 1.0)
            timestamp: ISO timestamp of signal (defaults to now)
            details: Additional details about the signal
        """
        if timestamp is None:
            timestamp = datetime.utcnow().isoformat()
        
        # Only record and log when the signal type actually changes
        current = self.states.get(symbol)
        if current and current.get('signal_type') == signal_type:
            logger.debug(f"State unchanged for {symbol}: {signal_type}, not updating timestamp")
            return
        
        self.states[symbol] = {
            'signal_type': signal_type,
            'confidence': confidence,
            'timestamp': timestamp,
            'details': details or {}
        }
        
        self._save_states()
        logger.info(f"Updated state for {symbol}: {signal_type} (confidence: {confidence:.2%})")
    
    def has_signal_changed(self, symbol: str, new_signal_type: str) -> bool:
        """
        Check if signal has changed for a symbol.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            new_signal_type: New signal type to compare
        
        Returns:
            True if signal has changed, False otherwise
        """
        current_state = self.get_state(symbol)
        
        # If no previous state, this is a new signal
        if current_state is None:
            # Only report actionable signals on first run
            if new_signal_type != "NONE":
                logger.info(f"New symbol {symbol}, signal: {new_signal_type}")
                return True
            else:
                logger.info(f"New symbol {symbol}, no actionable signal yet")
                return False
        
        # Check if signal type has changed
        previous_signal = current_state.get('signal_type', 'NONE')
        
        if previous_signal != new_signal_type:
            # Signal has changed
            if new_signal_type != "NONE":
                logger.info(f"Signal changed for {symbol}: {previous_signal} -> {new_signal_type}")
                return True
            else:
                # Signal returned to NONE - don't notify
                logger.info(f"Signal for {symbol} returned to NONE (was {previous_signal})")
                # Still update state but don't notify
                return False
        else:
            # Signal unchanged
            logger.debug(f"Signal unchanged for {symbol}: {new_signal_type}")
            return False
    
    def clear_state(self, symbol: str):
        """
        Clear state for a symbol.
        
        Args:
            symbol: Trading pair to clear
        """
        if symbol in self.states:
            del self.states[symbol]
            self._save_states()
            logger.info(f"Cleared state for {symbol}")
    
    def clear_all_states(self):
        """Clear all states."""
        self.states = {}
        self._save_states()
        logger.info("Cleared all states")
    
    def get_all_states(self) -> Dict:
        """Get all current states."""
        return self.states.copy()
    
    def get_symbols_with_active_signals(self) -> Dict[str, str]:
        """
        Get symbols with active signals (not NONE).
        
        Returns:
            Dictionary mapping symbol to signal type
        """
        active = {}
        for symbol, state in self.states.items():
            signal_type = state.get('signal_type', 'NONE')
            if signal_type != 'NONE':
                active[symbol] = signal_type
        return active
    
    def get_summary(self) -> Dict:
        """Get summary of all states."""
        summary = {
            'total_symbols': len(self.states),
            'active_signals': 0,
            'signals_by_type': {
                'LONG': 0,
                'SHORT': 0,
                'EXIT LONG': 0,
                'EXIT SHORT': 0,
                'NONE': 0
            }
        }
        
        for state in self.states.values():
            signal_type = state.get('signal_type', 'NONE')
            summary['signals_by_type'][signal_type] = summary['signals_by_type'].get(signal_type, 0) + 1
            if signal_type != 'NONE':
                summary['active_signals'] += 1
        
        return summary
