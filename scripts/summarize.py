"""Fetch README and summarize repos with Claude Haiku."""

import base64
import os
import re

import anthropic
import requests
import yaml

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
HEADERS = {"Accept": "application/vnd.github+json"}
if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"

# Load settings
_settings_path = os.path.join(os.path.dirname(__file__), "..", "config", "settings.yaml")
with open(_settings_path) as f:
    _settings = yaml.safe_load(f)

MODEL = _settings["llm"]["model"]
MAX_README_CHARS = _settings["llm"]["max_readme_chars"]
MAX_TOKENS = _settings["llm"]["max_tokens"]


def fetch_readme(full_name: str) -> str:
    """Fetch and decode a repo's README via the GitHub API."""
    try:
        resp = requests.get(
            f"https://api.github.com/repos/{full_name}/readme",
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        content = resp.json().get("content", "")
        return base64.b64decode(content).decode("utf-8", errors="replace")
    except Exception as exc:
        print(f"[summarize] failed to fetch README for {full_name}: {exc}")
        return ""


def summarize_repo(full_name: str, stars: int, readme: str) -> str:
    """Call Claude Haiku to produce a 2-3 sentence summary."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return "Summary unavailable (no API key)."

    truncated = readme[:MAX_README_CHARS]
    prompt = (
        "Write a 1-2 sentence summary of this GitHub repo for an awesome-list. "
        "Be concise and compelling — like a pitch that makes developers want to try it. "
        "Focus on what problem it solves and why someone should care. "
        "Use a friendly, encouraging tone. No headings, no markdown formatting, no bullet points. "
        "Just plain text, max 2 sentences.\n\n"
        f"Repo: {full_name} ({stars} stars)\n"
        f"README:\n{truncated}"
    )

    client = anthropic.Anthropic(api_key=api_key)
    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()
    except Exception as exc:
        print(f"[summarize] Claude call failed for {full_name}: {exc}")
        return "Summary unavailable."


def extract_image(readme: str, full_name: str) -> str:
    """Extract the best image URL from a README for visual display.

    Looks for screenshots, demos, banners — skips tiny badges and icons.
    Falls back to GitHub's auto-generated OpenGraph card.
    """
    # Common badge/icon hosts to skip
    skip_patterns = [
        r"shields\.io", r"badge", r"img\.shields", r"travis-ci",
        r"codecov", r"coveralls", r"david-dm", r"gitter\.im",
        r"githubusercontent.*badge", r"github\.com.*badge",
        r"\.svg$", r"icon", r"logo.*16", r"logo.*32", r"favicon",
    ]

    # Find all markdown images: ![alt](url) and HTML <img src="url">
    md_images = re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', readme)
    html_images = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', readme)

    candidates = []
    for alt, url in md_images:
        candidates.append((alt.lower(), url.strip()))
    for url in html_images:
        candidates.append(("", url.strip()))

    for alt, url in candidates:
        # Skip badges, icons, small images
        combined = (alt + " " + url).lower()
        if any(re.search(p, combined) for p in skip_patterns):
            continue
        # Prefer images with these keywords
        if not url.startswith("http"):
            # Relative URL — resolve to raw GitHub content
            url = f"https://raw.githubusercontent.com/{full_name}/main/{url.lstrip('/')}"
        return url

    # Fallback: GitHub OpenGraph card (always available, looks decent)
    return f"https://opengraph.githubassets.com/1/{full_name}"


def summarize_repos(repos: list[dict]) -> list[dict]:
    """Fetch READMEs and summarize a list of repo dicts in-place."""
    for repo in repos:
        print(f"[summarize] processing {repo['full_name']} …")
        readme = fetch_readme(repo["full_name"])
        repo["summary"] = summarize_repo(repo["full_name"], repo["stars"], readme)
        repo["image"] = extract_image(readme, repo["full_name"])
    return repos
