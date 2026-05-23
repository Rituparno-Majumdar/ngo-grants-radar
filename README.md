# NGO Grants & RFP Tracker

![GitHub Actions](https://github.com/Rituparno-Majumdar/ngo-grants-radar/actions/workflows/ngo_project_tracker.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-GitHub%20Actions-lightgrey)

I built this to track institutional funding opportunities without checking multiple platforms manually. It monitors grants, RFPs, tenders, and CSR consultancies across four platforms and sends Telegram alerts twice daily via GitHub Actions.

## What I Track

I track **open grant calls from institutional funders** — organizations that provide funding to NGOs for running projects. This includes:

- **CSR funders**: Corporate foundations and company CSR arms announcing grant programmes
- **Government grants**: Central and state government schemes open for NGO applications
- **FCRA / foreign funding**: International donors with India-specific open calls (USAID, GIZ, UN agencies, foundations)
- **RFPs and tenders**: Requests for proposals from development organisations seeking implementing NGO partners
- **Challenge funds**: Competitive grant rounds from philanthropy networks

## Sources

| Platform | Type | Focus |
|---|---|---|
| **NGOBOX** | Web scrape | India grant announcements from CSR, government, and FCRA funders |
| **FundsForNGOs** | Web scrape | Global and India-specific open grant calls for NGOs |
| **ReliefWeb** | REST API (UN OCHA) | Humanitarian and development funding opportunities in India |
| **DevNetJobsIndia** | Web scrape | RFPs, tenders, and assignments in the development sector |

## Architecture

```
├── main.py                   # Orchestrator — deduplication, logging, summary
├── scraper.py                # 4 scrapers with keyword filtering
├── notifier.py               # Telegram bot with HTML formatting + retry logic
├── get_chat_id.py            # Helper to find your Telegram chat ID
├── seen_projects.json        # Persisted project IDs (auto-committed)
├── requirements.txt
├── .env                      # Local credentials (NOT committed)
└── .github/
    └── workflows/
        └── ngo_project_tracker.yml
```

## Setup

### 1. Clone and install

```bash
git clone https://github.com/Rituparno-Majumdar/ngo-grants-rfp-tracker.git
cd ngo-grants-rfp-tracker
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Telegram credentials

Create a `.env` file:
```env
NGO_PROJECT_TELEGRAM_BOT_TOKEN="your_bot_token_here"
NGO_PROJECT_TELEGRAM_CHAT_ID="your_chat_id_here"
```

To find your chat ID after creating a bot with @BotFather:
```bash
python get_chat_id.py
```

### 3. Add GitHub Secrets

In your repo: **Settings → Secrets and variables → Actions**

| Secret | Value |
|---|---|
| `NGO_PROJECT_TELEGRAM_BOT_TOKEN` | Your bot token from @BotFather |
| `NGO_PROJECT_TELEGRAM_CHAT_ID` | Your personal chat ID |

Also enable **Read and write permissions** under **Settings → Actions → General → Workflow permissions**.

### 4. Run locally

```bash
python main.py
```

## Schedule

Runs automatically twice daily at **06:15 AM and 06:15 PM IST** (00:45 and 12:45 UTC).

## Sample Telegram Alert

```
📦 New Institutional Grant Alert (CSR / Govt / FCRA) — NGOBOX

📋 Grant Opportunity: Call for Proposals – Women's Livelihood Programme
🏢 Donor / Foundation: Tata Trusts
📍 Location: Jharkhand, India

Seeking proposals from registered NGOs working in rural livelihoods...

📂 View Grant Funding Guidelines & Application
```

## Customisation

Edit `scraper.py` → `CORE_TERMS` to add keywords relevant to your funding focus.
Edit `scraper.py` → `EXCLUDE_TERMS` to filter out irrelevant listings.
