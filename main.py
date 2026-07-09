"""
Main entry point for Instagram scraper - simplified.
"""

import sys
import os
import argparse
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from config import CDP_PORT, DEFAULT_REPLIES, DEFAULT_MAX_REELS
    from utils import log_message, init_log_file
except ImportError:
    from config import CDP_PORT, DEFAULT_REPLIES
    DEFAULT_MAX_REELS = 10
    
    def log_message(message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    def init_log_file():
        from pathlib import Path
        from datetime import datetime
        log_file = Path(f"instagram_scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        with open(log_file, 'w') as f:
            f.write(f"Instagram Scraper Log - {datetime.now()}\n")
        return log_file

try:
    from browser_manager import BrowserManager
    from scraper import InstagramScraper
    from collector import InstagramDataCollector
except ImportError as e:
    log_message(f"❌ Import error: {e}", "ERROR")
    sys.exit(1)


def main():
    """Main entry point."""
    # Initialize log file first
    log_file = init_log_file()
    
    args = parse_arguments()
    
    log_message("=" * 60, "START")
    log_message("  Instagram Data Collector (Simplified)", "START")
    log_message("=" * 60, "START")
    log_message(f"📁 Log file: {log_file}", "INFO")
    
    browser_manager = BrowserManager(port=CDP_PORT)
    
    try:
        # Setup browser
        log_message("📱 STEP 1: Setting up browser...", "STEP")
        setup_browser(browser_manager)
        log_message("✅ Browser setup complete", "SUCCESS")
        
        # Connect and login
        log_message("🔗 STEP 2: Connecting to browser...", "STEP")
        browser_manager.connect()
        log_message("✅ Connected to Chrome", "SUCCESS")
        
        log_message("🔐 STEP 3: Checking login status...", "STEP")
        scraper = InstagramScraper(browser_manager)
        scraper.ensure_logged_in()
        log_message("✅ Login verified", "SUCCESS")
        
        # Execute based on mode
        if args.search:
            log_message(f"🔍 STEP 4: Starting search for '#{args.search}'...", "STEP")
            log_message(f"📊 Settings: max_media={args.max_media}", "INFO")
            
            collector = InstagramDataCollector(
                browser_manager, 
                export_formats=args.export_formats.split(',') if args.export_formats else ["json", "csv"]
            )
            
            # Remove max_comments parameter - it's not used anymore
            result = collector.collect_for_keyword(
                args.search,
                max_media=args.max_media,
                auto_export=True
            )
            
            log_message(f"✅ Completed search for '#{args.search}'", "SUCCESS")
            display_search_result(result)
            
        elif args.url:
            log_message(f"📄 STEP 4: Scraping media: {args.url}", "STEP")
            data = scraper.scrape_media(args.url)
            display_results(data)
            
            from utils import save_result
            filename = save_result(data, platform="instagram")
            log_message(f"💾 Data saved to: {filename}", "SUCCESS")
        
        else:
            log_message("❌ ERROR: No command specified", "ERROR")
            print("\n" + "="*60)
            print("  ❌ ERROR: No command specified")
            print("="*60)
            print("\nPlease specify one of the following:")
            print("\n  📌 Search by hashtag:")
            print("    python3 main.py --search 'GlobalWarming' --max-media 3")
            print("\n  📌 Scrape single media:")
            print("    python3 main.py https://www.instagram.com/reel/xxx/")
            print("\n  📌 For help:")
            print("    python3 main.py --help")
            print("="*60)
            sys.exit(1)
        
    except Exception as e:
        log_message(f"❌ Error: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        log_message("🔚 Closing browser...", "STEP")
        browser_manager.close()
        log_message("✅ Done", "SUCCESS")


def parse_arguments():
    """Parse command line arguments."""
    ap = argparse.ArgumentParser(
        description="Scrape Instagram - metadata only (no comments)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
  # Search by hashtag
  python3 main.py --search "GlobalWarming" --max-media 3
  
  # Scrape single reel
  python3 main.py https://www.instagram.com/reel/CxYz123ABCD/
        """
    )
    
    ap.add_argument("url", nargs="?", help="Instagram media URL to scrape")
    ap.add_argument("--search", "-s", type=str, 
                   help="Hashtag to search (without #, e.g., 'GlobalWarming')")
    ap.add_argument("--max-media", "-m", type=int, default=10,
                   help="Maximum media to collect (default: 10)")
    ap.add_argument("--export-formats", "-e", type=str, default="json,csv",
                   help="Export formats: json,csv (default: json,csv)")
    
    return ap.parse_args()


def setup_browser(browser_manager: BrowserManager):
    """Set up browser connection."""
    if not browser_manager.is_chrome_running():
        log_message(f"❌ No Chrome instance found on port {CDP_PORT}", "WARNING")
        response = input("\nWould you like to launch Chrome? (y/n): ")
        
        if response.lower() == 'y':
            log_message("🚀 Launching Chrome...", "STEP")
            print("\n⚠️  Important: Close all Chrome windows first!")
            input("Press Enter when all Chrome windows are closed...")
            browser_manager.launch_chrome()
            log_message("✅ Chrome launched successfully!", "SUCCESS")
            log_message("📱 Please log in to Instagram if needed...", "INFO")
            input("Press Enter to continue...")
        else:
            print("\nPlease launch Chrome manually with:")
            print(f"  google-chrome --remote-debugging-port={CDP_PORT} ")
            print("\nThen log in to instagram.com and run this script again.")
            sys.exit(1)
    else:
        log_message(f"✅ Chrome found running on port {CDP_PORT}", "SUCCESS")


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