"""Orchestrator: run the full daily pipeline.

Usage:
    python scripts/main.py                  # normal daily run
    python scripts/main.py --resummarize    # re-summarize all existing repos with current prompt
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Ensure scripts/ is on the path
sys.path.insert(0, os.path.dirname(__file__))

from discover import discover_repos
from discover_models import discover_models
from summarize import extract_image, fetch_readme, summarize_repo, summarize_repos
from generate_markdown import generate_daily_file, generate_readme

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "repos.json"
MODELS_FILE = ROOT / "data" / "models.json"


def load_seen_repos() -> dict:
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return {}


def save_seen_repos(seen: dict) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(seen, indent=2, ensure_ascii=False), encoding="utf-8")


def load_models() -> dict:
    if MODELS_FILE.exists():
        return json.loads(MODELS_FILE.read_text(encoding="utf-8"))
    return {}


def save_models(models_by_company: dict) -> None:
    MODELS_FILE.parent.mkdir(parents=True, exist_ok=True)
    MODELS_FILE.write_text(json.dumps(models_by_company, indent=2, ensure_ascii=False), encoding="utf-8")


def resummarize_all():
    """Re-summarize every repo in data/repos.json with the current prompt."""
    seen = load_seen_repos()
    if not seen:
        print("[resummarize] no repos in data/repos.json")
        return

    print(f"[resummarize] re-summarizing {len(seen)} repos …")
    for full_name, entry in seen.items():
        print(f"  → {full_name}")
        readme = fetch_readme(full_name)
        entry["summary"] = summarize_repo(full_name, entry.get("stars", 0), readme)
        entry["image"] = extract_image(readme, full_name)

    save_seen_repos(seen)

    # Regenerate today's daily file and README with all repos
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    all_repos = [
        {"full_name": k, "url": f"https://github.com/{k}", "stars": v.get("stars", 0),
         "summary": v.get("summary", ""), "image": v.get("image", ""),
         "language": v.get("language", ""), "created_at": v.get("created_at", v.get("first_seen", "")),
         "topics": v.get("topics", [])}
        for k, v in seen.items()
    ]
    all_repos.sort(key=lambda r: r["stars"], reverse=True)
    models_by_company = load_models() or None
    generate_daily_file(all_repos, today, models_by_company=models_by_company)
    generate_readme(all_repos, today, models_by_company=models_by_company)
    print(f"[resummarize] done — {len(seen)} repos updated")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--resummarize", action="store_true",
                        help="Re-summarize all existing repos with the current prompt")
    args = parser.parse_args()

    if args.resummarize:
        resummarize_all()
        return

    # 1. Load config
    config_path = ROOT / "config" / "sources.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # 2. Discover repos
    print("=== Discovery ===")
    candidates = discover_repos(config)

    # 3. Deduplicate against seen repos
    seen = load_seen_repos()
    new_repos = [r for r in candidates if r["full_name"] not in seen]
    print(f"[main] {len(new_repos)} new repos (out of {len(candidates)} candidates)")

    if not new_repos:
        print("[main] nothing new today, generating empty daily file")

    # 4. Summarize new repos
    if new_repos:
        print("\n=== Summarization ===")
        summarize_repos(new_repos)

    # 5. Update seen repos
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for r in new_repos:
        seen[r["full_name"]] = {
            "first_seen": today,
            "stars": r["stars"],
            "summary": r.get("summary", ""),
            "image": r.get("image", ""),
            "language": r.get("language", ""),
            "topics": r.get("topics", []),
            "created_at": r.get("created_at", ""),
        }
    save_seen_repos(seen)

    # 5b. Discover models from Hugging Face
    print("\n=== Model Discovery ===")
    models_by_company = discover_models(config)
    save_models(models_by_company)

    # 6. Generate markdown
    print("\n=== Markdown Generation ===")
    generate_daily_file(new_repos, today, models_by_company=models_by_company)
    generate_readme(new_repos, today, models_by_company=models_by_company)

    print(f"\n=== Done — {len(new_repos)} repos processed ===")


if __name__ == "__main__":
    main()
