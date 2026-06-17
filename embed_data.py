"""
Embeds all_schools_rmp_cleaned.csv into rmp_dashboard.html as inline data.
Run this after each scrape to update the baked-in default dataset.

Usage:
    python embed_data.py
"""

from pathlib import Path
import json, csv

CSV_FILE  = Path("all_schools_rmp_cleaned.csv")
HTML_FILE = Path("rmp_dashboard.html")

START_MARKER = "// @@EMBEDDED_DATA_START@@"
END_MARKER   = "// @@EMBEDDED_DATA_END@@"

if not CSV_FILE.exists():
    print("ERROR: all_schools_rmp_cleaned.csv not found. Run the scraper first.")
    exit(1)

# Read CSV into list of dicts
with open(CSV_FILE, newline="", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

print(f"  Read {len(rows)} rows from {CSV_FILE}")

csv_text = CSV_FILE.read_text(encoding="utf-8-sig")
embedded = f"{START_MARKER}\nconst EMBEDDED_CSV = {json.dumps(csv_text)};\n{END_MARKER}"

html = HTML_FILE.read_text(encoding="utf-8")

if START_MARKER in html:
    # Replace existing embedded data
    start = html.index(START_MARKER)
    end   = html.index(END_MARKER) + len(END_MARKER)
    html  = html[:start] + embedded + html[end:]
    print("  Updated existing embedded data.")
else:
    # Inject before closing </script> of the first script block
    html = html.replace(
        "// ============================================================\n// SCRAPER BUTTON + POLLING",
        embedded + "\n\n// ============================================================\n// SCRAPER BUTTON + POLLING",
        1
    )
    print("  Injected embedded data for the first time.")

HTML_FILE.write_text(html, encoding="utf-8")
print(f"  Done! {HTML_FILE} updated with baked-in data.")
print(f"  Commit and push to update the live site:")
print(f"    git add rmp_dashboard.html")
print(f'    git commit -m "Embed RMP data $(date +%Y-%m-%d)"')
print(f"    git push")
