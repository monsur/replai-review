#!/usr/bin/env python3
"""
Generate Team Icons Data URIs

This script downloads NFL team logos and converts them to data URIs
for embedding directly in the newsletter HTML.
"""

import base64
import io
import json
import sys
from pathlib import Path
from typing import Dict
import requests
from PIL import Image


# NFL Team Abbreviations and Names
NFL_TEAMS = {
    # AFC East
    "BUF": "Buffalo Bills",
    "MIA": "Miami Dolphins",
    "NE": "New England Patriots",
    "NYJ": "New York Jets",

    # AFC North
    "BAL": "Baltimore Ravens",
    "CIN": "Cincinnati Bengals",
    "CLE": "Cleveland Browns",
    "PIT": "Pittsburgh Steelers",

    # AFC South
    "HOU": "Houston Texans",
    "IND": "Indianapolis Colts",
    "JAX": "Jacksonville Jaguars",
    "TEN": "Tennessee Titans",

    # AFC West
    "DEN": "Denver Broncos",
    "KC": "Kansas City Chiefs",
    "LV": "Las Vegas Raiders",
    "LAC": "Los Angeles Chargers",

    # NFC East
    "DAL": "Dallas Cowboys",
    "NYG": "New York Giants",
    "PHI": "Philadelphia Eagles",
    "WAS": "Washington Commanders",

    # NFC North
    "CHI": "Chicago Bears",
    "DET": "Detroit Lions",
    "GB": "Green Bay Packers",
    "MIN": "Minnesota Vikings",

    # NFC South
    "ATL": "Atlanta Falcons",
    "CAR": "Carolina Panthers",
    "NO": "New Orleans Saints",
    "TB": "Tampa Bay Buccaneers",

    # NFC West
    "ARI": "Arizona Cardinals",
    "LAR": "Los Angeles Rams",
    "SF": "San Francisco 49ers",
    "SEA": "Seattle Seahawks",
}


def crop_transparent_borders(image: Image.Image) -> Image.Image:
    """
    Crop transparent borders from an image.

    Args:
        image: PIL Image object

    Returns:
        Cropped PIL Image object
    """
    # Convert to RGBA if not already
    if image.mode != 'RGBA':
        image = image.convert('RGBA')

    # Get the bounding box of non-transparent pixels
    bbox = image.getbbox()

    if bbox:
        return image.crop(bbox)
    else:
        # If completely transparent, return original
        return image


def download_team_logo(team_abbr: str, output_dir: Path, target_width: int = 50) -> bool:
    """
    Download a team logo from ESPN, crop whitespace, and resize.

    Args:
        team_abbr: Team abbreviation (e.g., 'BUF')
        output_dir: Directory to save the logo
        target_width: Target width in pixels (default: 50)

    Returns:
        True if successful, False otherwise
    """
    # ESPN provides team logos via their CDN
    # Format: https://a.espncdn.com/i/teamlogos/nfl/500/{abbr}.png
    # Using 500x500 size for good quality
    url = f"https://a.espncdn.com/i/teamlogos/nfl/500/{team_abbr.lower()}.png"

    output_file = output_dir / f"{team_abbr}.png"

    try:
        print(f"  Downloading {team_abbr}...", end=" ")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # Load image into PIL
        image = Image.open(io.BytesIO(response.content))
        original_size = image.size

        # Crop transparent borders
        cropped_image = crop_transparent_borders(image)
        cropped_size = cropped_image.size

        # Resize to target width while maintaining aspect ratio
        aspect_ratio = cropped_image.height / cropped_image.width
        target_height = int(target_width * aspect_ratio)
        resized_image = cropped_image.resize(
            (target_width, target_height),
            Image.Resampling.LANCZOS  # High-quality downsampling
        )
        final_size = resized_image.size

        # Save the processed logo
        resized_image.save(output_file, 'PNG', optimize=True)

        # Get file size
        file_size = output_file.stat().st_size

        print(f"✓ {original_size} → {cropped_size} → {final_size} ({file_size:,} bytes)")
        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def image_to_data_uri(image_path: Path, mime_type: str = "image/png") -> str:
    """
    Convert an image file to a data URI.

    Args:
        image_path: Path to the image file
        mime_type: MIME type of the image

    Returns:
        Data URI string
    """
    with open(image_path, 'rb') as f:
        image_data = f.read()

    base64_data = base64.b64encode(image_data).decode('utf-8')
    return f"data:{mime_type};base64,{base64_data}"


def generate_team_icons_json(logos_dir: Path, output_file: Path) -> Dict:
    """
    Generate a JSON file with team icons as data URIs.

    Args:
        logos_dir: Directory containing downloaded logos
        output_file: Path to save the JSON file

    Returns:
        Dictionary of team data
    """
    team_data = {}

    print("\nConverting logos to data URIs...")

    for team_abbr, team_name in NFL_TEAMS.items():
        logo_path = logos_dir / f"{team_abbr}.png"

        if not logo_path.exists():
            print(f"  Warning: Logo not found for {team_abbr}")
            continue

        print(f"  Processing {team_abbr}...", end=" ")

        try:
            data_uri = image_to_data_uri(logo_path)

            team_data[team_abbr] = {
                "name": team_name,
                "abbreviation": team_abbr,
                "icon_data_uri": data_uri,
                "icon_size_bytes": len(data_uri)
            }

            print(f"✓ ({team_data[team_abbr]['icon_size_bytes']:,} chars)")

        except Exception as e:
            print(f"✗ Error: {e}")

    # Save to JSON file
    print(f"\nSaving to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(team_data, f, indent=2)

    return team_data


def main():
    """Main execution function."""
    print("=" * 60)
    print("NFL Team Icons Data URI Generator")
    print("=" * 60)

    # Create directories
    logos_dir = Path("team_logos")
    logos_dir.mkdir(exist_ok=True)

    print(f"\n1. Downloading team logos to {logos_dir}/")
    print("-" * 60)

    successful = 0
    failed = 0

    for team_abbr in NFL_TEAMS.keys():
        if download_team_logo(team_abbr, logos_dir):
            successful += 1
        else:
            failed += 1

    print(f"\nDownload Summary: {successful} succeeded, {failed} failed")

    if successful == 0:
        print("\nError: No logos were downloaded successfully")
        sys.exit(1)

    # Generate JSON file
    output_file = Path("team_icons.json")

    print("\n" + "=" * 60)
    print(f"2. Generating Data URIs")
    print("-" * 60)

    team_data = generate_team_icons_json(logos_dir, output_file)

    # Print summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Teams processed: {len(team_data)}")
    print(f"Output file: {output_file}")
    print(f"File size: {output_file.stat().st_size:,} bytes")

    # Calculate average data URI size
    if team_data:
        avg_size = sum(t['icon_size_bytes'] for t in team_data.values()) // len(team_data)
        print(f"Average data URI size: {avg_size:,} characters")

    print("\nNext steps:")
    print("1. Review team_icons.json to see the data URIs")
    print("2. Update your newsletter generation code to load this file")
    print("3. Modify your HTML template to include team icons")
    print("\nSee the example usage in the script comments for integration ideas.")
    print("=" * 60)


if __name__ == "__main__":
    main()
