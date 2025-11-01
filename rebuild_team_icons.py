#!/usr/bin/env python3
"""
Rebuild team_icons.json to use file paths instead of data URIs.
"""

import json
from pathlib import Path

# Get all PNG files in web/images directory
images_dir = Path("web/images")
png_files = sorted(images_dir.glob("*.png"))

# Build the team_icons dictionary
team_icons = {}

for png_file in png_files:
    abbr = png_file.stem  # Get filename without extension
    team_icons[abbr] = {
        "abbreviation": abbr,
        "icon_file_path": f"images/{png_file.name}"
    }

# Write to team_icons.json
with open("team_icons.json", "w", encoding="utf-8") as f:
    json.dump(team_icons, f, indent=2)

print(f"Generated team_icons.json with {len(team_icons)} teams")
