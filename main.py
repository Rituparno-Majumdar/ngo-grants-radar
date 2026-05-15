import os
import json
import logging
import time
from dotenv import load_dotenv

load_dotenv()

from scraper import get_all_scrapers
from notifier import TelegramNotifier

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("tracker.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

SEEN_PROJECTS_FILE = "seen_projects.json"
MAX_SEEN_PROJECTS = 2000


def load_seen_projects():
    if os.path.exists(SEEN_PROJECTS_FILE):
        try:
            with open(SEEN_PROJECTS_FILE, 'r') as f:
                return set(json.load(f))
        except (json.JSONDecodeError, TypeError):
            logger.warning("Could not parse seen_projects.json. Starting fresh.")
            return set()
    return set()


def save_seen_projects(seen_projects: set):
    projects_list = list(seen_projects)[-MAX_SEEN_PROJECTS:]
    with open(SEEN_PROJECTS_FILE, 'w') as f:
        json.dump(projects_list, f, indent=2)


def main():
    logger.info("=" * 60)
    logger.info("🚀 NGO Project Tracker Starting...")
    logger.info("=" * 60)

    seen_projects = load_seen_projects()
    notifier = TelegramNotifier()
    scrapers = get_all_scrapers()

    new_projects_found = 0
    total_checked = 0

    for scraper in scrapers:
        scraper_name = scraper.__class__.__name__
        logger.info(f"📡 Running scraper: {scraper_name}")

        try:
            projects = scraper.fetch_projects()
        except Exception as e:
            logger.error(f"Scraper {scraper_name} failed with unhandled exception: {e}")
            continue

        total_checked += len(projects)

        for project in projects:
            project_id = project.get('id')
            if not project_id:
                continue

            if project_id not in seen_projects:
                logger.info(f"  🆕 New project / RFP: {project.get('title')} [{project.get('source')}]")

                success = notifier.send_project_alert(project)
                
                if success:
                    seen_projects.add(project_id)
                    new_projects_found += 1
                    # Small delay to prevent Telegram rate limiting
                    time.sleep(1)
                else:
                    logger.error(f"  ❌ Failed to notify for: {project_id}")
            else:
                logger.debug(f"  ✅ Already seen: {project_id}")

    save_seen_projects(seen_projects)

    notifier.send_summary(new_projects_found, total_checked)

    logger.info("=" * 60)
    logger.info(f"✅ Done. Sent {new_projects_found} new project alerts from {total_checked} listings checked.")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
