import streamlit as st
import httpx
from selectolax.parser import HTMLParser
import sys
import os
import re
import urllib.parse

# Add scraper logic to path
current_dir = os.getcwd()
scraper_path = os.path.join(current_dir, 'stream_scraper')
if scraper_path not in sys.path:
    sys.path.append(scraper_path)

# from scraper import scrape_stream_app_mode

# Constants
BASE_URL = "https://web12818x.faselhdx.bid"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

# --- Backend Functions ---

@st.cache_data(ttl=3600)
def search_fasel(query):
    params = {"s": query}
    try:
        resp = httpx.get(BASE_URL, params=params, headers=HEADERS, timeout=10, follow_redirects=True)
        tree = HTMLParser(resp.text)
        results = []
        for node in tree.css("div.postDiv"):
            title_node = node.css_first("div.postInner h1, div.h1")
            link_node = node.css_first("a")
            img_node = node.css_first("div.imgdiv-class img")
            img_src = None
            if img_node:
                img_src = img_node.attributes.get("data-src") or img_node.attributes.get("src")
            if title_node and link_node:
                results.append({
                    "title": title_node.text(strip=True),
                    "link": link_node.attributes.get("href"),
                    "img": img_src
                })
        return results
    except: return []

@st.cache_data(ttl=3600)
def get_seasons(hub_url):
    try:
        resp = httpx.get(hub_url, headers=HEADERS, timeout=10, follow_redirects=True)
        tree = HTMLParser(resp.text)
        seasons = []
        # Support both 'seasons/' hubs and normal series pages with season selection
        for node in tree.css("div.seasonDiv"):
            title_node = node.css_first("div.title")
            title = title_node.text(strip=True) if title_node else "Unknown Season"
            
            onclick = node.attributes.get("onclick")
            link = None
            if onclick:
                # Extract URL from window.location.href = '...'
                match = re.search(r"window\.location\.href\s*=\s*['\"]([^'\"]+)['\"]", onclick)
                if match:
                    link = match.group(1)
                    if not link.startswith("http"):
                        link = urllib.parse.urljoin(hub_url, link)
            
            if not link:
                # Check parent or child <a>
                a_tag = node.css_first("a") or (node.parent if node.parent and node.parent.tag == "a" else None)
                if a_tag:
                    link = a_tag.attributes.get("href")
            
            if link:
                seasons.append({"title": title, "link": link})
        return seasons
    except: return []

@st.cache_data(ttl=3600)
def get_episodes(series_url):
    try:
        resp = httpx.get(series_url, headers=HEADERS, timeout=10, follow_redirects=True)
        tree = HTMLParser(resp.text)
        episodes = []
        # More robust episode list selectors
        for node in tree.css("div.epAll a, div.epNodes a, div.episodes-list a"):
            title = node.text(strip=True)
            link = node.attributes.get("href")
            if link and ("الحلقة" in title or "Episode" in title):
                episodes.append({
                    "title": title,
                    "link": link
                })
        
        # Deduplicate
        seen = set()
        unique_eps = []
        for ep in episodes:
            if ep['link'] not in seen:
                unique_eps.append(ep)
                seen.add(ep['link'])
        
        # Sort so 1 is first if naturally descending
        if unique_eps and "الحلقة 1" in unique_eps[-1]['title'] and len(unique_eps) > 1:
            unique_eps = unique_eps[::-1]
        return unique_eps
    except: return []

def parse_m3u8(master_url, referer):
    """
    Parses a master m3u8 playlist to extract quality variants.
    """
    try:
        headers = {
            "User-Agent": HEADERS["User-Agent"],
            "Referer": referer
        }
        resp = httpx.get(master_url, headers=headers, follow_redirects=True, timeout=10)
        content = resp.text
        
        lines = content.splitlines()
        variants = []
        
        current_res = "Unknown"
        for i, line in enumerate(lines):
            if line.startswith("#EXT-X-STREAM-INF"):
                # Extract Resolution
                match = re.search(r'RESOLUTION=(\d+x\d+)', line)
                if match:
                    current_res = match.group(1)
                else:
                    current_res = "Auto/Other"
            elif line.strip() and not line.startswith("#"):
                # This is the URL for the previous STREAM-INF
                variant_url = line.strip()
                if not variant_url.startswith("http"):
                    variant_url = urllib.parse.urljoin(master_url, variant_url)
                
                variants.append({
                    "quality": current_res,
                    "url": variant_url
                })
        return variants
    except Exception as e:
        st.error(f"Failed to parse M3U8: {e}")
        return []

def fetch_stream_from_api(target_url):
    """
    Calls the Backend API on Render to scrape the stream.
    """
    # Get API URL from secrets or default to local
    # Remove trailing slash if present
    api_url = st.secrets.get("API_URL", "http://localhost:10000").rstrip("/")
    scrape_endpoint = f"{api_url}/scrape"
    
    try:
        # 180s timeout: Render free tier can take 30-60s to cold start, plus scraping time
        resp = httpx.get(scrape_endpoint, params={"url": target_url}, timeout=180.0)
        if resp.status_code == 200:
            return resp.json()
        else:
            return {"error": f"API Error {resp.status_code}: {resp.text}"}
    except Exception as e:
        return {"error": f"Connection Failed: {e}"}

# --- UI Layout ---

st.set_page_config(page_title="FaselHD Link Fetcher", page_icon="🔗", layout="wide")

st.title("🔗 FaselHD Direct Link Fetcher")
st.markdown("Search, choose quality, and get direct links for your player.")

# State Management
if "selected_item" not in st.session_state:
    st.session_state.selected_item = None
if "current_stream" not in st.session_state:
    st.session_state.current_stream = None
if "variants" not in st.session_state:
    st.session_state.variants = None
if "selected_season" not in st.session_state:
    st.session_state.selected_season = None
if "selected_episode" not in st.session_state:
    st.session_state.selected_episode = None

# Sidebar Search
with st.sidebar:
    st.header("Search")
    query = st.text_input("Find Content", placeholder="e.g. Squid Game")
    if query:
        results = search_fasel(query)
        if results:
            for item in results:
                c1, c2 = st.columns([1, 4])
                with c1:
                    if item['img']: st.image(item['img'], width=50)
                with c2:
                    if st.button(item['title'], key=item['link'], use_container_width=True):
                        st.session_state.selected_item = item
                        st.session_state.selected_season = None
                        st.session_state.selected_episode = None
                        st.session_state.current_stream = None
                        st.session_state.variants = None
                        st.rerun()

# Main Content
if st.session_state.selected_item:
    item = st.session_state.selected_item
    col1, col2 = st.columns([1, 4])
    with col1:
        if item['img']: st.image(item['img'], use_container_width=True)
    with col2:
        st.header(item['title'])
        is_hub = "seasons" in item['link']
        
        target_url = item['link']
        
        # Step 1: Season Selection (if hub or multiple seasons detected)
        seasons = get_seasons(item['link'])
        if seasons:
            season_titles = [s['title'] for s in seasons]
            # Find default index
            default_ix = 0
            if st.session_state.selected_season:
                try: default_ix = season_titles.index(st.session_state.selected_season['title'])
                except: pass
                
            sel_season_title = st.selectbox("Select Season", season_titles, index=default_ix)
            sel_season = next((s for s in seasons if s['title'] == sel_season_title), None)
            
            if st.session_state.selected_season != sel_season:
                st.session_state.selected_season = sel_season
                st.session_state.selected_episode = None
                st.session_state.current_stream = None
                st.session_state.variants = None
                st.rerun()
                
            target_url = sel_season['link']

        # Step 2: Episode Selection
        is_series = "مسلسل" in item['title'] or "season" in item['link'] or seasons
        if is_series:
            ep_url = st.session_state.selected_season['link'] if st.session_state.selected_season else item['link']
            episodes = get_episodes(ep_url)
            if episodes:
                ep_titles = [e['title'] for e in episodes]
                # Find default index
                ep_default_ix = 0
                if st.session_state.selected_episode:
                    try: ep_default_ix = ep_titles.index(st.session_state.selected_episode['title'])
                    except: pass
                
                sel_ep_title = st.selectbox("Select Episode", ep_titles, index=ep_default_ix)
                sel_ep = next((e for e in episodes if e['title'] == sel_ep_title), None)
                
                if st.session_state.selected_episode != sel_ep:
                    st.session_state.selected_episode = sel_ep
                    st.session_state.current_stream = None
                    st.session_state.variants = None
                    # st.rerun() # Don't rerun immediately to allow button click, or handle state
                
                if sel_ep: target_url = sel_ep['link']
            else:
                st.warning("No episodes found for this selection.")
        
        # Stream Button

        if st.button("🚀 Fetch Stream Links", type="primary", use_container_width=True):
            with st.spinner("Extracting master playlist via Backend..."):
                res = fetch_stream_from_api(target_url)
                if res and "error" not in res:
                    st.session_state.current_stream = res
                    # Parse the m3u8 for qualities
                    variants = parse_m3u8(res['url'], res['headers']['Referer'])
                    st.session_state.variants = variants
                else:
                    err_msg = res['error'] if res and 'error' in res else "Unknown Error"
                    st.error(f"Extraction failed: {err_msg}")

    if st.session_state.variants:
        st.divider()
        st.subheader("📥 Available Qualities")
        
        for v in st.session_state.variants:
            with st.container(border=True):
                c1, c2 = st.columns([1, 5])
                with c1:
                    st.markdown(f"### {v['quality'].split('x')[-1]}p" if 'x' in v['quality'] else f"### {v['quality']}")
                with c2:
                    st.text_input("URL", value=v['url'], key=f"url_{v['url']}")
                    # Note: We can't use standard download buttons easily for m3u8 links without content,
                    # but we can provide a copyable VLC command.
                    curl_cmd = f"curl '{v['url']}' -H 'Referer: {st.session_state.current_stream['headers']['Referer']}' -H 'User-Agent: {HEADERS['User-Agent']}'"
                    st.code(curl_cmd, language="bash")
                    
                    # Redirect suggestion
                    st.markdown(f"[🔗 Open Variant Playlist (Requires HLS Browser Ext)]({v['url']})")

else:
    st.info("👈 Search for a movie or series in the sidebar to get started.")

st.markdown("---")
st.caption("FaselHD Streamer - Quality Extractor Mode")
