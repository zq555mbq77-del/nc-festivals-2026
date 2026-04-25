#!/usr/bin/env python3
"""
apply_updates.py
Reads festival_update_report.json and patches nc-festivals-2026.html.
Run this locally after reviewing and approving the weekly PR.

Usage:
    python apply_updates.py                        # Apply all high+medium confidence new festivals
    python apply_updates.py --include-low          # Also include low-confidence entries
    python apply_updates.py --dry-run              # Preview changes without writing
"""

import json
import re
import sys
import argparse
import datetime

HTML_FILE = "nc-festivals-2026.html"
REPORT_FILE = "festival_update_report.json"


def load_report() -> dict:
    with open(REPORT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_html() -> str:
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        return f.read()


def save_html(content: str):
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(content)


def festival_to_js(f: dict) -> str:
    """Convert a festival dict from the report into a JS object string."""
    def esc(s):
        if not s:
            return ""
        return (str(s)
                .replace("\\", "\\\\")
                .replace('"', '\\"')
                .replace("\u2019", "\\u2019")
                .replace("\u2014", "\\u2014")
                .replace("\u2013", "\\u2013")
                .replace("\u2018", "\\u2018"))

    end = f"\"{esc(f['endDate'])}\"" if f.get("endDate") else "null"
    return (
        f'  {{ name:"{esc(f["name"])}", '
        f'date:"{f["date"]}", '
        f'endDate:{end}, '
        f'location:"{esc(f["location"])}", '
        f'lat:{f["lat"]}, '
        f'lng:{f["lng"]}, '
        f'theme:"{esc(f["theme"])}", '
        f'url:"{esc(f.get("url", ""))}", '
        f'desc:"{esc(f["desc"])}" }},'
    )


def get_existing_names(html: str) -> set:
    return set(re.findall(r'name:"([^"]+)"', html))


def insert_festival(html: str, fest_js: str) -> str:
    """Insert a new festival before the closing ]; of the festivals array."""
    # Find the closing bracket of the festivals array
    marker = "];"
    # Find last occurrence before the scripts end
    idx = html.rfind("  " + marker)
    if idx == -1:
        idx = html.rfind(marker)
    if idx == -1:
        raise ValueError("Could not find end of festivals array in HTML.")
    return html[:idx] + fest_js + "\n" + html[idx:]


def apply_date_change(html: str, change: dict) -> str:
    """Update a festival's date in the HTML."""
    name = change["name"].replace('"', '\\"')
    old_date = change["old_date"]
    new_date = change["new_date"]
    new_end = change.get("new_endDate")

    # Find the festival entry
    pattern = rf'(name:"{re.escape(name)}"[^}}]+?)date:"{re.escape(old_date)}"'
    match = re.search(pattern, html)
    if not match:
        print(f"  ⚠️  Could not find '{change['name']}' with date {old_date} — skipping.")
        return html

    updated = html.replace(
        f'date:"{old_date}"',
        f'date:"{new_date}"',
        1  # Only replace first occurrence after finding the festival
    )

    if new_end is not None:
        # Also update endDate if provided
        end_str = f'"{new_end}"' if new_end else "null"
        # This is approximate — may need manual check
        print(f"  ℹ️  Note: Also update endDate for '{change['name']}' to {end_str} manually if needed.")

    return updated


def main():
    parser = argparse.ArgumentParser(description="Apply festival updates to HTML.")
    parser.add_argument("--include-low", action="store_true", help="Include low-confidence entries")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, don't write")
    args = parser.parse_args()

    report = load_report()
    html = load_html()
    existing_names = get_existing_names(html)

    print(f"\n🎪 NC Festivals Apply Script")
    print(f"   Report from: {report.get('generated_at', 'unknown')}")
    print(f"   Current festivals in file: {len(existing_names)}\n")

    new_festivals = report.get("new_festivals", [])
    date_changes = report.get("date_changes", [])
    applied = 0
    skipped = 0

    # ── Apply new festivals ────────────────────────────────────────────────
    print(f"── New Festivals ({len(new_festivals)} candidates) ──────────────")
    for f in new_festivals:
        name = f.get("name", "")
        confidence = f.get("confidence", "medium")

        if name in existing_names:
            print(f"  SKIP (exists): {name}")
            skipped += 1
            continue

        if confidence == "low" and not args.include_low:
            print(f"  SKIP (low confidence 🔴): {name} — run with --include-low to add")
            skipped += 1
            continue

        conf_icon = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(confidence, "⚪")
        print(f"  ADD {conf_icon}: {name} | {f.get('date')} | {f.get('location')}")

        if not args.dry_run:
            fest_js = festival_to_js(f)
            html = insert_festival(html, fest_js)
            existing_names.add(name)
            applied += 1

    # ── Apply date changes ────────────────────────────────────────────────
    print(f"\n── Date Changes ({len(date_changes)} found) ──────────────────")
    for change in date_changes:
        print(f"  UPDATE: {change['name']} | {change['old_date']} → {change['new_date']}")
        print(f"          {change.get('note', '')}")
        if not args.dry_run:
            html = apply_date_change(html, change)
            applied += 1

    # ── Count and save ────────────────────────────────────────────────────
    final_count = len(re.findall(r'name:"', html))
    print(f"\n── Summary {'(DRY RUN)' if args.dry_run else ''} ────────────────────────")
    print(f"  Applied: {applied} | Skipped: {skipped}")
    print(f"  Festival count: {len(existing_names)} → {final_count}")

    if not args.dry_run and applied > 0:
        save_html(html)
        print(f"  ✅ Saved to {HTML_FILE}")
    elif args.dry_run:
        print(f"  ℹ️  Dry run — no changes written.")
    else:
        print(f"  ℹ️  Nothing to apply.")


if __name__ == "__main__":
    main()
