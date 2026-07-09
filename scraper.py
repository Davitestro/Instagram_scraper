"""
Core scraping logic for Instagram - clean version without view_count.
"""

import json
import re
import time
import random
from typing import Optional, List, Dict, Any
from datetime import datetime

from playwright.sync_api import TimeoutError as PWTimeout

from config import (
    TIMEOUT_ELEMENT, TIMEOUT_WAIT, TIMEOUT_NAVIGATION,
    MAX_RETRIES, DEBUG_DIR
)
from exceptions import (
    MediaNotFoundError, ProfileNotFoundError, 
    LoginError, ElementNotFoundError, RateLimitError
)
from models import InstagramMedia, InstagramProfile
from utils import parse_count, log_message
from browser_manager import BrowserManager


class InstagramScraper:
    """Main scraper for Instagram."""
    
    def __init__(self, browser_manager: BrowserManager):
        self.browser_manager = browser_manager
        self.page = browser_manager.page
    
    def _human_like_delay(self, min_sec: float = 1.0, max_sec: float = 3.0):
        """Add human-like delays between actions."""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)
    
    def _check_rate_limit(self) -> bool:
        """Check if we're being rate limited."""
        try:
            rate_limit_selectors = [
                'div:has-text("Sorry, we couldn\'t find that page")',
                'div:has-text("Too many requests")',
                'div:has-text("Please wait a few minutes")',
                'button:has-text("Try Again")',
                'div:has-text("Error")',
            ]
            
            for selector in rate_limit_selectors:
                if self.page.locator(selector).count() > 0:
                    return True
            
            current_url = self.page.url
            if "challenge" in current_url or "login" in current_url:
                return True
                
            return False
            
        except Exception:
            return False
    
    def verify_logged_in(self) -> bool:
        """Check if user is logged into Instagram."""
        try:
            self.page.goto("https://www.instagram.com/", 
                         wait_until="domcontentloaded", 
                         timeout=TIMEOUT_NAVIGATION)
            self._human_like_delay()
            
            if self._check_rate_limit():
                return False
            
            checks = []
            
            if "login" not in self.page.url.lower():
                checks.append(True)
            
            for selector in [
                'svg[aria-label="Home"]',
                'svg[aria-label="Explore"]',
                'svg[aria-label="New post"]',
                'article[role="presentation"]',
                'header[role="banner"]'
            ]:
                try:
                    if self.page.locator(selector).count() > 0:
                        checks.append(True)
                except Exception:
                    pass
            
            is_logged_in = len(checks) >= 2
            log_message(f"  Login check: {'✅ Logged in' if is_logged_in else '❌ Not logged in'}")
            
            return is_logged_in
            
        except Exception as e:
            log_message(f"  Login verification error: {e}", "ERROR")
            return False
    
    def ensure_logged_in(self):
        """Ensure user is logged in, prompt if not."""
        if not self.verify_logged_in():
            log_message("⚠️  Not logged in to Instagram!", "WARNING")
            self.page.goto("https://www.instagram.com/accounts/login/")
            log_message("📱 Please log in manually in the Chrome window...")
            input("⏳ Press Enter when you're logged in and can see your feed...")
            
            self._human_like_delay()
            self.page.goto("https://www.instagram.com/")
            self._human_like_delay()
            
            if not self.verify_logged_in():
                raise LoginError("Still not logged in. Please log in and try again.")
    
    def _dump_debug(self, label: str):
        """Save debug information."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_file = DEBUG_DIR / f"{label}_{timestamp}"
            self.page.screenshot(path=str(debug_file.with_suffix('.png')), full_page=True)
            (debug_file.with_suffix('.html')).write_text(
                self.page.content(), encoding="utf-8"
            )
            log_message(f"  [debug] saved {debug_file}.png and .html")
        except Exception as e:
            log_message(f"  [debug] could not save debug snapshot: {e}", "ERROR")
    
    def _extract_shortcode(self, url: str) -> str:
        """Extract shortcode from Instagram URL."""
        match = re.search(r'/(?:reel|p|tv)/([A-Za-z0-9_-]+)', url)
        if match:
            return match.group(1)
        return ""
    
    def _extract_username_from_url(self, url: str) -> str:
        """Extract username from profile URL."""
        match = re.search(r'instagram\.com/([^/?]+)', url)
        if match:
            return match.group(1)
        return ""
    
    def _extract_hashtags(self, text: str) -> List[str]:
        """Extract hashtags from text."""
        if not text:
            return []
        return re.findall(r'#([A-Za-z0-9_]+)', text)
    
    def _extract_mentions(self, text: str) -> List[str]:
        """Extract mentions from text."""
        if not text:
            return []
        return re.findall(r'@([A-Za-z0-9_.]+)', text)
    
    def _extract_links(self, text: str) -> List[str]:
        """Extract URLs from text."""
        if not text:
            return []
        return re.findall(r'https?://[^\s]+', text)
    
    def _extract_from_meta(self, property_name: str) -> Optional[str]:
        """Extract data from meta tags."""
        try:
            meta = self.page.locator(f'meta[property="{property_name}"]')
            if meta.count() > 0:
                return meta.get_attribute("content")
        except:
            pass
        return None
    
    def _clean_caption(self, caption: str) -> str:
        """Clean the caption by removing stats prefix."""
        if not caption:
            return ""
        
        # Try to extract just the caption after the stats prefix
        patterns = [
            r'^[\d,]+\s*(?:likes?|views?)[,.]?\s*[\d,]+\s*(?:comments?)?\s*[-—–]\s*[^:]+:\s*(.+)$',
            r'^[\d,]+\s*(?:likes?|views?)\s*[-—–]\s*[^:]+:\s*(.+)$',
            r'^[\d,]+\s*(?:likes?|views?)[,.]?\s*[\d,]+\s*(?:comments?)?\s*[-—–]\s*[^:]+:\s*(.+)$',
        ]
        
        for pattern in patterns:
            match = re.match(pattern, caption, re.IGNORECASE | re.DOTALL)
            if match:
                cleaned = match.group(1).strip()
                if cleaned.startswith('"') and cleaned.endswith('"'):
                    cleaned = cleaned[1:-1]
                return cleaned
        
        return caption
    
    def _extract_media_data(self, url: str) -> InstagramMedia:
        """Extract media data from the page."""
        shortcode = self._extract_shortcode(url)
        
        # Initialize with defaults
        author = ""
        caption = ""
        created_at = None
        like_count = "0"
        comment_count = "0"
        media_type = "post"
        location = None
        music = None
        thumbnail_url = ""
        is_video = False
        
        # Get page text for parsing
        page_text = ""
        try:
            page_text = self.page.inner_text('body')
        except:
            pass
        
        # METHOD 1: Extract author from the page
        try:
            author_el = self.page.locator('article header a, header a[href*="/"]').first
            if author_el.count() > 0:
                href = author_el.get_attribute("href")
                if href:
                    username_match = re.search(r'/([^/?]+)/?$', href)
                    if username_match:
                        author = username_match.group(1)
                        log_message(f"  ✅ Found author from link: @{author}")
        except:
            pass
        
        if not author and page_text:
            lines = page_text.split('\n')
            for line in lines[:10]:
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('@'):
                    if len(line) < 30 and ' ' not in line and '/' not in line:
                        author = line
                        log_message(f"  ✅ Found author from page text: @{author}")
                        break
        
        # METHOD 2: Determine media type
        if "/reel/" in url:
            media_type = "reel"
            is_video = True
        elif "/tv/" in url:
            media_type = "video"
            is_video = True
        elif "/p/" in url:
            media_type = "post"
        
        # METHOD 3: Extract caption from page
        try:
            caption_selectors = [
                'article h1 span[dir="auto"]',
                'article div[role="presentation"] span[dir="auto"]',
                'div[data-testid="caption"]',
                'div[class*="caption"] span',
            ]
            for selector in caption_selectors:
                try:
                    cap_el = self.page.locator(selector).first
                    if cap_el.count() > 0:
                        text = cap_el.inner_text()
                        if text and len(text) > 10:
                            caption = text
                            log_message(f"  ✅ Found caption from page: {len(caption)} chars")
                            break
                except:
                    continue
        except:
            pass
        
        if not caption:
            meta_desc = self._extract_from_meta('og:description')
            if meta_desc:
                caption = self._clean_caption(meta_desc)
                if caption:
                    log_message(f"  ✅ Found caption from meta: {len(caption)} chars")
        
        # METHOD 4: Extract metrics (likes, comments) - get the LARGEST numbers
        if page_text:
            # Find all numbers with K/M/B or commas
            all_numbers = re.findall(r'([\d,]+[KMB]?|[\d,]+)', page_text)
            
            # Convert to integers and find the largest ones
            numeric_values = []
            for num in all_numbers:
                try:
                    clean_num = num.replace(',', '').upper()
                    if 'K' in clean_num:
                        val = int(float(clean_num.replace('K', '')) * 1000)
                    elif 'M' in clean_num:
                        val = int(float(clean_num.replace('M', '')) * 1000000)
                    elif 'B' in clean_num:
                        val = int(float(clean_num.replace('B', '')) * 1000000000)
                    else:
                        val = int(clean_num)
                    # Skip numbers that are clearly dates or years
                    if val > 0 and not (1000 <= val <= 2100 and str(val).startswith(('19', '20'))):
                        numeric_values.append(val)
                except:
                    continue
            
            # Sort and get the top values
            numeric_values.sort(reverse=True)
            
            # The post likes is usually the largest number (1,268)
            if len(numeric_values) >= 1:
                like_count = str(numeric_values[0])
                log_message(f"  ✅ Found likes from text: {like_count}")
            if len(numeric_values) >= 2:
                comment_count = str(numeric_values[1])
                log_message(f"  ✅ Found comments from text: {comment_count}")
            
            # If we got too many numbers, try to identify likes/comments from patterns
            if like_count == "0" or comment_count == "0":
                like_pattern = re.search(r'([\d,]+[KMB]?)\s*(?:likes?)', page_text, re.IGNORECASE)
                if like_pattern:
                    like_count = parse_count(like_pattern.group(1))
                    log_message(f"  ✅ Found likes from pattern: {like_count}")
                
                comment_pattern = re.search(r'([\d,]+[KMB]?)\s*(?:comments?)', page_text, re.IGNORECASE)
                if comment_pattern:
                    comment_count = parse_count(comment_pattern.group(1))
                    log_message(f"  ✅ Found comments from pattern: {comment_count}")
        
        # METHOD 5: Extract date
        try:
            time_el = self.page.locator('time').first
            if time_el.count() > 0:
                created_at = time_el.get_attribute("datetime")
        except:
            pass
        
        # METHOD 6: Extract location
        try:
            location_el = self.page.locator('a[href*="/explore/locations/"]').first
            if location_el.count() > 0:
                location = location_el.inner_text().strip()
        except:
            pass
        
        # METHOD 7: Extract music
        if page_text:
            music_patterns = [
                r'🎵\s*([^\n]+)',
                r'Music\s*[:：]\s*([^\n]+)',
                r'Audio\s*[:：]\s*([^\n]+)',
            ]
            for pattern in music_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    music = match.group(1).strip()
                    if music and len(music) < 100:
                        break
        
        # METHOD 8: Extract thumbnail
        meta_image = self._extract_from_meta('og:image')
        if meta_image:
            thumbnail_url = meta_image
        
        # METHOD 9: Extract hashtags from caption
        hashtags = self._extract_hashtags(caption)
        mentions = self._extract_mentions(caption)
        links = self._extract_links(caption)
        
        # Final clean of caption
        if caption:
            caption = caption.strip()
            if caption.startswith('"') and caption.endswith('"'):
                caption = caption[1:-1]
            if 'likes' in caption.lower() or 'comments' in caption.lower():
                caption = self._clean_caption(caption)
        
        return InstagramMedia(
            url=url,
            shortcode=shortcode,
            caption=caption,
            created_at=created_at,
            like_count=like_count,
            comment_count=comment_count,
            view_count="0",  # Always 0 as requested
            author=author,
            media_type=media_type,
            hashtags=hashtags,
            mentions=mentions,
            links=links,
            music=music,
            location=location,
            is_video=is_video,
            thumbnail_url=thumbnail_url
        )
    
    def scrape_media(self, url: str, retry_count: int = 3) -> dict:
        """Scrape a single Instagram reel/post."""
        for attempt in range(retry_count):
            try:
                log_message(f"\n📄 Navigating to media: {url}")
                self.page.goto(url, wait_until="domcontentloaded")
                self._human_like_delay(2.0, 4.0)
                
                if self._check_rate_limit():
                    log_message(f"  ⚠️ Rate limited! Waiting 30 seconds...", "WARNING")
                    time.sleep(30)
                    continue
                
                # Wait for content
                content_found = False
                selectors = [
                    'section',
                    'main',
                    'article',
                    'a[href*="/p/"]',
                    'a[href*="/reel/"]',
                ]
                
                for selector in selectors:
                    try:
                        self.page.wait_for_selector(selector, timeout=5000)
                        count = self.page.locator(selector).count()
                        if count > 0:
                            log_message(f"  ✅ Found content with selector: {selector} ({count} elements)")
                            content_found = True
                            break
                    except:
                        continue
                
                if not content_found:
                    log_message("  ⚠️ No content found", "WARNING")
                    self._dump_debug("no_content_found")
                    raise MediaNotFoundError("Media page never loaded")
                
                # Handle popups
                self._handle_popups()
                
                # Extract media data
                media = self._extract_media_data(url)
                
                log_message(f"  Media type: {media.media_type}")
                log_message(f"  Author: @{media.author}")
                log_message(f"  Caption length: {len(media.caption) if media.caption else 0} chars")
                log_message(f"  Likes: {media.like_count} | Comments: {media.comment_count}")
                if media.music:
                    log_message(f"  Music: {media.music}")
                
                return {
                    "url": url,
                    "shortcode": media.shortcode,
                    "media_type": media.media_type,
                    "author": media.author,
                    "caption": media.caption,
                    "created_at": media.created_at,
                    "like_count": media.like_count,
                    "comment_count": media.comment_count,
                    "view_count": "0",  # Always 0
                    "hashtags": media.hashtags,
                    "mentions": media.mentions,
                    "links": media.links,
                    "music": media.music,
                    "location": media.location,
                    "is_video": media.is_video,
                    "thumbnail_url": media.thumbnail_url
                }
                
            except Exception as e:
                if attempt < retry_count - 1:
                    log_message(f"  ⚠️ Error: {e}. Retrying...", "WARNING")
                    time.sleep(random.uniform(5, 10))
                else:
                    raise
    
    def _handle_popups(self):
        """Handle common Instagram popups."""
        try:
            not_now = self.page.locator('button:has-text("Not Now")')
            if not_now.count() > 0:
                not_now.click()
                self._human_like_delay()
        except:
            pass
        
        try:
            save_info = self.page.locator('button:has-text("Save Info")')
            if save_info.count() > 0:
                save_info.click()
                self._human_like_delay()
        except:
            pass
    
    def scrape_profile(self, url: str, max_media: int = 10) -> dict:
        """Scrape an Instagram profile."""
        log_message(f"\n📄 Navigating to profile: {url}")
        self.page.goto(url, wait_until="domcontentloaded")
        self._human_like_delay(2.0, 4.0)
        
        if self._check_rate_limit():
            raise RateLimitError("Rate limited while loading profile.")
        
        try:
            self.page.wait_for_selector('header', timeout=TIMEOUT_ELEMENT)
            self._human_like_delay()
        except PWTimeout:
            self._dump_debug("profile_load_failed")
            raise ProfileNotFoundError("Profile page never loaded")
        
        username = self._extract_username_from_url(url)
        display_name = ""
        bio = ""
        follower_count = "0"
        following_count = "0"
        post_count = "0"
        is_private = False
        is_verified = False
        
        try:
            name_el = self.page.locator('header h2').first
            if name_el.count() > 0:
                display_name = name_el.inner_text()
        except:
            pass
        
        try:
            bio_el = self.page.locator('header div[class*="bio"] span, header div[class*="description"]').first
            if bio_el.count() > 0:
                bio = bio_el.inner_text()
        except:
            pass
        
        try:
            stats = self.page.locator('header ul').first
            if stats.count() > 0:
                stat_items = stats.locator('li').all()
                if len(stat_items) >= 3:
                    try:
                        post_count = parse_count(stat_items[0].inner_text().split()[0])
                        follower_count = parse_count(stat_items[1].inner_text().split()[0])
                        following_count = parse_count(stat_items[2].inner_text().split()[0])
                    except:
                        pass
        except:
            pass
        
        log_message(f"  Profile: @{username} ({display_name})")
        log_message(f"  Bio: {bio[:100] if bio else 'None'}...")
        log_message(f"  Followers: {follower_count} | Posts: {post_count}")
        
        return {
            "url": url,
            "username": username,
            "display_name": display_name,
            "bio": bio,
            "follower_count": follower_count,
            "following_count": following_count,
            "post_count": post_count,
            "is_private": is_private,
            "is_verified": is_verified,
            "media": []
        }