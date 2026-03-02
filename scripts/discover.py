"""Repo discovery: trending scrape, GitHub Search API, tracked orgs."""

import os
import time
from datetime import datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
HEADERS = {"Accept": "application/vnd.github+json"}
if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"


def _repo_dict(repo: dict) -> dict:
    """Normalise a GitHub API repo object to our slim format."""
    return {
        "name": repo["name"],
        "full_name": repo["full_name"],
        "url": repo["html_url"],
        "description": repo.get("description") or "",
        "stars": repo.get("stargazers_count", 0),
        "created_at": repo.get("created_at", ""),
        "language": repo.get("language") or "",
        "topics": repo.get("topics", []),
    }


# ── 1. Trending ──────────────────────────────────────────────────────────────

def discover_trending() -> list[dict]:
    """Scrape github.com/trending for today's trending repos."""
    repos = []
    try:
        resp = requests.get(
            "https://github.com/trending",
            params={"since": "daily"},
            timeout=15,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"[discover] trending scrape failed: {exc}")
        return repos

    soup = BeautifulSoup(resp.text, "html.parser")
    for article in soup.select("article.Box-row"):
        h2 = article.select_one("h2 a")
        if not h2:
            continue
        href = h2.get("href", "").strip("/")
        if "/" not in href:
            continue
        full_name = href
        desc_tag = article.select_one("p")
        description = desc_tag.get_text(strip=True) if desc_tag else ""
        star_tag = article.select_one("a[href$='/stargazers']")
        stars_text = star_tag.get_text(strip=True).replace(",", "") if star_tag else "0"
        try:
            stars = int(stars_text)
        except ValueError:
            stars = 0
        lang_tag = article.select_one("[itemprop='programmingLanguage']")
        language = lang_tag.get_text(strip=True) if lang_tag else ""

        repos.append({
            "name": full_name.split("/")[-1],
            "full_name": full_name,
            "url": f"https://github.com/{full_name}",
            "description": description,
            "stars": stars,
            "created_at": "",
            "language": language,
            "topics": [],
        })
    return repos


# ── 2. Search API ────────────────────────────────────────────────────────────

def discover_search(keywords: list[str], min_stars: int, max_age_days: int) -> list[dict]:
    """Use GitHub Search API to find recent AI/ML repos."""
    since = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).strftime("%Y-%m-%d")
    repos: dict[str, dict] = {}

    for kw in keywords:
        query = f"{kw} stars:>={min_stars} created:>{since}"
        try:
            resp = requests.get(
                "https://api.github.com/search/repositories",
                headers=HEADERS,
                params={"q": query, "sort": "stars", "order": "desc", "per_page": 20},
                timeout=15,
            )
            resp.raise_for_status()
            for item in resp.json().get("items", []):
                repos[item["full_name"]] = _repo_dict(item)
        except requests.RequestException as exc:
            print(f"[discover] search failed for '{kw}': {exc}")
        time.sleep(2)  # stay under rate limit

    return list(repos.values())


# ── 3. Tracked orgs ──────────────────────────────────────────────────────────

def discover_orgs(orgs: list[str], min_stars: int, max_age_days: int) -> list[dict]:
    """Fetch recent repos from tracked organisations."""
    since = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    repos: list[dict] = []

    for org in orgs:
        try:
            resp = requests.get(
                f"https://api.github.com/orgs/{org}/repos",
                headers=HEADERS,
                params={"sort": "created", "direction": "desc", "per_page": 30},
                timeout=15,
            )
            resp.raise_for_status()
            for item in resp.json():
                created = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
                if created >= since and item.get("stargazers_count", 0) >= min_stars:
                    repos.append(_repo_dict(item))
        except requests.RequestException as exc:
            print(f"[discover] org fetch failed for '{org}': {exc}")
        time.sleep(1)

    return repos


# ── Public entry point ────────────────────────────────────────────────────────

def discover_repos(config: dict) -> list[dict]:
    """Run all discovery methods and return a deduplicated list of repos."""
    min_stars = config.get("min_stars", 50)
    max_age = config.get("max_age_days", 7)
    max_repos = config.get("max_repos_per_day", 30)

    print("[discover] scraping trending repos …")
    trending = discover_trending()
    print(f"[discover] found {len(trending)} trending repos")

    print("[discover] searching by keywords …")
    searched = discover_search(config.get("search_keywords", []), min_stars, max_age)
    print(f"[discover] found {len(searched)} repos via search")

    print("[discover] checking tracked orgs …")
    from_orgs = discover_orgs(config.get("tracked_orgs", []), min_stars, max_age)
    print(f"[discover] found {len(from_orgs)} repos from tracked orgs")

    # deduplicate by full_name
    seen: dict[str, dict] = {}
    for repo in trending + searched + from_orgs:
        key = repo["full_name"]
        if key not in seen or repo["stars"] > seen[key]["stars"]:
            seen[key] = repo

    # filter by min stars and cap
    results = [r for r in seen.values() if r["stars"] >= min_stars]
    results.sort(key=lambda r: r["stars"], reverse=True)
    results = results[:max_repos]

    print(f"[discover] {len(results)} repos after dedup + filter")
    return results
