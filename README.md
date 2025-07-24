# DexBoost Monitor

🆓 **Free-to-use example project** for automated monitoring of boosted tokens on DexScreener with Telegram notifications.

## ⚠️ Disclaimer

This project is provided as a **free example** for educational and demonstration purposes. Use at your own risk and responsibility.

## Features

- 🚀 Monitors high boost tokens on DexScreener
- 📊 Tracks boost changes (sends alerts when boosts increase by 5+)
- 💬 Telegram notifications with detailed token information
- 🗄️ SQLite database for tracking sent tokens
- 🛡️ Cloudflare bypass using 2captcha
- ⏱️ Configurable time delays to avoid spam
- 🤖 Crontab scheduling support
- 👻 Headless mode compatibility

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd dexboost
```

2. Install required packages:
```bash
pip install -r requirements.txt 
playwright install chromium
```

3. Create `config.json` from example:
```json
{
  "boost_threshold": 500,
  "hours_delay": 24,
  "two_captcha_key": "YOUR_2CAPTCHA_API_KEY_HERE",
  "telegram": {
    "bot_token": "YOUR_TELEGRAM_BOT_TOKEN",
    "chat_id": "YOUR_CHAT_ID"
  },
  "database": {
    "filename": "sent_tokens.db"
  }
}
```

## Configuration

### Required Settings

- `two_captcha_key`: Your 2captcha API key for Cloudflare bypass
- `telegram.bot_token`: Your Telegram bot token
- `telegram.chat_id`: Your Telegram chat ID

### Optional Settings

- `boost_threshold`: Minimum boosts to trigger notification (default: 500)
- `hours_delay`: Hours to wait before resending same token (default: 24)
- `database.filename`: Database file name (default: "sent_tokens.db")

## Usage

### Manual Run
```bash
python main.py
```

### Automated Scheduling (Recommended)

**I personally use crontab for scheduling:**

```bash
# Edit crontab
crontab -e

# Add entry to run every 30 minutes
*/30 * * * * cd /path/to/dexboost && /usr/bin/python3 main.py >> logs/dexboost.log 2>&1

# Or every hour
0 * * * * cd /path/to/dexboost && /usr/bin/python3 main.py >> logs/dexboost.log 2>&1
```

### Headless Mode

You can use headless mode by modifying the cloudflare.py settings:

```python
# In cloudflare.py, change:
context = p.chromium.launch_persistent_context(
    user_data_dir="./browser_data",
    headless=True,  # Set to True for headless
    user_agent=chrome_ug
)
```

**Note:** Headless mode works well when proper cookies and user-agent are configured.

## How It Works

The script will:
1. Fetch boosted tokens from DexScreener
2. Check for new high-boost tokens above threshold
3. Monitor boost changes (≥5 increase) for existing tokens
4. Send Telegram notifications
5. Update database records

## Files Structure

- `main.py` - Main application logic
- `database.py` - SQLite database operations
- `telegram_sender.py` - Telegram message formatting and sending
- `cloudflare.py` - Cloudflare bypass using Playwright
- `config.json` - Configuration file (not tracked in git)

## Database Schema

The SQLite database stores:
- `pair_address` - Unique token pair address
- `token_name` - Token name
- `base_symbol` - Token symbol
- `boosts` - Current boost count
- `sent_at` - Last notification timestamp

## Example Crontab Setup

```bash
# Create logs directory
mkdir -p /path/to/dexboost/logs

# Example crontab entries:
# Every 15 minutes
*/15 * * * * cd /path/to/dexboost && python3 main.py >> logs/dexboost.log 2>&1

# Every hour at minute 5
5 * * * * cd /path/to/dexboost && python3 main.py >> logs/dexboost.log 2>&1

# Twice a day at 9 AM and 9 PM
0 9,21 * * * cd /path/to/dexboost && python3 main.py >> logs/dexboost.log 2>&1
```

## Troubleshooting

### Common Issues:
- **Cloudflare blocking**: Ensure valid 2captcha API key
- **Telegram not working**: Check bot token and chat ID
- **Database errors**: Ensure write permissions in project directory
- **Headless issues**: Use non-headless mode first to establish cookies

### Debug Mode:
Uncomment debug prints in the code to see detailed execution logs.

## Contact & Support

📱 **Telegram:** [@wwafwt](https://t.me/wwafwt)

For questions, suggestions, or issues related to this free example project.

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Test thoroughly
5. Submit pull request

## License

This project is provided as-is for educational purposes. Free to use and modify.

---

**⚠️ Remember:** This is an example project. Always test thoroughly before using in production environments.
