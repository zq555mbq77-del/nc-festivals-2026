#!/usr/bin/env python3
"""
NC Festivals Auto-Updater
Runs every Thursday via GitHub Actions.
Scrapes festival sources, calls Claude API to analyze new festivals,
and writes a structured JSON report for PR review.
"""

import os
import json
import re
import datetime
import urllib.request
import urllib.error

# ── Config ────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
HTML_FILE = "nc-festivals-2026.html"
REPORT_FILE = "festival_update_report.json"

SOURCES = [
    "https://festivalguidesandreviews.com/north-carolina-festivals/",
    "https://www.carolinamusicfests.com/",
    "https://www.visitnc.com/events",
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def fetch_url(url: str, timeout: int = 15) -> str:
    """Fetch a URL and return text content, stripping HTML tags."""
    req = urllib.request.Request(url, headers={"User-Agent": "NCFestivalsBot/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
        # Strip script/style blocks
        raw = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", raw, flags=re.S)
        # Strip remaining tags
        text = re.sub(r"<[^>]+>", " ", raw)
        # Collapse whitespace
        text = re.sub(r"\s{2,}", "\n", text).strip()
        return text[:12000]  # Keep within token budget
    except Exception as e:
        return f"[Could not fetch {url}: {e}]"


def load_existing_festivals(html_path: str) -> list[dict]:
    """Extract current festival names and dates from the HTML file."""
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()
    # Extract the festivals JS array
    match = re.search(r"const festivals\s*=\s*(\[.*?\]);", content, re.S)
    if not match:
        raise ValueError("Could not find festivals array in HTML file.")
    # Parse names and dates for the prompt (don't need full objects)
    names = re.findall(r'name:"([^"]+)"', match.group(1))
    dates = re.findall(r'date:"([^"]+)"', match.group(1))
    return [{"name": n, "date": d} for n, d in zip(names, dates)]


def call_claude(prompt: str) -> str:
    """Call Claude claude-sonnet-4-20250514 and return text response."""
    payload = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 4000,
        "messages": [{"role": "user", "content": prompt}]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    return data["content"][0]["text"]


def build_prompt(existing: list[dict], scraped_text: str) -> str:
    today = datetime.date.today().isoformat()
    existing_json = json.dumps(existing, indent=2)
    return f"""You are helping maintain a North Carolina festivals directory (nc-festivals-2026.html).

TODAY'S DATE: {today}

EXISTING FESTIVALS IN THE APP ({len(existing)} total):
{existing_json}

SCRAPED CONTENT FROM FESTIVAL SOURCES:
{scraped_text}

YOUR TASK:
1. Identify festivals mentioned in the scraped content that are NOT already in the existing list.
2. Only include NC festivals happening between today and December 31, 2026.
3. For each new festival, provide as much verified detail as possible.
4. Also flag any existing festivals whose dates appear to have changed.

Respond ONLY with a valid JSON object in this exact format (no markdown, no preamble):
{{
  "new_festivals": [
    {{
      "name": "Festival Name",
      "date": "YYYY-MM-DD",
      "endDate": "Mon D or null",
      "location": "City",
      "lat": 00.0000,
      "lng": -00.0000,
      "theme": "Music|Food & Drink|Cultural|Arts|Heritage|Nature|Seasonal|Sports",
      "url": "https://...",
      "desc": "Description under 200 chars.",
      "confidence": "high|medium|low",
      "source": "URL where found"
    }}
  ],
  "date_changes": [
    {{
      "name": "Existing Festival Name",
      "old_date": "YYYY-MM-DD",
      "new_date": "YYYY-MM-DD",
      "new_endDate": "Mon D or null",
      "source": "URL where found",
      "note": "Brief explanation"
    }}
  ],
  "summary": "1-2 sentence summary of what was found this week."
}}

IMPORTANT RULES:
- Only include festivals you are confident exist in NC in 2026.
- Set confidence=low if dates are estimated; confidence=high if confirmed on official site.
- Latitude/longitude must be accurate for the specific city in NC.
- Theme must be one of the 8 options listed.
- If nothing new was found, return empty arrays and say so in summary.
"""


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"[{datetime.datetime.now()}] Starting NC festivals update check...")

    # 1. Load existing festivals
    existing = load_existing_festivals(HTML_FILE)
    print(f"  Loaded {len(existing)} existing festivals.")

    # 2. Scrape sources
    print("  Scraping festival sources...")
    scraped_parts = []
    for url in SOURCES:
        print(f"    Fetching {url}...")
        text = fetch_url(url)
        scraped_parts.append(f"=== SOURCE: {url} ===\n{text}\n")
    scraped_text = "\n".join(scraped_parts)

    # 3. Call Claude
    print("  Calling Claude API for analysis...")
    prompt = build_prompt(existing, scraped_text)
    response_text = call_claude(prompt)

    # 4. Parse response
    try:
        # Strip any accidental markdown fences
        clean = re.sub(r"```json|```", "", response_text).strip()
        report = json.loads(clean)
    except json.JSONDecodeError as e:
        print(f"  WARNING: Could not parse Claude response as JSON: {e}")
        report = {
            "new_festivals": [],
            "date_changes": [],
            "summary": "Parse error — see raw_response.",
            "raw_response": response_text,
        }

    # 5. Add metadata
    report["generated_at"] = datetime.datetime.utcnow().isoformat() + "Z"
    report["existing_count"] = len(existing)
    report["sources_checked"] = SOURCES

    # 6. Write report
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # 7. Summary output
    n_new = len(report.get("new_festivals", []))
    n_changed = len(report.get("date_changes", []))
    print(f"\n  ✅ Done. Found {n_new} new festival(s), {n_changed} date change(s).")
    print(f"  Summary: {report.get('summary', '')}")
    print(f"  Report written to {REPORT_FILE}")

    # 8. Set GitHub Actions output (for PR body)
    github_output = os.environ.get("GITHUB_OUTPUT", "")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"new_count={n_new}\n")
            f.write(f"changed_count={n_changed}\n")
            summary = report.get("summary", "").replace("\n", " ")
            f.write(f"summary={summary}\n")


if __name__ == "__main__":
    main()
