"""
Search functionality for Instagram.
"""

import time
from typing import List, Optional
from urllib.parse import quote_plus

from playwright.sync_api import TimeoutError as PWTimeout

from config import TIMEOUT_ELEMENT, TIMEOUT_WAIT, SCROLL_AMOUNT, SCROLL_DELAY
from exceptions import ElementNotFoundError


class InstagramSearchScraper:
    """Handles search on Instagram."""
    
    def __init__(self, page):
        self.page = page
    
    def search_keyword(self, keyword: str, max_results: int = 10) -> List[str]:
        """
        Search for a keyword and return media URLs.
        
        Args:
            keyword: Search term (e.g., "Global warming")
            max_results: Maximum number of media URLs to collect
        
        Returns:
            List of media URLs
        """
        # Encode keyword for URL
        encoded_keyword = quote_plus(keyword)
        search_url = f"https://www.instagram.com/explore/tags/{encoded_keyword}/"
        
        print(f"\n🔍 Searching for hashtag: '#{keyword}'")
        print(f"📄 Navigating to: {search_url}")
        
        self.page.goto(search_url, wait_until="domcontentloaded")
        
        try:
            # Wait for content to load
            self.page.wait_for_selector('article', timeout=TIMEOUT_ELEMENT)
            self.page.wait_for_timeout(TIMEOUT_WAIT)
            
        except PWTimeout:
            raise ElementNotFoundError(
                f"No content found for '#{keyword}'. The hashtag might not exist."
            )
        
        # Collect media URLs
        media_urls = []
        seen_urls = set()
        attempts = 0
        max_attempts = min(max_results // 2 + 5, 20)
        
        print(f"📥 Collecting up to {max_results} media URLs...")
        
        while len(media_urls) < max_results and attempts < max_attempts:
            # Find all media links
            links = self.page.locator('article a[href*="/p/"], article a[href*="/reel/"]').all()
            
            for link in links:
                try:
                    href = link.get_attribute("href")
                    if not href:
                        continue
                    
                    # Skip ads and sponsored content
                    if "/ad/" in href or "/explore/" in href:
                        continue
                    
                    # Ensure it's a media URL
                    if "/p/" in href or "/reel/" in href or "/tv/" in href:
                        # Get the full URL
                        if href.startswith("/"):
                            href = f"https://www.instagram.com{href}"
                        
                        # Clean URL
                        href = href.split('?')[0]
                        
                        if href not in seen_urls:
                            seen_urls.add(href)
                            media_urls.append(href)
                            
                            if len(media_urls) >= max_results:
                                break
                                
                except Exception:
                    continue
            
            # Scroll to load more
            self.page.mouse.wheel(0, SCROLL_AMOUNT)
            self.page.wait_for_timeout(SCROLL_DELAY)
            attempts += 1
            
            print(f"  [{len(media_urls)}/{max_results}] URLs collected "
                  f"(attempt {attempts}/{max_attempts})")
        
        print(f"✅ Found {len(media_urls)} media URLs for '#{keyword}'")
        return media_urls
    
    def search_users(self, keyword: str, max_results: int = 10) -> List[str]:
        """
        Search for users by keyword.
        
        Args:
            keyword: Search term
            max_results: Maximum number of profiles to collect
        
        Returns:
            List of profile URLs
        """
        encoded_keyword = quote_plus(keyword)
        search_url = f"https://www.instagram.com/explore/search/?q={encoded_keyword}"
        
        print(f"\n🔍 Searching for users: '{keyword}'")
        print(f"📄 Navigating to: {search_url}")
        
        self.page.goto(search_url, wait_until="domcontentloaded")
        
        try:
            self.page.wait_for_selector('article', timeout=TIMEOUT_ELEMENT)
            self.page.wait_for_timeout(TIMEOUT_WAIT)
        except PWTimeout:
            raise ElementNotFoundError(f"No users found for '{keyword}'.")
        
        # Switch to users tab
        try:
            users_tab = self.page.locator('a:has-text("Users")').first
            if users_tab.count() > 0:
                users_tab.click()
                self.page.wait_for_timeout(TIMEOUT_WAIT)
        except Exception:
            pass
        
        # Collect user URLs
        user_urls = []
        seen_urls = set()
        attempts = 0
        
        while len(user_urls) < max_results and attempts < 10:
            # Find user links
            links = self.page.locator('article a[href^="/"]').all()
            
            for link in links:
                try:
                    href = link.get_attribute("href")
                    if not href or "/explore/" in href:
                        continue
                    
                    if href.startswith("/") and len(href) > 1:
                        href = f"https://www.instagram.com{href}"
                    
                    if href not in seen_urls:
                        seen_urls.add(href)
                        user_urls.append(href)
                        
                        if len(user_urls) >= max_results:
                            break
                            
                except Exception:
                    continue
            
            self.page.mouse.wheel(0, SCROLL_AMOUNT)
            self.page.wait_for_timeout(SCROLL_DELAY)
            attempts += 1
        
        print(f"✅ Found {len(user_urls)} user profiles")
        return user_urls