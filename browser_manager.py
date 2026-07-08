"""
Browser management for Instagram scraper.
"""

import socket
import subprocess
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

from config import CDP_PORT, CHROME_PATHS, MAX_RETRIES
from exceptions import BrowserConnectionError


class BrowserManager:
    """Manages Chrome browser instance for scraping."""
    
    def __init__(self, port: int = CDP_PORT):
        self.port = port
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
    
    def is_chrome_running(self) -> bool:
        """Check if Chrome is running on the debug port."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', self.port))
        sock.close()
        return result == 0
    
    def launch_chrome(self) -> bool:
        """Launch Chrome with remote debugging enabled."""
        temp_dir = self._get_temp_dir()
        chrome_cmd = self._find_chrome_executable()
        
        if not chrome_cmd:
            raise BrowserConnectionError("Could not find Chrome/Chromium installation.")
        
        print(f"\n🚀 Launching Chrome: {chrome_cmd}")
        print(f"   Debug port: {self.port}")
        print(f"   Profile dir: {temp_dir}")
        
        try:
            cmd = [
                chrome_cmd,
                f"--remote-debugging-port={self.port}",
                f"--user-data-dir={temp_dir}",
                "--no-first-run",
                "--no-default-browser-check",
                "--start-maximized",
                "https://www.instagram.com"
            ]
            
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            
            print("\n✅ Chrome launched successfully!")
            time.sleep(3)
            return True
            
        except Exception as e:
            raise BrowserConnectionError(f"Failed to launch Chrome: {e}")
    
    def connect(self, retries: int = MAX_RETRIES):
        """Connect to Chrome instance with retries."""
        self.playwright = sync_playwright().start()
        
        for attempt in range(retries):
            try:
                self.browser = self.playwright.chromium.connect_over_cdp(
                    f"http://localhost:{self.port}"
                )
                print(f"✅ Connected to Chrome on port {self.port}")
                
                # Get or create context
                if self.browser.contexts:
                    self.context = self.browser.contexts[0]
                else:
                    self.context = self.browser.new_context()
                
                # Get or create page
                if self.context.pages:
                    self.page = self.context.pages[0]
                else:
                    self.page = self.context.new_page()
                
                return True
                
            except Exception as e:
                if attempt < retries - 1:
                    print(f"  Attempt {attempt + 1}/{retries} failed, retrying...")
                    time.sleep(2)
                else:
                    raise BrowserConnectionError(f"Failed to connect: {e}")
    
    def _find_chrome_executable(self) -> str:
        """Find Chrome executable based on platform."""
        system = sys.platform
        
        if system == "linux":
            for cmd in CHROME_PATHS["linux"]:
                try:
                    result = subprocess.run(["which", cmd], capture_output=True, text=True)
                    if result.returncode == 0:
                        return result.stdout.strip()
                except Exception:
                    continue
        elif system == "darwin":
            chrome_path = CHROME_PATHS["darwin"]
            if Path(chrome_path).exists():
                return chrome_path
        elif system == "win32":
            for chrome_path in CHROME_PATHS["win32"]:
                if Path(chrome_path).exists():
                    return chrome_path
        
        return None
    
    def _get_temp_dir(self) -> Path:
        """Get temporary directory for Chrome profile."""
        if sys.platform == "win32":
            return Path("/tmp/chrome_debug_profile")
        else:
            return Path("/tmp/chrome_debug_profile")
    
    def close(self):
        """Clean up browser resources."""
        if self.playwright:
            self.playwright.stop()
            self.browser = None
            self.context = None
            self.page = None