"""
Main entry point for Instagram scraper - Profile mode.
"""

import sys
import os
import argparse
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from config import CDP_PORT, DEFAULT_MAX_REELS
    from utils import log_message, init_log_file
except ImportError:
    from config import CDP_PORT
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
    log_file = init_log_file()
    
    args = parse_arguments()
    
    log_message("=" * 60, "START")
    log_message("  Instagram Profile Scraper", "START")
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
        if args.profile:
            log_message(f"👤 STEP 4: Starting profile scrape for '@{args.profile}'...", "STEP")
            log_message(f"📊 Settings: max_posts={args.max_posts}", "INFO")
            
            collector = InstagramDataCollector(
                browser_manager, 
                export_formats=args.export_formats.split(',') if args.export_formats else ["json", "csv"]
            )
            
            result = collector.collect_from_profile(
                args.profile,
                max_posts=args.max_posts,
                auto_export=True
            )
            
            log_message(f"✅ Completed scraping '@{args.profile}'", "SUCCESS")
            display_result(result)
            
        elif args.profile_file:
            log_message(f"📋 STEP 4: Reading profiles from file...", "STEP")
            profiles = read_profiles_from_file(args.profile_file)
            log_message(f"📊 Found {len(profiles)} profiles", "INFO")
            
            collector = InstagramDataCollector(
                browser_manager, 
                export_formats=args.export_formats.split(',') if args.export_formats else ["json", "csv"]
            )
            
            results = collector.collect_multiple_profiles(
                profiles,
                max_posts=args.max_posts
            )
            
            log_message(f"✅ Completed scraping {len(profiles)} profiles", "SUCCESS")
        
        else:
            log_message("❌ ERROR: No command specified", "ERROR")
            print("\n" + "="*60)
            print("  ❌ ERROR: No command specified")
            print("="*60)
            print("\nPlease specify one of the following:")
            print("\n  📌 Scrape a single profile:")
            print("    python3 main.py --profile 'username' --max-posts 5")
            print("\n  📌 Scrape multiple profiles from file:")
            print("    python3 main.py --profile-file profiles.txt --max-posts 3")
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
        description="Scrape Instagram posts from user profiles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
  # Scrape a single profile
  python3 main.py --profile "pubity" --max-posts 5
  
  # Scrape multiple profiles from file
  python3 main.py --profile-file profiles.txt --max-posts 3
  
  # Profile file format (one username per line):
  pubity
  elonmusk
  natgeo
        """
    )
    
    ap.add_argument("--profile", "-p", type=str, 
                   help="Instagram username to scrape (without @)")
    ap.add_argument("--profile-file", "-f", type=str,
                   help="File containing usernames (one per line)")
    ap.add_argument("--max-posts", "-m", type=int, default=DEFAULT_MAX_REELS,
                   help=f"Maximum posts to collect per profile (default: {DEFAULT_MAX_REELS})")
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


def read_profiles_from_file(filename: str) -> list[str]:
    """Read usernames from a text file (one per line)."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            profiles = [line.strip() for line in f if line.strip()]
        log_message(f"📖 Read {len(profiles)} profiles from {filename}")
        return profiles
    except FileNotFoundError:
        log_message(f"❌ File not found: {filename}", "ERROR")
        sys.exit(1)


def display_result(result):
    """Display search result summary."""
    print("\n" + "="*60)
    print(f"  PROFILE RESULTS: @{result.keyword}")
    print("="*60)
    print(f"  Total posts found: {result.total_media_found}")
    print(f"  Posts collected: {result.media_collected}")
    print(f"  Scraped at: {result.scraped_at}")
    print("="*60)


if __name__ == "__main__":
    main()