#!/usr/bin/env python3
"""
Stage 1: Fetch Games from ESPN API

This script:
1. Accepts --date (required) and --type (optional, default: day)
2. Calculates week number from date
3. Fetches all games for that week from ESPN API
4. Filters games by date (if type=day) or keeps all (if type=week)
5. Saves to tmp/YYYY-weekWW/YYYYMMDD/games.json (day) or tmp/YYYY-weekWW/games.json (week)
6. Exits with code 0 (success), 1 (no games), or 2 (error)

Usage:
    python3 fetch_games.py --date 20251109 --type day
    python3 fetch_games.py --date 20251109 --type week
"""

import argparse
import json
import sys
import re
import concurrent.futures
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
import yaml
from bs4 import BeautifulSoup

from week_calculator import DateBasedWeekCalculator
from stage_utils import (
    get_work_directory,
    get_games_file_path,
    parse_date,
    validate_type,
)


def fetch_scoreboard_api(week: int, year: int, season_type: int = 2) -> dict:
    """
    Fetch scoreboard data from ESPN API.

    Args:
        week: Week number
        year: Season year
        season_type: 1=preseason, 2=regular season, 3=playoffs

    Returns:
        JSON response from API

    Raises:
        requests.RequestException: If API call fails
    """
    url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
    params = {
        "seasontype": season_type,
        "week": week,
        "year": year
    }

    print(f"📡 Fetching scoreboard: week={week}, year={year}")
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

    Raises:
        requests.RequestException: If API call fails
    """
    url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary"
    params = {"event": game_id}

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()

    return response.json()


def strip_html_tags(html_text: str) -> str:
    """Remove HTML tags and clean up text."""
    soup = BeautifulSoup(html_text, 'html.parser')
    text = soup.get_text(separator=' ', strip=True)
    # Clean up multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text


def format_game_date(iso_date: str) -> str:
    """
    Convert ISO date to newsletter display format.

    Args:
        iso_date: ISO 8601 date string (e.g., "2025-10-30T20:15Z")

    Returns:
        Formatted date (e.g., "Thu 10/30 8:15PM ET")
    """
    try:
        dt_utc = datetime.fromisoformat(iso_date.replace('Z', '+00:00'))

        # Try to use ZoneInfo, fall back to hardcoded offset if tzdata not available
        try:
            dt_et = dt_utc.astimezone(ZoneInfo('US/Eastern'))
        except Exception:
            # Fallback: US/Eastern is UTC-4 (EDT) during game season
            from datetime import timedelta, timezone
            eastern_offset = timedelta(hours=-4)
            dt_et = dt_utc.astimezone(timezone(eastern_offset))

        day_name = dt_et.strftime('%a')
        month_day = dt_et.strftime('%-m/%-d')
        time_part = dt_et.strftime('%-I:%M%p')

        return f"{day_name} {month_day} {time_part} ET"
    except (ValueError, KeyError) as e:
        raise ValueError(f"Invalid ISO date format: {iso_date}") from e


def parse_game_from_api(event: dict) -> dict:
    """
    Parse a single game from API response.

    Args:
        event: Single event from API response

    Returns:
        Game dictionary with all metadata fields
    """
    competition = event['competitions'][0]

    # ESPN API: competitors[0] is home, competitors[1] is away
    home = competition['competitors'][0]
    away = competition['competitors'][1]

    game_data = {
        'game_id': event['id'],
        'away_team': away['team']['displayName'],
        'away_abbr': away['team']['abbreviation'],
        'away_score': int(away['score']),
        'home_team': home['team']['displayName'],
        'home_abbr': home['team']['abbreviation'],
        'home_score': int(home['score']),
        'game_date_iso': event['date'],  # Keep ISO format for later processing
        'game_date_display': format_game_date(event['date']),
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


def filter_games_by_date(games: list, target_date: str) -> list:
    """
    Filter games to only those played on target_date.

    Args:
        games: List of games with game_date_iso field
        target_date: Target date in YYYYMMDD format

    Returns:
        Filtered list of games
    """
    target_dt = datetime.strptime(target_date, "%Y%m%d")

    filtered = []
    for game in games:
        # Parse ISO date and convert to Eastern Time
        game_dt_utc = datetime.fromisoformat(game['game_date_iso'].replace('Z', '+00:00'))

        # Try to use ZoneInfo, fall back if not available
        try:
            game_dt_et = game_dt_utc.astimezone(ZoneInfo('US/Eastern'))
        except Exception:
            # Fallback: assume UTC-4 (EDT)
            from datetime import timedelta, timezone
            eastern_offset = timedelta(hours=-4)
            game_dt_et = game_dt_utc.astimezone(timezone(eastern_offset))

        # Compare dates (not times)
        if game_dt_et.date() == target_dt.date():
            filtered.append(game)

    return filtered


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Stage 1: Fetch games from ESPN API'
    )
    parser.add_argument(
        '--date',
        type=str,
        required=True,
        help='Date in YYYYMMDD format (e.g., 20251109)'
    )
    parser.add_argument(
        '--type',
        type=str,
        default='day',
        help='Newsletter type: day or week (default: day)'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='Path to config file'
    )

    args = parser.parse_args()

    try:
        # Validate inputs
        date_str = args.date
        parse_date(date_str)  # Validates format

        type_str = validate_type(args.type)

        # Load config
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)

        year = config['nfl_season']['year']
        season_start = config['nfl_season']['season_start_date']

        # Calculate week from date
        week_calc = DateBasedWeekCalculator(season_start)
        target_dt = datetime.strptime(date_str, "%Y%m%d")
        week = week_calc.get_week_for_date(target_dt)

        print("=" * 70)
        print("Stage 1: Fetch Games")
        print("=" * 70)
        print(f"Date: {date_str}, Type: {type_str}, Week: {week}")
        print()

        # Fetch all games for the week
        scoreboard = fetch_scoreboard_api(week, year)
        all_games = []

        for event in scoreboard.get('events', []):
            game = parse_game_from_api(event)
            all_games.append(game)

        print(f"✅ Found {len(all_games)} games in week {week}")

        # Filter by type
        if type_str == 'day':
            games = filter_games_by_date(all_games, date_str)
            print(f"✅ Filtered to {len(games)} games on {date_str}")
        else:  # type_str == 'week'
            games = all_games
            print(f"✅ Including all {len(games)} games from week")

        print()

        # Check if any games found
        if len(games) == 0:
            print(f"ℹ️  No games found for {date_str} (type: {type_str})")
            sys.exit(1)  # Exit code 1: no games (expected)

        # Fetch recap text for each game (in parallel for speed)
        print("📝 Fetching recap articles...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_game = {
                executor.submit(fetch_recap_text, game['game_id']): game
                for game in games
            }

            for i, future in enumerate(concurrent.futures.as_completed(future_to_game), 1):
                game = future_to_game[future]
                recap_text = future.result()
                game['recap_text'] = recap_text
                print(f"  [{i}/{len(games)}] {game['away_abbr']} @ {game['home_abbr']}")

        print(f"✅ Fetched {len(games)} recap articles")
        print()

        # Prepare output
        output_data = {
            'metadata': {
                'date': date_str,
                'type': type_str,
                'week': week,
                'year': year,
                'fetched_at': datetime.now(ZoneInfo('UTC')).isoformat()
            },
            'games': games
        }

        # Save to file
        work_dir = get_work_directory(year, week, date_str, type_str)
        work_dir.mkdir(parents=True, exist_ok=True)
        output_file = get_games_file_path(year, week, date_str, type_str)

        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)

        print("=" * 70)
        print(f"✅ Saved to: {output_file}")
        print("=" * 70)

        sys.exit(0)  # Success

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(2)  # Exit code 2: error


if __name__ == "__main__":
    main()
