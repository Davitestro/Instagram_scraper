"""
Data export functionality for CSV and JSON formats.
"""

import csv
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

from models import SearchResult


class DataExporter:
    """Handles exporting data to various formats."""
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        self.json_dir = self.output_dir / "json"
        self.csv_dir = self.output_dir / "csv"
        self.json_dir.mkdir(exist_ok=True)
        self.csv_dir.mkdir(exist_ok=True)
    
    def export_search_result(self, result: SearchResult, 
                            formats: List[str] = ["json", "csv"],
                            platform: str = "instagram") -> Dict[str, Path]:
        """
        Export a search result to specified formats.
        
        Args:
            result: SearchResult object
            formats: List of formats to export ('json', 'csv')
            platform: 'instagram' or 'twitter'
        
        Returns:
            Dictionary mapping format to file path
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"{platform}_search_{result.keyword.replace(' ', '_')}_{timestamp}"
        
        exported_files = {}
        
        if "json" in formats:
            json_path = self.export_json(result, base_name, platform)
            exported_files["json"] = json_path
        
        if "csv" in formats:
            if platform == "instagram":
                csv_paths = self._export_instagram_csv(result, base_name)
            else:
                csv_paths = self._export_twitter_csv(result, base_name)
            exported_files.update(csv_paths)
        
        return exported_files
    
    def export_json(self, result: SearchResult, base_name: str, platform: str) -> Path:
        """Export search result as JSON."""
        filepath = self.json_dir / f"{base_name}.json"
        
        data = {
            "platform": platform,
            "keyword": result.keyword,
            "scraped_at": result.scraped_at,
            "total_media_found": result.total_media_found,
            "media_collected": result.media_collected,
            "media": result.media_data
        }
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"  ✅ JSON exported: {filepath}")
        return filepath
    
    def _export_instagram_csv(self, result: SearchResult, base_name: str) -> Dict[str, Path]:
        """
        Export Instagram results to multiple CSV files.
        """
        exported = {}
        
        # 1. Export main media
        main_file = self.csv_dir / f"{base_name}_media.csv"
        self._export_instagram_media_csv(result, main_file)
        exported["media_csv"] = main_file
        
        # 2. Export comments
        comments_file = self.csv_dir / f"{base_name}_comments.csv"
        self._export_instagram_comments_csv(result, comments_file)
        exported["comments_csv"] = comments_file
        
        # 3. Export flat view
        flat_file = self.csv_dir / f"{base_name}_flat.csv"
        self._export_instagram_flat_csv(result, flat_file)
        exported["flat_csv"] = flat_file
        
        return exported
    
    def _export_instagram_media_csv(self, result: SearchResult, filepath: Path):
        """Export Instagram media to CSV."""
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            fieldnames = [
                'keyword',
                'media_url',
                'media_type',
                'shortcode',
                'author_username',
                'caption',
                'created_at',
                'like_count',
                'comment_count',
                'view_count',
                'hashtags',
                'mentions',
                'links',
                'music',
                'location'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for media in result.media_data:
                writer.writerow({
                    'keyword': result.keyword,
                    'media_url': media.get('url', ''),
                    'media_type': media.get('media_type', ''),
                    'shortcode': media.get('shortcode', ''),
                    'author_username': media.get('author_username', ''),
                    'caption': media.get('caption', '').replace('\n', ' ') if media.get('caption') else '',
                    'created_at': media.get('created_at', ''),
                    'like_count': media.get('like_count', '0'),
                    'comment_count': media.get('comment_count', '0'),
                    'view_count': media.get('view_count', '0'),
                    'hashtags': ', '.join(media.get('hashtags', [])),
                    'mentions': ', '.join(media.get('mentions', [])),
                    'links': ', '.join(media.get('links', [])),
                    'music': media.get('music', ''),
                    'location': media.get('location', '')
                })
        
        print(f"  ✅ Media CSV: {filepath}")
    
    def _export_instagram_comments_csv(self, result: SearchResult, filepath: Path):
        """Export Instagram comments to CSV."""
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            fieldnames = [
                'keyword',
                'media_url',
                'media_type',
                'media_author',
                'comment_author',
                'comment_text',
                'comment_likes',
                'comment_created_at',
                'comment_level'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for media in result.media_data:
                media_url = media.get('url', '')
                media_type = media.get('media_type', '')
                media_author = media.get('author_username', '')
                
                for comment in media.get('comments', []):
                    writer.writerow({
                        'keyword': result.keyword,
                        'media_url': media_url,
                        'media_type': media_type,
                        'media_author': media_author,
                        'comment_author': comment.get('author_username', ''),
                        'comment_text': comment.get('text', '').replace('\n', ' '),
                        'comment_likes': comment.get('like_count', '0'),
                        'comment_created_at': comment.get('created_at', ''),
                        'comment_level': comment.get('level', 1)
                    })
        
        print(f"  ✅ Comments CSV: {filepath}")
    
    def _export_instagram_flat_csv(self, result: SearchResult, filepath: Path):
        """Export flattened Instagram data to CSV."""
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            fieldnames = [
                'keyword',
                'media_url',
                'media_type',
                'author_username',
                'caption',
                'like_count',
                'comment_count',
                'view_count',
                'comment_number',
                'comment_author',
                'comment_text',
                'comment_likes'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for media in result.media_data:
                comments = media.get('comments', [])
                
                if not comments:
                    # Output media without comments
                    writer.writerow({
                        'keyword': result.keyword,
                        'media_url': media.get('url', ''),
                        'media_type': media.get('media_type', ''),
                        'author_username': media.get('author_username', ''),
                        'caption': media.get('caption', '').replace('\n', ' ') if media.get('caption') else '',
                        'like_count': media.get('like_count', '0'),
                        'comment_count': media.get('comment_count', '0'),
                        'view_count': media.get('view_count', '0'),
                        'comment_number': 0,
                        'comment_author': '',
                        'comment_text': '',
                        'comment_likes': ''
                    })
                else:
                    for idx, comment in enumerate(comments, 1):
                        writer.writerow({
                            'keyword': result.keyword,
                            'media_url': media.get('url', ''),
                            'media_type': media.get('media_type', ''),
                            'author_username': media.get('author_username', ''),
                            'caption': media.get('caption', '').replace('\n', ' ') if media.get('caption') else '',
                            'like_count': media.get('like_count', '0'),
                            'comment_count': media.get('comment_count', '0'),
                            'view_count': media.get('view_count', '0'),
                            'comment_number': idx,
                            'comment_author': comment.get('author_username', ''),
                            'comment_text': comment.get('text', '').replace('\n', ' '),
                            'comment_likes': comment.get('like_count', '0')
                        })
        
        print(f"  ✅ Flat CSV: {filepath}")
    
    def _export_twitter_csv(self, result: SearchResult, base_name: str) -> Dict[str, Path]:
        """Export Twitter results to CSV (existing implementation)."""
        # ... (keep your existing Twitter CSV export code)
        return {}