#!/usr/bin/env python3
"""
Script 1: Fetch NFL Game Recaps

This script:
1. Determines the target NFL week (using configurable week calculator)
2. Navigates to ESPN's scoreboard for that week
3. Finds all game recap links
4. Downloads each recap HTML file
5. Saves recaps to a week-specific directory
"""

import argparse
import os
import sys
import time
from pathlib import Path
from typing import List, Tuple

import requests
from bs4 import BeautifulSoup

from utils import (
    load_config,
    get_week_directory_path,
    setup_week_calculator,
    create_base_parser,
    handle_fatal_error,
    handle_recoverable_error
)


def create_week_directory(tmp_dir: str, week: int, year: int, recap_subdir: str) -> Path:
    """
    Create directory structure for storing week's recaps.

    Args:
        tmp_dir: Temporary directory for intermediate files
        week: NFL week number
        year: NFL season year
        recap_subdir: Subdirectory name for recaps

    Returns:
        Path to the recaps directory
    """
    week_dir = Path(tmp_dir) / f"{year}-week{week:02d}"
    recaps_dir = week_dir / recap_subdir

    recaps_dir.mkdir(parents=True, exist_ok=True)

    return recaps_dir


def build_scoreboard_url(base_url: str, year: int, week: int) -> str:
    """
    Build ESPN scoreboard URL for a specific week.

    Args:
        base_url: Base ESPN scoreboard URL
        year: NFL season year
        week: NFL week number

    Returns:
        Complete scoreboard URL
    """
    # ESPN URL structure: /nfl/scoreboard/_/year/YYYY/seasontype/2/week/W
    # seasontype 2 = regular season
    return f"{base_url}/_/year/{year}/seasontype/2/week/{week}"


def fetch_scoreboard(url: str) -> BeautifulSoup:
    """
    Fetch the scoreboard page and return parsed HTML.

    Args:
        url: Scoreboard URL

    Returns:
        BeautifulSoup object of the page
    """
    print(f"Fetching scoreboard: {url}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return BeautifulSoup(response.text, 'html.parser')


def extract_recap_links(soup: BeautifulSoup) -> List[Tuple[str, str]]:
    """
    Extract game recap links from the scoreboard page.

    Args:
        soup: BeautifulSoup object of scoreboard page

    Returns:
        List of tuples: (game_id, recap_url)
    """
    import re

    game_ids = set()

    # ESPN's scoreboard contains game IDs in various places in the HTML
    # We'll extract all game IDs and construct recap URLs from them
    # Pattern: gameId followed by = or / and then digits

    # Search the entire page text for game IDs
    page_text = str(soup)
    game_id_pattern = r'gameId[=/](\d+)'

    for match in re.finditer(game_id_pattern, page_text):
        game_id = match.group(1)
        game_ids.add(game_id)

    # Convert to list of (game_id, recap_url) tuples
    recap_links = []
    for game_id in sorted(game_ids):  # Sort for consistent ordering
        recap_url = f"https://www.espn.com/nfl/recap?gameId={game_id}"
        recap_links.append((game_id, recap_url))

    return recap_links


def download_recap(game_id: str, url: str, output_dir: Path) -> bool:
    """
    Download a single game recap HTML file.

    Args:
        game_id: Unique game identifier
        url: URL of the recap page
        output_dir: Directory to save the file

    Returns:
        True if successful, False otherwise
    """
    output_file = output_dir / f"{game_id}.html"

    # Skip if already downloaded
    if output_file.exists():
        print(f"  Skipping {game_id} (already exists)")
        return True

    try:
        print(f"  Downloading {game_id}...")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        # Save the HTML content
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(response.text)

        print(f"  ✓ Saved to {output_file}")

        # Be polite to ESPN's servers
        time.sleep(1)

        return True

    except Exception as e:
        handle_recoverable_error(f"Error downloading {game_id}", e)
        return False


def main():
    """Main execution function."""
    parser = create_base_parser('Fetch NFL game recaps from ESPN for a specific week')
    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)

    # Determine target week
    target_week, year, _ = setup_week_calculator(config, args.week)

    print(f"Target week: {target_week}")

    # Create output directory
    recaps_dir = create_week_directory(
        config.storage.tmp_dir,
        target_week,
        year,
        config.storage.recap_subdir
    )

    print(f"Output directory: {recaps_dir}")

    # Build scoreboard URL
    scoreboard_url = build_scoreboard_url(
        config.espn.scoreboard_url,
        year,
        target_week
    )

    # Fetch scoreboard
    try:
        soup = fetch_scoreboard(scoreboard_url)
    except Exception as e:
        handle_fatal_error("Failed to fetch ESPN scoreboard", e)

    # Extract recap links
    recap_links = extract_recap_links(soup)

    if not recap_links:
        print("Warning: No recap links found on the scoreboard page")
        print("This could mean:")
        print("  - The week hasn't been played yet")
        print("  - ESPN's page structure has changed")
        print("  - The URL is incorrect")
        sys.exit(1)

    print(f"\nFound {len(recap_links)} game recaps")

    # Download each recap
    successful = 0
    failed = 0

    for game_id, url in recap_links:
        if download_recap(game_id, url, recaps_dir):
            successful += 1
        else:
            failed += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Week: {target_week}")
    print(f"  Total games: {len(recap_links)}")
    print(f"  Successfully downloaded: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Output directory: {recaps_dir}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
