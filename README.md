# EIS Tender Monitor & Analytics Bot
An asynchronous ETL service and Telegram bot for automated scraping, normalization, and paginated monitoring of public procurement data (EIS).

## Architecture & Features
 *Data Collection (`main.py`):* Asynchronous multi-page scraping of dynamic web pages powered by **Playwright** with browser fingerprint emulation.

 *ETL & Normalization:* HTML parsing and data cleaning using **BeautifulSoup4** and Regular Expressions (`re`), including price formatting and whitespace normalization.

 *Storage (`database.py`):* Local **SQLite** database with deduplication via unique registry IDs (`PRIMARY KEY`).

 *User Interface (`bot.py`):* Asynchronous Telegram bot built on **aiogram 3.x** featuring inline pagination, automatic cleanup of status messages, and network error handling.

 *Security:* Isolation of sensitive credentials (API tokens) using environment variables (`python-dotenv`).

## Tech Stack
 Python 3.11+
 Playwright, BeautifulSoup4, Regex
 aiogram 3.x
 SQLite3
 python-dotenv

## Installation & Setup
1. **Clone the repository:**
   ```bash
   git clone https://github.com/PhuCo
   cd eis-tender-monitor.git
   ```
2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. **Install dependencies and the Chromium browser:**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```
4. **Configure environment variables:**
   Create a `.env` file based on `.env.example` and add your token from `@BotFather` in telegram:
   ```bash
   cp .env.example .env
   ```
5. **Initialize the database and run the bot:**
   ```bash
   python3 database.py
   python3 bot.py
   ```