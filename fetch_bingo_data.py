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

# PLACEHOLDER: pulls real clan members from Wise Old Man and arbitrarily splits them across
# teams just to preview the roster row's layout. Remove this once the sheet has a real Rosters tab.
WOM_GROUP_ID = 13796

SHEET_ID_PATTERN = re.compile(r"/d/([a-zA-Z0-9-_]+)")
GID_PATTERN = re.compile(r"[#?&]gid=(\d+)")


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
    """Detects a team block structurally — any cell whose next row down (same column) reads
    'Tile 1' is treated as that team's header, whatever text it contains. This works for both
    literal 'Team 1' labels and custom team names, and survives the sheet being reordered."""
    teams = {}
    for r, row in enumerate(rows):
        for c, cell in enumerate(row):
            if not cell or not cell.strip():
                continue
            next_row = rows[r + 1] if r + 1 < len(rows) else []
            first_tile_label = next_row[c].strip() if c < len(next_row) else ""
            if first_tile_label != "Tile 1":
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


PLACEHOLDER_ROSTER_SIZE = 6


def fetch_placeholder_rosters(team_names: list) -> dict:
    """Splits a handful of real WOM group members across teams, just for layout preview
    (capped per team so it looks like a realistic roster size, not the whole 100+ member clan)."""
    response = requests.get(f"https://api.wiseoldman.net/v2/groups/{WOM_GROUP_ID}", timeout=15)
    response.raise_for_status()
    members = [m["player"]["displayName"] for m in response.json()["memberships"]]
    members.sort()
    members = members[: PLACEHOLDER_ROSTER_SIZE * len(team_names)]

    rosters = {name: [] for name in team_names}
    for i, member in enumerate(members):
        team_name = team_names[i % len(team_names)]
        rosters[team_name].append(member)
    return rosters


def main():
    rows = fetch_csv_rows(SHEET_URL)
    teams = parse_overview(rows)

    rosters = fetch_placeholder_rosters(list(teams.keys())) if teams else {}
    for team_name, tiles in teams.items():
        teams[team_name] = {"tiles": tiles, "roster": rosters.get(team_name, [])}

    output = {"generated_at": datetime.now(timezone.utc).isoformat(), "teams": teams}
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Saved {len(teams)} teams to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
