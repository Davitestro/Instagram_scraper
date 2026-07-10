"""
Orchestrates Instagram profile scraping and data collection.
"""

import json
import time
import random
from datetime import datetime
from typing import List, Dict

from browser_manager import BrowserManager
from scraper import InstagramScraper
from profile_scraper import InstagramProfileScraper
from models import SearchResult
from exporters import DataExporter
from config import DEFAULT_MAX_REELS
from exceptions import RateLimitError
from utils import log_message


class InstagramDataCollector:
    """Orchestrates the data collection process from profiles."""
    
    def __init__(self, browser_manager: BrowserManager, 
                 export_formats: List[str] = ["json", "csv"]):
        self.browser_manager = browser_manager
        self.scraper = InstagramScraper(browser_manager)
        self.profile_scraper = InstagramProfileScraper(browser_manager.page)
        self.exporter = DataExporter()
        self.export_formats = export_formats
    
    def collect_from_profile(self, username: str, 
                           max_posts: int = DEFAULT_MAX_REELS,
                           auto_export: bool = True) -> SearchResult:
        """
        Collect data from a user's profile.
        
        Args:
            username: Instagram username (without @)
            max_posts: Maximum number of posts to collect
            auto_export: Automatically export results
        
        Returns:
            SearchResult object with collected data
        """
        log_message(f"\n{'='*60}")
        log_message(f"  COLLECTING DATA FROM PROFILE: @{username}")
        log_message(f"{'='*60}")
        
        # Step 1: Get post URLs from profile
        post_urls = self.profile_scraper.get_profile_posts(username, max_posts)
        
        if not post_urls:
            log_message(f"⚠️  No posts found for @{username}")
            return SearchResult(
                keyword=username,  # Use username as key
                scraped_at=datetime.now().isoformat(),
                total_media_found=0,
                media_collected=0,
                media_data=[]
            )
        
        # Step 2: Scrape each post
        collected_data = []
        failed_urls = []
        
        for i, url in enumerate(post_urls, 1):
            log_message(f"\n📌 [{i}/{len(post_urls)}] Processing: {url}")
            
            try:
                media_data = self.scraper.scrape_media(url)
                collected_data.append(media_data)
                log_message(f"  ✅ Collected metadata for: {media_data.get('media_type')} by @{media_data.get('author')}")
                
            except Exception as e:
                log_message(f"  ❌ Error scraping {url}: {e}", "ERROR")
                failed_urls.append(url)
                continue
            
            # Wait between requests
            if i < len(post_urls):
                wait_time = random.uniform(3, 7)
                log_message(f"  ⏳ Waiting {wait_time:.1f} seconds...")
                time.sleep(wait_time)
        
        # Step 3: Create search result
        result = SearchResult(
            keyword=username,  # Use username as key
            scraped_at=datetime.now().isoformat(),
            total_media_found=len(post_urls),
            media_collected=len(collected_data),
            media_data=collected_data
        )
        
        # Step 4: Auto-export if requested
        if auto_export and collected_data:
            log_message(f"\n📤 Exporting data...")
            exported_files = self.exporter.export_search_result(
                result, 
                self.export_formats,
                platform="instagram"
            )
            log_message(f"  ✅ Exported {len(exported_files)} files")
        
        # Print summary
        log_message(f"\n📊 Summary for @{username}:")
        log_message(f"  • Total posts found: {result.total_media_found}")
        log_message(f"  • Successfully scraped: {result.media_collected}")
        log_message(f"  • Failed: {len(failed_urls)}")
        
        return result
    
    def collect_multiple_profiles(self, usernames: List[str],
                                 max_posts: int = DEFAULT_MAX_REELS) -> Dict[str, SearchResult]:
        """
        Collect data from multiple profiles.
        """
        results = {}
        
        for i, username in enumerate(usernames, 1):
            log_message(f"\n{'#'*60}")
            log_message(f"  PROFILE {i}/{len(usernames)}")
            log_message(f"{'#'*60}")
            
            result = self.collect_from_profile(username, max_posts)
            results[username] = result
            
            # Save individual result
            if result.media_data:
                self._save_search_result(result)
            
            # Wait between profiles
            if username != usernames[-1]:
                wait_time = random.uniform(5, 10)
                log_message(f"\n⏳ Waiting {wait_time:.1f} seconds before next profile...")
                time.sleep(wait_time)
        
        # Export batch summary
        self._export_batch_summary(results)
        
        return results
    
    def _save_search_result(self, result: SearchResult):
        """Save search result to JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.exporter.json_dir / f"instagram_profile_{result.keyword}_{timestamp}.json"
        
        output_data = {
            "platform": "instagram",
            "profile": result.keyword,
            "scraped_at": result.scraped_at,
            "total_posts_found": result.total_media_found,
            "posts_collected": result.media_collected,
            "posts": result.media_data
        }
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        log_message(f"  💾 JSON saved to: {filename}")
    
    def _export_batch_summary(self, results: Dict[str, SearchResult]):
        """Export a summary CSV of all collected data."""
        import csv
        summary_file = self.exporter.output_dir / "instagram_profiles_summary.csv"
        
        with open(summary_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow([
                'profile',
                'total_posts_found',
                'posts_collected',
                'total_likes',
                'total_comments',
                'scraped_at'
            ])
            
            for username, result in results.items():
                total_likes = sum(int(media.get('like_count', '0')) for media in result.media_data)
                total_comments = sum(int(media.get('comment_count', '0')) for media in result.media_data)
                
                writer.writerow([
                    username,
                    result.total_media_found,
                    result.media_collected,
                    total_likes,
                    total_comments,
                    result.scraped_at
                ])
        
        log_message(f"\n📊 Batch summary saved to: {summary_file}")