#!/usr/bin/env python3
"""
Fetch game data from ESPN APIs (no HTML scraping).

This script replaces fetch_recaps.py and process_recaps.py by getting
all data directly from ESPN's public APIs.

Output:
  tmp/YYYY-weekWW/game_data.json - Complete game data (metadata + recap text)

Usage:
    python fetch_game_data.py --week 9
    python fetch_game_data.py  # Auto-detect current week
"""

import requests
import json
import re
import argparse
import yaml
import concurrent.futures
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup
from week_calculator import create_week_calculator


def fetch_scoreboard_api(week: int, year: int = 2025, season_type: int = 2) -> dict:
    """
    Fetch scoreboard data from ESPN API.

    Args:
        week: Week number
        year: Season year
        season_type: 1=preseason, 2=regular season, 3=playoffs

    Returns:
        JSON response from API
    """
    url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
    params = {
        "seasontype": season_type,
        "week": week,
        "year": year
    }

    print(f"📡 Fetching scoreboard from ESPN API: week={week}, year={year}")
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()

    return response.json()


def fetch_game_summary_api(game_id: str) -> dict:
    """
    Fetch game summary data from ESPN API (includes recap article).

    Args:
        game_id: ESPN game ID

    Returns:
        JSON response from API
    """
    url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary"
    params = {"event": game_id}

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()

    return response.json()


def strip_html_tags(html_text: str) -> str:
    """
    Remove HTML tags and clean up text.

    Args:
        html_text: HTML text with tags

    Returns:
        Clean text without HTML tags
    """
    soup = BeautifulSoup(html_text, 'html.parser')
    text = soup.get_text(separator=' ', strip=True)
    # Clean up multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text


def format_game_date(iso_date: str) -> str:
    """
    Convert ISO date to newsletter format with proper timezone handling.

    Args:
        iso_date: ISO 8601 date string (e.g., "2025-10-30T20:15Z")

    Returns:
        Formatted date (e.g., "Thu 10/30 8:15PM ET")
    """
    # Parse ISO date (assumes UTC with 'Z' suffix)
    dt_utc = datetime.fromisoformat(iso_date.replace('Z', '+00:00'))

    # Convert to US/Eastern timezone (handles DST automatically)
    dt_et = dt_utc.astimezone(ZoneInfo('US/Eastern'))

    # Format
    day_name = dt_et.strftime('%a')  # Thu, Fri, Sun, Mon
    month_day = dt_et.strftime('%-m/%-d')  # 10/30 (no leading zeros)
    time_part = dt_et.strftime('%-I:%M%p')  # 8:15PM (no leading zero on hour)

    return f"{day_name} {month_day} {time_part} ET"


def parse_game_from_api(event: dict) -> dict:
    """
    Parse a single game from API response into newsletter format.

    Args:
        event: Single event from API response

    Returns:
        Game dictionary with all metadata fields
    """
    competition = event['competitions'][0]

    # ESPN API: competitors[0] is home, competitors[1] is away
    home = competition['competitors'][0]
    away = competition['competitors'][1]

    # Extract basic info
    game_data = {
        'game_id': event['id'],
        'away_team': away['team']['displayName'],
        'away_abbr': away['team']['abbreviation'],
        'away_score': int(away['score']),
        'home_team': home['team']['displayName'],
        'home_abbr': home['team']['abbreviation'],
        'home_score': int(home['score']),
        'game_date': format_game_date(event['date']),
        'recap_url': f"https://www.espn.com/nfl/recap?gameId={event['id']}"
    }

    # Extract records
    if 'records' in away and len(away['records']) > 0:
        game_data['away_record'] = away['records'][0]['summary']
    else:
        game_data['away_record'] = 'N/A'

    if 'records' in home and len(home['records']) > 0:
        game_data['home_record'] = home['records'][0]['summary']
    else:
        game_data['home_record'] = 'N/A'

    # Extract venue
    if 'venue' in competition and 'fullName' in competition['venue']:
        game_data['stadium'] = competition['venue']['fullName']
    else:
        game_data['stadium'] = 'N/A'

    # Extract TV network
    if 'broadcasts' in competition and len(competition['broadcasts']) > 0:
        networks = competition['broadcasts'][0].get('names', [])
        game_data['tv_network'] = networks[0] if networks else 'N/A'
    else:
        game_data['tv_network'] = 'N/A'

    return game_data


def fetch_recap_text(game_id: str) -> str:
    """
    Fetch recap article text from summary API.

    Args:
        game_id: ESPN game ID

    Returns:
        Clean recap text (HTML tags stripped)
    """
    try:
        summary_data = fetch_game_summary_api(game_id)

        # Extract article text
        if 'article' in summary_data and 'story' in summary_data['article']:
            html_text = summary_data['article']['story']
            clean_text = strip_html_tags(html_text)
            return clean_text
        else:
            print(f"  ⚠️  No article found for game {game_id}")
            return ""
    except Exception as e:
        print(f"  ❌ Error fetching recap for game {game_id}: {e}")
        return ""


def fetch_week_data(week: int, year: int = 2025) -> list:
    """
    Fetch all data for a week (metadata + recap text).

    Args:
        week: Week number
        year: Season year

    Returns:
        List of game dictionaries with metadata and recap_text
    """
    # 1. Get game IDs and metadata from scoreboard API
    scoreboard = fetch_scoreboard_api(week, year)
    games = []

    for event in scoreboard.get('events', []):
        game = parse_game_from_api(event)
        games.append(game)

    print(f"✅ Found {len(games)} games")

    # 2. Fetch recap text for each game (in parallel for speed)
    print(f"📝 Fetching recap articles...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # Create a mapping of future to game
        future_to_game = {
            executor.submit(fetch_recap_text, game['game_id']): game
            for game in games
        }

        # Collect results as they complete
        for i, future in enumerate(concurrent.futures.as_completed(future_to_game), 1):
            game = future_to_game[future]
            recap_text = future.result()
            game['recap_text'] = recap_text
            print(f"  [{i}/{len(games)}] {game['away_abbr']} @ {game['home_abbr']}")

    print(f"✅ Fetched {len(games)} recap articles")

    return games


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Fetch game data from ESPN APIs'
    )
    parser.add_argument(
        '--week',
        type=int,
        help='Week number to fetch (auto-detected if not provided)'
    )

    args = parser.parse_args()

    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    year = config['nfl_season']['year']

    # Determine week
    if args.week:
        week = args.week
    else:
        week_calc = create_week_calculator(config['nfl_season']['season_start_date'])
        week = week_calc.get_week()
        print(f"Auto-detected: Week {week}")

    # Fetch data
    print("=" * 70)
    print(f"Fetching game data for Week {week}")
    print("=" * 70)

    games = fetch_week_data(week, year)

    # Save to file
    output_dir = Path(f"tmp/{year}-week{week:02d}")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "game_data.json"

    output_data = {
        'week': week,
        'year': year,
        'fetched_at': datetime.now().isoformat(),
        'games': games
    }

    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    print()
    print("=" * 70)
    print(f"✅ Saved game data to: {output_file}")
    print("=" * 70)
    print()
    print("Game Summary:")
    for i, game in enumerate(games, 1):
        recap_len = len(game['recap_text'])
        print(f"  {i:2d}. {game['away_abbr']:3s} @ {game['home_abbr']:3s}  "
              f"{game['away_score']:2d}-{game['home_score']:2d}  "
              f"(recap: {recap_len:,} chars)")


if __name__ == "__main__":
    main()
