# Web Scraper (web_scraper.py)

## Brief Description
Fetches a URL and returns the clean plain-text content of the webpage.

## Prerequisites
1. **Playwright/Selenium**: Browser automation drivers.
2. **Dependencies**: Required pip packages.

## Step-by-Step Setup Guide
1. Install dependencies: `pip install playwright markdownify`.
2. Install browser binaries: `playwright install`.
3. (Optional) Set up proxies if scraping heavily restricted sites.

## How to Update
- The code for this agent lives in `agents/web_scraper.py`.
- To modify its behavior or add new parameters, edit the `PARAMETERS` dictionary and the primary function in the Python file.
