"""
Profile scraping functionality for Instagram.
"""

import time
import random
from typing import List, Optional
from urllib.parse import quote_plus

from playwright.sync_api import TimeoutError as PWTimeout

from config import TIMEOUT_ELEMENT, SCROLL_AMOUNT, SCROLL_DELAY
from exceptions import ElementNotFoundError, RateLimitError
from utils import log_message


class InstagramProfileScraper:
    """Handles scraping posts from a user's profile."""
    
    def __init__(self, page):
        self.page = page
    
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
            
            if "challenge" in self.page.url or "login" in self.page.url:
                return True
                
            return False
            
        except Exception:
            return False
    
    def get_profile_posts(self, username: str, max_posts: int = 10) -> List[str]:
        """
        Navigate to a user's profile and collect post URLs.
        
        Args:
            username: Instagram username (without @)
            max_posts: Maximum number of posts to collect
        
        Returns:
            List of post URLs
        """
        profile_url = f"https://www.instagram.com/{username}/"
        
        log_message(f"\n👤 Navigating to profile: @{username}")
        log_message(f"📄 URL: {profile_url}")
        
        self.page.goto(profile_url, wait_until="domcontentloaded")
        self._human_like_delay(2.0, 4.0)
        
        if self._check_rate_limit():
            raise RateLimitError("Rate limited while loading profile.")
        
        # Check if profile exists
        try:
            # Wait for profile header or posts to load
            content_found = False
            selectors = [
                'header',
                'article',
                'a[href*="/p/"]',
                'a[href*="/reel/"]',
                'section[role="presentation"]'
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
                # Check if profile is private
                private_el = self.page.locator('button:has-text("Request to Follow")')
                if private_el.count() > 0:
                    raise ElementNotFoundError(f"Profile @{username} is private.")
                
                # Check if user not found
                not_found = self.page.locator('div:has-text("Sorry, this page isn\'t available.")')
                if not_found.count() > 0:
                    raise ElementNotFoundError(f"User @{username} not found.")
                
                raise ElementNotFoundError(f"No content found for @{username}")
        except Exception as e:
            if "private" in str(e) or "not found" in str(e):
                raise
            raise ElementNotFoundError(f"Could not load profile @{username}")
        
        # Collect post URLs
        post_urls = self._collect_post_urls(max_posts)
        
        if not post_urls:
            log_message(f"⚠️  No posts found for @{username}")
        else:
            log_message(f"✅ Found {len(post_urls)} posts for @{username}")
        
        return post_urls
    
    def _collect_post_urls(self, max_posts: int) -> List[str]:
        """
        Collect post URLs from the profile with scrolling.
        
        Args:
            max_posts: Maximum number of posts to collect
        
        Returns:
            List of post URLs
        """
        post_urls = []
        seen_urls = set()
        attempts = 0
        max_attempts = 7  # Maximum scroll attempts
        no_new_urls_count = 0
        
        log_message(f"📥 Collecting up to {max_posts} posts...")
        log_message(f"📊 Max scroll attempts: {max_attempts}")
        
        while len(post_urls) < max_posts and attempts < max_attempts:
            log_message(f"  🔄 Scroll attempt {attempts + 1}/{max_attempts}")
            
            # Find all post links
            links = self.page.locator('a[href*="/p/"], a[href*="/reel/"], a[href*="/tv/"]').all()
            
            new_urls_found = 0
            
            for link in links:
                try:
                    href = link.get_attribute("href")
                    if not href:
                        continue
                    
                    # Skip ads and sponsored content
                    if "/ad/" in href or "/explore/" in href or "/accounts/" in href:
                        continue
                    
                    # Get full URL
                    if href.startswith("/"):
                        href = f"https://www.instagram.com{href}"
                    
                    # Clean URL
                    href = href.split('?')[0]
                    
                    if href not in seen_urls:
                        seen_urls.add(href)
                        post_urls.append(href)
                        new_urls_found += 1
                        
                        if len(post_urls) >= max_posts:
                            break
                            
                except Exception:
                    continue
            
            log_message(f"    Found {new_urls_found} new posts (total: {len(post_urls)}/{max_posts})")
            
            # Check if we've reached the target
            if len(post_urls) >= max_posts:
                log_message(f"  ✅ Reached target of {max_posts} posts")
                break
            
            # Check if no new URLs found
            if new_urls_found == 0:
                no_new_urls_count += 1
                log_message(f"    ⚠️ No new URLs found ({no_new_urls_count}/3 consecutive)")
                
                if no_new_urls_count >= 3:
                    log_message(f"  📌 No new posts after 3 attempts. Stopping scroll.")
                    break
            else:
                no_new_urls_count = 0
            
            # Scroll to load more posts
            scroll_amount = random.randint(600, 1000)
            self.page.mouse.wheel(0, scroll_amount)
            log_message(f"    📜 Scrolled {scroll_amount}px")
            self._human_like_delay(1.0, 2.0)
            
            attempts += 1
        
        # If we reached max attempts without enough posts
        if len(post_urls) < max_posts and attempts >= max_attempts:
            log_message(f"  ⚠️ Reached max scroll attempts ({max_attempts}) with {len(post_urls)} posts")
        
        return post_urls