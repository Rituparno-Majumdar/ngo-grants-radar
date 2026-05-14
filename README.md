# NGO Project Tracking Automation

This automated tracking system monitors top platforms (LinkedIn and Indeed) for new NGO projects, RFPs (Request for Proposals), tenders, grant opportunities, and CSR consultancies in India. It delivers real-time notifications directly to Telegram and runs twice daily via GitHub Actions.

## Architecture

1. **Scraper (`scraper.py`)**: Fetches public project listings from LinkedIn and Indeed. Filters opportunities based on development sector keywords (`rfp`, `tender`, `grant`, `consultancy`, `csr project`, `call for proposals`) and excludes irrelevant technical/corporate/construction tenders.
2. **Notifier (`notifier.py`)**: Formats project alerts with clean HTML typography, source emojis, organization names, locations, and direct application/RFP links.
3. **Orchestrator (`main.py`)**: Coordinates scraping and notifications, managing `seen_projects.json` to prevent duplicate alerts.
4. **Automation (`.github/workflows/ngo_project_tracker.yml`)**: Runs automatically at 11:30 AM and 11:30 PM IST (06:00 and 18:00 UTC) every day.

## Local Setup

### 1. Environment Setup

Create a virtual environment and install dependencies:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file in the project root:

```env
NGO_PROJECT_TELEGRAM_BOT_TOKEN="your_bot_token_here"
NGO_PROJECT_TELEGRAM_CHAT_ID="your_chat_id_here"
```

### 3. Execution

Run the tracker locally:

```bash
python main.py
```

## Deployment

1. Push this codebase to a GitHub repository.
2. In the repository settings, go to **Settings > Secrets and variables > Actions**.
3. Add repository secrets:
   - `NGO_PROJECT_TELEGRAM_BOT_TOKEN`
   - `NGO_PROJECT_TELEGRAM_CHAT_ID`
4. Go to **Settings > Actions > General > Workflow permissions** and ensure **Read and write permissions** is selected so the bot can update `seen_projects.json`.
