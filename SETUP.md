# Setting Up Your Own AI Repo Tracker

This guide walks you through forking this repo and running your own daily AI/ML tracker.

## Prerequisites

- A GitHub account
- An [Anthropic API key](https://console.anthropic.com/) (for Claude Haiku summaries)

## Quick Start

### 1. Fork the Repository

Click the **Fork** button at the top of this page, then clone your fork:

```bash
git clone https://github.com/<your-username>/awesome-ai-tracker
cd awesome-ai-tracker
```

### 2. Add Secrets

In your forked repo, go to **Settings → Secrets and variables → Actions** and add:

| Secret | Description |
|--------|-------------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key for Claude Haiku summaries |

> **Note:** `GITHUB_TOKEN` is provided automatically by GitHub Actions — no setup needed.

### 3. Enable GitHub Actions

Go to **Actions** in your fork and click **"I understand my workflows, go ahead and enable them"** if prompted.

The workflow runs automatically every day at 08:00 UTC. You can also trigger it manually from the **Actions** tab using the **"Run workflow"** button.

### 4. Customise Your Tracker

Edit `config/sources.yaml` to tailor what gets tracked:

```yaml
# Organisations to watch for new repos
tracked_orgs:
  - openai
  - meta-llama
  - your-favourite-org

# Keywords for GitHub Search API
search_keywords:
  - "large language model"
  - "AI agent"
  - your-keyword-here

# How many stars a repo needs to be included
min_stars: 50

# Only pick up repos created within this many days
max_age_days: 7
```

Edit `config/settings.yaml` to change the LLM model or output limits.

### 5. Local Development

```bash
pip install -r requirements.txt

# Set environment variables
export GITHUB_TOKEN=ghp_...
export ANTHROPIC_API_KEY=sk-ant-...

# Run the full pipeline
python scripts/main.py

# Re-summarise all existing repos with the current prompt
python scripts/main.py --resummarize
```

## How It Works

```
GitHub Actions (daily 08:00 UTC)
    │
    ├─ discover.py      → scrapes github.com/trending + GitHub Search API + tracked orgs
    ├─ summarize.py     → fetches READMEs, calls Claude Haiku for 1-2 sentence summaries
    ├─ discover_models.py → pulls latest models from Hugging Face
    └─ generate_markdown.py → writes daily/YYYY-MM-DD.md and updates README.md
         │
         └─ git-auto-commit-action → commits & pushes changes
```

Repos are tracked in `data/repos.json` so the same repo is never surfaced twice.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| No repos discovered | Check `GITHUB_TOKEN` is valid; unauthenticated requests have very low rate limits |
| Summaries say "unavailable" | Check `ANTHROPIC_API_KEY` secret is set correctly |
| Workflow not running | Ensure Actions are enabled; check the workflow YAML is on the default branch |
