"""Generate daily markdown files and the main README in awesome-list style."""

import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAILY_DIR = ROOT / "daily"
README_PATH = ROOT / "README.md"

# Model capability constants
MAIN_CAPS = ["Text", "Code", "Vision", "Multilingual"]
NICHE_CAPS = ["Math", "Audio", "Video", "Image Gen", "Tool Use"]

# Category definitions: name -> (emoji, keyword patterns)
CATEGORIES = {
    "LLMs & Language Models": (
        "\U0001f4ac",
        [r"\bllm\b", r"language.model", r"\bgpt\b", r"\btransformer\b",
         r"text.generation", r"\bchat\b", r"\binstruct\b", r"fine.?tun"],
    ),
    "Agents & Autonomous Systems": (
        "\U0001f916",
        [r"\bagent\b", r"autonomous", r"tool.use", r"function.call",
         r"planning", r"reasoning", r"\bcrew\b", r"agentic"],
    ),
    "Image & Video Generation": (
        "\U0001f3a8",
        [r"diffusion", r"text.to.image", r"image.generat", r"stable.diffusion",
         r"video.generat", r"\bgan\b", r"inpaint", r"img2img"],
    ),
    "Multimodal & Vision-Language": (
        "\U0001f441\ufe0f",
        [r"multimodal", r"vision.language", r"\bvlm\b", r"visual.question",
         r"image.text", r"ocr", r"document.understand"],
    ),
    "RAG & Information Retrieval": (
        "\U0001f50d",
        [r"\brag\b", r"retrieval", r"vector.search", r"embedding",
         r"knowledge.base", r"semantic.search", r"rerank"],
    ),
    "ML Infrastructure & Tools": (
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
    lang_part = f" `{lang}`" if lang else ""

    # Use OpenGraph fallback if no image
    if not image:
        image = f"https://opengraph.githubassets.com/1/{name}"

    lines = [
        f"<a href=\"{url}\">",
        f"  <img src=\"{image}\" width=\"400\" alt=\"{name}\" />",
        "</a>",
        "",
        f"**[{name}]({url})** \u2b50 {stars}{lang_part}",
        "",
        f"{summary}",
        "",
    ]
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

    if not image:
        image = f"https://opengraph.githubassets.com/1/{name}"

    # Compact card with thumbnail
    return (
        f"- <a href=\"{url}\"><img src=\"{image}\" width=\"70\" align=\"left\" alt=\"{name}\" /></a>"
        f" **[{name}]({url})** \u2b50 {stars}{lang_part}<br/>"
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

    # Table of contents
    grouped = _group_and_sort(repos)
    lines.append("## Contents")
    lines.append("")
    for category in grouped:
        emoji, _ = CATEGORIES[category]
        anchor = category.lower().replace(" ", "-").replace("&", "").replace("/", "").replace("--", "-")
        lines.append(f"- [{emoji} {category}](#{anchor})")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Entries with full image cards
    for category, cat_repos in grouped.items():
        emoji, _ = CATEGORIES[category]
        lines.append(f"## {emoji} {category}")
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
        grouped = _group_and_sort(repos)
        for category, cat_repos in grouped.items():
            emoji, _ = CATEGORIES[category]
            lines.append(f"**{emoji} {category}**")
            for r in cat_repos:
                name = r["full_name"]
                url = r["url"]
                stars = _format_stars(r["stars"])
                summary = r.get("summary", "").replace("\n", " ").strip()
                # Truncate long summaries for conciseness
                if len(summary) > 120:
                    summary = summary[:117] + "..."
                lines.append(f"- **[{name}]({url})** \u2b50 {stars} \u2014 {summary}")
            lines.append("")
    else:
        lines.append("No new repos today.")
        lines.append("")

    lines.append(f"> [Full details \u2192](daily/{date_str}.md)")
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
    ]

    # Models section
    if models_by_company:
        header.extend(_render_models_section(models_by_company))
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
        # Replace today's existing entry with updated one
        # Find the start and end of the existing entry
        start = existing_changelog.find(today_heading)
        # Find the next ## heading after this one
        next_heading = existing_changelog.find("\n## ", start + 1)
        if next_heading == -1:
            # Also check for footer marker
            footer_pos = existing_changelog.find("\n---\n\n<div align=\"center\">", start + 1)
            next_heading = footer_pos if footer_pos != -1 else len(existing_changelog)
        existing_changelog = existing_changelog[:start] + existing_changelog[next_heading:].lstrip("\n")

    # --- Assemble: header + today's entry + previous entries + footer ---
    footer = [
        "---",
        "",
        "<div align=\"center\">",
        "",
        "**How it works:** GitHub Actions runs daily \u2192 discovers trending + new repos \u2192 Claude Haiku writes summaries \u2192 auto-commits",
        "",
        "Made with \u2764\ufe0f and [Claude](https://claude.ai) | [How to set up your own](/.github/workflows/daily_update.yml)",
        "",
        "</div>",
        "",
    ]

    # Strip any existing footer from changelog
    footer_marker = "---\n\n<div align=\"center\">"
    footer_pos = existing_changelog.find(footer_marker)
    if footer_pos != -1:
        existing_changelog = existing_changelog[:footer_pos].rstrip("\n") + "\n\n"

    full = "\n".join(header) + "\n".join(today_entry) + existing_changelog + "\n".join(footer)

    README_PATH.write_text(full, encoding="utf-8")
    print(f"[markdown] wrote {README_PATH}")
    return README_PATH
