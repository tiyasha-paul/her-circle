from html import unescape
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "HerCircle/1.0"}
SEARCH_TIMEOUT = 12
EXCERPT_TIMEOUT = 10
MAX_RESULTS = 7
MAX_PER_SOURCE = 2
MIN_QUERY_TOKEN_HITS = 1

REPRODUCTIVE_KEYWORDS = {
    "period",
    "menstrual",
    "sanitary",
    "pad",
    "pads",
    "tampon",
    "liners",
    "discharge",
    "itching",
    "rash",
    "irritation",
    "pcos",
    "endometriosis",
    "fibroid",
    "hormone",
    "ovulation",
    "fertility",
    "pregnancy",
    "contraception",
    "birth control",
    "vaginal",
    "pelvic",
    "uterus",
    "bleeding",
    "pmdd",
    "pms",
    "cyst",
    "ovary",
    "ovaries",
    "amenorrhea",
}

DUCKDUCKGO_SOURCES = [
    {
        "source": "Office on Women's Health",
        "site": "womenshealth.gov",
        "allowed_prefixes": ("/",),
        "priority": 5,
    },
    {
        "source": "MedlinePlus",
        "site": "medlineplus.gov",
        "allowed_prefixes": ("/",),
        "priority": 5,
    },
    {
        "source": "ACOG",
        "site": "acog.org",
        "allowed_prefixes": ("/womens-health/",),
        "priority": 5,
    },
    {
        "source": "Cleveland Clinic",
        "site": "my.clevelandclinic.org",
        "allowed_prefixes": ("/health/",),
        "priority": 4,
    },
    {
        "source": "Planned Parenthood",
        "site": "plannedparenthood.org",
        "allowed_prefixes": ("/learn/",),
        "priority": 3,
    },
]

SOURCE_PRIORITY = {
    "Office on Women's Health": 5,
    "ACOG": 5,
    "MedlinePlus": 5,
    "NHS": 4,
    "Mayo Clinic": 4,
    "Cleveland Clinic": 4,
    "Planned Parenthood": 3,
}


def _clean_text(value):
    return " ".join(unescape(value or "").split())


def _tokenize(value):
    return {part for part in value.lower().replace("/", " ").replace("-", " ").split() if len(part) > 2}


def _dedupe_results(items):
    unique = []
    seen_urls = set()
    for item in items:
        url = item.get("url", "")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        unique.append(item)
    return unique


def _is_reproductive_result(title, url):
    combined = f"{title} {url}".lower()
    return any(keyword in combined for keyword in REPRODUCTIVE_KEYWORDS)


def _extract_duckduckgo_url(href):
    if not href:
        return ""

    if href.startswith("//"):
        return f"https:{href}"

    if href.startswith("/l/?"):
        parsed = urlparse(href)
        encoded_target = parse_qs(parsed.query).get("uddg", [""])[0]
        return unquote(encoded_target)

    return href


def _is_allowed_domain(url, source_config):
    parsed = urlparse(url)
    if not parsed.scheme.startswith("http"):
        return False
    if source_config["site"] not in parsed.netloc:
        return False
    return any(parsed.path.startswith(prefix) for prefix in source_config["allowed_prefixes"])


def _fetch_excerpt(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=EXCERPT_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        meta_candidates = [
            soup.find("meta", attrs={"property": "og:description"}),
            soup.find("meta", attrs={"name": "description"}),
            soup.find("meta", attrs={"name": "twitter:description"}),
        ]
        for candidate in meta_candidates:
            content = _clean_text(candidate.get("content", "")) if candidate else ""
            if len(content) >= 80:
                return content[:320]

        for paragraph in soup.select("main p, article p, p"):
            text = _clean_text(paragraph.get_text(" ", strip=True))
            if len(text) >= 100:
                return text[:320]
    except Exception as exc:
        print(f"Excerpt fetch error for {url}: {exc}")

    return ""


def _score_result(item, query):
    query_tokens = _tokenize(query)
    searchable_text = " ".join(
        [
            item.get("title", ""),
            item.get("url", ""),
            item.get("excerpt", ""),
        ]
    ).lower()
    token_hits = sum(1 for token in query_tokens if token in searchable_text)
    reproductive_bonus = 3 if _is_reproductive_result(item.get("title", ""), item.get("url", "")) else 0
    source_bonus = SOURCE_PRIORITY.get(item.get("source"), 1) * 4
    return source_bonus + reproductive_bonus + token_hits


def _query_token_hits(item, query):
    query_tokens = _tokenize(query)
    searchable_text = " ".join(
        [
            item.get("title", ""),
            item.get("url", ""),
            item.get("excerpt", ""),
        ]
    ).lower()
    return sum(1 for token in query_tokens if token in searchable_text)


def _seems_query_relevant(title, url, query):
    temp_item = {"title": title, "url": url, "excerpt": ""}
    return _query_token_hits(temp_item, query) >= 1 or _is_reproductive_result(title, url)


def scrape_nhs(query):
    results = []
    try:
        url = f"https://www.nhs.uk/search/results?q={quote_plus(query)}"
        response = requests.get(url, headers=HEADERS, timeout=SEARCH_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        links = soup.select("a.nhsuk-card__link, a[href^='/conditions/'], a[href^='/pregnancy/']")
        for link in links:
            title = _clean_text(link.get_text(" ", strip=True))
            href = link.get("href", "")
            if not title or not href:
                continue
            if href.startswith("/"):
                href = f"https://www.nhs.uk{href}"
            if not href.startswith("https://www.nhs.uk"):
                continue
            if not _seems_query_relevant(title, href, query):
                continue
            results.append({"source": "NHS", "title": title, "url": href})
    except Exception as exc:
        print(f"NHS scrape error: {exc}")

    return _dedupe_results(results)[:4]


def scrape_mayo(query):
    results = []
    try:
        url = f"https://www.mayoclinic.org/search/search-results?q={quote_plus(query)}"
        response = requests.get(url, headers=HEADERS, timeout=SEARCH_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        for link in soup.select("a.azsearchlink, a[href*='/diseases-conditions/'], a[href*='/tests-procedures/']"):
            title = _clean_text(link.get_text(" ", strip=True))
            href = link.get("href", "")
            if not title or not href:
                continue
            if href.startswith("/"):
                href = f"https://www.mayoclinic.org{href}"
            if "mayoclinic.org" not in href:
                continue
            if not _seems_query_relevant(title, href, query):
                continue
            results.append({"source": "Mayo Clinic", "title": title, "url": href})
    except Exception as exc:
        print(f"Mayo scrape error: {exc}")

    return _dedupe_results(results)[:4]


def scrape_duckduckgo_source(query, source_config):
    results = []
    try:
        search_query = f"site:{source_config['site']} {query}"
        url = f"https://duckduckgo.com/html/?q={quote_plus(search_query)}"
        response = requests.get(url, headers=HEADERS, timeout=SEARCH_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        links = soup.select("a.result__a, a[data-testid='result-title-a']")
        for link in links:
            title = _clean_text(link.get_text(" ", strip=True))
            href = _extract_duckduckgo_url(link.get("href", ""))
            if not title or not href:
                continue
            if not _is_allowed_domain(href, source_config):
                continue
            if not _seems_query_relevant(title, href, query):
                continue
            results.append(
                {
                    "source": source_config["source"],
                    "title": title,
                    "url": href,
                }
            )
    except Exception as exc:
        print(f"{source_config['source']} search error: {exc}")

    return _dedupe_results(results)[:3]


def fetch_medical_sources(query):
    results = []
    results.extend(scrape_nhs(query))
    results.extend(scrape_mayo(query))

    for source_config in DUCKDUCKGO_SOURCES:
        results.extend(scrape_duckduckgo_source(query, source_config))

    ranked_results = []
    for item in _dedupe_results(results):
        item["excerpt"] = _fetch_excerpt(item["url"])
        if _query_token_hits(item, query) < MIN_QUERY_TOKEN_HITS and not _is_reproductive_result(item["title"], item["url"]):
            continue
        item["score"] = _score_result(item, query)
        ranked_results.append(item)

    ranked_results.sort(key=lambda item: item["score"], reverse=True)

    diverse_results = []
    source_counts = {}

    for item in ranked_results:
        source_name = item.get("source", "Unknown")
        current_count = source_counts.get(source_name, 0)
        if current_count >= MAX_PER_SOURCE:
            continue
        diverse_results.append(item)
        source_counts[source_name] = current_count + 1
        if len(diverse_results) >= MAX_RESULTS:
            break

    if len(diverse_results) < min(MAX_RESULTS, len(ranked_results)):
        for item in ranked_results:
            if item in diverse_results:
                continue
            diverse_results.append(item)
            if len(diverse_results) >= MAX_RESULTS:
                break

    return diverse_results[:MAX_RESULTS]


if __name__ == "__main__":
    sources = fetch_medical_sources("late period causes")
    for source in sources:
        print(source["source"], "-", source["title"])
        print(source["url"])
        if source.get("excerpt"):
            print(source["excerpt"])
        print()
