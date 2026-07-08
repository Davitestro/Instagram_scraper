"""
Main entry point for Instagram scraper.
"""

import argparse
import sys
from typing import List

from config import CDP_PORT, DEFAULT_MAX_REELS, DEFAULT_REPLIES
from browser_manager import BrowserManager
from scraper import InstagramScraper
from collector import InstagramDataCollector
from utils import is_instagram_media_url, save_result
from exceptions import ScraperError


def main():
    """Main entry point."""
    args = parse_arguments()
    
    print("\n" + "="*60)
    print("  Instagram Data Collector")
    print("="*60)
    
    browser_manager = BrowserManager(port=CDP_PORT)
    
    try:
        # Setup browser
        setup_browser(browser_manager)
        
        # Connect and login
        browser_manager.connect()
        scraper = InstagramScraper(browser_manager)
        scraper.ensure_logged_in()
        
        # Execute based on mode
        if args.search or args.keyword_file:
            # Search mode
            collector = InstagramDataCollector(
                browser_manager, 
                export_formats=args.export_formats.split(',') if args.export_formats else ["json", "csv"]
            )
            
            if args.keyword_file:
                keywords = read_keywords_from_file(args.keyword_file)
                results = collector.collect_multiple_keywords(
                    keywords, 
                    max_media=args.max_media,
                    max_comments=args.replies
                )
                print(f"\n✅ Completed search for {len(keywords)} keywords")
                print(f"📁 Output files in: {collector.exporter.output_dir}/")
                
            else:
                result = collector.collect_for_keyword(
                    args.search,
                    max_media=args.max_media,
                    max_comments=args.replies,
                    auto_export=True
                )
                print(f"\n✅ Completed search for '#{args.search}'")
                display_search_result(result)
                
        else:
            # Single media mode
            if not args.url:
                print("❌ Please provide a URL or use --search")
                sys.exit(1)
            
            data = scraper.scrape_media(args.url, args.replies)
            display_results(data)
            filename = save_result(data, platform="instagram")
            print(f"\n💾 Data saved to: {filename}")
        
    except ScraperError as e:
        print(f"\n❌ Error: {e}")
        print("Check the debug/ folder for screenshots if available.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        browser_manager.close()


def parse_arguments():
    """Parse command line arguments."""
    ap = argparse.ArgumentParser(
        description="Scrape Instagram using your existing Chrome browser",
        epilog="""
Examples:
  # Single media (reel/post)
  python main.py https://www.instagram.com/reel/CxYz123ABCD/
  
  # Search by hashtag
  python main.py --search "GlobalWarming" --max-media 5 --replies 10
  
  # Multiple hashtags from file
  python main.py --keyword-file keywords.txt --max-media 3 --replies 5
  
  # Search with only CSV export
  python main.py --search "ClimateAction" --export-formats csv
        """
    )
    
    # Single URL mode
    ap.add_argument("url", nargs="?", help="Instagram media URL to scrape")
    
    # Search mode
    ap.add_argument("--search", "-s", type=str, 
                   help="Hashtag to search (without #, e.g., 'GlobalWarming')")
    ap.add_argument("--keyword-file", "-f", type=str,
                   help="File containing keywords (one per line)")
    ap.add_argument("--max-media", "-m", type=int, default=DEFAULT_MAX_REELS,
                   help=f"Maximum media to collect per keyword (default: {DEFAULT_MAX_REELS})")
    
    # Export options
    ap.add_argument("--export-formats", "-e", type=str, default="json,csv",
                   help="Export formats: json,csv (default: json,csv)")
    
    # Common options
    ap.add_argument("--replies", "-r", type=int, default=DEFAULT_REPLIES,
                   help=f"Number of comments to collect per media (default: {DEFAULT_REPLIES})")
    
    return ap.parse_args()


def setup_browser(browser_manager: BrowserManager):
    """Set up browser connection."""
    if not browser_manager.is_chrome_running():
        print(f"\n❌ No Chrome instance found on port {CDP_PORT}")
        response = input("\nWould you like to launch Chrome? (y/n): ")
        
        if response.lower() == 'y':
            print("\n⚠️  Important: Close all Chrome windows first!")
            input("Press Enter when all Chrome windows are closed...")
            browser_manager.launch_chrome()
            print("\n✅ Chrome is ready!")
            print("📱 Please log in to Instagram if needed...")
            input("Press Enter to continue...")
        else:
            print("\nPlease launch Chrome manually with:")
            print(f"  google-chrome --remote-debugging-port={CDP_PORT} "
                  f"--user-data-dir=/tmp/chrome_debug")
            print("\nThen log in to instagram.com and run this script again.")
            sys.exit(1)
    else:
        print(f"\n✅ Chrome found running on port {CDP_PORT}")


def read_keywords_from_file(filename: str) -> List[str]:
    """Read keywords from a text file (one per line)."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            keywords = [line.strip() for line in f if line.strip()]
        print(f"📖 Read {len(keywords)} keywords from {filename}")
        return keywords
    except FileNotFoundError:
        print(f"❌ File not found: {filename}")
        sys.exit(1)


def display_results(data: dict):
    """Display results in a formatted way."""
    print("\n" + "="*60)
    print("  RESULTS")
    print("="*60)
    
    import json
    print(json.dumps(data, indent=2, ensure_ascii=False))


def display_search_result(result):
    """Display search result summary."""
    print("\n" + "="*60)
    print(f"  SEARCH RESULTS: '#{result.keyword}'")
    print("="*60)
    print(f"  Total media found: {result.total_media_found}")
    print(f"  Media collected: {result.media_collected}")
    print(f"  Scraped at: {result.scraped_at}")
    print("="*60)


if __name__ == "__main__":
    main()