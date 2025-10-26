## 📋 Detailed Implementation Plan: Live Crypto Trading Assistant

### **Project Overview**
Create a Dockerized service that monitors BTC/USDT, SOL/USDT, and ETH/USDT every 4 hours, calculates Ichimoku signals using existing strategy logic, and sends alerts via Discord/Telegram/Email when LONG or SHORT signals are detected with LLM-enhanced insights.

---

### **Architecture Components**

#### **1. Final Project Structure**
```
Ichimoku_Assistant/
├── .env                       # API keys & configuration
├── .gitignore
├── requirements.txt
├── IMPLEMENTATION_PLAN.md
├── PHASE1_COMPLETED.md        ✅ Phase 1 complete
├── PHASE2_COMPLETED.md        ✅ Phase 2 complete
├── test_phase1.py
│
├── config/
│   └── strategy.yaml         # Ichimoku strategy configuration (ichimoku_default)
│
├── live_monitor/              ✅ Phase 1 - Core Monitoring
│   ├── __init__.py
│   ├── market_data_fetcher.py # Fetch 4h data from Binance
│   ├── signal_detector.py     # Detect LONG/SHORT/EXIT signals
│   ├── state_manager.py       # Track state, avoid duplicates
│   └── scheduler.py           # Run at 00:00:15, 04:00:15, etc.
│
├── notifications/             ✅ Phase 2 - Alert System
│   ├── __init__.py
│   ├── discord_notifier.py    # Discord webhook notifications
│   ├── telegram_notifier.py   # Telegram bot API notifications
│   └── message_formatter.py   # LLM-enhanced messages (Gemini/OpenAI)
│
├── llm_analysis/              # Minimal LLM support (cleaned up)
│   ├── __init__.py
│   ├── env_loader.py          # Load API keys from .env
│   └── llm_client.py          # Unified Gemini/OpenAI client
│
├── strategy/
│   └── ichimoku_strategy.py   # Core Ichimoku calculation
│
├── data/
│   └── state/
│       └── signal_states.json # Runtime state file
│
└── docker/                    # Phase 3 - To be implemented
    ├── Dockerfile
    └── docker-compose.yml
```

**Note:** Obsolete modules removed:
- ❌ `data_fetching/` - SQL-based (not needed)
- ❌ `backtesting/` - Historical analysis (separate use case)
- ❌ `reporting/` - PDF generation (not needed)
- ❌ `app.py` - Old CLI interface

---

### **Phase 1: Core Monitoring Infrastructure**

#### **1.1 Market Data Fetcher** (`live_monitor/market_data_fetcher.py`)
- **Purpose**: Fetch latest 300 candles for 4h timeframe from Binance
- **Reuse**: Leverage existing `data_fetching/data_fetcher.py` DataCollector
- **Key Features**:
  - Use Binance API (via CCXT library already in requirements)
  - Fetch 300 x 4h candles = ~50 days of data (sufficient for Ichimoku with 52-period Senkou B)
  - Store temporarily in memory (no DB needed for live monitoring)
  - Error handling for API rate limits

#### **1.2 Signal Detector** (`live_monitor/signal_detector.py`)
- **Purpose**: Calculate Ichimoku and detect LONG/SHORT/EXIT signals
- **Reuse**: 
  - `strategy/ichimoku_strategy.py` for indicator calculation
  - `config/strategy.yaml` ichimoku_default for signal conditions
- **Logic**:
  - Calculate Ichimoku components (Tenkan, Kijun, Senkou A/B, Chikou)
  - Evaluate buy_conditions from ichimoku_default:
    - PriceAboveCloud
    - TenkanAboveKijun
    - SpanAaboveSpanB
    - ChikouAboveCloud
    - ChikouAbovePrice
  - Evaluate sell_conditions (TenkanBelowKijun)
  - Return signal: "LONG", "SHORT", "EXIT LONG", or "EXIT SHORT"
  - Signal logic:
    - **LONG**: All buy_conditions met (entry signal)
    - **EXIT LONG**: sell_conditions met while in LONG position
    - **SHORT**: All inverse conditions met for bearish setup
    - **EXIT SHORT**: buy_conditions met while in SHORT position

#### **1.3 State Manager** (`live_monitor/state_manager.py`)
- **Purpose**: Avoid duplicate notifications
- **Implementation**:
  - Store last known signal state per symbol in JSON file
  - Only trigger notification when signal changes (e.g., LONG→EXIT LONG, SHORT→EXIT SHORT)
  - Persist state to disk for Docker container restarts

#### **1.4 Scheduler** (`live_monitor/scheduler.py`)
- **Purpose**: Run analysis every 4 hours
- **Implementation**:
  - Use `schedule` library (add to requirements.txt)
  - Alternative: APScheduler for more robust scheduling
  - Schedule: run at 00:01, 04:01, 08:01, 12:01, 16:01, 20:01 UTC
  - 1-minute offset ensures full 4-hour candle is closed before analysis
  - Graceful error handling - continue on exceptions

---

### **Phase 2: Notification System**

#### **2.1 Discord Notifier** (`notifications/discord_notifier.py`)
- **Library**: `discord.py` or webhook approach
- **Configuration**: Discord webhook URL or bot token in `.env`
- **Message Format**:
  ```
  🚨 **LONG Signal Detected: BTC/USDT**
  
  📊 Market Data (4h):
  - Price: $67,450
  - Tenkan-sen: $66,800
  - Kijun-sen: $65,200
  - Cloud: Green (bullish)
  
  🤖 AI Analysis:
  [LLM-generated 2-3 sentence insight about why signal triggered and key levels]
  
  ⏰ Time: 2025-10-26 12:00 UTC
  ```

#### **2.2 Telegram Notifier** (`notifications/telegram_notifier.py`)
- **Library**: `python-telegram-bot`
- **Configuration**: Bot token and chat_id in `.env`
- **Supports**: Markdown formatting, inline buttons (future: "Mute", "Details")

#### **2.3 Email Notifier** (`notifications/email_notifier.py`)
- **Library**: `smtplib` (built-in) + `email` module
- **Configuration**: SMTP settings in `.env` (Gmail, Outlook, etc.)
- **Format**: HTML email with styled tables

#### **2.4 Message Formatter with LLM** (`notifications/message_formatter.py`)
- **Purpose**: Generate concise, actionable insights
- **Reuse**: `llm_analysis/llm_client.py` and `llm_analysis/prompt_builder.py`
- **Prompt Template**:
  ```
  You are a crypto trading assistant. A {signal_type} signal has been detected for {symbol} on 4h timeframe.
  
  Market Data:
  - Current Price: {price}
  - Tenkan-sen: {tenkan}
  - Kijun-sen: {kijun}
  - Cloud status: {cloud_status}
  - Chikou span: {chikou_status}
  
  Provide a 2-3 sentence analysis explaining:
  1) Why this signal is significant
  2) Key support/resistance levels to watch
  3) Brief risk consideration
  
  Keep it concise and actionable for a trader.
  ```

---

### **Phase 3: Configuration & Secrets Management**

#### **3.1 Monitor Configuration** (`config/monitor_config.yaml`)
```yaml
monitoring:
  enabled: true
  schedule: "00:01,04:01,08:01,12:01,16:01,20:01"  # 1 minute after candle close
  symbols: ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
  timeframe: "4h"
  data_points: 300
  
  notifications:
    discord:
      enabled: true
      webhook_url: "${DISCORD_WEBHOOK_URL}"  # From .env
    telegram:
      enabled: false
      bot_token: "${TELEGRAM_BOT_TOKEN}"
      chat_id: "${TELEGRAM_CHAT_ID}"
    email:
      enabled: false
      smtp_server: "smtp.gmail.com"
      smtp_port: 587
      sender: "${EMAIL_SENDER}"
      receiver: "${EMAIL_RECEIVER}"
      password: "${EMAIL_PASSWORD}"
  
  llm:
    enabled: true
    provider: "gemini"  # or "openai"
    model: "gemini-2.0-flash-exp"  # Faster for real-time
    max_tokens: 200

  binance:
    use_testnet: false
    rate_limit_buffer: 1.2  # Margin for rate limits
```

#### **3.2 Updated .env Template**
Add to existing `.env`:
```bash
# Notification Services
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
EMAIL_SENDER=your_email@gmail.com
EMAIL_RECEIVER=alert_recipient@gmail.com
EMAIL_PASSWORD=your_app_password

# Binance API (if using authenticated endpoints)
BINANCE_API_KEY=your_binance_api_key
BINANCE_SECRET_KEY=your_binance_secret
```

---

### **Phase 4: Docker Setup**

#### **4.1 Dockerfile** (`docker/Dockerfile`)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY ../requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY .. .

# Create data directory for state persistence
RUN mkdir -p /app/data/state

# Set timezone (important for 4-hour scheduling)
ENV TZ=UTC

# Run the monitoring service
CMD ["python", "-u", "main_monitor.py"]
```

#### **4.2 Docker Compose** (`docker/docker-compose.yml`)
```yaml
version: '3.8'

services:
  ichimoku-monitor:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    container_name: crypto-monitor
    env_file:
      - ../.env
    volumes:
      - ../data/state:/app/data/state  # Persist signal states
      - ../logs:/app/logs              # Persist logs
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

---

### **Phase 5: Main Entry Point**

#### **5.1 Main Monitor Script** (`main_monitor.py`)
```python
"""
Live Crypto Trading Monitor
Analyzes BTC/USDT, SOL/USDT, ETH/USDT every 4 hours using Ichimoku indicators
Sends notifications via Discord/Telegram/Email when signals change
"""

import schedule
import time
import logging
from datetime import datetime
from live_monitor.market_data_fetcher import MarketDataFetcher
from live_monitor.signal_detector import SignalDetector
from live_monitor.state_manager import StateManager
from notifications.message_formatter import MessageFormatter
from notifications.discord_notifier import DiscordNotifier
# ... other imports

def analyze_and_notify():
    """Main analysis loop - runs every 4 hours"""
    logger.info(f"Starting analysis cycle at {datetime.utcnow()}")
    
    for symbol in ["BTC/USDT", "ETH/USDT", "SOL/USDT"]:
        try:
            # 1. Fetch market data
            data = fetcher.fetch_latest_data(symbol, timeframe="4h", limit=300)
            
            # 2. Calculate Ichimoku and detect signal
            signal = detector.detect_signal(data, symbol)
            
            # 3. Check if signal changed
            if state_manager.has_signal_changed(symbol, signal):
                # 4. Generate LLM-enhanced message
                message = formatter.create_message(symbol, signal, data)
                
                # 5. Send notifications
                if config.discord_enabled:
                    discord.send(message)
                if config.telegram_enabled:
                    telegram.send(message)
                
                # 6. Update state
                state_manager.update_state(symbol, signal)
                
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
    
    logger.info("Analysis cycle completed")

if __name__ == "__main__":
    # Initialize components
    setup_logging()
    load_config()
    
    # Run immediately on startup
    analyze_and_notify()
    
    # Schedule every 4 hours at :01 minute mark
    schedule.every().day.at("00:01").do(analyze_and_notify)
    schedule.every().day.at("04:01").do(analyze_and_notify)
    schedule.every().day.at("08:01").do(analyze_and_notify)
    schedule.every().day.at("12:01").do(analyze_and_notify)
    schedule.every().day.at("16:01").do(analyze_and_notify)
    schedule.every().day.at("20:01").do(analyze_and_notify)
    
    # Keep running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute
```

---

### **Phase 6: Testing & Deployment**

#### **6.1 Testing Strategy**
1. **Unit Tests**: Test signal detection with historical data
2. **Integration Tests**: Mock Binance API responses
3. **End-to-End Test**: Run locally with test notifications
4. **Dry Run**: Monitor for 24h without sending notifications

#### **6.2 Deployment Steps**
```bash
# 1. Configure environment
cp .env.example .env
nano .env  # Add API keys and notification tokens

# 2. Build Docker image
cd docker
docker-compose build

# 3. Test locally
docker-compose up

# 4. Run in background
docker-compose up -d

# 5. View logs
docker-compose logs -f

# 6. Stop service
docker-compose down
```

---

### **Alternative Considerations**

#### **Data Points: Why 300 on 4h chart?**
- **Current suggestion**: 300 candles × 4h = 50 days
- **Sufficient for**: Senkou Span B (52 periods = 208 hours = ~9 days)
- **Alternative**: 150 candles (25 days) - minimum recommended
- **Overkill**: 500+ candles (increases API load unnecessarily)

#### **Notification Preference Recommendations**
1. **Discord** (Recommended):
   - Easy webhook setup
   - Rich formatting support
   - Mobile app notifications
   - No rate limits for webhooks

2. **Telegram** (Good alternative):
   - Reliable delivery
   - Better mobile UX than email
   - Requires bot setup

3. **Email** (Fallback):
   - Universal but may go to spam
   - Slower delivery
   - Good for archival

---

### **Updated Requirements**

Add to `requirements.txt`:
```txt
# Scheduling
schedule>=1.2.0

# Notifications
discord.py>=2.3.0
python-telegram-bot>=20.0
```

---

### **Estimated Implementation Timeline**

| Phase | Task | Time Estimate |
|-------|------|---------------|
| 1 | Core monitoring infrastructure | 4-6 hours |
| 2 | Notification system (all 3 channels) | 3-4 hours |
| 3 | Configuration & secrets management | 1-2 hours |
| 4 | Docker setup | 2-3 hours |
| 5 | Main entry point & integration | 2-3 hours |
| 6 | Testing & deployment | 2-3 hours |
| **Total** | | **14-21 hours** |

---

### **Adjustments & Decisions**

#### **Signal Types**
- **LONG**: All buy conditions met (entry)
- **EXIT LONG**: Sell conditions met (exit long position)
- **SHORT**: All short conditions met (entry)
- **EXIT SHORT**: Buy conditions met (exit short position)
- No "NEUTRAL" signal - only notify on actionable signals

#### **Scheduler Timing**
- Run at: 00:01, 04:01, 08:01, 12:01, 16:01, 20:01 UTC
- 1-minute offset ensures full 4-hour candle is closed before analysis
- Prevents analyzing incomplete candles

---

### **Next Steps**

1. **Confirm preferences**:
   - Primary notification channel (Discord/Telegram/Email)?
   - Binance API keys already available?
   - Prefer Gemini or OpenAI for LLM insights?

2. **Start implementation**:
   - Create modular structure
   - Implement Phase 1 (core monitoring)
   - Test with single symbol
   - Expand to all three symbols

3. **Deployment target**:
   - Local machine with Docker?
   - Cloud VPS (DigitalOcean, AWS, etc.)?
   - Raspberry Pi?
