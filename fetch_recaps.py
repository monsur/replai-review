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
import yaml
from bs4 import BeautifulSoup

from week_calculator import create_week_calculator


def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def create_week_directory(base_dir: str, week: int, recap_subdir: str) -> Path:
    """
    Create directory structure for storing week's recaps.

    Args:
        base_dir: Base directory for storage
        week: NFL week number
        recap_subdir: Subdirectory name for recaps

    Returns:
        Path to the recaps directory
    """
    week_dir = Path(base_dir) / f"week_{week}"
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
    recap_links = []

    # Look for recap links - ESPN typically has them in the game cards
    # The structure is: <a href="/nfl/recap/_/gameId/401671716">Recap</a>
    # or variations of this pattern

    # Find all links containing "recap" in the href
    links = soup.find_all('a', href=True)

    for link in links:
        href = link.get('href', '')

        # Check if this is a recap link
        # ESPN uses formats like:
        # - https://www.espn.com/nfl/recap?gameId=401671817
        # - /nfl/recap/_/gameId/401671716
        if 'recap' in href and 'gameId' in href:
            # Extract game ID from URL
            # Handle both query parameter (?gameId=XXX) and path (/gameId/XXX) formats
            if 'gameId=' in href:
                # Query parameter format: ?gameId=401671817
                game_id = href.split('gameId=')[-1].split('&')[0].split('#')[0]
            elif 'gameId/' in href:
                # Path format: /gameId/401671716
                game_id = href.split('gameId/')[-1].split('/')[0]
            else:
                # Fallback
                game_id = f"game_{len(recap_links) + 1}"

            # Make absolute URL if needed
            if href.startswith('http'):
                full_url = href
            else:
                full_url = f"https://www.espn.com{href}"

            recap_links.append((game_id, full_url))

    # Remove duplicates (same game ID)
    seen = set()
    unique_links = []
    for game_id, url in recap_links:
        if game_id not in seen:
            seen.add(game_id)
            unique_links.append((game_id, url))

    return unique_links


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
        print(f"  ✗ Error downloading {game_id}: {e}")
        return False


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Fetch NFL game recaps from ESPN for a specific week'
    )
    parser.add_argument(
        '--week',
        type=int,
        help='Specific week number to fetch (overrides auto-calculation)'
    )
    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )

    args = parser.parse_args()

    # Load configuration
    try:
        config = load_config(args.config)
    except FileNotFoundError:
        print(f"Error: Configuration file '{args.config}' not found")
        sys.exit(1)

    # Determine target week
    week_calculator = create_week_calculator(
        season_start_date=config['nfl_season']['season_start_date'],
        manual_week=args.week
    )
    target_week = week_calculator.get_week()

    print(f"Target week: {target_week}")

    # Create output directory
    recaps_dir = create_week_directory(
        config['storage']['base_dir'],
        target_week,
        config['storage']['recap_subdir']
    )

    print(f"Output directory: {recaps_dir}")

    # Build scoreboard URL
    scoreboard_url = build_scoreboard_url(
        config['espn']['scoreboard_url'],
        config['nfl_season']['year'],
        target_week
    )

    # Fetch scoreboard
    try:
        soup = fetch_scoreboard(scoreboard_url)
    except Exception as e:
        print(f"Error fetching scoreboard: {e}")
        sys.exit(1)

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
