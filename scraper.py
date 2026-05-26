import hashlib
import requests
from bs4 import BeautifulSoup
import logging
import time
import random
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

# Keywords that indicate a genuine grant/funding call (not a job listing)
CORE_TERMS = [
    "grant", "call for proposals", "cfp", "rfp", "request for proposals",
    "funding opportunity", "grant announcement", "grant application",
    "call for applications", "call for submissions", "call for projects",
    "grant fund", "challenge fund", "innovation grant", "community grant",
    "csr grant", "fcra", "institutional grant", "donor funding",
    "expressions of interest", "eoi", "call for tenders",
    "philanthropic grant", "social impact fund", "development fund",
    "nonprofit grant", "ngo grant", "grant-in-aid"
]

# Terms that indicate a job listing or irrelevant content
EXCLUDE_TERMS = [
    "job opening", "we are hiring", "recruitment", "vacancy",
    "apply for the position", "years of experience required",
    "salary", "resume", "curriculum vitae", "job description",
    "construction tender", "civil tender", "bpo", "call center",
    "react developer", "software engineer", "devops", "machine learning engineer",
    "erp", "sap", "oracle", "full stack developer", "backend engineer"
]

BROWSER_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
}


class BaseScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(BROWSER_HEADERS)

    def fetch_projects(self):
        raise NotImplementedError

    def matches_grant_criteria(self, title="", description=""):
        combined = f"{title} {description}".lower()
        has_core = any(term in combined for term in CORE_TERMS)
        is_excluded = any(ex in combined for ex in EXCLUDE_TERMS)
        return has_core and not is_excluded


# ─── Scraper 1: NGOBOX ───────────────────────────────────────────────────────
# Scrapes the grant announcement listing page on NGOBOX.org.
# This is a dedicated India-facing grant aggregator — high signal.
class NGOBOXScraper(BaseScraper):
    URL = "https://ngobox.org/grant_announcement_listing.php"

    def fetch_projects(self):
        grants = []
        try:
            response = self.session.get(self.URL, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            seen_urls = set()
            for a in soup.find_all("a", href=True):
                href = a['href']
                if "full_grant_announcement_" not in href or href in seen_urls:
                    continue
                seen_urls.add(href)

                title = a.text.strip()
                if not title:
                    continue

                grant_url = urljoin("https://ngobox.org/", href)
                # ID is the numeric suffix after the last underscore
                grant_id = href.rsplit('_', 1)[-1]

                # Try to extract donor name from title (pattern: "Title - Donor Name")
                parts = title.split(' - ')
                donor = parts[-1].strip() if len(parts) > 1 else "See grant listing"

                grants.append({
                    "id": f"ngobox_{grant_id}",
                    "title": title,
                    "company": donor,
                    "url": grant_url,
                    "source": "NGOBOX",
                    "description": "View full grant announcement for eligibility, funding guidelines, and application deadline.",
                    "location": "India / Global",
                })
        except Exception as e:
            logger.error(f"[NGOBOX] Error: {e}")

        logger.info(f"[NGOBOX] Found {len(grants)} grant opportunities.")
        return grants


# ─── Scraper 2: FundsForNGOs ──────────────────────────────────────────────────
# Scrapes fundsforngos.org — a dedicated grant aggregator with an India section.
# Each article covers one open grant call with donor name, theme, and deadline.
class FundsForNGOsScraper(BaseScraper):
    PAGES = [
        "https://www.fundsforngos.org/category/india-2/",
        "https://www.fundsforngos.org/latest-funds-for-ngos/",
    ]

    def fetch_projects(self):
        grants = []
        seen_ids = set()

        for page_url in self.PAGES:
            try:
                response = self.session.get(page_url, timeout=15)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')

                # WordPress archive: articles with h2.entry-title containing the link
                articles = soup.find_all('article')
                if not articles:
                    # Fallback: look for h2 entry titles directly
                    titles = soup.find_all('h2', class_='entry-title')
                    for h2 in titles:
                        a = h2.find('a', href=True)
                        if a:
                            articles.append(a)

                for article in articles:
                    # Handle both <article> tags and <a> fallback
                    if article.name == 'article':
                        a = article.find('h2', class_='entry-title')
                        if a:
                            a = a.find('a', href=True)
                        if not a:
                            a = article.find('a', class_='entry-title-link')
                        if not a:
                            continue
                    else:
                        a = article  # already an <a> tag from fallback

                    title = a.text.strip()
                    url = a.get('href', '')
                    if not title or not url:
                        continue

                    # Use the slug from the URL as a stable ID
                    slug = url.rstrip('/').rsplit('/', 1)[-1]
                    if slug in seen_ids:
                        continue
                    seen_ids.add(slug)

                    if not self.matches_grant_criteria(title):
                        continue

                    # Try to get excerpt/description from the article
                    desc = ""
                    if article.name == 'article':
                        excerpt = article.find(class_='entry-summary') or article.find('p')
                        if excerpt:
                            desc = excerpt.text.strip()[:300]

                    grants.append({
                        "id": f"fundsforngos_{slug}",
                        "title": title,
                        "company": "See grant listing",
                        "url": url,
                        "source": "FundsForNGOs",
                        "description": desc or "View full grant details including donor, eligibility, and deadline.",
                        "location": "India / Global",
                    })

                time.sleep(random.uniform(1, 2))

            except Exception as e:
                logger.error(f"[FundsForNGOs] Error fetching {page_url}: {e}")

        logger.info(f"[FundsForNGOs] Found {len(grants)} grant opportunities.")
        return grants


# ─── Scraper 3: ReliefWeb ─────────────────────────────────────────────────────
# Uses the ReliefWeb public API (UN OCHA). No auth required.
# Targets "Consultancy" type entries (RFPs, EOIs, ToRs) filtered to India.
# Note: /v1/jobs covers consultancies/EOIs as well as regular job listings;
# the type filter below restricts to Consultancy entries which are closer to
# grant calls and RFPs rather than permanent employment vacancies.
class ReliefWebScraper(BaseScraper):
    API_URL = "https://api.reliefweb.int/v1/jobs"

    def fetch_projects(self):
        grants = []
        try:
            params = [
                ("appname", "ngo-grants-rfp-tracker"),
                ("filter[operator]", "AND"),
                # India filter
                ("filter[conditions][0][field]", "country.iso3"),
                ("filter[conditions][0][value]", "IND"),
                # Consultancy type — excludes regular vacancies, targets RFPs/EOIs/ToRs
                ("filter[conditions][1][field]", "type.name"),
                ("filter[conditions][1][value]", "Consultancy"),
                ("limit", 50),
                ("sort[]", "date:desc"),
                # Request relevant fields explicitly
                ("fields[include][]", "title"),
                ("fields[include][]", "url"),
                ("fields[include][]", "source.name"),
                ("fields[include][]", "body"),
                ("fields[include][]", "date.created"),
            ]
            response = self.session.get(
                self.API_URL,
                params=params,
                headers={"Accept": "application/json"},
                timeout=20,
            )
            response.raise_for_status()
            data = response.json()

            for item in data.get("data", []):
                fields = item.get("fields", {})
                title = fields.get("title", "").strip()
                url = fields.get("url", "")
                sources = fields.get("source", [])
                donor = sources[0].get("name", "See listing") if sources else "See listing"
                body = fields.get("body", "")
                description = body[:300].rsplit(' ', 1)[0] + "..." if body and len(body) > 300 else body

                if not title or not url:
                    continue

                if not self.matches_grant_criteria(title, description):
                    continue

                item_id = str(item.get("id", ""))
                grants.append({
                    "id": f"reliefweb_{item_id}",
                    "title": title,
                    "company": donor,
                    "url": url,
                    "source": "ReliefWeb",
                    "description": description or "View full opportunity on ReliefWeb.",
                    "location": "India",
                })

        except Exception as e:
            logger.error(f"[ReliefWeb] Error: {e}")

        logger.info(f"[ReliefWeb] Found {len(grants)} matching opportunities.")
        return grants


# ─── Scraper 4: DevNetJobsIndia RFP ──────────────────────────────────────────
# Scrapes the RFP/assignments listing page on DevNetJobsIndia.
# Note: individual links use ASP.NET postbacks so we link to the main RFP
# page as the canonical URL and use title + a hash as the stable ID.
class DevNetRFPScraper(BaseScraper):
    URL = "https://www.devnetjobsindia.org/rfp_assignments.aspx"

    def fetch_projects(self):
        grants = []
        seen_titles = set()
        try:
            response = self.session.get(self.URL, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # Try direct links first (jobdescription.aspx pattern)
            for a in soup.find_all("a", href=True):
                href = a['href']
                title = a.text.strip()
                if not title or title in seen_titles:
                    continue

                if "jobdescription.aspx?job_id=" in href:
                    job_id = href.split('job_id=')[-1].split('&')[0]
                    job_url = urljoin("https://www.devnetjobsindia.org/", href)
                    seen_titles.add(title)

                    if self.matches_grant_criteria(title):
                        grants.append({
                            "id": f"devnet_{job_id}",
                            "title": title,
                            "company": "Development Sector",
                            "url": job_url,
                            "source": "DevNetJobsIndia",
                            "description": "View full RFP/assignment details on DevNetJobsIndia.",
                            "location": "India",
                        })

            # Fallback: extract titles from postback links, link to listing page
            if not grants:
                for a in soup.find_all("a", href=True):
                    href = a['href']
                    title = a.text.strip()
                    if not title or title in seen_titles:
                        continue
                    if "__doPostBack" not in href:
                        continue

                    seen_titles.add(title)
                    if not self.matches_grant_criteria(title):
                        continue

                    # Use a deterministic hash of the title as a stable ID
                    # (hashlib.md5 is stable across Python runs; built-in hash() is not)
                    title_hash = hashlib.md5(title.encode()).hexdigest()[:8]
                    grants.append({
                        "id": f"devnet_{title_hash}",
                        "title": title,
                        "company": "Development Sector",
                        "url": self.URL,
                        "source": "DevNetJobsIndia",
                        "description": "View full RFP details on DevNetJobsIndia RFP page.",
                        "location": "India",
                    })

        except Exception as e:
            logger.error(f"[DevNetJobsIndia] Error: {e}")

        logger.info(f"[DevNetJobsIndia] Found {len(grants)} matching RFPs.")
        return grants


def get_all_scrapers():
    return [
        NGOBOXScraper(),
        FundsForNGOsScraper(),
        ReliefWebScraper(),
        DevNetRFPScraper(),
    ]
