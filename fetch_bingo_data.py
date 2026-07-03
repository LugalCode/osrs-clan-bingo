"""
Fetches the clan bingo Overview tab from Google Sheets and writes data.json for the static site.
Run manually (python fetch_bingo_data.py) or via the scheduled GitHub Action.
"""

import csv
import io
import json
import re
from datetime import datetime, timezone

import requests

SHEET_URL = "https://docs.google.com/spreadsheets/d/13RTvN7TxLMFTij03AiuzMi6NKwdBhqPfn31kf_djJ8A/edit"
OUTPUT_FILE = "data.json"

SHEET_ID_PATTERN = re.compile(r"/d/([a-zA-Z0-9-_]+)")
GID_PATTERN = re.compile(r"[#?&]gid=(\d+)")
TEAM_HEADER_PATTERN = re.compile(r"^Team \d+$")


def fetch_csv_rows(link: str) -> list:
    sheet_id = SHEET_ID_PATTERN.search(link).group(1)
    gid_match = GID_PATTERN.search(link)
    params = {"format": "csv"}
    if gid_match:
        params["gid"] = gid_match.group(1)
    response = requests.get(
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/export", params=params, timeout=15
    )
    response.raise_for_status()
    return list(csv.reader(io.StringIO(response.text)))


def parse_overview(rows: list) -> dict:
    """Scans for 'Team N' headers anywhere in the grid, reads the tile rows beneath them."""
    teams = {}
    for r, row in enumerate(rows):
        for c, cell in enumerate(row):
            if not cell or not TEAM_HEADER_PATTERN.match(cell.strip()):
                continue
            team_name = cell.strip()
            tiles = {}
            i = 1
            while True:
                tr = r + i
                if tr >= len(rows):
                    break
                trow = rows[tr]
                tile_label = trow[c].strip() if c < len(trow) else ""
                if not tile_label.startswith("Tile"):
                    break
                task_name = trow[c + 1].strip() if c + 1 < len(trow) else ""
                complete_raw = trow[c + 2].strip() if c + 2 < len(trow) else ""
                tiles[tile_label] = {"name": task_name, "complete": complete_raw.upper() == "TRUE"}
                i += 1
            if tiles:
                teams[team_name] = tiles
    return teams


def main():
    rows = fetch_csv_rows(SHEET_URL)
    teams = parse_overview(rows)
    output = {"generated_at": datetime.now(timezone.utc).isoformat(), "teams": teams}
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Saved {len(teams)} teams to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
