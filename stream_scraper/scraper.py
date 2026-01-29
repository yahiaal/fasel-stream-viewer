from seleniumbase import SB
import re
import json
import time
import sys

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
        
        # Fix for Cloud: 'uc=True' fails with Permission Denied on Streamlit Cloud.
        # We must use standard mode (uc=False) on Linux.
        # On Windows, we keep uc=True (Visible) for local testing.
        use_uc = False if is_linux else True
        use_headless = True if is_linux else False
        
        with SB(uc=use_uc, headless=use_headless, xvfb=is_linux) as sb:
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
                # Maybe we need to click "Watch" or a server tab first?
                # Common in movies: '.server--item'
                if sb.is_element_visible(".server--item"):
                    try:
                        sb.click(".server--item")
                        sb.sleep(2)
                        # Re-check frames
                        frames = sb.find_elements("iframe")
                        for f in frames:
                            src = f.get_attribute("src")
                            if src and "video_player" in src:
                                player_url = src
                                break
                    except: pass
            
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
                    
                    result_data = {
                        "url": master,
                        "headers": headers,
                        "curl": curl_cmd
                    }
                
    except Exception as e:
        print(f"Scraper Error: {e}")
        # Return error so UI can show it
        return {"error": str(e)}
        
    return result_data

if __name__ == "__main__":
    # Test
    url = "https://web12818x.faselhdx.bid/asian_seasons/مسلسل-squid-game" 
    print(scrape_stream_app_mode(url))
