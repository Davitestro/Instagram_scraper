"""
Core scraping logic for Instagram.
"""

import json
import re
import time
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse

from playwright.sync_api import TimeoutError as PWTimeout, Page

from config import (
    TIMEOUT_ELEMENT, TIMEOUT_WAIT, TIMEOUT_NAVIGATION,
    SCROLL_AMOUNT, SCROLL_DELAY, MAX_RETRIES, DEBUG_DIR
)
from exceptions import (
    MediaNotFoundError, ProfileNotFoundError, 
    LoginError, ElementNotFoundError
)
from models import InstagramMedia, InstagramComment, InstagramMediaDetails, InstagramProfile
from utils import parse_count
from browser_manager import BrowserManager


class InstagramScraper:
    """Main scraper for Instagram."""
    
    def __init__(self, browser_manager: BrowserManager):
        self.browser_manager = browser_manager
        self.page = browser_manager.page
    
    def verify_logged_in(self) -> bool:
        """Check if user is logged into Instagram."""
        try:
            self.page.goto("https://www.instagram.com/", 
                         wait_until="domcontentloaded", 
                         timeout=TIMEOUT_NAVIGATION)
            self.page.wait_for_timeout(TIMEOUT_WAIT)
            
            # Check multiple indicators
            checks = []
            
            # Check for login page
            if "login" not in self.page.url.lower():
                checks.append(True)
            
            # Check for main feed elements
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
            print(f"  Login check: {'✅ Logged in' if is_logged_in else '❌ Not logged in'}")
            
            return is_logged_in
            
        except Exception as e:
            print(f"  Login verification error: {e}")
            return False
    
    def ensure_logged_in(self):
        """Ensure user is logged in, prompt if not."""
        if not self.verify_logged_in():
            print("\n⚠️  Not logged in to Instagram!")
            self.page.goto("https://www.instagram.com/accounts/login/")
            print("📱 Please log in manually in the Chrome window...")
            print("   (If you see a popup asking to save login info, click 'Save Info')")
            input("⏳ Press Enter when you're logged in and can see your feed...")
            
            if not self.verify_logged_in():
                raise LoginError("Still not logged in. Please log in and try again.")
    
    def _dump_debug(self, label: str):
        """Save debug information."""
        try:
            self.page.screenshot(path=str(DEBUG_DIR / f"{label}.png"), full_page=True)
            (DEBUG_DIR / f"{label}.html").write_text(
                self.page.content(), encoding="utf-8"
            )
            print(f"  [debug] saved {DEBUG_DIR / (label + '.png')} and .html")
        except Exception as e:
            print(f"  [debug] could not save debug snapshot: {e}")
    
    def _extract_shortcode(self, url: str) -> str:
        """Extract shortcode from Instagram URL."""
        # Handle URLs like:
        # https://www.instagram.com/reel/CxYz123ABCD/
        # https://www.instagram.com/p/CxYz123ABCD/
        # https://www.instagram.com/tv/CxYz123ABCD/
        match = re.search(r'/(?:reel|p|tv)/([A-Za-z0-9_-]+)', url)
        if match:
            return match.group(1)
        return ""
    
    def _extract_username_from_url(self, url: str) -> str:
        """Extract username from profile URL."""
        # https://www.instagram.com/username/
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
    
    def scrape_media(self, url: str, n_comments: int = 10) -> dict:
        """
        Scrape a single Instagram reel/post and its comments.
        
        Args:
            url: Instagram media URL
            n_comments: Number of comments to collect
        
        Returns:
            Dictionary with media data and comments
        """
        print(f"\n📄 Navigating to media: {url}")
        self.page.goto(url, wait_until="domcontentloaded")
        
        try:
            # Wait for content to load
            self.page.wait_for_selector('article', timeout=TIMEOUT_ELEMENT)
            self.page.wait_for_timeout(TIMEOUT_WAIT)
            
            # Handle potential login popup
            try:
                self.page.locator('button:has-text("Not now")').click()
            except Exception:
                pass
            
        except PWTimeout:
            self._dump_debug("media_load_failed")
            raise MediaNotFoundError(
                "Media page never loaded — check if the link exists. "
                "See debug/media_load_failed.png"
            )
        
        # Extract media data
        media = self._extract_media_data(url)
        
        print(f"  Media type: {media.media_type}")
        print(f"  Author: @{media.author_username}")
        print(f"  Caption: {media.caption[:100] if media.caption else 'None'}...")
        print(f"  Likes: {media.like_count} | Comments: {media.comment_count}")
        
        # Extract comments
        comments = self._collect_comments(n_comments)
        
        return {
            "url": url,
            "shortcode": media.shortcode,
            "media_type": media.media_type,
            "author": media.author,
            "author_username": media.author_username,
            "caption": media.caption,
            "created_at": media.created_at,
            "like_count": media.like_count,
            "comment_count": media.comment_count,
            "view_count": media.view_count,
            "hashtags": media.hashtags,
            "mentions": media.mentions,
            "links": media.links,
            "music": media.music,
            "location": media.location,
            "is_video": media.is_video,
            "thumbnail_url": media.thumbnail_url,
            "comments": [c.__dict__ for c in comments]
        }
    
    def _extract_media_data(self, url: str) -> InstagramMedia:
        """Extract media data from the page."""
        shortcode = self._extract_shortcode(url)
        
        # Extract author
        author_username = ""
        author_name = ""
        try:
            # Click on the author name to reveal the username
            author_el = self.page.locator('article header a').first
            if author_el.count() > 0:
                href = author_el.get_attribute('href')
                if href:
                    author_username = href.strip('/')
                    # The display name is the text content
                    author_name = author_el.inner_text()
        except Exception:
            pass
        
        # Extract caption
        caption = ""
        try:
            # Try different possible caption selectors
            for selector in [
                'article h1 span[dir="auto"]',  # Sometimes this works
                'article div[role="presentation"] span[dir="auto"]',
                'article div[data-testid="caption"]',
                'article div[class*="caption"]'
            ]:
                try:
                    cap_el = self.page.locator(selector).first
                    if cap_el.count() > 0:
                        caption = cap_el.inner_text()
                        break
                except Exception:
                    continue
        except Exception:
            pass
        
        # Extract timestamps
        created_at = None
        try:
            time_el = self.page.locator('time').first
            if time_el.count() > 0:
                created_at = time_el.get_attribute("datetime")
        except Exception:
            pass
        
        # Extract metrics
        like_count = "0"
        comment_count = "0"
        view_count = "0"
        
        try:
            # Extract likes
            for selector in [
                'button[class*="like"] span',
                'article button[type="button"] span[class*="like"]',
                'div[class*="likeCount"] span'
            ]:
                try:
                    like_el = self.page.locator(selector).first
                    if like_el.count() > 0:
                        like_text = like_el.inner_text()
                        like_count = parse_count(like_text)
                        break
                except Exception:
                    continue
        except Exception:
            pass
        
        try:
            # Extract comments
            comment_el = self.page.locator('button:has-text("Comment") span').first
            if comment_el.count() > 0:
                comment_text = comment_el.inner_text()
                comment_count = parse_count(comment_text)
        except Exception:
            pass
        
        try:
            # Extract view count (for reels)
            view_el = self.page.locator('span:has-text("views")').first
            if view_el.count() > 0:
                view_text = view_el.inner_text()
                view_count = parse_count(view_text)
        except Exception:
            pass
        
        # Determine media type
        media_type = "post"
        if "/reel/" in url:
            media_type = "reel"
        elif "/tv/" in url:
            media_type = "video"
        elif "/p/" in url:
            media_type = "post"
        
        # Extract hashtags, mentions, links
        hashtags = self._extract_hashtags(caption)
        mentions = self._extract_mentions(caption)
        links = self._extract_links(caption)
        
        # Extract music if available
        music = None
        try:
            music_el = self.page.locator('a[href*="/music/"]').first
            if music_el.count() > 0:
                music = music_el.inner_text()
        except Exception:
            pass
        
        # Extract location if available
        location = None
        try:
            location_el = self.page.locator('a[href*="/explore/locations/"]').first
            if location_el.count() > 0:
                location = location_el.inner_text()
        except Exception:
            pass
        
        return InstagramMedia(
            url=url,
            shortcode=shortcode,
            caption=caption,
            created_at=created_at,
            like_count=like_count,
            comment_count=comment_count,
            view_count=view_count,
            author=author_name,
            author_username=author_username,
            media_type=media_type,
            hashtags=hashtags,
            mentions=mentions,
            links=links,
            music=music,
            location=location,
            is_video=media_type in ["reel", "video"],
            thumbnail_url=""  # Would need additional scraping
        )
    
    def _collect_comments(self, n_comments: int) -> List[InstagramComment]:
        """
        Collect comments by scrolling and expanding.
        
        Args:
            n_comments: Number of comments to collect
        
        Returns:
            List of InstagramComment objects
        """
        print(f"\n📥 Collecting up to {n_comments} comments...")
        comments = []
        seen_texts = set()
        attempts = 0
        max_attempts = min(n_comments // 2 + 5, 30)
        
        # Click to load comments section if needed
        try:
            # Sometimes comments need to be clicked to load
            comment_button = self.page.locator('button:has-text("View all comments")')
            if comment_button.count() > 0:
                comment_button.click()
                self.page.wait_for_timeout(TIMEOUT_WAIT)
        except Exception:
            pass
        
        # Try to expand comments
        try:
            # Click on comment section to load more
            comment_section = self.page.locator('section[role="presentation"]')
            if comment_section.count() > 0:
                comment_section.click()
                self.page.wait_for_timeout(TIMEOUT_WAIT)
        except Exception:
            pass
        
        while len(comments) < n_comments and attempts < max_attempts:
            # Scroll to load more comments
            self.page.mouse.wheel(0, SCROLL_AMOUNT)
            self.page.wait_for_timeout(SCROLL_DELAY)
            
            # Find comment elements
            comment_elements = self.page.locator('ul[role="list"] li').all()
            
            new_count = 0
            
            for el in comment_elements:
                try:
                    # Check if it's a comment (has author and text)
                    author_el = el.locator('span[class*="username"]').first
                    if author_el.count() == 0:
                        continue
                    
                    text_el = el.locator('span[dir="auto"]').last
                    if text_el.count() == 0:
                        continue
                    
                    # Extract data
                    author_username = author_el.inner_text()
                    
                    # Full comment text
                    comment_text = text_el.inner_text()
                    
                    # Avoid duplicates
                    key = f"{author_username}:{comment_text[:50]}"
                    if key in seen_texts:
                        continue
                    seen_texts.add(key)
                    
                    # Extract timestamp
                    created_at = None
                    try:
                        time_el = el.locator('time').first
                        if time_el.count() > 0:
                            created_at = time_el.get_attribute("datetime")
                    except Exception:
                        pass
                    
                    # Extract likes
                    like_count = "0"
                    try:
                        like_el = el.locator('button[class*="like"] span').first
                        if like_el.count() > 0:
                            like_text = like_el.inner_text()
                            if like_text:
                                like_count = parse_count(like_text)
                    except Exception:
                        pass
                    
                    # Check for replies
                    reply_links = el.locator('button:has-text("reply")')
                    has_replies = reply_links.count() > 0
                    
                    comment = InstagramComment(
                        text=comment_text,
                        author=author_username,
                        author_username=author_username,
                        created_at=created_at,
                        like_count=like_count,
                        reply_count="0",
                        replies=[],
                        level=1
                    )
                    
                    comments.append(comment)
                    new_count += 1
                    
                    if len(comments) >= n_comments:
                        break
                    
                except Exception as e:
                    continue
            
            attempts += 1
            print(f"  [{len(comments)}/{n_comments}] comments collected "
                  f"(found {new_count} new, attempt {attempts}/{max_attempts})")
            
            if new_count == 0 and attempts > 3:
                # Try clicking "View more" if available
                try:
                    view_more = self.page.locator('button:has-text("View more comments")')
                    if view_more.count() > 0:
                        view_more.click()
                        self.page.wait_for_timeout(TIMEOUT_WAIT)
                except Exception:
                    pass
        
        return comments
    
    def scrape_profile(self, url: str, max_media: int = 10) -> dict:
        """
        Scrape an Instagram profile.
        
        Args:
            url: Instagram profile URL
            max_media: Maximum number of media to collect
        
        Returns:
            Dictionary with profile data and media
        """
        print(f"\n📄 Navigating to profile: {url}")
        self.page.goto(url, wait_until="domcontentloaded")
        
        try:
            self.page.wait_for_selector('header', timeout=TIMEOUT_ELEMENT)
            self.page.wait_for_timeout(TIMEOUT_WAIT)
            
            # Handle potential login popup
            try:
                self.page.locator('button:has-text("Not now")').click()
            except Exception:
                pass
                
        except PWTimeout:
            self._dump_debug("profile_load_failed")
            raise ProfileNotFoundError(
                "Profile page never loaded — see debug/profile_load_failed.png"
            )
        
        # Extract profile info
        username = self._extract_username_from_url(url)
        display_name = ""
        bio = ""
        follower_count = "0"
        following_count = "0"
        post_count = "0"
        is_private = False
        is_verified = False
        
        try:
            # Display name
            name_el = self.page.locator('header h2').first
            if name_el.count() > 0:
                display_name = name_el.inner_text()
        except Exception:
            pass
        
        try:
            # Bio
            bio_el = self.page.locator('header div[class*="bio"] span').first
            if bio_el.count() > 0:
                bio = bio_el.inner_text()
        except Exception:
            pass
        
        try:
            # Stats
            stats = self.page.locator('header ul').first
            if stats.count() > 0:
                stat_items = stats.locator('li').all()
                if len(stat_items) >= 3:
                    try:
                        post_count = parse_count(stat_items[0].inner_text().split()[0])
                        follower_count = parse_count(stat_items[1].inner_text().split()[0])
                        following_count = parse_count(stat_items[2].inner_text().split()[0])
                    except Exception:
                        pass
        except Exception:
            pass
        
        try:
            # Check if private
            private_el = self.page.locator('button:has-text("Request to Follow")')
            is_private = private_el.count() > 0
        except Exception:
            pass
        
        try:
            # Check if verified
            verified_el = self.page.locator('svg[aria-label="Verified"]')
            is_verified = verified_el.count() > 0
        except Exception:
            pass
        
        print(f"  Profile: @{username} ({display_name})")
        print(f"  Bio: {bio[:100] if bio else 'None'}...")
        print(f"  Followers: {follower_count} | Posts: {post_count}")
        print(f"  Private: {is_private} | Verified: {is_verified}")
        
        # Collect media
        media = self._collect_profile_media(max_media)
        
        # Sort media by type
        reels = [m for m in media if m.media_type == "reel"]
        posts = [m for m in media if m.media_type == "post"]
        
        print(f"  Found {len(reels)} reels, {len(posts)} posts")
        
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
            "media": [m.__dict__ for m in media]
        }
    
    def _collect_profile_media(self, max_media: int) -> List[InstagramMedia]:
        """
        Collect media from profile by scrolling.
        
        Args:
            max_media: Maximum number of media to collect
        
        Returns:
            List of InstagramMedia objects
        """
        print(f"\n📥 Collecting up to {max_media} media items...")
        media = []
        seen_shortcodes = set()
        attempts = 0
        max_attempts = min(max_media + 5, 30)
        
        while len(media) < max_media and attempts < max_attempts:
            # Find media grid items
            grid_items = self.page.locator('article a[href*="/p/"], article a[href*="/reel/"]').all()
            
            new_count = 0
            
            for item in grid_items:
                try:
                    href = item.get_attribute("href")
                    if not href:
                        continue
                    
                    # Extract shortcode
                    shortcode = self._extract_shortcode(href)
                    if not shortcode or shortcode in seen_shortcodes:
                        continue
                    
                    seen_shortcodes.add(shortcode)
                    new_count += 1
                    
                    # Determine media type
                    media_type = "post"
                    if "/reel/" in href:
                        media_type = "reel"
                    elif "/tv/" in href:
                        media_type = "video"
                    
                    # Get thumbnail
                    thumbnail = ""
                    try:
                        img = item.locator('img').first
                        if img.count() > 0:
                            thumbnail = img.get_attribute("src")
                    except Exception:
                        pass
                    
                    # Get view/like count from the grid item
                    like_count = "0"
                    try:
                        count_el = item.locator('span').last
                        if count_el.count() > 0:
                            count_text = count_el.inner_text()
                            # Check if it's like count
                            if "view" not in count_text.lower():
                                like_count = parse_count(count_text)
                    except Exception:
                        pass
                    
                    # Try to get view count for reels
                    view_count = "0"
                    if media_type == "reel":
                        try:
                            view_el = item.locator('span:has-text("views")').first
                            if view_el.count() > 0:
                                view_count = parse_count(view_el.inner_text())
                        except Exception:
                            pass
                    
                    media.append(InstagramMedia(
                        url=f"https://www.instagram.com{href}",
                        shortcode=shortcode,
                        media_type=media_type,
                        thumbnail_url=thumbnail,
                        like_count=like_count,
                        view_count=view_count,
                        author_username=self._extract_username_from_url(self.page.url)
                    ))
                    
                    if len(media) >= max_media:
                        break
                    
                except Exception as e:
                    continue
            
            # Scroll to load more
            self.page.mouse.wheel(0, SCROLL_AMOUNT)
            self.page.wait_for_timeout(SCROLL_DELAY)
            attempts += 1
            print(f"  [{len(media)}/{max_media}] media collected "
                  f"(found {new_count} new, attempt {attempts}/{max_attempts})")
        
        return media