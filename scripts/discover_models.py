"""Fetch latest models from Hugging Face API per company with capability detection."""

import requests

# Fixed capability set
ALL_CAPABILITIES = [
    "Text", "Code", "Vision", "Multilingual",
    "Math", "Audio", "Video", "Image Gen", "Tool Use",
]

# Main capabilities that always show (checked or unchecked)
MAIN_CAPABILITIES = {"Text", "Code", "Vision", "Multilingual"}

# pipeline_tag -> capabilities
PIPELINE_MAP = {
    "text-generation": ["Text"],
    "text2text-generation": ["Text"],
    "conversational": ["Text"],
    "image-text-to-text": ["Text", "Vision"],
    "image-to-text": ["Vision"],
    "visual-question-answering": ["Vision"],
    "document-question-answering": ["Vision"],
    "text-classification": ["Text"],
    "text-to-image": ["Image Gen"],
    "image-to-image": ["Image Gen"],
    "text-to-video": ["Video"],
    "text-to-audio": ["Audio"],
    "automatic-speech-recognition": ["Audio"],
    "text-to-speech": ["Audio"],
    "audio-classification": ["Audio"],
    "translation": ["Text", "Multilingual"],
}

# tag substrings -> capabilities
TAG_MAP = {
    "code": "Code",
    "vision": "Vision",
    "vision-language": "Vision",
    "multilingual": "Multilingual",
    "math": "Math",
    "function-calling": "Tool Use",
    "audio": "Audio",
    "video": "Video",
    "image-generation": "Image Gen",
    "ocr": "Vision",
}

# Tags that must match exactly (not substring)
TAG_EXACT = {
    "vl": "Vision",
}

# model ID substrings -> capabilities
NAME_HINTS = {
    "Coder": "Code",
    "coder": "Code",
    "Devstral": "Code",
    "devstral": "Code",
    "VL-": "Vision",
    "-VL-": "Vision",
    "-vl-": "Vision",
    "Vision": "Vision",
    "vision": "Vision",
    "OCR": "Vision",
    "Math": "Math",
    "math": "Math",
    "Audio": "Audio",
    "audio": "Audio",
    "Voxtral": "Audio",
    "translate": "Multilingual",
    "Translate": "Multilingual",
}

HF_API = "https://huggingface.co/api/models"


def _detect_capabilities(model: dict) -> list[str]:
    """Detect model capabilities using 3-pass approach."""
    caps = set()

    # Pass 1: pipeline_tag
    pipeline_tag = model.get("pipeline_tag") or ""
    if pipeline_tag in PIPELINE_MAP:
        caps.update(PIPELINE_MAP[pipeline_tag])

    # Pass 2: tags array
    tags = model.get("tags") or []
    tags_lower = [t.lower() for t in tags]
    for tag_sub, cap in TAG_MAP.items():
        for t in tags_lower:
            if tag_sub in t:
                caps.add(cap)
                break
    for tag_exact, cap in TAG_EXACT.items():
        if tag_exact in tags_lower:
            caps.add(cap)

    # Detect multilingual from multiple language code tags
    lang_codes = {"en", "fr", "de", "es", "pt", "it", "ja", "ko", "ru", "zh",
                  "ar", "hi", "vi", "id", "th", "tr", "pl", "nl", "sv", "bn"}
    lang_count = sum(1 for t in tags_lower if t in lang_codes)
    if lang_count >= 3:
        caps.add("Multilingual")

    # Pass 3: model ID heuristic
    model_id = model.get("modelId") or model.get("id") or ""
    for hint, cap in NAME_HINTS.items():
        if hint in model_id:
            caps.add(cap)

    # Text-generation models without other primary caps default to Text
    if not caps and pipeline_tag in ("text-generation", "text2text-generation", "conversational", ""):
        caps.add("Text")

    return [c for c in ALL_CAPABILITIES if c in caps]


def _format_downloads(n: int) -> str:
    """Format download count with commas."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def _fetch_company_models(org: str, limit: int) -> list[dict]:
    """Fetch latest models for a single HF organization."""
    try:
        resp = requests.get(
            HF_API,
            params={
                "author": org,
                "sort": "lastModified",
                "direction": "-1",
                "limit": limit,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        print(f"[models] warning: failed to fetch models for {org}: {e}")
        return []


def discover_models(config: dict) -> dict[str, list[dict]]:
    """Fetch latest models from Hugging Face for all configured companies.

    Returns dict keyed by company display name, each value a list of model dicts.
    """
    companies = config.get("model_companies", {})
    limit = config.get("models_per_company", 5)
    results: dict[str, list[dict]] = {}

    for display_name, company_cfg in companies.items():
        hf_orgs = company_cfg.get("hf_orgs", [])
        models = []
        for org in hf_orgs:
            raw_models = _fetch_company_models(org, limit)
            for m in raw_models:
                model_id = m.get("modelId") or m.get("id") or ""
                capabilities = _detect_capabilities(m)
                models.append({
                    "model_id": model_id,
                    "author": org,
                    "company": display_name,
                    "last_modified": m.get("lastModified", ""),
                    "downloads": m.get("downloads", 0),
                    "likes": m.get("likes", 0),
                    "pipeline_tag": m.get("pipeline_tag", ""),
                    "tags": m.get("tags", []),
                    "capabilities": capabilities,
                })

        # Sort by last_modified descending and take top N
        models.sort(key=lambda x: x["last_modified"], reverse=True)
        results[display_name] = models[:limit]
        print(f"[models] {display_name}: fetched {len(results[display_name])} models")

    return results
