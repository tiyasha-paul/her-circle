from urllib.parse import quote_plus

import requests

HEADERS = {"User-Agent": "HerCircle/1.0"}
TIMEOUTS = (8, 12, 16)
POSTS_PER_SUBREDDIT = 4

GENERAL_SUBREDDITS = [
    "WomensHealth",
    "TwoXChromosomes",
    "Healthyhooha",
    "periods",
    "menstruationstation",
    "obgyn",
    "women",
    "AskWomen",
    "TwoXSupport",
    "TheGirlSurvivalGuide",
    "breaktheredwall",
    "AskIndianWomen",
]

TOPIC_SUBREDDITS = {
    "pcos": ["PCOS", "TTC_PCOS"],
    "pcod": ["PCOS", "TTC_PCOS"],
    "endo": ["Endo", "endometriosis"],
    "endometriosis": ["Endo", "endometriosis"],
    "adenomyosis": ["adenomyosis"],
    "pmdd": ["PMDD"],
    "pms": ["PMDD", "periods"],
    "fertility": ["tryingforababy", "fertility", "TTC30", "femaleinfertility", "TTCHormoneCharts", "TryingForABaby", "Fertility"],
    "ovulation": ["tryingforababy", "fertility", "femaleinfertility", "TTCHormoneCharts", "TryingForABaby", "Fertility"],
    "pregnancy": ["babybumps", "pregnant", "tryingforababy", "Miscarriage"],
    "contraception": ["birthcontrol"],
    "birth control": ["birthcontrol"],
    "iud": ["birthcontrol"],
    "pill": ["birthcontrol"],
    "bleeding": ["periods", "WomensHealth", "menstruation", "period"],
    "period": ["periods", "period", "menstruationstation", "menstruation", "PeriodUnderwear"],
    "periods": ["periods", "period", "menstruationstation", "menstruation", "PeriodUnderwear"],
    "menstrual": ["periods", "period", "menstruationstation", "menstruation"],
    "fibroid": ["WomensHealth"],
    "rash": ["Healthyhooha", "WomensHealth"],
    "discharge": ["Healthyhooha", "WomensHealth"],
    "itching": ["Healthyhooha", "WomensHealth"],
    "pain": ["WomensHealth", "Endo", "endometriosis"],
    "menopause": ["Menopause", "Perimenopause", "women", "WomensHealth"],
    "perimenopause": ["Perimenopause", "Menopause"],
    "vaginismus": ["vaginismus", "Healthyhooha", "WomensHealth"],
    "miscarriage": ["Miscarriage", "pregnant", "TryingForABaby"],
    "teen": ["AskTeenGirls"],
    "teenage": ["AskTeenGirls"],
    "india": ["AskIndianWomen"],
    "indian": ["AskIndianWomen"],
}


def _tokenize(value):
    return {part for part in value.lower().replace("/", " ").replace("-", " ").split() if len(part) > 2}


def _select_subreddits(query):
    lowered = query.lower()
    selected = list(GENERAL_SUBREDDITS)

    for keyword, subreddit_list in TOPIC_SUBREDDITS.items():
        if keyword in lowered:
            selected.extend(subreddit_list)

    unique = []
    seen = set()
    for subreddit in selected:
        normalized = subreddit.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        unique.append(subreddit)
    return unique


def _build_query_variants(query):
    variants = [query.strip()]
    compact = " ".join(query.split())
    if compact not in variants:
        variants.append(compact)

    query_tokens = _tokenize(query)
    focused_terms = [
        token
        for token in (
            "period",
            "pcos",
            "endometriosis",
            "endo",
            "pmdd",
            "fertility",
            "ovulation",
            "birth",
            "control",
            "pregnancy",
            "bleeding",
            "pain",
        )
        if token in query_tokens
    ]
    if focused_terms:
        focused_query = " ".join(focused_terms)
        if focused_query not in variants:
            variants.append(focused_query)

    return variants[:3]


def _fetch_subreddit_results(subreddit, query):
    encoded_query = quote_plus(query)
    url = (
        f"https://www.reddit.com/r/{subreddit}/search.json"
        f"?q={encoded_query}&limit={POSTS_PER_SUBREDDIT}&sort=relevance&t=all&restrict_sr=1"
    )

    last_error = None
    for timeout in TIMEOUTS:
        try:
            response = requests.get(url, headers=HEADERS, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            last_error = exc

    raise last_error


def _build_post_snippet(payload):
    body = " ".join((payload.get("selftext") or "").split())
    if body:
        return body[:420]

    title = " ".join((payload.get("title") or "").split())
    return title[:220]


def _query_token_hits(query, payload):
    query_tokens = _tokenize(query)
    searchable = " ".join(
        [
            payload.get("title", ""),
            payload.get("selftext", ""),
            payload.get("subreddit", ""),
        ]
    ).lower()
    return sum(1 for token in query_tokens if token in searchable)


def _is_low_quality_post(payload):
    title = (payload.get("title") or "").strip().lower()
    body = (payload.get("selftext") or "").strip().lower()
    combined = f"{title} {body}".strip()

    if not combined:
        return True
    if title in {"[deleted]", "[removed]"} or body in {"[deleted]", "[removed]"}:
        return True
    if payload.get("over_18"):
        return True
    if payload.get("score", 0) <= 0 and payload.get("num_comments", 0) == 0:
        return True
    if len(body) < 40 and payload.get("num_comments", 0) < 2:
        return True
    if any(phrase in combined for phrase in ("dm me", "snapchat", "telegram", "onlyfans", "selling")):
        return True
    return False


def _score_post(query, payload):
    searchable = " ".join(
        [
            payload.get("title", ""),
            payload.get("selftext", ""),
            payload.get("subreddit", ""),
        ]
    ).lower()
    token_hits = _query_token_hits(query, payload)
    score = payload.get("score", 0)
    comments = payload.get("num_comments", 0)
    length_bonus = 2 if len((payload.get("selftext") or "").strip()) >= 80 else 0
    first_person_bonus = 2 if any(term in searchable for term in (" i ", " my ", " me ", " i've ", " i’m ")) else 0
    detail_bonus = 2 if any(term in searchable for term in ("symptom", "doctor", "diagnosed", "bleeding", "pain", "cramps", "period")) else 0
    return (token_hits * 8) + min(score, 250) * 0.04 + min(comments, 120) * 0.08 + length_bonus + first_person_bonus + detail_bonus


def _is_relevant_post(query, payload):
    token_hits = _query_token_hits(query, payload)
    if token_hits >= 2:
        return True

    combined = " ".join(
        [
            payload.get("title", ""),
            payload.get("selftext", ""),
        ]
    ).lower()
    if token_hits >= 1 and any(term in combined for term in ("period", "bleeding", "pain", "pcos", "pregnan", "ovulation", "birth control", "cramp", "discharge")):
        return True

    return False


def fetch_reddit_posts(query, limit=6):
    results = []
    seen_urls = set()
    subreddits = _select_subreddits(query)
    variants = _build_query_variants(query)

    for subreddit in subreddits:
        for variant in variants:
            try:
                data = _fetch_subreddit_results(subreddit, variant)
                posts = data.get("data", {}).get("children", [])

                for post in posts:
                    payload = post.get("data", {})
                    permalink = payload.get("permalink", "")
                    url = f"https://reddit.com{permalink}" if permalink else ""

                    if not url or url in seen_urls:
                        continue
                    if payload.get("removed_by_category") or payload.get("is_self") is False:
                        continue
                    if not payload.get("title"):
                        continue
                    if _is_low_quality_post(payload):
                        continue
                    if not _is_relevant_post(query, payload):
                        continue

                    snippet = _build_post_snippet(payload)
                    if not snippet:
                        continue

                    seen_urls.add(url)
                    results.append(
                        {
                            "title": payload.get("title", ""),
                            "body": snippet,
                            "url": url,
                            "upvotes": payload.get("score", 0),
                            "num_comments": payload.get("num_comments", 0),
                            "subreddit": payload.get("subreddit", subreddit),
                            "relevance": _score_post(query, payload),
                        }
                    )
            except Exception as exc:
                print(f"Error fetching from r/{subreddit} with '{variant}': {exc}")
                continue

    results.sort(
        key=lambda item: (item["relevance"], item["num_comments"], item["upvotes"]),
        reverse=True,
    )
    return results[:limit]


if __name__ == "__main__":
    posts = fetch_reddit_posts("late period causes")
    for post in posts:
        print(post["subreddit"], "-", post["title"])
        print(post["url"])
        print(post["body"])
        print()
