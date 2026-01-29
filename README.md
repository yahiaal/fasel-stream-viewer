# 🎬 FaselHD Streamer & Link Fetcher

A powerful, dynamic web application built with **Streamlit** and **SeleniumBase** to search, browse, and extract direct high-quality stream links from FaselHD.

## 🚀 Features
- **Dynamic Search**: Instantly search for any movie or series on FaselHD.
- **Episode Browser**: Automatically detects series and fetches a categorized list of episodes.
- **Stealth Scraper**: Uses `SeleniumBase` with Undetected Chromedriver (UC) and CDP ad-blocking to bypass protections and ad-overlays.
- **Quality Extractor**: Parses the master `.m3u8` playlist to provide direct URLs for all available resolutions (1080p, 720p, 480p, 360p).
- **CORS Bypass**: Provides pre-formatted `curl` commands with correct `Referer` and `User-Agent` headers for external players.

---

## 📂 Project Structure

### 1. `fasel_streamlit.py`
The **Main UI** of the application. 
- **Purpose**: Provides the web interface using Streamlit.
- **Functionality**:
    - Handles user input and displays search results.
    - Manages the application state (selection, fetched links).
    - Calls the scraper engine to get the stream URL.
    - Parses the `.m3u8` playlist to extract resolution-specific variants.

### 2. `stream_scraper/`
This directory contains the core scraping logic.
- **`scraper.py`**: The **Scraper Engine**.
    - **Purpose**: Automates the browser to find the hidden video player.
    - **How it works**:
        1. Launches a headless Chrome instance with ad-blocking enabled.
        2. Navigates to the episode/movie page.
        3. Extracts the direct URL of the `player_iframe`.
        4. Accesses the player page directly and scans the source for the `.m3u8` link.
        5. Returns the stream URL and required headers to the main app.

---

## 🛠️ Setup & Installation

### Prerequisites
- Python 3.10+
- Google Chrome installed

### Installation
1. Install the required dependencies:
   ```bash
   pip install streamlit seleniumbase selectolax httpx
   ```
2. (Optional) Install the SeleniumBase drivers:
   ```bash
   sbase install chromedriver
   ```

---

## 🎮 How to Run

Launch the web app by running:
```bash
streamlit run fasel_streamlit.py
```

1. **Search**: Type the name of a movie or series in the sidebar.
2. **Select**: Click on the content you want to watch.
3. **Fetch**: Choose the episode (if applicable) and click **"Fetch Stream Links"**.
4. **Play**: Copy the direct link or the `curl` command to play in players like **VLC**, **IINA**, or **MPV**.

---

## ⚠️ Important Notes
- **Referer Header**: Most FaselHD streams require a specific `Referer` header to play. The app provides a `curl` command that includes this automatically.
- **Headless Mode**: The scraper runs in the background. You won't see a browser window open during extraction.
- **Ad-Blocking**: The app uses CDP (Chrome DevTools Protocol) to block trackers and ad-scripts during scraping to ensure maximum speed and stability.
