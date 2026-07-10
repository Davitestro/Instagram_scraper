# Instagram Profile Scraper

A Python-based Instagram profile scraper that collects posts, media, comments, and metadata from user profiles using Playwright and Chrome DevTools Protocol.

## Features

- ✅ Scrape single Instagram profiles
- ✅ Batch scrape multiple profiles from a file
- ✅ Extract posts, reels, captions, hashtags, and mentions
- ✅ Export to JSON and CSV formats
- ✅ Human-like delays to avoid detection
- ✅ Automatic rate limit handling
- ✅ Detailed logging and error handling
- ✅ Configurable post limits per profile

## Requirements

- **Python**: 3.8+
- **Chrome/Chromium**: Required for remote debugging protocol
- **Playwright**: For browser automation
- **Additional dependencies**: See `requirements.txt`

## Installation

### 1. Clone or extract the project
```bash
cd instagram_scraper
```

### 2. Create a virtual environment
```bash
# On Linux/macOS
python3 -m venv .venv
source .venv/bin/activate

# On Windows
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Install Playwright browsers
```bash
playwright install chromium
```

## How to Run

### Prerequisites: Start Chrome with Remote Debugging

Before running the scraper, you must launch Chrome with remote debugging enabled:

```bash
# On Linux
google-chrome --remote-debugging-port=9222

# On macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222

# On Windows (PowerShell)
& 'C:\Program Files\Google\Chrome\Application\chrome.exe' --remote-debugging-port=9222
```

Then **log in to Instagram** in the Chrome browser and keep it open.

### Run Method 1: Scrape a Single Profile

```bash
python3 main.py --profile "username" --max-posts 5
```

**Examples:**
```bash
python3 main.py --profile "pubity" --max-posts 10
python3 main.py --profile "natgeo" --max-posts 5
python3 main.py -p "elonmusk" -m 3
```

### Run Method 2: Scrape Multiple Profiles from File

```bash
python3 main.py --profile-file profiles.txt --max-posts 3
```

**Profile file format** (`profiles.txt`):
```
pubity
natgeo
elonmusk
```

One username per line, without the @ symbol.

### Command Line Options

```
--profile, -p          Instagram username to scrape (without @)
--profile-file, -f     File containing usernames (one per line)
--max-posts, -m        Maximum posts to collect per profile (default: 10)
--export-formats, -e   Export formats: json,csv (default: json,csv)
```

### CSV Files
- **media.csv**: Post metadata (URL, caption, likes, comments, etc.)
- **comments.csv**: Comment data for each post
- **flat.csv**: Flattened combined data

### JSON Files
- Complete structured data with all post information

## Configuration

Edit `config.py` to customize behavior:

```python
CDP_PORT = 9222              # Chrome DevTools Protocol port
DEFAULT_MAX_REELS = 10       # Default posts per profile
SCROLL_AMOUNT = 800          # Pixels to scroll
SCROLL_DELAY = 1500          # Delay between scrolls (ms)
RATE_LIMIT_WAIT = 30         # Wait time when rate limited (s)
MAX_SCRAPE_RETRIES = 3       # Retry attempts on failure
```

## Workflow Example

```bash
# 1. Start Chrome
google-chrome --remote-debugging-port=9222 &

# 2. Log in to Instagram in the browser that opens
# (Keep the browser open!)

# 3. Activate virtual environment
source .venv/bin/activate

# 4. Run scraper
python3 main.py --profile "pubity" --max-posts 5

# 5. Check output in output/csv/ or output/json/
ls -la output/csv/
```

## Project Structure

```
instagram_scraper/
├── main.py                 # Entry point for profile scraping
├── config.py              # Configuration settings
├── browser_manager.py     # Chrome browser automation
├── scraper.py            # Core scraping logic
├── collector.py          # Data collection orchestration
├── models.py             # Data models (InstagramMedia, etc.)
├── exporters.py          # CSV and JSON exporters
├── utils.py              # Helper functions
├── exceptions.py         # Custom exceptions
├── requirements.txt      # Python dependencies
├── profiles.txt          # Sample profile list
└── output/               # Scraped data (auto-created)
```

## Troubleshooting

### Chrome not found
**Error**: "No Chrome instance found on port 9222"  
**Solution**: Manually start Chrome with `google-chrome --remote-debugging-port=9222`

### Login required
**Error**: "Not logged in to Instagram"  
**Solution**: Ensure you're logged in to instagram.com in the Chrome browser before running the scraper

### Rate limiting
**Error**: "Too many requests"  
**Solution**: The scraper has automatic rate limit handling. It will wait 30+ seconds before retrying

### Profile not found
**Error**: "Profile not found"  
**Solution**: Verify the username is correct (without @ symbol) and is a public profile

## Dependencies

- **playwright** (>=1.40.0): Browser automation
- **python-dotenv** (>=1.0.0): Environment variable management
- **pytest** (>=7.0.0): Testing framework

## Contributing

- Submit issues for bugs or feature requests
- Update `profiles.txt` to test multiple profiles
- Check logs for debugging (`instagram_scraper_YYYYMMDD_HHMMSS.log`)

## License

This project is licensed under the MIT License — see the `LICENSE` file for details.

## Disclaimer

This tool is for educational purposes only. Respect Instagram's Terms of Service and robots.txt. Use responsibly and don't violate any platform policies.
