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
        
        # 1. Setup Driver Path
        custom_driver_path = None
        # if is_linux:
        #     custom_driver_path = setup_local_driver()
            
        #     # Start Xvfb if available (better than headless for detection)
        if is_linux and Display:
            display = Display(visible=0, size=(1280, 720))
            display.start()

        # 2. Initialize Chrome Options
        options = uc.ChromeOptions()
        if is_linux and not Display:
            # If no Xvfb, forced to use headless
            options.add_argument("--headless=new") 
        
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        # 3. Initialize Driver
        # We explicitly pass driver_executable_path if we found it
        kwargs = {"options": options}
        # if custom_driver_path:
        #     kwargs["driver_executable_path"] = custom_driver_path
            
        driver = uc.Chrome(**kwargs)
        
        # 4. Navigation & Logic
        driver.get(target_url)
        time.sleep(3)
        
        # Find player iframe
        player_url = None
        try:
            # Try finding by name first
            frames = driver.find_elements(By.NAME, "player_iframe")
            if frames:
                player_url = frames[0].get_attribute("src")
            else:
                # Fallback: find any iframe with 'video_player'
                frames = driver.find_elements(By.TAG_NAME, "iframe")
                for f in frames:
                    src = f.get_attribute("src")
                    if src and "video_player" in src:
                        player_url = src
                        break
        except: pass
        
        if not player_url:
            # Check for server buttons (common in Fasel)
            try:
                servers = driver.find_elements(By.CSS_SELECTOR, ".server--item")
                if servers:
                    servers[0].click()
                    time.sleep(2)
                    # Re-check iframes
                    frames = driver.find_elements(By.TAG_NAME, "iframe")
                    for f in frames:
                        src = f.get_attribute("src")
                        if src and "video_player" in src:
                            player_url = src
                            break
            except: pass
            
        if not player_url:
            return {"error": f"Player not found. Title: {driver.title}"}
            
        # 5. Extract M3U8 from Player
        driver.get(player_url)
        time.sleep(3)
        source = driver.page_source
        
        matches = re.findall(r'(https?://[^"\s\']+\.m3u8[^"\s\']*)', source)
        if matches:
            master = next((m for m in matches if "master" in m), matches[0])
            headers = {
                "Referer": player_url,
                "User-Agent": driver.execute_script("return navigator.userAgent;")
            }
            curl_cmd = f"curl '{master}' -H 'Referer: {player_url}' -H 'User-Agent: {headers['User-Agent']}'"
            
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
