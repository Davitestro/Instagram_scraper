"""
Orchestrates Instagram search and data collection.
"""

import json
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

from browser_manager import BrowserManager
from scraper import InstagramScraper
from search_scraper import InstagramSearchScraper
from models import SearchResult
from exporters import DataExporter
from config import DEFAULT_MAX_REELS, DEFAULT_REPLIES


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
                           max_comments: int = DEFAULT_REPLIES,
                           auto_export: bool = True) -> SearchResult:
        """
        Collect data for a single keyword/hashtag.
        
        Args:
            keyword: Search term (hashtag without #)
            max_media: Number of media items to collect
            max_comments: Number of comments per media
            auto_export: Automatically export results
        
        Returns:
            SearchResult object with collected data
        """
        print(f"\n{'='*60}")
        print(f"  COLLECTING DATA FOR: '#{keyword}'")
        print(f"{'='*60}")
        
        # Step 1: Search and get URLs
        media_urls = self.search_scraper.search_keyword(keyword, max_media)
        
        if not media_urls:
            print(f"⚠️  No media found for '#{keyword}'")
            return SearchResult(
                keyword=keyword,
                scraped_at=datetime.now().isoformat(),
                total_media_found=0,
                media_collected=0,
                media_data=[]
            )
        
        # Step 2: Scrape each media
        collected_data = []
        failed_urls = []
        
        for i, url in enumerate(media_urls, 1):
            print(f"\n📌 [{i}/{len(media_urls)}] Processing: {url}")
            
            try:
                media_data = self.scraper.scrape_media(url, max_comments)
                collected_data.append(media_data)
                print(f"  ✅ Collected: {len(media_data.get('comments', []))} comments")
                
            except Exception as e:
                print(f"  ❌ Error scraping {url}: {e}")
                failed_urls.append(url)
                continue
            
            # Wait between requests
            if i < len(media_urls):
                wait_time = 3
                print(f"  ⏳ Waiting {wait_time} seconds...")
                time.sleep(wait_time)
        
        # Step 3: Create search result
        result = SearchResult(
            keyword=keyword,
            scraped_at=datetime.now().isoformat(),
            total_media_found=len(media_urls),
            media_collected=len(collected_data),
            media_data=collected_data
        )
        
        # Step 4: Auto-export if requested
        if auto_export and collected_data:
            print(f"\n📤 Exporting data...")
            exported_files = self.exporter.export_search_result(
                result, 
                self.export_formats,
                platform="instagram"
            )
            print(f"  ✅ Exported {len(exported_files)} files")
        
        # Print summary
        print(f"\n📊 Summary for '#{keyword}':")
        print(f"  • Total media found: {result.total_media_found}")
        print(f"  • Successfully scraped: {result.media_collected}")
        print(f"  • Failed: {len(failed_urls)}")
        if failed_urls:
            print(f"  • Failed URLs: {failed_urls[:3]}{'...' if len(failed_urls) > 3 else ''}")
        
        return result
    
    def collect_multiple_keywords(self, keywords: List[str],
                                 max_media: int = DEFAULT_MAX_REELS,
                                 max_comments: int = DEFAULT_REPLIES) -> Dict[str, SearchResult]:
        """
        Collect data for multiple keywords.
        """
        results = {}
        
        for i, keyword in enumerate(keywords, 1):
            print(f"\n{'#'*60}")
            print(f"  KEYWORD {i}/{len(keywords)}")
            print(f"{'#'*60}")
            
            result = self.collect_for_keyword(keyword, max_media, max_comments)
            results[keyword] = result
            
            # Save individual result
            if result.media_data:
                self._save_search_result(result)
            
            # Wait between keywords
            if keyword != keywords[-1]:
                wait_time = 5
                print(f"\n⏳ Waiting {wait_time} seconds before next keyword...")
                time.sleep(wait_time)
        
        # Export batch summary
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
        
        print(f"  💾 JSON saved to: {filename}")
    
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
                'total_comments_collected',
                'total_likes',
                'total_views',
                'scraped_at'
            ])
            
            for keyword, result in results.items():
                total_comments = sum(len(media.get('comments', [])) for media in result.media_data)
                total_likes = sum(int(media.get('like_count', '0')) for media in result.media_data)
                total_views = sum(int(media.get('view_count', '0')) for media in result.media_data)
                
                writer.writerow([
                    keyword,
                    result.total_media_found,
                    result.media_collected,
                    total_comments,
                    total_likes,
                    total_views,
                    result.scraped_at
                ])
        
        print(f"\n📊 Batch summary saved to: {summary_file}")