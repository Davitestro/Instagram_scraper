"""
Utility functions for Instagram scraper.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from config import OUTPUT_DIR, DEBUG_DIR

# Global log file for the current session
_CURRENT_LOG_FILE = None


def init_log_file():
    """Initialize the log file for this session."""
    global _CURRENT_LOG_FILE
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    _CURRENT_LOG_FILE = DEBUG_DIR / f"instagram_scraper_{timestamp}.log"
    # Clear and initialize the log file
    with open(_CURRENT_LOG_FILE, 'w', encoding='utf-8') as f:
        f.write(f"Instagram Scraper Log - {datetime.now()}\n")
        f.write("=" * 60 + "\n\n")
    return _CURRENT_LOG_FILE


def get_log_file():
    """Get the current log file path."""
    global _CURRENT_LOG_FILE
    if _CURRENT_LOG_FILE is None:
        return init_log_file()
    return _CURRENT_LOG_FILE


def log_message(message: str, level: str = "INFO"):
    """Log message with timestamp to single log file."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}"
    print(log_entry)
    
    # Write to single log file
    try:
        log_file = get_log_file()
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')
    except:
        pass


def parse_count(text: str) -> str:
    """
    Parse count strings like "1.2K", "3.4M", "1,234".
    """
    if not text:
        return "0"
    
    text = text.strip().lower()
    text = text.replace(',', '')
    
    try:
        if 'k' in text:
            return str(int(float(text.replace('k', '')) * 1000))
        elif 'm' in text:
            return str(int(float(text.replace('m', '')) * 1000000))
        elif 'b' in text:
            return str(int(float(text.replace('b', '')) * 1000000000))
        else:
            # Remove any non-numeric characters
            numbers = re.findall(r'\d+', text)
            if numbers:
                return str(int(numbers[0]))
            return "0"
    except (ValueError, TypeError):
        return "0"


def is_instagram_media_url(url: str) -> bool:
    """Check if URL is an Instagram media URL."""
    patterns = [
        r'instagram\.com/(?:reel|p|tv)/[A-Za-z0-9_-]+',
        r'instagram\.com/share/[A-Za-z0-9_-]+'
    ]
    return any(re.search(pattern, url) for pattern in patterns)


def is_instagram_profile_url(url: str) -> bool:
    """Check if URL is an Instagram profile URL."""
    pattern = r'instagram\.com/(?!reel|p|tv|share|explore|accounts|direct)[A-Za-z0-9_.]+/?$'
    return bool(re.search(pattern, url))


def extract_shortcode(url: str) -> str:
    """Extract shortcode from Instagram URL."""
    match = re.search(r'/(?:reel|p|tv)/([A-Za-z0-9_-]+)', url)
    if match:
        return match.group(1)
    return ""


def extract_username(url: str) -> str:
    """Extract username from Instagram profile URL."""
    match = re.search(r'instagram\.com/([^/?]+)', url)
    if match:
        return match.group(1)
    return ""


def save_result(data: dict, platform: str = "instagram") -> str:
    """Save scraping result to file."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if platform == "instagram":
        if "author_username" in data and data.get('author_username'):
            filename = f"instagram_{data.get('author_username')}_{timestamp}.json"
        elif "username" in data and data.get('username'):
            filename = f"instagram_profile_{data.get('username')}_{timestamp}.json"
        else:
            filename = f"instagram_scrape_{timestamp}.json"
    else:
        filename = f"{platform}_scrape_{timestamp}.json"
    
    filepath = OUTPUT_DIR / filename
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    return str(filepath)