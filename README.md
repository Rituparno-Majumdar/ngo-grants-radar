# 💰 NGO Grants Radar

![GitHub Actions](https://github.com/Rituparno-Majumdar/ngo-grants-radar/actions/workflows/ngo_project_tracker.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11-3776ab?logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-22c55e)
![Runs on](https://img.shields.io/badge/runs%20on-GitHub%20Actions-2088ff?logo=github-actions&logoColor=white)
![Notifications](https://img.shields.io/badge/alerts-Telegram-26a5e4?logo=telegram&logoColor=white)

> **Never miss a funding call again.** This pipeline monitors institutional funders — corporate CSR arms, government bodies, UN agencies, and philanthropic foundations — for open grant calls, RFPs, and funding announcements targeted at NGOs. Alerts land in Telegram twice a day, automatically.

---

## 🎯 What I Track

I track **open grant calls from institutional funders** — organizations that provide funds for NGOs to design and run projects.

| Funding Type | Examples |
|---|---|
| **CSR Grants** | Tata Trusts, Azim Premji Foundation, corporate CSR funds |
| **Government Grants** | Central & state schemes open for NGO applications, CAPART |
| **FCRA / Foreign Funding** | USAID, GIZ, UN agencies, international foundations |
| **RFPs & Tenders** | Development organizations seeking NGO implementing partners |
| **Challenge Funds** | Competitive grant rounds from philanthropy networks |

---

## 📡 Sources

| Platform | Method | Coverage |
|---|---|---|
| 📦 **NGOBOX** | Web scrape | India grant announcements — CSR, govt, FCRA |
| 💰 **FundsForNGOs** | Web scrape | Global & India-specific open grant calls |
| 🇺🇳 **ReliefWeb (UN OCHA)** | REST API | Humanitarian & development funding for India |
| 🇮🇳 **DevNetJobsIndia** | Web scrape | RFPs, tenders & assignments in development sector |

---

## 🏗️ How It Works

```
GitHub Actions (cron — twice daily)
        │
        ▼
   main.py (orchestrator)
        │
        ├── scraper.py  ──►  4 funding sources  ──►  keyword filter
        │
        ├── deduplication  (seen_projects.json — auto-committed)
        │
        └── notifier.py  ──►  Telegram Bot API
```

**Files:**
```
├── main.py                   # Orchestrator — deduplication, logging, summary
├── scraper.py                # 4 scrapers targeting institutional grant sources
├── notifier.py               # Telegram bot — formatted alerts + retry logic
├── get_chat_id.py            # Helper to find your Telegram chat ID
├── seen_projects.json        # Persisted grant IDs (auto-committed by CI)
├── requirements.txt
├── .env                      # Local secrets (never committed)
└── .github/workflows/
    └── ngo_project_tracker.yml
```

---

## ⚙️ Setup

### 1. Clone and install

```bash
git clone https://github.com/Rituparno-Majumdar/ngo-grants-radar.git
cd ngo-grants-radar
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 2. Create `.env`

```env
NGO_PROJECT_TELEGRAM_BOT_TOKEN="your_bot_token_here"
NGO_PROJECT_TELEGRAM_CHAT_ID="your_chat_id_here"
```

Create a bot via [@BotFather](https://t.me/BotFather) on Telegram, then find your chat ID:

```bash
python get_chat_id.py
```

### 3. Test locally

```bash
python main.py
```

### 4. Add GitHub Secrets

**Settings → Secrets and variables → Actions → New repository secret**

| Secret | Value |
|---|---|
| `NGO_PROJECT_TELEGRAM_BOT_TOKEN` | Your bot token |
| `NGO_PROJECT_TELEGRAM_CHAT_ID` | Your chat ID |

Also enable: **Settings → Actions → General → Workflow permissions → Read and write**

---

## ⏰ Schedule

Runs at **06:15 AM and 06:15 PM IST** every day (`cron: '45 0,12 * * *'`).

---

## 📬 Sample Alert

```
📦 New Institutional Grant Alert (CSR / Govt / FCRA) — NGOBOX

📋 Grant Opportunity:  Call for Proposals – Women's Livelihood Programme
🏢 Donor / Foundation: Tata Trusts
📍 Location:           Jharkhand, India

Seeking proposals from registered NGOs working in rural
livelihoods, women's self-help groups, and skill development...

📂 View Grant Funding Guidelines & Application
```

---

## 🔧 Customise

Edit `scraper.py` to adjust what qualifies as a grant call:

- **`CORE_TERMS`** — keywords that qualify a listing (e.g. add `"WASH"`, `"gender fund"`)
- **`EXCLUDE_TERMS`** — keywords that disqualify a listing (e.g. add `"hardware tender"`)

---

## 📄 License

[MIT](LICENSE) © Rituparno Majumdar
