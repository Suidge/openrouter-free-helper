#!/usr/bin/env python3
"""
fetch-page.py - Web scraping module with 3-layer fallback for OpenRouter

Fallback strategy:
  Layer 1: requests + BeautifulSoup (fast, lightweight)
  Fallback → Layer 2: web_fetch tool (OpenClaw built-in)
  Fallback → Layer 3: bb-browser --openclaw (browser automation)
"""

import subprocess
import json
import sys
from typing import Optional, Tuple

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"


def fetch_with_requests(url: str, timeout: int = 15) -> Tuple[bool, str]:
    """Layer 1: Direct HTTP request with requests library"""
    try:
        import requests
        from bs4 import BeautifulSoup
        
        headers = {"User-Agent": USER_AGENT}
        resp = requests.get(url, headers=headers, timeout=timeout)
        
        if resp.status_code != 200:
            return False, f"HTTP {resp.status_code}"
        
        # Return full HTML for parsing
        return True, resp.text
    except ImportError as e:
        return False, f"requests/bs4 not installed: {e}"
    except Exception as e:
        return False, f"requests failed: {e}"


def fetch_with_web_fetch(url: str, timeout: int = 30) -> Tuple[bool, str]:
    """Layer 2: OpenClaw web_fetch tool"""
    try:
        # Call web_fetch via OpenClaw tool (simulated via subprocess to openclaw CLI)
        # Note: This is a placeholder - in actual skill execution, 
        # the parent script should call the web_fetch tool directly
        result = subprocess.run(
            ["openclaw", "tool", "web_fetch", "--url", url, "--extract-mode", "markdown"],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, f"web_fetch failed: {result.stderr}"
    except Exception as e:
        return False, f"web_fetch error: {e}"


def fetch_with_bb_browser(url: str, timeout: int = 60) -> Tuple[bool, str]:
    """Layer 3: bb-browser with --openclaw (browser automation)"""
    try:
        # Use bb-browser to capture page content
        # Note: bb-browser doesn't have a generic "fetch URL" command,
        # so we use a workaround with browser tool or custom adapter
        result = subprocess.run(
            ["openclaw", "browser", "open", url],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if result.returncode == 0:
            # Browser opened, now need to snapshot
            snapshot = subprocess.run(
                ["openclaw", "browser", "snapshot"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if snapshot.returncode == 0:
                return True, snapshot.stdout
            else:
                return False, f"snapshot failed: {snapshot.stderr}"
        else:
            return False, f"browser open failed: {result.stderr}"
    except Exception as e:
        return False, f"bb-browser error: {e}"


def fetch_page(url: str, verbose: bool = False) -> Optional[str]:
    """
    Fetch page content with 3-layer fallback.
    Returns HTML content on success, None on failure.
    """
    if verbose:
        print(f"Fetching: {url}")
    
    # Layer 1: requests (preferred - fast)
    success, content = fetch_with_requests(url)
    if success:
        if verbose:
            print("  ✓ Layer 1 (requests) succeeded")
        return content
    else:
        if verbose:
            print(f"  ✗ Layer 1 (requests) failed: {content}")
    
    # Layer 2: web_fetch
    success, content = fetch_with_web_fetch(url)
    if success:
        if verbose:
            print("  ✓ Layer 2 (web_fetch) succeeded")
        return content
    else:
        if verbose:
            print(f"  ✗ Layer 2 (web_fetch) failed: {content}")
    
    # Layer 3: bb-browser
    success, content = fetch_with_bb_browser(url)
    if success:
        if verbose:
            print("  ✓ Layer 3 (bb-browser) succeeded")
        return content
    else:
        if verbose:
            print(f"  ✗ Layer 3 (bb-browser) failed: {content}")
    
    # All layers failed
    print(f"ERROR: All fetch methods failed for {url}", file=sys.stderr)
    return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: fetch-page.py <url> [--verbose]")
        sys.exit(1)
    
    url = sys.argv[1]
    verbose = "--verbose" in sys.argv
    
    content = fetch_page(url, verbose)
    if content:
        # Output first 1000 chars for testing
        print(content[:1000])
    else:
        sys.exit(1)
