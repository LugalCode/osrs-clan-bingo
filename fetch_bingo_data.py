"""
Fetches the clan bingo Overview tab from Google Sheets and writes data.json for the static site.
Run manually (python fetch_bingo_data.py) or via the scheduled GitHub Action.
"""

import csv
import io
import json
import os
import re
from datetime import datetime, timezone

import requests

SHEET_URL = "https://docs.google.com/spreadsheets/d/1aRS9pJ3ePWiwOtD_yx7qLJpNFXT0HjBWOZTXihi4gEI/edit?gid=2001374638#gid=2001374638"
OUTPUT_FILE = "data.json"

# Final rosters for the current bingo event, decided and locked in.
ROSTERS = {
    "Team 1": [
        "Neyes",
        "Bungaku",
        "MCLOVINNN316",
        "Player263241",
        "Stayin Olive",
        "TheGothGF",
    ],
    "Team 2": [
        "A C E 5",
        "DR Mafia",
        "DFirth1993",
        "VZIU",
        "Death Lion2",
        "feralg00se",
    ],
    "Team 3": [
        "Tiki Mug",
        "Darth Grave",
        "LostCaws",
        "MarkDavidIM",
        "evilorcmind",
        "Split it I",
    ],
    "Team 4": [
        "I Skrill",
        "NayffWeb",
        "TheOneJBass",
        "GIM Korakie",
        "That Bearded",
        "KoalaNoodle",
    ],
    "Team 5": [
        "TyboJones",
        "Schools",
        "Podcasters",
        "Dapphne",
        "Eshcka",
        "JohnnyScaper",
    ],
}

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


def _load_existing_teams() -> dict:
    if not os.path.exists(OUTPUT_FILE):
        return None
    with open(OUTPUT_FILE, "r") as f:
        return json.load(f).get("teams")


def _team_sort_key(team_name: str):
    """Sorts 'Team N' names numerically so tab order matches team number, regardless of
    which column the team happened to land in on the sheet."""
    match = re.search(r"\d+", team_name)
    return (int(match.group()), team_name) if match else (float("inf"), team_name)


def main():
    rows = fetch_csv_rows(SHEET_URL)
    teams = parse_overview(rows)

    teams = {name: teams[name] for name in sorted(teams, key=_team_sort_key)}
    for team_name, tiles in teams.items():
        teams[team_name] = {"tiles": tiles, "roster": ROSTERS.get(team_name, [])}

    # Only rewrite the file (and bump generated_at) if the actual tile/roster data changed —
    # otherwise every run "changes" the file just via the timestamp, forcing a redeploy every
    # time regardless of whether anything real happened. See deploy.yml for why that matters.
    if teams == _load_existing_teams():
        print("No changes since last run — leaving data.json untouched.")
        return

    output = {"generated_at": datetime.now(timezone.utc).isoformat(), "teams": teams}
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Saved {len(teams)} teams to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
