import os
import stat
import seleniumbase
from seleniumbase import SB
import re
import json
import time
import sys

import shutil

def setup_custom_driver():
    """
    Copies uc_driver to a writable local directory and makes it executable.
    Returns the path to the custom driver.
    """
    try:
        # Locate original driver
        sb_path = os.path.dirname(seleniumbase.__file__)
        original_driver_path = os.path.join(sb_path, "drivers", "uc_driver")
        
        # Define local writable path (in the project directory)
        local_driver_path = os.path.abspath("uc_driver_local")
        
        if os.path.exists(original_driver_path):
            # Copy to local path
            shutil.copy2(original_driver_path, local_driver_path)
            
            # Make executable
            st_mode = os.stat(local_driver_path).st_mode
            os.chmod(local_driver_path, st_mode | stat.S_IEXEC)
            print(f"Set up local driver at: {local_driver_path}")
            return local_driver_path
    except Exception as e:
        print(f"Failed to setup custom driver: {e}")
    return None

def scrape_stream_app_mode(target_url):
    """
    Callable function for the app.
    Takes a specific URL (Movie page or Episode page).
    Returns dict with stream info or None.
    """
    # Prepare custom driver path if on Linux
    custom_driver_path = None
    if sys.platform.startswith("linux"):
        custom_driver_path = setup_custom_driver()

    result_data = None
    
    # Check if we need to navigate to an episode or if this is already the player page/episode page.
    # If the user selected an episode link from the app, 'target_url' is the episode page.
    # If the user selected a movie, 'target_url' is the movie page (which contains the player).
    
    try:
        # Re-enabling uc=True because standard headless is blocked.
        # Adding xvfb=True ONLY on Linux (Cloud) to help with stability.
        is_linux = sys.platform.startswith("linux")
        
        # We re-enable uc=True on Linux because we are fixing permissions now.
        use_uc = True 
        use_headless = True if is_linux else False
        
        # Pass the custom driver path if available
        # SB() context manager might pass kwargs to Driver(), let's try injecting it.
        # Note: SB() -> BaseCase -> Driver(). 
        # Warning: 'driver_executable_path' might not be passed directly by SB() context.
        # If this fails, we might need a workaround. But let's try passing it.
        
        sb_kwargs = {
            "uc": use_uc,
            "headless": use_headless,
            "xvfb": is_linux
        }
        
        if custom_driver_path:
             # This argument is specific to undetected_chromedriver but SB *might* pass it.
             # If not, we rely on the fact that we put it in valid path or rely on PATH?
             # Actually, best way to force it in SB context is undocumented.
             # Let's try attempting to set 'driver_version' maybe? No.
             
             # Better fallback: If SB doesn't accept it, we might just rely on PATH if we add our cwd to PATH?
             os.environ["PATH"] += os.pathsep + os.path.dirname(custom_driver_path)
             pass 

        # We will try passing it as a kwarg, hoping SB passes extra kwargs to uc.Chrome
        # If SB filters kwargs, this might need a different approach.
        # But 'undetected' arg in SB calls Driver(uc=True).
        
        with SB(**sb_kwargs) as sb:
            # print(f"DEBUG: Navigating to {target_url}")
            sb.open(target_url)
            sb.wait_for_ready_state_complete()
            sb.sleep(2)
            
            # Logic to find player iframe
            # 1. Look for 'player_iframe'
            player_url = None
            try:
                iframe = sb.find_element("iframe[name='player_iframe']")
                player_url = iframe.get_attribute("src")
            except:
                # Fallback
                frames = sb.find_elements("iframe")
                for f in frames:
                    src = f.get_attribute("src")
                    if src and "video_player" in src:
                        player_url = src
                        break
            
            if not player_url:
                # Debugging info
                page_title = sb.get_title()
                page_url = sb.get_current_url()
                return {"error": f"Player iframe not found. Title: {page_title}, URL: {page_url}"}
            
            if player_url:
                # print(f"DEBUG: Found player: {player_url}")
                sb.open(player_url)
                sb.wait_for_ready_state_complete()
                sb.sleep(3)
                
                source = sb.get_page_source()
                matches = re.findall(r'(https?://[^"\s\']+\.m3u8[^"\s\']*)', source)
                
                if matches:
                    master = next((m for m in matches if "master" in m), matches[0])
                    
                    headers = {
                        "Referer": player_url,
                        "User-Agent": sb.get_user_agent()
                    }
                    curl_cmd = f"curl '{master}' -H 'Referer: {player_url}' -H 'User-Agent: {headers['User-Agent']}'"
                    
                    return {
                        "url": master,
                        "headers": headers,
                        "curl": curl_cmd
                    }
                else:
                    return {"error": f"No M3U8 found in player source. Player: {player_url}"}
                
    except Exception as e:
        print(f"Scraper Error: {e}")
        return {"error": str(e)}
        
    return {"error": "Unknown scraper failure"}

if __name__ == "__main__":
    # Test
    url = "https://web12818x.faselhdx.bid/asian_seasons/مسلسل-squid-game" 
    print(scrape_stream_app_mode(url))
