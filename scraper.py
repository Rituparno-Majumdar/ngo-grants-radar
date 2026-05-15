import requests
from bs4 import BeautifulSoup
import re
import os
import logging
import time
import random
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

# --- Keyword Configuration Strictly for Full-Time Institutional NGO Grants (CSR / Govt / FCRA) ---
CORE_TERMS = [
    "grant", "csr grant", "fcra", "government grant", "govt grant",
    "grant-in-aid", "call for grant proposals", "nonprofit grant", "ngo grant",
    "funding opportunity", "grant application", "grant announcement", "grant funding",
    "institutional grant", "donor funding", "grant fund", "philanthropic grant",
    "challenge fund", "innovation grant", "community grant"
]

EXCLUDE_TERMS = [
    "job", "hiring", "recruitment", "vacancy", "career", "full-time job",
    "resume", "cv", "interview", "salary", "project manager", "project coordinator",
    "project officer", "program manager", "consultant editor", "facilitator",
    "data entry", "mobilization executive", "case worker", "teacher", "accountant",
    "react developer", "software engineer", "backend engineer", "devops",
    "machine learning engineer", "data engineer", "cybersecurity", "cloud architect",
    "game developer", "senior software engineer", "full stack", "oracle", "ebs",
    "erp", "sap", "it project manager", "software project manager", "construction tender",
    "civil tender", "bpo", "call center", "vendor", "bgv agency", "audit firm"
]


class BaseScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

    def fetch_projects(self):
        """Must return a list of dicts: id, title, company, url, source, description, location"""
        raise NotImplementedError

    def matches_grant_criteria(self, title="", description="", location=""):
        combined = f"{title} {description} {location}".lower()
        has_core = any(term in combined for term in CORE_TERMS)
        is_excluded = any(ex in combined for ex in EXCLUDE_TERMS)
        return has_core and not is_excluded


# ─── Scraper 1: NGOBOX Grant Scraper ─────────────────────────────────────────
class NGOBOXScraper(BaseScraper):
    def fetch_projects(self):
        grants = []
        url = "https://ngobox.org/grant_announcement_listing.php"
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            seen_urls = set()
            for a in soup.find_all("a", href=True):
                href = a['href']
                if "full_grant_announcement_" in href and href not in seen_urls:
                    seen_urls.add(href)
                    title = a.text.strip()
                    if not title:
                        continue

                    grant_url = f"https://ngobox.org/{href}" if not href.startswith('http') else href
                    grant_id = href.split('_')[-1]

                    parts = title.split('-')
                    donor = parts[-1].strip() if len(parts) > 1 else "Institutional Donor / Foundation"

                    grants.append({
                        "id": f"ngobox_grant_{grant_id}",
                        "title": title,
                        "company": donor,
                        "url": grant_url,
                        "source": "NGOBOX",
                        "description": "View official Grant Announcement on NGOBOX for funding guidelines, eligibility (CSR/Govt/FCRA), and submission timeline.",
                        "location": "India / Global"
                    })
        except Exception as e:
            logger.error(f"[NGOBOX Grants] Error fetching grant announcements: {e}")

        logger.info(f"[NGOBOX Grants] Found {len(grants)} institutional grant opportunities.")
        return grants


# ─── Scraper 2: DevNetJobsIndia Grant Scraper ────────────────────────────────
class DevNetJobsIndiaScraper(BaseScraper):
    def fetch_projects(self):
        grants = []
        url = "http://www.devnetjobsindia.org/rfp_assignments.aspx"
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            seen_ids = set()
            for a in soup.find_all("a", href=True):
                href = a['href']
                if "jobdescription.aspx?job_id=" in href:
                    title = a.text.strip()
                    if not title:
                        continue

                    job_id = href.split('job_id=')[-1]
                    if job_id in seen_ids:
                        continue
                    seen_ids.add(job_id)

                    grant_url = f"https://devnetjobsindia.org/{href}" if not href.startswith('http') else href

                    if self.matches_grant_criteria(title, "", ""):
                        grants.append({
                            "id": f"devnet_grant_{job_id}",
                            "title": title,
                            "company": "Development Sector Foundation",
                            "url": grant_url,
                            "source": "DevNetJobsIndia",
                            "description": "View DevNetJobs notice for full grant funding specifications.",
                            "location": "India"
                        })
        except Exception as e:
            logger.error(f"[DevNetJobsIndia Grants] Error fetching grants: {e}")

        logger.info(f"[DevNetJobsIndia Grants] Found {len(grants)} matching grant opportunities.")
        return grants


# ─── Scraper 3: LinkedIn Grant Scraper ───────────────────────────────────────
class LinkedInProjectScraper(BaseScraper):
    SEARCH_QUERIES = [
        ("csr grant ngo", "India"),
        ("government grant ngo", "India"),
        ("fcra grant ngo", "India"),
        ("grant announcement non profit", "India"),
        ("call for grant proposals", "India"),
    ]

    def fetch_projects(self):
        grants = []
        seen_ids = set()

        for keywords, location in self.SEARCH_QUERIES:
            encoded_kw = quote_plus(keywords)
            encoded_loc = quote_plus(location)
            url = f"https://www.linkedin.com/jobs/search?keywords={encoded_kw}&location={encoded_loc}&f_TPR=r604800"
            try:
                response = self.session.get(url, timeout=15)
                # Random delay between queries to avoid bot detection
                time.sleep(random.uniform(2, 4))
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')

                cards = soup.find_all('div', class_='base-card')
                for card in cards:
                    title_el = card.find('h3', class_='base-search-card__title')
                    company_el = card.find('h4', class_='base-search-card__subtitle')
                    link_el = card.find('a', class_='base-card__full-link')
                    loc_el = card.find('span', class_='job-search-card__location')

                    if not title_el or not link_el:
                        continue

                    title = title_el.text.strip()
                    company = company_el.text.strip() if company_el else "Institutional Donor"
                    grant_url = link_el['href'].split('?')[0]
                    location_text = loc_el.text.strip() if loc_el else "Unknown"
                    grant_id = grant_url.split('-')[-1] if '-' in grant_url else grant_url

                    if grant_id in seen_ids:
                        continue

                    if self.matches_grant_criteria(title, "", location_text):
                        seen_ids.add(grant_id)
                        grants.append({
                            "id": f"linkedin_grant_{grant_id}",
                            "title": title,
                            "company": company,
                            "url": grant_url,
                            "source": "LinkedIn",
                            "description": "View LinkedIn announcement for CSR/Govt/FCRA grant submission details.",
                            "location": location_text
                        })
            except Exception as e:
                logger.error(f"[LinkedIn Grants] Error for '{keywords}': {e}")

        logger.info(f"[LinkedIn Grants] Found {len(grants)} matching grant announcements.")
        return grants


# ─── Scraper 4: Indeed Grant Scraper ─────────────────────────────────────────
class IndeedProjectScraper(BaseScraper):
    SEARCH_QUERIES = [
        ("csr grant ngo", "India"),
        ("govt grant non profit", "India"),
        ("fcra grant funding", "India"),
        ("call for grant proposals", "India"),
    ]

    def fetch_projects(self):
        grants = []
        seen_ids = set()

        # Pre-flight: visit home page to get session cookies
        try:
            self.session.get("https://in.indeed.com/", timeout=10)
            time.sleep(random.uniform(1, 2))
        except Exception as e:
            logger.warning(f"[Indeed Grants] Pre-flight failed: {e}")

        for keywords, location in self.SEARCH_QUERIES:
            encoded_kw = quote_plus(keywords)
            encoded_loc = quote_plus(location)
            url = f"https://in.indeed.com/jobs?q={encoded_kw}&l={encoded_loc}&fromage=7"
            try:
                # Set Referer to make it look like a search from the home page
                self.session.headers.update({'Referer': 'https://in.indeed.com/'})

                # Indeed requires clean headers to bypass bot blocks
                response = self.session.get(url, timeout=15)
                # Indeed is very sensitive; longer random delay
                time.sleep(random.uniform(3, 6))
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')

                cards = soup.find_all('td', class_='resultContent') or soup.find_all('div', class_='job_seen_beacon')
                for card in cards:
                    title_el = card.find('h2', class_='jobTitle') or card.find('span', title=True)
                    company_el = card.find('span', class_='companyName') or card.find('span', attrs={'data-testid': 'company-name'})
                    loc_el = card.find('div', class_='companyLocation') or card.find('div', attrs={'data-testid': 'text-location'})
                    link_el = card.find('a', href=True)

                    if not title_el or not link_el:
                        continue

                    title = title_el.text.strip()
                    company = company_el.text.strip() if company_el else "Institutional Donor"
                    location_text = loc_el.text.strip() if loc_el else "India"
                    href = link_el['href']
                    grant_url = f"https://in.indeed.com{href}" if href.startswith('/') else href
                    
                    jk_match = re.search(r'jk=([a-f0-9]+)', grant_url)
                    grant_id = jk_match.group(1) if jk_match else grant_url.split('/')[-1]

                    if grant_id in seen_ids:
                        continue

                    if self.matches_grant_criteria(title, "", location_text):
                        seen_ids.add(grant_id)
                        grants.append({
                            "id": f"indeed_grant_{grant_id}",
                            "title": title,
                            "company": company,
                            "url": grant_url,
                            "source": "Indeed",
                            "description": "View Indeed announcement for full institutional grant funding criteria.",
                            "location": location_text
                        })
            except Exception as e:
                logger.error(f"[Indeed Grants] Error for '{keywords}': {e}")

        logger.info(f"[Indeed Grants] Found {len(grants)} matching grant announcements.")
        return grants


def get_all_scrapers():
    return [
        NGOBOXScraper(),
        DevNetJobsIndiaScraper(),
        LinkedInProjectScraper(),
        IndeedProjectScraper(),
    ]
