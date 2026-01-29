import os
import stat
import shutil
import time
import sys
import re
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Optional: for running "visible" mode in headless environment
try:
    from pyvirtualdisplay import Display
except ImportError:
    Display = None

def setup_local_driver():
    """
    Copies the system uc_driver to /tmp/uc_driver and makes it executable.
    Returns the path to the new writable driver.
    """
    try:
        import seleniumbase
        sb_path = os.path.dirname(seleniumbase.__file__)
        system_driver_path = os.path.join(sb_path, "drivers", "uc_driver")
        
        local_target = "/tmp/uc_driver"
        
        if os.path.exists(system_driver_path):
            if os.path.exists(local_target):
                try: os.remove(local_target)
                except: pass
            
            shutil.copy2(system_driver_path, local_target)
            st_mode = os.stat(local_target).st_mode
            os.chmod(local_target, st_mode | stat.S_IEXEC)
            return local_target
    except Exception as e:
        print(f"Driver setup error: {e}")
    return None

def scrape_stream_app_mode(target_url):
    """
    Scraper using raw undetected-chromedriver to bypass SeleniumBase permission issues.
    """
    driver = None
    display = None
    
    try:
        is_linux = sys.platform.startswith("linux")
        print(f"[SCRAPER] Platform: {sys.platform}, is_linux: {is_linux}")
        
        # 1. Setup Driver Path
        custom_driver_path = None
        # if is_linux:
        #     custom_driver_path = setup_local_driver()
            
        #     # Start Xvfb if available (better than headless for detection)
        if is_linux and Display:
            print("[SCRAPER] Starting Xvfb display...")
            display = Display(visible=0, size=(1280, 720))
            display.start()
            print("[SCRAPER] Xvfb started.")

        # 2. Initialize Chrome Options
        print("[SCRAPER] Configuring Chrome options...")
        options = uc.ChromeOptions()
        if is_linux and not Display:
            # If no Xvfb, forced to use headless
            options.add_argument("--headless=new") 
        
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-software-rasterizer")
        print("[SCRAPER] Chrome options configured.")
        
        # 3. Initialize Driver
        print("[SCRAPER] Initializing ChromeDriver (version_main=144)... This may take time.")
        # Force ChromeDriver version to match installed Chrome (144)
        kwargs = {
            "options": options,
            "version_main": 144  # Match the installed Chrome version on Render
        }
            
        driver = uc.Chrome(**kwargs)
        print("[SCRAPER] ChromeDriver initialized successfully!")
        
        # Set timeouts to prevent infinite hangs
        driver.set_page_load_timeout(30)  # 30 seconds max for page load
        driver.set_script_timeout(30)
        print("[SCRAPER] Timeouts set (30s)")
        
        # 4. Navigation & Logic
        print(f"[SCRAPER] Navigating to: {target_url}")
        try:
            driver.get(target_url)
        except Exception as nav_error:
            print(f"[SCRAPER] Navigation timeout/error: {nav_error}")
            # Even if timeout, we might have partial page - continue
            
        print("[SCRAPER] Page loaded (or timed out), waiting 3 seconds...")
        time.sleep(3)
        print(f"[SCRAPER] Current page title: {driver.title}")
        
        # Find player iframe
        print("[SCRAPER] Looking for player iframe...")
        player_url = None
        try:
            # Try finding by name first
            print("[SCRAPER] Trying By.NAME='player_iframe'...")
            frames = driver.find_elements(By.NAME, "player_iframe")
            print(f"[SCRAPER] Found {len(frames)} frames by name")
            if frames:
                player_url = frames[0].get_attribute("src")
                print(f"[SCRAPER] Got player_url from name: {player_url}")
            else:
                # Fallback: find any iframe with 'video_player'
                print("[SCRAPER] Trying all iframes...")
                frames = driver.find_elements(By.TAG_NAME, "iframe")
                print(f"[SCRAPER] Found {len(frames)} total iframes")
                for i, f in enumerate(frames):
                    src = f.get_attribute("src")
                    print(f"[SCRAPER] iframe[{i}] src: {src}")
                    if src and "video_player" in src:
                        player_url = src
                        print(f"[SCRAPER] Found video_player iframe!")
                        break
        except Exception as e:
            print(f"[SCRAPER] Error finding iframes: {e}")
        
        if not player_url:
            # Check for server buttons (common in Fasel)
            print("[SCRAPER] No player found, checking for server buttons...")
            try:
                servers = driver.find_elements(By.CSS_SELECTOR, ".server--item")
                print(f"[SCRAPER] Found {len(servers)} server buttons")
                if servers:
                    print("[SCRAPER] Clicking first server button...")
                    servers[0].click()
                    time.sleep(2)
                    # Re-check iframes
                    frames = driver.find_elements(By.TAG_NAME, "iframe")
                    print(f"[SCRAPER] After click, found {len(frames)} iframes")
                    for f in frames:
                        src = f.get_attribute("src")
                        if src and "video_player" in src:
                            player_url = src
                            print(f"[SCRAPER] Found player after click: {player_url}")
                            break
            except Exception as e:
                print(f"[SCRAPER] Error with server buttons: {e}")
            
        if not player_url:
            print("[SCRAPER] FAILED: No player found anywhere")
            return {"error": f"Player not found. Title: {driver.title}"}
        
        print(f"[SCRAPER] SUCCESS: Player URL = {player_url}")
            
        # 5. Extract M3U8 from Player
        print(f"[SCRAPER] Navigating to player: {player_url}")
        try:
            driver.get(player_url)
        except Exception as nav_err:
            print(f"[SCRAPER] Player navigation error: {nav_err}")
            
        print("[SCRAPER] Player loaded, waiting 3 seconds...")
        time.sleep(3)
        source = driver.page_source
        print(f"[SCRAPER] Got page source, length: {len(source)}")
        
        print("[SCRAPER] Searching for m3u8 URLs...")
        matches = re.findall(r'(https?://[^"\s\']+\.m3u8[^"\s\']*)', source)
        print(f"[SCRAPER] Found {len(matches)} m3u8 URLs")
        if matches:
            master = next((m for m in matches if "master" in m), matches[0])
            print(f"[SCRAPER] Selected m3u8: {master}")
            headers = {
                "Referer": player_url,
                "User-Agent": driver.execute_script("return navigator.userAgent;")
            }
            curl_cmd = f"curl '{master}' -H 'Referer: {player_url}' -H 'User-Agent: {headers['User-Agent']}'"
            
            print("[SCRAPER] SUCCESS! Returning result.")
            return {
                "url": master,
                "headers": headers,
                "curl": curl_cmd
            }
        else:
            return {"error": f"No M3U8 found. Player: {player_url}"}

    except Exception as e:
        return {"error": str(e)}
        
    finally:
        # Cleanup
        if driver:
            try: driver.quit()
            except: pass
        if display:
            try: display.stop()
            except: pass

if __name__ == "__main__":
    url = "https://web12818x.faselhdx.bid/asian_seasons/مسلسل-squid-game" 
    print(scrape_stream_app_mode(url))
