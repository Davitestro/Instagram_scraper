"""
Orchestrates Instagram search and data collection.
"""

import json
import time
import random
from datetime import datetime
from typing import List, Dict

from browser_manager import BrowserManager
from scraper import InstagramScraper
from search_scraper import InstagramSearchScraper
from models import SearchResult
from exporters import DataExporter
from config import DEFAULT_MAX_REELS
from exceptions import RateLimitError
from utils import log_message  # Add this import


class InstagramDataCollector:
    """Orchestrates the data collection process."""
    
    def __init__(self, browser_manager: BrowserManager, 
                 export_formats: List[str] = ["json", "csv"]):
        self.browser_manager = browser_manager
        self.scraper = InstagramScraper(browser_manager)
        self.search_scraper = InstagramSearchScraper(browser_manager.page)
        self.exporter = DataExporter()
        self.export_formats = export_formats
    
    def collect_for_keyword(self, keyword: str, 
                           max_media: int = DEFAULT_MAX_REELS,
                           auto_export: bool = True) -> SearchResult:
        """Collect data for a single keyword/hashtag."""
        log_message(f"\n{'='*60}")
        log_message(f"  COLLECTING DATA FOR: '#{keyword}'")
        log_message(f"{'='*60}")
        
        media_urls = self.search_scraper.search_keyword(keyword, max_media)
        
        if not media_urls:
            log_message(f"⚠️  No media found for '#{keyword}'")
            return SearchResult(
                keyword=keyword,
                scraped_at=datetime.now().isoformat(),
                total_media_found=0,
                media_collected=0,
                media_data=[]
            )
        
        collected_data = []
        failed_urls = []
        
        for i, url in enumerate(media_urls, 1):
            log_message(f"\n📌 [{i}/{len(media_urls)}] Processing: {url}")
            
            try:
                media_data = self.scraper.scrape_media(url)
                collected_data.append(media_data)
                log_message(f"  ✅ Collected metadata for: {media_data.get('media_type')} by @{media_data.get('author_username')}")
                
            except Exception as e:
                log_message(f"  ❌ Error scraping {url}: {e}", "ERROR")
                failed_urls.append(url)
                continue
            
            if i < len(media_urls):
                wait_time = random.uniform(3, 7)
                log_message(f"  ⏳ Waiting {wait_time:.1f} seconds...")
                time.sleep(wait_time)
        
        result = SearchResult(
            keyword=keyword,
            scraped_at=datetime.now().isoformat(),
            total_media_found=len(media_urls),
            media_collected=len(collected_data),
            media_data=collected_data
        )
        
        if auto_export and collected_data:
            log_message(f"\n📤 Exporting data...")
            exported_files = self.exporter.export_search_result(
                result, 
                self.export_formats,
                platform="instagram"
            )
            log_message(f"  ✅ Exported {len(exported_files)} files")
        
        log_message(f"\n📊 Summary for '#{keyword}':")
        log_message(f"  • Total media found: {result.total_media_found}")
        log_message(f"  • Successfully scraped: {result.media_collected}")
        log_message(f"  • Failed: {len(failed_urls)}")
        
        return result
    
    def collect_multiple_keywords(self, keywords: List[str],
                                 max_media: int = DEFAULT_MAX_REELS) -> Dict[str, SearchResult]:
        """Collect data for multiple keywords."""
        results = {}
        
        for i, keyword in enumerate(keywords, 1):
            log_message(f"\n{'#'*60}")
            log_message(f"  KEYWORD {i}/{len(keywords)}")
            log_message(f"{'#'*60}")
            
            result = self.collect_for_keyword(keyword, max_media)
            results[keyword] = result
            
            if result.media_data:
                self._save_search_result(result)
            
            if keyword != keywords[-1]:
                wait_time = random.uniform(5, 10)
                log_message(f"\n⏳ Waiting {wait_time:.1f} seconds before next keyword...")
                time.sleep(wait_time)
        
        self._export_batch_summary(results)
        
        return results
    
    def _save_search_result(self, result: SearchResult):
        """Save search result to JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.exporter.json_dir / f"instagram_search_{result.keyword.replace(' ', '_')}_{timestamp}.json"
        
        output_data = {
            "platform": "instagram",
            "keyword": result.keyword,
            "scraped_at": result.scraped_at,
            "total_media_found": result.total_media_found,
            "media_collected": result.media_collected,
            "media": result.media_data
        }
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        log_message(f"  💾 JSON saved to: {filename}")
    
    def _export_batch_summary(self, results: Dict[str, SearchResult]):
        """Export a summary CSV of all collected data."""
        import csv
        summary_file = self.exporter.output_dir / "instagram_batch_summary.csv"
        
        with open(summary_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow([
                'keyword',
                'total_media_found',
                'media_collected',
                'total_likes',
                'total_comments',
                'total_views',
                'scraped_at'
            ])
            
            for keyword, result in results.items():
                total_likes = sum(int(media.get('like_count', '0')) for media in result.media_data)
                total_comments = sum(int(media.get('comment_count', '0')) for media in result.media_data)
                total_views = sum(int(media.get('view_count', '0')) for media in result.media_data)
                
                writer.writerow([
                    keyword,
                    result.total_media_found,
                    result.media_collected,
                    total_likes,
                    total_comments,
                    total_views,
                    result.scraped_at
                ])
        
        log_message(f"\n📊 Batch summary saved to: {summary_file}")