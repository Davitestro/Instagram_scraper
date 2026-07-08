"""
Utility functions for Instagram scraper.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from config import OUTPUT_DIR


def parse_count(text: str) -> str:
    """
    Parse count strings like "1.2K", "3.4M", "1,234".
    
    Args:
        text: Count string to parse
    
    Returns:
        Parsed count as string
    """
    if not text:
        return "0"
    
    # Clean up
    text = text.strip().lower()
    text = text.replace(',', '')
    
    # Handle K, M, B suffixes
    try:
        if 'k' in text:
            return str(int(float(text.replace('k', '')) * 1000))
        elif 'm' in text:
            return str(int(float(text.replace('m', '')) * 1000000))
        elif 'b' in text:
            return str(int(float(text.replace('b', '')) * 1000000000))
        else:
            # Just a number
            return str(int(float(text)))
    except (ValueError, TypeError):
        return text if text else "0"


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
    """
    Save scraping result to file.
    
    Args:
        data: Data to save
        platform: Platform name
    
    Returns:
        Path to saved file
    """
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Generate filename
    if platform == "instagram":
        if "author_username" in data:
            filename = f"instagram_{data.get('author_username', 'unknown')}_{timestamp}.json"
        elif "username" in data:
            filename = f"instagram_profile_{data.get('username', 'unknown')}_{timestamp}.json"
        else:
            filename = f"instagram_scrape_{timestamp}.json"
    else:
        filename = f"{platform}_scrape_{timestamp}.json"
    
    filepath = OUTPUT_DIR / filename
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    return str(filepath)