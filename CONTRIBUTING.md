# Contributing to AI Repo Tracker

Thank you for your interest in contributing! 🎉

## Ways to Contribute

### Report Issues
- Found a miscategorised repo? Open an issue with the repo name and suggested category.
- Spotted a non-AI repo that slipped through? Let us know.
- Have a suggestion for a new search keyword or tracked org? Open an issue.

### Improve the Code
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-improvement`
3. Make your changes and test locally (see [Setup Guide](SETUP.md))
4. Open a pull request with a clear description of what changed and why

### Suggest Repos / Sources
- Open an issue titled `[Source] <org-or-keyword>` to suggest a new tracked GitHub org or search keyword.
- Edit `config/sources.yaml` and open a PR to add it directly.

## Code Style
- Python code should follow PEP 8.
- Keep functions small and well-named — the pipeline scripts (`discover.py`, `summarize.py`, `generate_markdown.py`) should each do one thing.
- Add a brief docstring to any new public function.

## Project Structure

```
.
├── config/
│   ├── settings.yaml      # LLM + GitHub API settings
│   └── sources.yaml       # Tracked orgs, search keywords, and model companies
├── data/
│   ├── repos.json         # Persistent store of all seen repos (prevents re-discovery)
│   └── models.json        # Latest model snapshots from Hugging Face
├── daily/                 # One markdown file per day
├── scripts/
│   ├── main.py            # Orchestrator — runs the full pipeline
│   ├── discover.py        # GitHub trending scrape + Search API
│   ├── discover_models.py # Hugging Face model discovery
│   ├── summarize.py       # Claude Haiku summaries
│   └── generate_markdown.py # Markdown rendering
└── .github/workflows/
    └── daily_update.yml   # GitHub Actions workflow (runs daily at 08:00 UTC)
```

## Questions?
Open an issue — we are happy to help!
