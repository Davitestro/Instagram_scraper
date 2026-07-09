"""
Search functionality for Instagram.
"""

import time
import random
from typing import List
from urllib.parse import quote_plus

from playwright.sync_api import TimeoutError as PWTimeout

from config import TIMEOUT_ELEMENT
from exceptions import ElementNotFoundError, RateLimitError
from utils import log_message  # Add this import


class InstagramSearchScraper:
    """Handles search on Instagram."""
    
    def __init__(self, page):
        self.page = page
    
    def _human_like_delay(self):
        """Add human-like delays between actions."""
        delay = random.uniform(1.0, 3.0)
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
            
            if "challenge" in self.page.url or "login" in self.page.url:
                return True
                
            return False
            
        except Exception:
            return False
    
    def search_keyword(self, keyword: str, max_results: int = 10) -> List[str]:
        """
        Search for a keyword and return media URLs.
        """
        encoded_keyword = quote_plus(keyword)
        
        # Try multiple search approaches
        search_urls = [
            f"https://www.instagram.com/explore/tags/{encoded_keyword}/",
            f"https://www.instagram.com/explore/search/keyword/?q=%23{encoded_keyword}",
            f"https://www.instagram.com/explore/search/?q=%23{encoded_keyword}",
        ]
        
        log_message(f"\n🔍 Searching for hashtag: '#{keyword}'")
        
        for search_url in search_urls:
            try:
                log_message(f"📄 Trying: {search_url}")
                self.page.goto(search_url, wait_until="domcontentloaded")
                self._human_like_delay()
                
                if self._check_rate_limit():
                    log_message(f"  ⚠️ Rate limited! Waiting...", "WARNING")
                    time.sleep(30)
                    continue
                
                # Try multiple selectors for content
                content_found = False
                selectors = [
                    'article',
                    'a[href*="/p/"]',
                    'a[href*="/reel/"]',
                    'div[class*="post"]',
                    'div[class*="photo"]',
                    'section[role="presentation"]',
                    'main',
                    'div[class*="grid"]'
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
                
                if content_found:
                    urls = self._collect_media_urls(max_results)
                    if urls:
                        log_message(f"✅ Found {len(urls)} media URLs for '#{keyword}'")
                        return urls
                
            except Exception as e:
                log_message(f"  ❌ Error with {search_url}: {e}", "DEBUG")
                continue
        
        raise ElementNotFoundError(
            f"No content found for '#{keyword}'. The hashtag might not exist or you're being rate limited."
        )
    
    def _collect_media_urls(self, max_results: int) -> List[str]:
        """Collect media URLs from the page."""
        media_urls = []
        seen_urls = set()
        attempts = 0
        max_attempts = min(max_results // 2 + 5, 10)
        no_new_urls_count = 0
        
        log_message(f"📥 Collecting up to {max_results} media URLs...")
        
        while len(media_urls) < max_results and attempts < max_attempts:
            links = self.page.locator('a[href*="/p/"], a[href*="/reel/"], a[href*="/tv/"]').all()
            
            new_urls_found = 0
            
            for link in links:
                try:
                    href = link.get_attribute("href")
                    if not href:
                        continue
                    
                    if "/ad/" in href or "/explore/" in href or "/accounts/" in href:
                        continue
                    
                    if href.startswith("/"):
                        href = f"https://www.instagram.com{href}"
                    
                    href = href.split('?')[0]
                    
                    if href not in seen_urls:
                        seen_urls.add(href)
                        media_urls.append(href)
                        new_urls_found += 1
                        
                        if len(media_urls) >= max_results:
                            break
                            
                except Exception:
                    continue
            
            log_message(f"  [{len(media_urls)}/{max_results}] URLs collected "
                  f"(found {new_urls_found} new, attempt {attempts + 1}/{max_attempts})")
            
            if new_urls_found == 0:
                no_new_urls_count += 1
                if no_new_urls_count >= 3:
                    self.page.mouse.wheel(0, random.randint(500, 1200))
                    self._human_like_delay()
            else:
                no_new_urls_count = 0
            
            if len(media_urls) < max_results:
                self.page.mouse.wheel(0, random.randint(300, 600))
                self._human_like_delay()
                attempts += 1
            
            if no_new_urls_count >= 5:
                log_message(f"  📌 No new URLs found. Stopping collection.")
                break
        
        return media_urls