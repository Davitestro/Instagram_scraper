"""
Configuration for Instagram scraper.
"""

from pathlib import Path

# Browser settings
CDP_PORT = 9222
MAX_RETRIES = 3

# Timeouts (in milliseconds)
TIMEOUT_ELEMENT = 15000
TIMEOUT_NAVIGATION = 30000
TIMEOUT_WAIT = 2000

# Scrolling settings
SCROLL_AMOUNT = 800
SCROLL_DELAY = 1500

# Rate limiting settings
RATE_LIMIT_WAIT = 30
MAX_SEARCH_RETRIES = 3
MAX_SCRAPE_RETRIES = 3

# Search settings
DEFAULT_MAX_REELS = 10

# Chrome paths
CHROME_PATHS = {
    "linux": ["google-chrome", "google-chrome-stable", "chromium-browser", "chromium"],
    "darwin": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "win32": [
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
    ]
}

# Directories
BASE_DIR = Path(__file__).parent
DEBUG_DIR = BASE_DIR / "debug"
OUTPUT_DIR = BASE_DIR / "output"
JSON_DIR = OUTPUT_DIR / "json"
CSV_DIR = OUTPUT_DIR / "csv"

# Create directories
DEBUG_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
JSON_DIR.mkdir(exist_ok=True)
CSV_DIR.mkdir(exist_ok=True)

# Instagram URLs
INSTAGRAM_BASE_URL = "https://www.instagram.com"
INSTAGRAM_LOGIN_URL = f"{INSTAGRAM_BASE_URL}/accounts/login/"
INSTAGRAM_EXPLORE_URL = f"{INSTAGRAM_BASE_URL}/explore/"