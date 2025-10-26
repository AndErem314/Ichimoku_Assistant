# 🌊 Ichimoku Crypto Trading Monitor

Automated cryptocurrency trading signal monitor using Ichimoku Cloud indicators. Monitors BTC/USDT, ETH/USDT, and SOL/USDT every 4 hours and sends AI-enhanced alerts via Discord and Telegram.

## ✨ Features

- 📊 **Ichimoku Cloud Analysis** - Advanced technical analysis using the default `ichimoku_default` strategy
- 🚀 **Signal Detection** - LONG, SHORT, EXIT LONG, EXIT SHORT signals
- 🤖 **AI-Enhanced Insights** - LLM-powered analysis (Gemini/OpenAI)
- 💬 **Discord & Telegram Notifications** - Real-time alerts with rich formatting
- 🛡️ **4% Stop Loss** - Automatic stop loss calculation
- 🔄 **Scheduled Monitoring** - Runs at 00:00:15, 04:00:15, etc. UTC
- 🐳 **Docker Support** - Easy deployment with Docker Compose
- 📝 **State Management** - Avoids duplicate notifications

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Discord webhook URL or Telegram bot (optional)
- Gemini or OpenAI API key (for AI analysis)

### Installation

1. **Clone and setup**
   ```bash
   cd /Users/andrey/Python/Ichimoku_Assistant
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment**
   
   Create `.env` file:
   ```bash
   # LLM Configuration (choose one or both)
   GEMINI_API_KEY=your_gemini_api_key_here
   OPENAI_API_KEY=your_openai_api_key_here
   
   # Discord (optional)
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
   
   # Telegram (optional)
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   TELEGRAM_CHAT_ID=your_chat_id_here
   ```

3. **Get Telegram Chat ID** (if using Telegram)
   ```bash
   python3 get_telegram_chat_id.py
   ```

4. **Configure monitoring**
   
   Edit `config/monitor_config.yaml` to customize:
   - Trading pairs to monitor
   - Notification channels (Discord/Telegram)
   - LLM provider (Gemini/OpenAI)
   - Logging settings

### Running Locally

```bash
python3 monitor.py
```

### Running with Docker

1. **Build and start**
   ```bash
   cd docker
   docker-compose up -d
   ```

2. **View logs**
   ```bash
   docker-compose logs -f
   ```

3. **Stop**
   ```bash
   docker-compose down
   ```

## 📋 Configuration

### Monitor Config (`config/monitor_config.yaml`)

```yaml
monitoring:
  enabled: true
  symbols:
    - "BTC/USDT"
    - "ETH/USDT"
    - "SOL/USDT"
  timeframe: "4h"
  data_points: 300
  run_on_startup: true

notifications:
  discord:
    enabled: true
  telegram:
    enabled: true
  test_on_startup: false

llm:
  enabled: true
  provider: "gemini"  # or "openai"
```

### Strategy Config (`config/strategy.yaml`)

Uses `ichimoku_default` - Full Confirmation, TK Exit:
- LONG (AND logic): PriceAboveCloud, TenkanAboveKijun, SpanAaboveSpanB, ChikouAboveCloud, ChikouAbovePrice
- SHORT (AND logic): PriceBelowCloud, TenkanBelowKijun, SpanAbelowSpanB, ChikouBelowCloud, ChikouBelowPrice
- EXIT LONG: TenkanBelowKijun
- EXIT SHORT: LONG buy conditions met while in bearish setup

## 📱 Notifications

### Discord

Rich embeds with color-coding:
- 🚀 GREEN - LONG signals
- 📉 RED - SHORT signals  
- 🛑 ORANGE - EXIT LONG
- ✅ TURQUOISE - EXIT SHORT

**Setup:**
1. Go to Server Settings → Integrations → Webhooks
2. Create New Webhook
3. Copy URL to `.env` as `DISCORD_WEBHOOK_URL`

### Telegram

Markdown-formatted messages with:
- Price and confidence
- Ichimoku indicators
- AI analysis
- Stop loss levels

**Setup:**
1. Message @BotFather on Telegram
2. Create bot with `/newbot`
3. Copy token to `.env` as `TELEGRAM_BOT_TOKEN`
4. Run `python3 get_telegram_chat_id.py` to get your chat ID
5. Add chat ID to `.env` as `TELEGRAM_CHAT_ID`

## 🧪 Testing

### Test Phase 1 (Core Components)
```bash
python3 test_phase1.py
```

### Test Notifications
```bash
# Test Discord
python3 -c "from notifications import DiscordNotifier; import os; from dotenv import load_dotenv; load_dotenv(); DiscordNotifier(os.getenv('DISCORD_WEBHOOK_URL')).send_test_message()"

# Test Telegram  
python3 get_telegram_chat_id.py
```

## 📁 Project Structure

```
Ichimoku_Assistant/
├── monitor.py              # Main entry point
├── config/
│   ├── monitor_config.yaml # Monitor configuration
│   └── strategy.yaml      # Default Ichimoku strategy
├── live_monitor/           # Core monitoring
│   ├── market_data_fetcher.py
│   ├── signal_detector.py
│   ├── state_manager.py
│   └── scheduler.py
├── notifications/          # Alert system
│   ├── discord_notifier.py
│   ├── telegram_notifier.py
│   └── message_formatter.py
├── llm_analysis/           # AI integration
│   ├── llm_client.py
│   └── env_loader.py
├── strategy/               # Ichimoku calculation
│   └── ichimoku_strategy.py
└── docker/                 # Docker deployment
    ├── Dockerfile
    └── docker-compose.yml
```

## 🔧 Switching LLM Provider

The monitor uses Gemini by default. To switch to OpenAI:

1. **In config/monitor_config.yaml:**
   ```yaml
   llm:
     provider: "openai"
   ```

2. **Or programmatically:**
   ```python
   message_formatter.set_llm_provider("openai")
   ```

## 📊 Signals Explained

- **LONG** - All bullish conditions met, enter long position
- **SHORT** - All bearish conditions met, enter short position
- **EXIT LONG** - Exit long position (Tenkan crossed below Kijun)
- **EXIT SHORT** - Exit short position (bullish conditions met)
- **NONE** - No actionable signal (not sent as notification)

## 🛠️ Troubleshooting

### No signals detected
- Check that market data is being fetched (`logs/monitor.log`)
- Verify Ichimoku conditions in `config/strategy.yaml`
- Signals only trigger when conditions change

### Notifications not sending
- Verify `.env` has correct webhook URLs/tokens
- Check notification settings in `config/monitor_config.yaml`
- Test notifications with `test_on_startup: true`

### Docker issues
- Ensure `.env` file exists and is readable
- Check logs: `docker-compose logs -f`
- Verify volumes are mounted: `docker-compose ps`

## 📝 Logs

Logs are stored in `logs/monitor.log` with rotation:
- Max size: 10MB per file
- Keeps 5 backup files
- Also outputs to console

## 🔒 Security

- ⚠️ Never commit `.env` file (already in `.gitignore`)
- 🔐 Keep API keys secure
- 🚫 Don't share webhook URLs or bot tokens

## 📈 Performance

- Lightweight: ~50MB RAM usage
- Fast: Analysis completes in <10 seconds per cycle
- Efficient: Only sends notifications on signal changes

## 🤝 Support

For issues or questions:
1. Check `logs/monitor.log` for errors
2. Review configuration files
3. Test individual components with test scripts

## 📄 License

Private project for personal use.

---

**Built with:** Python 3.11, CCXT, Gemini/OpenAI, Discord, Telegram
