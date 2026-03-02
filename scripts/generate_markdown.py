"""Generate daily markdown files and the main README in awesome-list style."""

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAILY_DIR = ROOT / "daily"
README_PATH = ROOT / "README.md"

# Model capability constants
MAIN_CAPS = ["Text", "Code", "Vision", "Multilingual"]
NICHE_CAPS = ["Math", "Audio", "Video", "Image Gen", "Tool Use"]

# Category definitions: name -> (emoji, keyword patterns)
# Order matters — first match wins, so more specific categories come first.
CATEGORIES = {
    "Agent Skills & Plugins": (
        "\U0001f50c",
        [r"agent.skill", r"claude.skill", r"\bmcp\b", r"mcp.server",
         r"\bplugin\b", r"tool.use", r"function.call", r"extension"],
    ),
    "Multi-Agent Orchestration": (
        "\U0001f91d",
        [r"multi.agent", r"\bcrew\b", r"\bswarm\b", r"orchestrat",
         r"delegat", r"agentic.workflow", r"agent.framework"],
    ),
    "Coding Agents & Dev Tools": (
        "\U0001f4bb",
        [r"coding.agent", r"\bcopilot\b", r"code.gen", r"code.complet",
         r"ide.extension", r"dev.tool", r"code.review", r"code.assist"],
    ),
    "Vision & Image": (
        "\U0001f441\ufe0f",
        [r"vision", r"diffusion", r"text.to.image", r"image.generat",
         r"stable.diffusion", r"video.generat", r"\bgan\b", r"inpaint",
         r"img2img", r"\bvlm\b", r"visual.question", r"\bocr\b",
         r"image.understand", r"multimodal"],
    ),
    "Audio & Speech": (
        "\U0001f399\ufe0f",
        [r"\btts\b", r"\bstt\b", r"text.to.speech", r"speech.recogni",
         r"\baudio\b", r"\bvoice\b", r"\bwhisper\b", r"realtime.voice",
         r"speech.synthe"],
    ),
    "LLMs & Language Models": (
        "\U0001f4ac",
        [r"\bllm\b", r"language.model", r"\bgpt\b", r"\btransformer\b",
         r"text.generation", r"\bchat\b", r"\binstruct\b", r"fine.?tun",
         r"\bagent\b", r"autonomous", r"reasoning"],
    ),
    "RAG & Knowledge": (
        "\U0001f50d",
        [r"\brag\b", r"retrieval", r"vector.search", r"embedding",
         r"knowledge.base", r"semantic.search", r"rerank",
         r"vector.databas"],
    ),
    "ML Infrastructure": (
        "\U0001f6e0\ufe0f",
        [r"inference", r"serving", r"deploy", r"quantiz", r"optimi[sz]",
         r"benchmark", r"evaluat", r"training.framework", r"\bvllm\b",
         r"mlops", r"pipeline"],
    ),
    "Other AI/ML": (
        "\u2728",
        [],
    ),
}


def _classify(repo: dict) -> str:
    """Classify a repo into a category based on its metadata."""
    text = " ".join([
        repo.get("full_name", ""),
        repo.get("description", ""),
        repo.get("summary", ""),
        " ".join(repo.get("topics", [])),
    ]).lower()

    for category, (_, patterns) in CATEGORIES.items():
        if category == "Other AI/ML":
            continue
        for pattern in patterns:
            if re.search(pattern, text):
                return category
    return "Other AI/ML"


def _format_stars(stars: int) -> str:
    if stars >= 1000:
        return f"{stars / 1000:.1f}k"
    return str(stars)


def _truncate_summary(summary: str, limit: int = 120) -> str:
    """Truncate a summary at a sentence or word boundary."""
    if len(summary) <= limit:
        return summary
    # Try to break at last sentence ending (". " or " — ") within limit
    candidate = summary[:limit]
    for sep in [". ", " \u2014 "]:
        pos = candidate.rfind(sep)
        if pos > 20:
            return candidate[:pos + 1].rstrip()
    # Fall back to last word boundary (leave room for "...")
    trunc = summary[:limit - 3]
    pos = trunc.rfind(" ")
    if pos > 20:
        return trunc[:pos].rstrip() + "..."
    return trunc + "..."


def _is_new_repo(repo: dict, days: int = 30) -> bool:
    """Return True if the repo was created within the last *days* days."""
    created_at = repo.get("created_at", "")
    if not created_at:
        return False
    try:
        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt) <= timedelta(days=days)
    except (ValueError, TypeError):
        return False


def _format_created(repo: dict) -> str:
    """Return a short human-readable creation date, or empty string."""
    created_at = repo.get("created_at", "")
    if not created_at:
        return ""
    try:
        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return created_at[:10] if len(created_at) >= 10 else ""


def _shields_date(date_str: str) -> str:
    """Escape hyphens for shields.io (- becomes --)."""
    return date_str.replace("-", "--")


def _group_and_sort(repos: list[dict]) -> dict[str, list[dict]]:
    """Group repos by category and sort each group by created_at (newest first)."""
    groups: dict[str, list[dict]] = {}
    for r in repos:
        cat = _classify(r)
        groups.setdefault(cat, []).append(r)

    for cat in groups:
        groups[cat].sort(
            key=lambda r: (r.get("created_at", ""), r.get("stars", 0)),
            reverse=True,
        )

    ordered: dict[str, list[dict]] = {}
    for cat in CATEGORIES:
        if cat in groups:
            ordered[cat] = groups[cat]
    return ordered


def _repo_card(r: dict) -> list[str]:
    """Render a single repo as a visual card with image."""
    name = r["full_name"]
    url = r["url"]
    stars = _format_stars(r["stars"])
    summary = r.get("summary", "").replace("\n", " ").strip()
    lang = r.get("language", "")
    image = r.get("image", "")
    topics = r.get("topics", [])

    lang_part = f" `{lang}`" if lang else ""
    new_badge = " 🆕" if _is_new_repo(r) else ""

    # Metadata line: creation date and topics
    meta_parts = []
    date_str = _format_created(r)
    if date_str:
        meta_parts.append(f"📅 {date_str}")
    if topics:
        meta_parts.append(" ".join(f"`{t}`" for t in topics[:5]))
    meta_line = " · ".join(meta_parts)

    # Use OpenGraph fallback if no image
    if not image:
        image = f"https://opengraph.githubassets.com/1/{name}"

    lines = [
        f"<a href=\"{url}\">",
        f"  <img src=\"{image}\" width=\"400\" alt=\"{name}\" />",
        "</a>",
        "",
        f"**[{name}]({url})** \u2b50 {stars}{new_badge}{lang_part}",
        "",
        f"{summary}",
        "",
    ]
    if meta_line:
        lines.insert(-1, f"*{meta_line}*")
        lines.insert(-1, "")
    return lines


def _repo_line(r: dict) -> str:
    """Render a single repo as a compact awesome-list bullet (for README)."""
    name = r["full_name"]
    url = r["url"]
    stars = _format_stars(r["stars"])
    summary = r.get("summary", "").replace("\n", " ").strip()
    lang = r.get("language", "")
    image = r.get("image", "")

    lang_part = f" `{lang}`" if lang else ""
    new_badge = " 🆕" if _is_new_repo(r) else ""
    date_str = _format_created(r)
    date_part = f" · 📅 {date_str}" if date_str else ""

    if not image:
        image = f"https://opengraph.githubassets.com/1/{name}"

    # Compact card with thumbnail
    return (
        f"- <a href=\"{url}\"><img src=\"{image}\" width=\"70\" align=\"left\" alt=\"{name}\" /></a>"
        f" **[{name}]({url})** \u2b50 {stars}{new_badge}{lang_part}{date_part}<br/>"
        f"{summary}\n"
    )


def _capability_checkboxes(caps: list[str]) -> str:
    """Render capability checkboxes using emoji."""
    parts = []
    # Main caps: always shown (checked or unchecked)
    for c in MAIN_CAPS:
        if c in caps:
            parts.append(f"\u2705 {c}")
        else:
            parts.append(f"\u2796 {c}")
    # Niche caps: only shown when present
    niche_parts = [c for c in NICHE_CAPS if c in caps]
    if niche_parts:
        parts.append("\u00b7 " + " \u00b7 ".join(niche_parts))
    return " ".join(parts)


def _format_model_downloads(n: int) -> str:
    """Format download count for model tables."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n:,}"
    return str(n)


def _model_headline(company: str, models: list[dict]) -> str:
    """Generate a short news headline for a company's latest models."""
    if not models:
        return ""
    # Find distinct model families (strip size suffixes like -24B, -FP8, etc.)
    families = []
    seen = set()
    for m in models:
        model_id = m["model_id"]
        short = model_id.split("/")[-1] if "/" in model_id else model_id
        # Extract family name: remove size/quant suffixes
        family = re.sub(r"[-_](\d+[BbMm]|FP\d+|NVFP\d+|GGUF|AWQ|GPTQ|Base|Instruct|Chat|IT|it).*", "", short)
        if family not in seen:
            seen.add(family)
            families.append(family)
    # Build headline from top families
    top = families[:3]
    if len(top) == 1:
        return f"Latest: **{top[0]}** series"
    return "Latest: " + ", ".join(f"**{f}**" for f in top)


def _render_models_section(models_by_company: dict[str, list[dict]]) -> list[str]:
    """Render the Latest Model Releases section."""
    lines = [
        "## \U0001f3e2 Latest Model Releases",
        "",
        "> Tracked daily from Hugging Face \u00b7 5 latest models per company",
        "",
    ]

    for company, models in models_by_company.items():
        if not models:
            continue
        headline = _model_headline(company, models)
        lines.append(f"### {company}")
        if headline:
            lines.append(f"> {headline}")
        lines.append("")
        lines.append("| Model | \u2b07\ufe0f Downloads | \u2764\ufe0f Likes | Capabilities |")
        lines.append("|-------|-------------|---------|--------------|")
        for m in models:
            model_id = m["model_id"]
            hf_url = f"https://huggingface.co/{model_id}"
            short_name = model_id.split("/")[-1] if "/" in model_id else model_id
            downloads = _format_model_downloads(m.get("downloads", 0))
            likes = m.get("likes", 0)
            caps = _capability_checkboxes(m.get("capabilities", []))
            lines.append(f"| [{short_name}]({hf_url}) | {downloads} | {likes} | {caps} |")
        lines.append("")

    return lines


def generate_daily_file(repos: list[dict], date_str: str | None = None,
                        models_by_company: dict | None = None) -> Path:
    """Create daily/YYYY-MM-DD.md with visual repo cards."""
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    path = DAILY_DIR / f"{date_str}.md"

    lines = [
        f"# \U0001f680 New AI Repos \u2014 {date_str}",
        "",
        f"> Curated with \u2764\ufe0f by AI Repo Tracker. {len(repos)} new repos today.",
        "",
    ]

    # Models section (after header)
    if models_by_company:
        lines.extend(_render_models_section(models_by_company))
        lines.append("---")
        lines.append("")

    if not repos:
        lines.append("Nothing new today \u2014 check back tomorrow!")
        lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")
        print(f"[markdown] wrote {path}")
        return path

    # Table of contents — one entry per section (new/trending) × category
    new_repos = [r for r in repos if _is_new_repo(r, days=30)]
    trending_repos = [r for r in repos if not _is_new_repo(r, days=30)]
    sections = []
    if new_repos:
        sections.append(("\U0001f195 New This Month", "new-this-month", new_repos))
    if trending_repos:
        sections.append(("\U0001f4c8 Trending Today", "trending-today", trending_repos))
    if not sections:
        sections = [("All Repos", "all-repos", repos)]

    lines.append("## Contents")
    lines.append("")
    for section_title, section_anchor, section_repos in sections:
        lines.append(f"- [{section_title}](#{section_anchor})")
        grouped = _group_and_sort(section_repos)
        for category in grouped:
            emoji, _ = CATEGORIES[category]
            anchor = (section_anchor + "-" + category.lower()
                      .replace(" ", "-").replace("&", "").replace("/", "").replace("--", "-"))
            lines.append(f"  - [{emoji} {category}](#{anchor})")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Entries with full image cards, split by new vs trending
    for section_title, section_anchor, section_repos in sections:
        lines.append(f"## {section_title}")
        lines.append("")
        grouped = _group_and_sort(section_repos)
        for category, cat_repos in grouped.items():
            emoji, _ = CATEGORIES[category]
            lines.append(f"### {emoji} {category}")
            lines.append("")
            for r in cat_repos:
                lines.extend(_repo_card(r))
                lines.append("---")
                lines.append("")

    lines.append(f"[\u2b05 Back to main page](../README.md)")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[markdown] wrote {path}")
    return path


CHANGELOG_MARKER = "<!-- CHANGELOG -->"


def _build_daily_entry(repos: list[dict], date_str: str) -> list[str]:
    """Build a concise changelog entry for one day's discoveries."""
    lines = [f"## \U0001f525 {date_str} \u2014 {len(repos)} new repos"]
    lines.append("")

    if repos:
        # Split by whether the repo itself was recently created vs older but trending
        new_repos = [r for r in repos if _is_new_repo(r, days=30)]
        trending_repos = [r for r in repos if not _is_new_repo(r, days=30)]

        sections = []
        if new_repos:
            sections.append(("\U0001f195 New This Month", new_repos))
        if trending_repos:
            sections.append(("\U0001f4c8 Trending Today", trending_repos))
        if not sections:
            sections = [("All Repos", repos)]

        for section_title, section_repos in sections:
            lines.append(f"**{section_title}**")
            lines.append("")
            grouped = _group_and_sort(section_repos)
            for category, cat_repos in grouped.items():
                emoji, _ = CATEGORIES[category]
                lines.append(f"**{emoji} {category}**")
                for r in cat_repos:
                    name = r["full_name"]
                    url = r["url"]
                    stars = _format_stars(r["stars"])
                    summary = r.get("summary", "").replace("\n", " ").strip()
                    summary = _truncate_summary(summary, 120)
                    date_created = _format_created(r)
                    date_part = f" · 📅 {date_created}" if date_created else ""
                    lines.append(f"- **[{name}]({url})** \u2b50 {stars}{date_part} \u2014 {summary}")
                lines.append("")
    else:
        lines.append("No new repos today.")
        lines.append("")

    lines.append(f"> [Full details \u2192](daily/{date_str}.md)")
    lines.append("")
    return lines


def _render_top_picks(repos: list[dict], date_str: str, count: int = 5) -> list[str]:
    """Render a 'Today's Top Picks' section with the top repos by stars."""
    top = sorted(repos, key=lambda r: r.get("stars", 0), reverse=True)[:count]
    lines = [
        f"## \U0001f525 Today's Top Picks ({date_str})",
        "",
    ]
    for r in top:
        lines.append(_repo_line(r))
    lines.append("")
    lines.append(f"> **[See all {len(repos)} repos \u2192](daily/{date_str}.md)**")
    lines.append("")
    return lines


def generate_readme(repos: list[dict], date_str: str | None = None,
                    models_by_company: dict | None = None) -> Path:
    """Update README.md: rewrite header + models, append today's entry to changelog."""
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    badge_date = _shields_date(date_str)

    # --- Build the static header ---
    header = [
        "<div align=\"center\">",
        "",
        "# \U0001f31f AI Repo Tracker",
        "",
        "**A daily-updated, auto-curated awesome list of the hottest AI/ML repos on GitHub.**",
        "",
        f"![Last Update](https://img.shields.io/badge/last_update-{badge_date}-brightgreen?style=flat-square)",
        "![AI Powered](https://img.shields.io/badge/summaries-Claude_Haiku-blueviolet?style=flat-square)",
        "![Automation](https://img.shields.io/badge/updates-daily_via_Actions-orange?style=flat-square)",
        "",
        "*Star this repo to stay in the loop!* \u2b50",
        "",
        "</div>",
        "",
        "---",
        "",
        "### What is this?",
        "",
        "This repo automatically discovers the most interesting new and trending AI/ML repositories on GitHub every day at 08:00 UTC.",
        "An LLM reads each repo and writes a plain-English summary so you can decide what's worth exploring without opening a single link.",
        "",
        "### Built With",
        "",
        "- **GitHub Actions** \u2014 scheduled daily pipeline for data collection",
        "- **GitHub REST API** \u2014 discovers trending and new repos by topic, stars, and recency",
        "- **Claude Haiku** \u2014 generates concise, accurate summaries for every repo",
        "- **Hugging Face API** \u2014 tracks latest model releases across top AI companies",
        "",
        "---",
        "",
    ]

    # Top Picks section (top 5 repos by stars)
    if repos:
        header.extend(_render_top_picks(repos, date_str))
        header.append("---")
        header.append("")

    # Models section (collapsed)
    if models_by_company:
        header.append("<details>")
        header.append("<summary><strong>\U0001f3e2 Latest Model Releases</strong> (click to expand)</summary>")
        header.append("")
        header.extend(_render_models_section(models_by_company))
        header.append("</details>")
        header.append("")
        header.append("---")
        header.append("")

    header.append(CHANGELOG_MARKER)
    header.append("")

    # --- Read existing changelog entries (everything after the marker) ---
    existing_changelog = ""
    if README_PATH.exists():
        content = README_PATH.read_text(encoding="utf-8")
        marker_pos = content.find(CHANGELOG_MARKER)
        if marker_pos != -1:
            existing_changelog = content[marker_pos + len(CHANGELOG_MARKER):].lstrip("\n")

    # --- Build today's entry ---
    today_entry = _build_daily_entry(repos, date_str)

    # --- Check if today's entry already exists (avoid duplicates on re-runs) ---
    today_heading = f"## \U0001f525 {date_str}"
    if today_heading in existing_changelog:
        start = existing_changelog.find(today_heading)
        next_heading = existing_changelog.find("\n## ", start + 1)
        if next_heading == -1:
            footer_pos = existing_changelog.find("\n</details>", start + 1)
            if footer_pos == -1:
                footer_pos = existing_changelog.find("\n---\n\n<div align=\"center\">", start + 1)
            next_heading = footer_pos if footer_pos != -1 else len(existing_changelog)
        existing_changelog = existing_changelog[:start] + existing_changelog[next_heading:].lstrip("\n")

    # --- Wrap changelog in collapsible section ---
    changelog_body = "\n".join(today_entry) + existing_changelog

    changelog_section = [
        "<details>",
        "<summary><strong>\U0001f4dc Full Changelog</strong> (click to expand)</summary>",
        "",
        changelog_body.rstrip("\n"),
        "",
        "</details>",
        "",
    ]

    # --- Footer ---
    footer = [
        "---",
        "",
        "<div align=\"center\">",
        "",
        "**How it works:** GitHub Actions runs daily \u2192 discovers trending + new repos \u2192 Claude Haiku writes summaries \u2192 auto-commits",
        "",
        "Made with Github Actions and [Claude](https://claude.ai) | [How to set up your own](SETUP.md) | [Contributing](CONTRIBUTING.md)",
        "",
        "</div>",
        "",
    ]

    full = "\n".join(header) + "\n".join(changelog_section) + "\n".join(footer)

    README_PATH.write_text(full, encoding="utf-8")
    print(f"[markdown] wrote {README_PATH}")
    return README_PATH
