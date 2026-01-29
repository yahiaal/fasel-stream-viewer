import os
import stat
import seleniumbase
from seleniumbase import SB
import re
import json
import time
import sys

# Solution 1: Redirect SeleniumBase to writable /tmp directory to avoid Permission Denied in site-packages
os.environ['SELENIUMBASE_DIR'] = '/tmp/seleniumbase'

def scrape_stream_app_mode(target_url):
    """
    Callable function for the app.
    Takes a specific URL (Movie page or Episode page).
    Returns dict with stream info or None.
    """
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
        
        # We rely on the monkeypatch for the driver path now.
        
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
