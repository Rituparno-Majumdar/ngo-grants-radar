import hashlib
import requests
from bs4 import BeautifulSoup
import logging
import time
import random
import os
import json
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


# ─── Helper Functions for LLM Extraction ──────────────────────────────────────

def extract_clean_text(html_content, base_url=None):
    """Cleans up raw HTML into formatted text, preserving links as markdown [text](url)."""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        # Remove elements that contain navigation, scripts, styling, or boilerplate
        for element in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            element.extract()
        
        # Convert links to [text](url) format to allow Gemini to extract listing URLs
        for a in soup.find_all('a', href=True):
            href = a['href']
            if base_url:
                href = urljoin(base_url, href)
            text = a.get_text().strip()
            if text:
                a.replace_with(f" [{text}]({href}) ")
            else:
                a.replace_with(f" ({href}) ")
                
        text = soup.get_text(separator=' ')
        # Collapse whitespace and empty lines
        lines = [line.strip() for line in text.splitlines()]
        clean_lines = [line for line in lines if line]
        return '\n'.join(clean_lines)
    except Exception as e:
        logger.warning(f"Error cleaning HTML: {e}")
        return html_content[:50000]


def gemini_extract_items(text, schema_type, source_name, base_url=None):
    """Calls the Gemini API using requests to perform structured item extraction."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not found in environment. Fallback failed.")
        return []

    model = "gemini-2.5-flash"
    
    if schema_type == 'grant':
        prompt = (
            f"You are a web scraping assistant extracting institutional grant opportunities (CSR, Govt, FCRA, RFPs, funding calls) from the text of a webpage from '{source_name}'.\n"
            f"Analyze the text below and extract all open grant opportunities/funding calls. Ignore job vacancies or standard construction/civil tenders.\n\n"
            f"Extract the following fields for each grant opportunity and return them as a JSON list of objects:\n"
            f"- 'title': The title of the grant or RFP opportunity.\n"
            f"- 'company': The donor organization or foundation name (if not found, use 'See grant listing' or a reasonable guess from context).\n"
            f"- 'url': The URL link to the grant detail page (use links found in the text associated with the grant; resolve against '{base_url}' if relative).\n"
            f"- 'description': A brief summary of eligibility, guidelines, or scope (approx 100-200 characters).\n"
            f"- 'location': The target location or region (e.g. 'India', 'Global').\n\n"
            f"Only return a valid JSON list. Do not include markdown code block formatting like ```json ... ```. Just return the raw JSON string starting with [ and ending with ]."
        )
    else:
        prompt = (
            f"You are a web scraping assistant extracting NGO / development sector / social impact job openings from the text of a webpage from '{source_name}'.\n"
            f"Analyze the text below and extract all open job vacancies. Filter for relevant roles such as project coordinators, program officers, CSR managers, social work, monitoring & evaluation.\n\n"
            f"Extract the following fields for each job opening and return them as a JSON list of objects:\n"
            f"- 'title': The job title.\n"
            f"- 'company': The organization or company hiring (if not found, use 'Unknown' or a reasonable guess from context).\n"
            f"- 'location': The job location.\n"
            f"- 'url': The URL link to apply or view the job detail page (use links found in the text associated with the job; resolve against '{base_url}' if relative).\n"
            f"- 'description': A brief summary of the role (approx 100-200 characters).\n"
            f"- 'date_posted': The date posted if visible (otherwise empty string).\n\n"
            f"Only return a valid JSON list. Do not include markdown code block formatting like ```json ... ```. Just return the raw JSON string starting with [ and ending with ]."
        )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"{prompt}\n\nWebpage Text:\n\"\"\"\n{text}\n\"\"\""}
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        res_data = response.json()
        content = res_data['candidates'][0]['content']['parts'][0]['text'].strip()
        
        # Strip markdown format blocks if present
        if content.startswith("```"):
            lines = content.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines).strip()
            
        items = json.loads(content)
        if not isinstance(items, list):
            logger.error("Gemini returned JSON that is not a list.")
            return []
        return items
    except Exception as e:
        logger.error(f"Failed calling Gemini API or parsing response: {e}")
        return []


def generate_stable_id(prefix, item):
    """Generates a stable unique ID for an extracted item based on URL or Title."""
    url = item.get("url", "")
    title = item.get("title", "")
    if url and url != "#":
        unique_str = url.split("?")[0].rstrip("/")
    else:
        unique_str = title
    val_hash = hashlib.md5(unique_str.encode()).hexdigest()[:12]
    return f"{prefix}_{val_hash}"


# ─── Base Scraper Class ───────────────────────────────────────────────────────

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

    def llm_fallback(self, response, schema_type, source_name, prefix, base_url=None):
        """Standard fallback pipeline when HTML parsing yields 0 results or fails."""
        logger.info(f"[{source_name}] HTML parsing yielded 0 results or failed. Attempting LLM extraction fallback...")
        try:
            clean_text = extract_clean_text(response.text, base_url=base_url or response.url)
            items = gemini_extract_items(clean_text, schema_type, source_name, base_url=base_url or response.url)
            
            processed_items = []
            for item in items:
                item_id = item.get("id")
                if not item_id:
                    item_id = generate_stable_id(prefix, item)
                
                item["source"] = source_name
                title = item.get("title", "")
                desc = item.get("description", "")
                loc = item.get("location", "")
                
                if self.matches_grant_criteria(title, desc):
                    processed_items.append({
                        "id": item_id,
                        "title": title,
                        "company": item.get("company", "See grant listing"),
                        "url": item.get("url", ""),
                        "source": source_name,
                        "description": desc or "View listing for guidelines and details.",
                        "location": loc or "India / Global",
                    })
            
            logger.info(f"[{source_name}] LLM fallback successfully extracted {len(processed_items)} items.")
            return processed_items
        except Exception as fallback_err:
            logger.error(f"[{source_name}] LLM fallback failed: {fallback_err}")
            return []


# ─── Scraper 1: NGOBOX ───────────────────────────────────────────────────────

class NGOBOXScraper(BaseScraper):
    URL = "https://ngobox.org/grant_announcement_listing.php"

    def fetch_projects(self):
        grants = []
        response = None
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
                grant_id = href.rsplit('_', 1)[-1]

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

        # Fallback if scraping yielded no results but page loaded successfully
        if not grants and response is not None and response.status_code == 200:
            grants = self.llm_fallback(response, 'grant', 'NGOBOX', 'ngobox', base_url="https://ngobox.org/")

        logger.info(f"[NGOBOX] Found {len(grants)} grant opportunities.")
        return grants


# ─── Scraper 2: FundsForNGOs ──────────────────────────────────────────────────

class FundsForNGOsScraper(BaseScraper):
    PAGES = [
        "https://www.fundsforngos.org/category/india-2/",
        "https://www.fundsforngos.org/latest-funds-for-ngos/",
    ]

    def fetch_projects(self):
        grants = []
        seen_ids = set()

        for page_url in self.PAGES:
            page_grants = []
            response = None
            try:
                response = self.session.get(page_url, timeout=15)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')

                articles = soup.find_all('article')
                if not articles:
                    titles = soup.find_all('h2', class_='entry-title')
                    for h2 in titles:
                        a = h2.find('a', href=True)
                        if a:
                            articles.append(a)

                for article in articles:
                    if article.name == 'article':
                        a = article.find('h2', class_='entry-title')
                        if a:
                            a = a.find('a', href=True)
                        if not a:
                            a = article.find('a', class_='entry-title-link')
                        if not a:
                            continue
                    else:
                        a = article

                    title = a.text.strip()
                    url = a.get('href', '')
                    if not title or not url:
                        continue

                    slug = url.rstrip('/').rsplit('/', 1)[-1]
                    if slug in seen_ids:
                        continue
                    seen_ids.add(slug)

                    if not self.matches_grant_criteria(title):
                        continue

                    desc = ""
                    if article.name == 'article':
                        excerpt = article.find(class_='entry-summary') or article.find('p')
                        if excerpt:
                            desc = excerpt.text.strip()[:300]

                    page_grants.append({
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

            # Fallback if scraping yielded no results but page loaded successfully
            if not page_grants and response is not None and response.status_code == 200:
                page_grants = self.llm_fallback(response, 'grant', 'FundsForNGOs', 'fundsforngos')

            grants.extend(page_grants)

        logger.info(f"[FundsForNGOs] Found {len(grants)} grant opportunities.")
        return grants


# ─── Scraper 3: ReliefWeb ─────────────────────────────────────────────────────

class ReliefWebScraper(BaseScraper):
    API_URL = "https://api.reliefweb.int/v1/jobs"

    def fetch_projects(self):
        grants = []
        try:
            params = [
                ("appname", "ngo-grants-rfp-tracker"),
                ("filter[operator]", "AND"),
                ("filter[conditions][0][field]", "country.iso3"),
                ("filter[conditions][0][value]", "IND"),
                ("filter[conditions][1][field]", "type.name"),
                ("filter[conditions][1][value]", "Consultancy"),
                ("limit", 50),
                ("sort[]", "date:desc"),
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

class DevNetRFPScraper(BaseScraper):
    URL = "https://www.devnetjobsindia.org/rfp_assignments.aspx"

    def fetch_projects(self):
        grants = []
        seen_titles = set()
        response = None
        try:
            response = self.session.get(self.URL, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # Try direct links first
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

            # Fallback within scraper logic if no direct links: doPostBack links
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

        # Fallback if scraping yielded no results but page loaded successfully
        if not grants and response is not None and response.status_code == 200:
            grants = self.llm_fallback(response, 'grant', 'DevNetJobsIndia', 'devnet', base_url="https://www.devnetjobsindia.org/")

        logger.info(f"[DevNetJobsIndia] Found {len(grants)} matching RFPs.")
        return grants


def get_all_scrapers():
    return [
        NGOBOXScraper(),
        FundsForNGOsScraper(),
        ReliefWebScraper(),
        DevNetRFPScraper(),
    ]
