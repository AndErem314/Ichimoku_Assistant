# 🔄 Migration Guide - Upgrading to snake_case Architecture

**Version:** 2.0 (2025-11-05)  
**Breaking Change:** Signal naming convention changed from PascalCase to snake_case

---

## 📋 What Changed?

### **Signal Names**

| Old (PascalCase) | New (snake_case) |
|------------------|------------------|
| `PriceAboveCloud` | `price_above_cloud` |
| `PriceBelowCloud` | `price_below_cloud` |
| `TenkanAboveKijun` | `tenkan_above_kijun` |
| `TenkanBelowKijun` | `tenkan_below_kijun` |
| `SpanAaboveSpanB` | `span_a_above_span_b` |
| `SpanAbelowSpanB` | `span_a_below_span_b` |
| `ChikouAbovePrice` | `chikou_above_price` |
| `ChikouBelowPrice` | `chikou_below_price` |
| `ChikouAboveCloud` | `chikou_above_cloud` |
| `ChikouBelowCloud` | `chikou_below_cloud` |

### **Architecture Changes**

1. **Removed:** Legacy `SignalConditions` (buy/sell)
2. **Now Using:** `StrategyRules` (long_entry/short_entry/long_exit/short_exit)
3. **Signal Format:** All signals now use consistent snake_case

---

## 🚀 Migration Steps

### **Step 1: Existing State Files**

Your existing signal state file (`data/state/signal_states.json`) will continue to work. The system gracefully handles:
- Old states from previous version
- New states with enhanced context (previous_signal, transition_count)

**No action required** - old state files are compatible.

---

### **Step 2: Custom Strategy Configs**

If you have custom strategy configurations, update signal names:

#### **Before (Old Format):**
```yaml
strategies:
  my_custom_strategy:
    signal_conditions:
      long_entry: ["PriceAboveCloud", "TenkanAboveKijun"]
      short_entry: ["PriceBelowCloud", "TenkanBelowKijun"]
      long_exit: ["TenkanBelowKijun"]
      short_exit: ["TenkanAboveKijun"]
```

#### **After (New Format):**
```yaml
strategies:
  my_custom_strategy:
    signal_conditions:
      long_entry: ["price_above_cloud", "tenkan_above_kijun"]
      short_entry: ["price_below_cloud", "tenkan_below_kijun"]
      long_exit: ["tenkan_below_kijun"]
      short_exit: ["tenkan_above_kijun"]
```

**Action:** Update all signal names to snake_case in your YAML files.

---

### **Step 3: Git Pull Latest Changes**

```bash
cd /Users/andrey/Python/Ichimoku_Assistant
git pull origin main
```

---

### **Step 4: Test Configuration**

Test that your configuration loads correctly:

```bash
python3 -c "from live_monitor import SignalDetector; sd = SignalDetector(); print('✅ Config loaded successfully'); info = sd.get_strategy_info(); print(f'Strategy: {info[\"name\"]}')"
```

Expected output:
```
✅ Config loaded successfully
Strategy: Ichimoku Default (Full Confirmation, TK Exit)
```

---

### **Step 5: Restart Monitor**

If running via Docker:
```bash
cd docker
docker-compose restart
```

If running locally:
```bash
# Stop current process (Ctrl+C)
python3 monitor.py
```

---

## 🆕 New Features (v2.0)

### **Enhanced State Tracking**

StateManager now tracks signal context:

```python
# Get signal context for a symbol
from live_monitor import StateManager
sm = StateManager()
context = sm.get_signal_context('BTC/USDT')

print(context)
# Output:
# {
#   'symbol': 'BTC/USDT',
#   'current_signal': 'LONG',
#   'previous_signal': 'NONE',
#   'confidence': 1.0,
#   'timestamp': '2025-11-05T12:00:00',
#   'transitions': 5,
#   'signal_flow': 'NONE → LONG'
# }
```

### **Better Logging**

State changes now show transitions:
```
Updated state for BTC/USDT: NONE → LONG (confidence: 100.0%)
Updated state for ETH/USDT: LONG → EXIT LONG (confidence: 100.0%)
```

### **Monitoring Clarification**

README now clearly states: **This is a monitoring system only** - it does NOT execute trades. You manually decide whether to trade based on signals.

---

## ⚠️ Troubleshooting

### **Issue: "Unknown signal name" warnings**

**Cause:** Old PascalCase signal names in config

**Fix:** Update `config/strategy.yaml` to use snake_case:
```yaml
# Wrong
long_entry: ["PriceAboveCloud"]

# Correct
long_entry: ["price_above_cloud"]
```

---

### **Issue: No signals detected**

**Cause:** Config parsing error

**Steps:**
1. Check logs: `tail -f logs/monitor.log`
2. Validate config: `python3 -c "import yaml; print(yaml.safe_load(open('config/strategy.yaml')))"`
3. Test signal detector: `python3 -c "from live_monitor import SignalDetector; SignalDetector()"`

---

### **Issue: Old state file format**

**Symptom:** Missing `previous_signal` or `transition_count` fields

**Fix:** System automatically handles old format. To reset state:
```bash
rm data/state/signal_states.json
# Restart monitor to create fresh state file
```

---

## 📊 Backward Compatibility

### **What Still Works:**

✅ Existing state files (`signal_states.json`)  
✅ Existing environment variables (`.env`)  
✅ Discord/Telegram webhooks  
✅ LLM integration (Gemini/OpenAI)  
✅ Docker deployment  
✅ Notification format

### **What Changed (Breaking):**

❌ PascalCase signal names no longer supported  
❌ `SignalConditions` class removed (use `StrategyRules`)  
❌ `check_strategy_signals()` removed (use `check_position_signals()`)

---

## 🔍 Verification Checklist

After migration, verify:

- [ ] Monitor starts without errors
- [ ] Strategy config loads correctly
- [ ] Signal detection working (check logs)
- [ ] Notifications sending (Discord/Telegram)
- [ ] State persistence working
- [ ] LLM analysis generating

---

## 💡 Best Practices

### **1. Test in Development First**

Before updating production:
```bash
# Create test environment
python3 -m venv test_env
source test_env/bin/activate
pip install -r requirements.txt

# Test with your config
python3 monitor.py
```

### **2. Backup Your State**

Before migration:
```bash
cp data/state/signal_states.json data/state/signal_states.json.backup
```

### **3. Monitor Logs**

Watch logs during first few runs:
```bash
tail -f logs/monitor.log
```

### **4. Version Your Config**

Keep your custom strategies in version control:
```bash
git add config/strategy.yaml
git commit -m "Updated to snake_case signals"
```

---

## 📞 Support

### **Common Questions:**

**Q: Will EXIT signals still work if I didn't take the entry?**  
A: Yes! This is a monitoring system. EXIT signals are always sent regardless of whether you actually took the trade.

**Q: Do I need to delete my old state file?**  
A: No, old state files work fine. New fields are added automatically.

**Q: Can I use both PascalCase and snake_case?**  
A: No, only snake_case is supported in v2.0+. Update all signal names.

**Q: Will this affect my notification history?**  
A: No, past notifications are unaffected. New notifications use the new format.

---

## 🎯 Summary

**Required Actions:**
1. Update custom strategy configs to snake_case
2. Pull latest code from git
3. Restart monitor

**Optional Actions:**
- Review enhanced state tracking features
- Check updated README for signal explanations
- Consider adding custom signal history analysis

**Time Required:** 5-10 minutes

---

**Questions?** Check the logs or refer to:
- `docs/PROJECT_ANALYSIS.md` - Technical details
- `docs/QUICK_REFERENCE.md` - Quick reference guide
- `README.md` - Updated user guide

**Migration Status:** ✅ Simple and straightforward
