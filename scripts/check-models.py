#!/usr/bin/env python3
"""
check-models.py - OpenRouter Free Model Monitor

Checks configured free models for expiration notices and discovers new models.
Sends Feishu notification when changes detected.

Usage:
  python3 check-models.py [--verbose] [--dry-run]
"""

import json
import os
import re
import sys
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set

# Import fetch module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from fetch_page import fetch_page
except ImportError:
    # Fallback: define inline
    def fetch_page(url, verbose=False):
        import requests
        from bs4 import BeautifulSoup
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                return resp.text
        except:
            pass
        return None

# Paths
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
CONFIG_FILE = SKILL_DIR / "config" / "config.json"
STATUS_FILE = SKILL_DIR / "data" / "status.json"
OPENCLAW_CONFIG = Path.home() / ".openclaw" / "openclaw.json"

# OpenRouter URL patterns
OPENROUTER_BASE = "https://openrouter.ai"
MODEL_URL_TEMPLATE = f"{OPENROUTER_BASE}/{{model_id}}"
FREE_MODELS_LIST_URL = f"{OPENROUTER_BASE}/models?max_price=0"


def load_config() -> dict:
    """Load configuration file"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"⚠️ Config load failed: {e}, using defaults", file=sys.stderr)
    
    # Default config
    return {
        "notify_channel": "feishu",
        "notify_target": "user:ou_8072af07014ee36e1e66d6690be4d7",
        "status_file": str(STATUS_FILE),
        "openclaw_config": str(OPENCLAW_CONFIG)
    }


def load_status() -> dict:
    """Load last check status"""
    config = load_config()
    status_path = Path(config.get("status_file", str(STATUS_FILE)))
    
    if status_path.exists():
        try:
            with open(status_path) as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"⚠️ Status load failed: {e}, using empty status", file=sys.stderr)
    
    return {
        "last_check": None,
        "known_models": [],
        "expiring_soon": []
    }


def save_status(status: dict):
    """Save check status"""
    config = load_config()
    status_path = Path(config.get("status_file", str(STATUS_FILE)))
    
    # Ensure directory exists
    status_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(status_path, 'w') as f:
        json.dump(status, f, indent=2, ensure_ascii=False)


def get_configured_free_models() -> List[str]:
    """Extract configured free models from openclaw.json"""
    config = load_config()
    openclaw_config_path = Path(config.get("openclaw_config", str(OPENCLAW_CONFIG)))
    
    if not openclaw_config_path.exists():
        print(f"ERROR: OpenClaw config not found: {openclaw_config_path}", file=sys.stderr)
        return []
    
    with open(openclaw_config_path) as f:
        data = json.load(f)
    
    free_models = []
    
    # Check defaults.models
    models_section = data.get("defaults", {}).get("models", {})
    for model_id in models_section.keys():
        if model_id.endswith(":free"):
            free_models.append(model_id)
    
    # Check agents.list[].model (for each agent)
    agents = data.get("agents", {}).get("list", [])
    for agent in agents:
        model_config = agent.get("model", {})
        primary = model_config.get("primary")
        fallbacks = model_config.get("fallbacks", [])
        
        if primary and primary.endswith(":free"):
            free_models.append(primary)
        for fb in fallbacks:
            if fb.endswith(":free"):
                free_models.append(fb)
    
    # Deduplicate
    return list(set(free_models))


def check_expiration_notice(model_id: str, verbose: bool = False) -> Optional[Dict]:
    """
    Check if a model has "Going away" notice.
    Returns:
        - dict with expiration info if found
        - None if no notice or fetch failed (logged separately)
    """
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo
    
    url = MODEL_URL_TEMPLATE.format(model_id=model_id)
    
    if verbose:
        print(f"Checking: {model_id}")
    
    html = fetch_page(url, verbose)
    if not html:
        if verbose:
            print(f"  ⚠️ Fetch failed for {model_id}")
        return None  # Treat fetch failure as "no notice" to avoid false alerts
    
    # Search for "Going away" pattern
    # Patterns: "Going away April 22, 2026" or "Going away 2026 年 4 月 22 日"
    patterns = [
        r"Going away\s+(\w+)\s+(\d{1,2}),?\s+(\d{4})",  # English: April 22, 2026
        r"Going away\s+(\d{4})[年\-]\s*(\d{1,2})[月\-]\s*(\d{1,2})[日]?",  # Chinese
    ]
    
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            if len(match.groups()) == 3 and match.group(1).isdigit():
                # Chinese format: YYYY-MM-DD
                year, month, day = match.groups()[:3]
                date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            else:
                # English format: Month DD, YYYY
                month_name, day, year = match.groups()
                months = {
                    'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
                    'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
                    'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
                }
                month_num = months.get(month_name[:3].lower(), '01')
                date_str = f"{year}-{month_num}-{day.zfill(2)}"
            
            # Calculate days remaining (use Asia/Shanghai timezone)
            try:
                tz = ZoneInfo("Asia/Shanghai")
                expire_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=tz)
                days_left = (expire_date - datetime.now(tz)).days
            except:
                days_left = 0
            
            return {
                "model": model_id,
                "going_away_date": date_str,
                "days_left": days_left,
                "url": url
            }
    
    return None  # No expiration notice found


def ensure_chrome_debug_mode(verbose: bool = False) -> bool:
    """
    Ensure Chrome is running in debug mode (port 9222).
    Returns True if Chrome is available, False otherwise.
    """
    import time
    from urllib.request import urlopen
    from urllib.error import URLError
    
    # Check if Chrome debug port is already responding
    try:
        with urlopen("http://127.0.0.1:9222/json/version", timeout=2) as resp:
            if resp.status == 200:
                if verbose:
                    print(f"  ✓ Chrome debug mode already running (port 9222)")
                return True
    except URLError:
        pass
    except Exception:
        pass
    
    if verbose:
        print(f"  ℹ️  Chrome not in debug mode, starting...")
    
    # Try to start Chrome in debug mode with isolated profile
    try:
        # Use isolated profile to avoid conflicts with existing Chrome
        chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        profile_dir = "/tmp/openclaw-chrome-debug"
        
        # Start Chrome with debug port and isolated profile
        subprocess.Popen(
            [chrome_path, "--remote-debugging-port=9222", "--no-first-run", 
             "--no-default-browser-check", f"--user-data-dir={profile_dir}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        
        # Wait for Chrome to start by polling the debug port
        for i in range(15):
            time.sleep(1)
            try:
                with urlopen("http://127.0.0.1:9222/json/version", timeout=2) as resp:
                    if resp.status == 200:
                        if verbose:
                            print(f"  ✓ Chrome debug mode started (port 9222)")
                        return True
            except URLError:
                pass
            except Exception:
                pass
        
        if verbose:
            print(f"  ⚠ Chrome startup timed out (15s)")
        return False
    except Exception as e:
        if verbose:
            print(f"  ⚠ Failed to start Chrome: {e}")
        return False


def discover_new_models(verbose: bool = False) -> List[str]:
    """
    Discover new free models from OpenRouter.
    Auto-starts Chrome debug mode if needed, falls back to API.
    Returns list of new model IDs.
    """
    if verbose:
        print(f"Discovering new free models...")
    
    models = []
    
    # Try bb-browser adapter first (requires Chrome in debug mode)
    if ensure_chrome_debug_mode(verbose):
        try:
            result = subprocess.run(
                ["bb-browser", "site", "openrouter/free-models", "--json", "--openclaw"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                raw = json.loads(result.stdout)
                if isinstance(raw, dict) and raw.get("success") and "data" in raw:
                    data = raw["data"]
                else:
                    data = raw
                
                if isinstance(data, dict) and "models" in data:
                    models = [m.get("slug", "") for m in data["models"] if m.get("slug")]
                    if verbose:
                        print(f"  ✓ bb-browser: Found {len(models)} free models")
                    return models
        except subprocess.TimeoutExpired:
            if verbose:
                print(f"  ⚠ bb-browser timed out")
        except Exception as e:
            if verbose:
                print(f"  ⚠ bb-browser error: {e}")
    
    # Fallback: use OpenRouter internal API directly
    if verbose:
        print(f"  Trying API fallback...")
    
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://openrouter.ai/api/frontend/models",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            if isinstance(data, dict) and "data" in data:
                api_models = []
                for m in data["data"]:
                    endpoint = m.get("endpoint") or {}
                    if endpoint.get("is_free") and m.get("slug"):
                        api_models.append(m.get("slug", ""))
                if verbose:
                    print(f"  ✓ API: Found {len(api_models)} free models")
                return api_models
    except Exception as e:
        if verbose:
            print(f"  ⚠ API fallback failed: {e}")
    
    if verbose:
        print(f"  ⚠ All discovery methods failed")
    return []


def send_feishu_notification(message: str, dry_run: bool = False):
    """Send notification via Feishu"""
    config = load_config()
    target = config.get("notify_target", "user:ou_8072af07014ee36e1e66d6690be4d7")
    
    if dry_run:
        print(f"\n[DRY RUN] Would send to Feishu: {target}")
        print(message)
        return
    
    # Use OpenClaw message tool
    try:
        # Extract user ID from target (e.g., "user:ou_xxx" -> "ou_xxx")
        user_id = target.replace("user:", "") if target.startswith("user:") else target
        
        cmd = [
            "openclaw", "message", "send",
            "--channel", "feishu",
            "--target", target,
            "--message", message
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✓ Notification sent via Feishu")
        else:
            print(f"⚠ Feishu send failed: {result.stderr}", file=sys.stderr)
    except Exception as e:
        print(f"⚠ Failed to send notification: {e}", file=sys.stderr)


def format_notification(expiring: List[Dict], new_models: List[str], alert_level: str = "normal") -> str:
    """
    Format notification message.
    alert_level: "urgent" (≤1 天), "warning" (≤3 天), "normal" (new models or >3 天)
    """
    lines = []
    
    if expiring:
        if alert_level == "urgent":
            lines.append("🚨 OpenRouter 模型即将到期（紧急）")
        elif alert_level == "warning":
            lines.append("⚠️ OpenRouter 模型到期提醒（3 天内）")
        else:
            lines.append("📅 OpenRouter 模型到期预告")
        lines.append("")
        for item in expiring:
            model = item.get("model", "Unknown")
            date = item.get("going_away_date", "Unknown")
            days = item.get("days_left", 0)
            url = item.get("url", "")
            
            if days < 0:
                status = f"已过期 {abs(days)} 天"
            elif days == 0:
                status = "今天到期"
            else:
                status = f"还剩 {days} 天"
            
            lines.append(f"模型：{model}")
            lines.append(f"到期：{date}（{status}）")
            lines.append(f"链接：{url}")
            lines.append("")
    
    if new_models:
        if expiring:
            lines.append("---")
        lines.append("✨ OpenRouter 新模型发现")
        lines.append("")
        for model in new_models[:10]:  # Limit to 10
            lines.append(f"模型：{model}")
            lines.append(f"链接：{OPENROUTER_BASE}/{model}")
            lines.append("")
        
        if len(new_models) > 10:
            lines.append(f"... 还有 {len(new_models) - 10} 个新模型")
    
    lines.append(f"检查时间：{datetime.now().strftime('%Y-%m-%d %H:%M')} (Asia/Shanghai)")
    
    return "\n".join(lines)


def should_send_expiration_alert(current_expiring: List[Dict], previous_expiring: List[Dict]) -> tuple:
    """
    Determine if expiration alert should be sent.
    Returns (should_send, alert_level)
    alert_level: "urgent" (≤1 天), "warning" (≤3 天), "normal" (first notice)
    """
    if not current_expiring:
        return False, "normal"
    
    # Build lookup for previous state
    prev_lookup = {}
    for item in (previous_expiring or []):
        model_id = item.get("model")
        if model_id:
            prev_lookup[model_id] = item
    
    should_send = False
    max_alert_level = "normal"
    
    for item in current_expiring:
        model = item.get("model")
        days_left = item.get("days_left", 999)
        
        # Check if this is a new expiring model or date changed
        if model not in prev_lookup:
            should_send = True  # New expiring model
        elif prev_lookup[model].get("going_away_date") != item.get("going_away_date"):
            should_send = True  # Date changed
        
        # Determine alert level based on days left
        if days_left is not None:
            try:
                days = int(days_left)
                if days <= 1:
                    max_alert_level = "urgent"
                    should_send = True  # Always send urgent alerts
                elif days <= 3 and max_alert_level != "urgent":
                    max_alert_level = "warning"
                    should_send = True  # Send warning alerts
            except (ValueError, TypeError):
                pass
    
    return should_send, max_alert_level


def main():
    verbose = "--verbose" in sys.argv
    dry_run = "--dry-run" in sys.argv
    
    if verbose:
        print("=" * 60)
        print("OpenRouter Free Model Monitor")
        print("=" * 60)
    
    # Load status
    status = load_status()
    last_check = status.get("last_check")
    known_models = set(status.get("known_models", []))
    
    if verbose:
        print(f"Last check: {last_check or 'Never'}")
        print(f"Known models: {len(known_models)}")
    
    # Get configured free models
    configured_models = set(get_configured_free_models())
    
    if verbose:
        print(f"Configured free models: {len(configured_models)}")
        for m in configured_models:
            print(f"  - {m}")
    
    # Check expiration notices
    expiring = []
    for model_id in configured_models:
        result = check_expiration_notice(model_id, verbose)
        if result and "going_away_date" in result:
            expiring.append(result)
    
    if verbose:
        print(f"\nExpiring soon: {len(expiring)}")
    
    # Discover new models
    all_free_models = set(discover_new_models(verbose))
    
    # Find new models (not in known list)
    new_models = []
    if all_free_models:
        new_models = list(all_free_models - known_models - configured_models)
    
    if verbose:
        print(f"New models discovered: {len(new_models)}")
    
    # Determine if we should send expiration alert (with deduplication)
    prev_expiring = status.get("expiring_soon", [])
    send_expiring, alert_level = should_send_expiration_alert(expiring, prev_expiring)
    
    # New models: only send if there are actually new ones
    send_new_models = len(new_models) > 0
    
    # Update status (only update known_models if discovery succeeded)
    status["last_check"] = datetime.now().isoformat()
    if all_free_models:
        status["known_models"] = list(configured_models | all_free_models)
    status["expiring_soon"] = expiring
    save_status(status)
    
    if verbose:
        print(f"\nStatus saved to: {load_config().get('status_file', str(STATUS_FILE))}")
        print(f"Send expiration alert: {send_expiring} (level: {alert_level})")
        print(f"Send new models alert: {send_new_models}")
    
    # Send notification if needed
    if send_expiring or send_new_models:
        message = format_notification(expiring if send_expiring else [], new_models if send_new_models else [], alert_level)
        send_feishu_notification(message, dry_run)
    else:
        print("\n✓ No changes detected (silent)")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
