#!/usr/bin/env python3
"""
Script 3b: Format Newsletter HTML

This script:
1. Reads the newsletter JSON from tmp/YYYY-weekWW/newsletter.json
2. Parses and validates the JSON
3. Formats games into HTML
4. Wraps in complete HTML document
5. Saves to docs/YYYY-weekWW.html
6. Updates index.html with latest newsletter
7. Updates archive.json with newsletter metadata
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from week_calculator import create_week_calculator


def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def parse_game_datetime(game_date: str) -> datetime:
    """
    Parse game date string to datetime for sorting.

    Args:
        game_date: Date string in format "Day MM/DD H:MMAM/PM ET"
                   (e.g., "Thu 10/23 8:15PM ET")

    Returns:
        datetime object for sorting
    """
    try:
        # Extract the date and time parts
        # Format: "Day MM/DD H:MMAM/PM ET"
        parts = game_date.split()
        if len(parts) < 3:
            # If format is unexpected, return a default datetime
            return datetime.min

        # Day name (Mon, Tue, etc.) - parts[0]
        # Date (MM/DD) - parts[1]
        # Time (H:MMAM/PM) - parts[2]
        # Timezone (ET) - parts[3] (ignored for sorting within same week)

        day_of_week = parts[0].lower()
        date_str = parts[1]  # MM/DD
        time_str = parts[2]  # H:MMAM/PM

        # Map day names to sort order (Thu=0, Fri=1, Sat=2, Sun=3, Mon=4, Tue=5, Wed=6)
        day_order = {
            'thu': 0, 'thursday': 0,
            'fri': 1, 'friday': 1,
            'sat': 2, 'saturday': 2,
            'sun': 3, 'sunday': 3,
            'mon': 4, 'monday': 4,
            'tue': 5, 'tuesday': 5,
            'wed': 6, 'wednesday': 6
        }

        # Parse time (handle both 12:00PM and 12:00AM formats)
        time_upper = time_str.upper()
        # Parse the time
        if 'AM' in time_upper:
            time_part = time_upper.replace('AM', '')
            is_pm = False
        elif 'PM' in time_upper:
            time_part = time_upper.replace('PM', '')
            is_pm = True
        else:
            # Default to PM if not specified
            time_part = time_str
            is_pm = True

        # Split hours and minutes
        if ':' in time_part:
            hour_str, min_str = time_part.split(':')
            hour = int(hour_str)
            minute = int(min_str)
        else:
            hour = int(time_part)
            minute = 0

        # Convert to 24-hour format
        if is_pm and hour != 12:
            hour += 12
        elif not is_pm and hour == 12:
            hour = 0

        # Get day order (default to Sunday if not found)
        day_num = day_order.get(day_of_week, 3)

        # Parse month and day from date_str
        month_day = date_str.split('/')
        if len(month_day) == 2:
            month = int(month_day[0])
            day = int(month_day[1])
        else:
            month = 1
            day = 1

        # Create a sortable datetime (use a dummy year)
        # We'll use day_num as the primary sort key and time as secondary
        return datetime(2025, month, day, hour, minute)

    except (ValueError, IndexError, AttributeError):
        # If parsing fails, return minimum datetime to sort to beginning
        return datetime.min


def sort_games_chronologically(games: list) -> list:
    """
    Sort games in chronological order.

    Args:
        games: List of game dictionaries

    Returns:
        Sorted list of games (earliest first)
    """
    def get_sort_key(game):
        game_date = game.get('game_date', '')
        return parse_game_datetime(game_date)

    return sorted(games, key=get_sort_key)


def prepare_game_for_template(game: dict, base_url: str = "") -> dict:
    """
    Prepare a single game's data for template rendering.

    Args:
        game: Dictionary with game data from JSON
        base_url: Optional base URL for absolute image paths (for email)

    Returns:
        Dictionary with template-ready data
    """
    # Use consistent pattern: images/{TEAM_ABB}.png
    # For email, prepend base_url to make absolute URLs
    if base_url:
        away_icon = f"{base_url}/images/{game['away_abbr']}.png"
        home_icon = f"{base_url}/images/{game['home_abbr']}.png"
    else:
        away_icon = f"images/{game['away_abbr']}.png"
        home_icon = f"images/{game['home_abbr']}.png"

    # Determine winner and loser
    away_score = int(game['away_score'])
    home_score = int(game['home_score'])
    away_winner = away_score > home_score
    home_winner = home_score > away_score

    away_class = "winner" if away_winner else "loser"
    home_class = "winner" if home_winner else "loser"

    # Format badges
    badge_map = {
        'nail-biter': ('badge-nailbiter', '🎯 Nail-Biter'),
        'comeback': ('badge-comeback', '🔥 Comeback'),
        'blowout': ('badge-blowout', '💥 Blowout'),
        'upset': ('badge-upset', '⬆️ Upset'),
        'game-of-week': ('badge-game-of-week', '🏆 Game of the Week')
    }

    badges = []
    if 'badges' in game and game['badges']:
        for badge in game['badges']:
            if badge in badge_map:
                css_class, label = badge_map[badge]
                badges.append({'css_class': css_class, 'label': label})

    # Format game metadata
    meta = []
    if 'game_date' in game and game['game_date']:
        meta.append(f'📅 {game["game_date"]}')
    if 'stadium' in game and game['stadium']:
        meta.append(f'📍 {game["stadium"]}')
    if 'tv_network' in game and game['tv_network']:
        meta.append(f'📺 {game["tv_network"]}')

    return {
        'away_team': game['away_team'],
        'away_abbr': game['away_abbr'],
        'away_score': game['away_score'],
        'away_record': game.get('away_record'),
        'away_icon': away_icon,
        'away_class': away_class,
        'home_team': game['home_team'],
        'home_abbr': game['home_abbr'],
        'home_score': game['home_score'],
        'home_record': game.get('home_record'),
        'home_icon': home_icon,
        'home_class': home_class,
        'summary': game['summary'],
        'recap_url': game.get('recap_url', '#'),
        'badges': badges,
        'meta': meta
    }


def parse_json(json_content: str, base_url: str = "") -> tuple[dict, int]:
    """
    Parse JSON and prepare data for template rendering.

    Args:
        json_content: Raw JSON string
        base_url: Optional base URL for absolute image paths (for email)

    Returns:
        Tuple of (template data dict, game count)
    """
    # Clean up potential markdown code blocks
    json_str = json_content.strip()
    if json_str.startswith('```'):
        # Remove markdown code blocks
        lines = json_str.split('\n')
        # Find the actual JSON start and end
        start_idx = 1
        end_idx = len(lines) - 1
        # Skip the ```json line
        if lines[start_idx].strip().startswith('json'):
            start_idx += 1
        # Find the closing ```
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip() == '```':
                end_idx = i
                break
        json_str = '\n'.join(lines[start_idx:end_idx])

    data = json.loads(json_str)
    week = data.get('week', 'Unknown')
    games = data.get('games', [])

    print(f"Parsed {len(games)} games from JSON")

    # Sort games chronologically (Thursday first, Monday last)
    games = sort_games_chronologically(games)
    print("Games sorted chronologically")

    # Prepare games for template
    prepared_games = [prepare_game_for_template(game, base_url) for game in games]

    # Calculate stats
    game_count = len(games)
    upset_count = sum(1 for game in games if 'badges' in game and 'upset' in game.get('badges', []))

    # Prepare template data
    template_data = {
        'week': week,
        'game_count': game_count,
        'upset_count': upset_count,
        'games': prepared_games
    }

    return template_data, game_count


def render_newsletter(template_data: dict, template_file: str = "newsletter_template.html") -> str:
    """
    Render newsletter using Jinja2 template.

    Args:
        template_data: Dictionary with template variables
        template_file: Path to template file

    Returns:
        Rendered HTML
    """
    # Set up Jinja2 environment
    env = Environment(
        loader=FileSystemLoader('.'),
        autoescape=select_autoescape(['html'])
    )

    # Load template
    template = env.get_template(template_file)

    # Render template with data
    return template.render(**template_data)


def update_index_html(docs_dir: Path, newsletter_filename: str, year: int, week: int) -> None:
    """
    Update index.html to point to the latest newsletter if it's newer.

    Args:
        docs_dir: Documentation directory path
        newsletter_filename: New newsletter filename (e.g., "2025-week09.html")
        year: Year of the new newsletter
        week: Week number of the new newsletter
    """
    index_file = docs_dir / "index.html"

    if not index_file.exists():
        print(f"Warning: {index_file} not found, skipping index update")
        return

    # Read current index.html
    with open(index_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract current newsletter filename from iframe src
    match = re.search(r'<iframe\s+[^>]*src="([^"]+)"', content)

    if not match:
        print("Warning: Could not find iframe in index.html, skipping update")
        return

    current_filename = match.group(1)

    # Extract year and week from current filename (format: YYYY-weekWW.html)
    current_match = re.match(r'(\d{4})-week(\d{2})\.html', current_filename)

    if not current_match:
        print(f"Warning: Current iframe src '{current_filename}' doesn't match expected format")
        return

    current_year = int(current_match.group(1))
    current_week = int(current_match.group(2))

    # Check if new newsletter is newer
    if year > current_year or (year == current_year and week > current_week):
        # Update the iframe src
        updated_content = content.replace(
            f'src="{current_filename}"',
            f'src="{newsletter_filename}"'
        )

        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(updated_content)

        print(f"Updated index.html: {current_filename} → {newsletter_filename}")
    else:
        print(f"Index.html already points to week {current_week}, not updating")


def update_archive_json(docs_dir: Path, year: int, week: int,
                        newsletter_filename: str, game_count: int) -> None:
    """
    Update archive.json with the new newsletter information.

    Args:
        docs_dir: Documentation directory path
        year: Year of the newsletter
        week: Week number
        newsletter_filename: Filename of the newsletter
        game_count: Number of games in the newsletter
    """
    archive_file = docs_dir / "archive.json"

    # Read existing archive or create new structure
    if archive_file.exists():
        with open(archive_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = {"latest": {}, "weeks": []}

    # Create new entry
    new_entry = {
        "year": year,
        "week": week,
        "filename": newsletter_filename,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "games": game_count
    }

    # Update latest
    data["latest"] = {
        "year": year,
        "week": week,
        "filename": newsletter_filename
    }

    # Check if this week already exists in archive
    existing_index = None
    for i, entry in enumerate(data["weeks"]):
        if entry["year"] == year and entry["week"] == week:
            existing_index = i
            break

    if existing_index is not None:
        # Update existing entry
        data["weeks"][existing_index] = new_entry
        print(f"Updated existing archive entry for week {week}")
    else:
        # Add new entry at the beginning (most recent first)
        data["weeks"].insert(0, new_entry)
        print(f"Added new archive entry for week {week}")

    # Save archive.json
    with open(archive_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    print(f"Archive updated: {archive_file}")


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Format NFL newsletter from JSON to HTML'
    )
    parser.add_argument(
        '--week',
        type=int,
        help='Specific week number to process (overrides auto-calculation)'
    )
    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )
    parser.add_argument(
        '--json-file',
        help='Path to JSON file (overrides automatic path resolution)'
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

    print(f"Formatting newsletter for week: {target_week}")

    # Determine JSON file path
    year = config['nfl_season']['year']
    tmp_week_dir = Path(config['storage']['tmp_dir']) / f"{year}-week{target_week:02d}"

    if args.json_file:
        json_file = Path(args.json_file)
    else:
        json_file = tmp_week_dir / "newsletter.json"

    print(f"Input JSON: {json_file}")

    # Read JSON file
    if not json_file.exists():
        print(f"Error: JSON file not found: {json_file}")
        print(f"Have you run generate_json.py first?")
        sys.exit(1)

    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            json_content = f.read()
    except Exception as e:
        print(f"Error reading JSON file: {e}")
        sys.exit(1)

    # Get GitHub Pages URL for absolute image paths (required for email)
    github_pages_url = config.get('github_pages_url', '').rstrip('/')
    if not github_pages_url:
        print("Warning: github_pages_url not configured in config.yaml")
        print("Images will use relative paths (won't work in email)")

    # Parse JSON and prepare template data with absolute URLs
    try:
        template_data, game_count = parse_json(json_content, base_url=github_pages_url)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        print(f"JSON file: {json_file}")
        print(f"Error at line {e.lineno}, column {e.colno}")

        # Save debug file to tmp directory
        tmp_week_dir.mkdir(parents=True, exist_ok=True)
        debug_file = tmp_week_dir / "newsletter_debug.json"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(json_content)
        print(f"Raw JSON saved to {debug_file} for debugging")

        sys.exit(1)
    except Exception as e:
        print(f"Error parsing newsletter data: {e}")

        # Save debug file to tmp directory
        tmp_week_dir.mkdir(parents=True, exist_ok=True)
        debug_file = tmp_week_dir / "newsletter_debug.json"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(json_content)
        print(f"Raw JSON saved to {debug_file} for debugging")

        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Render newsletter using template (email-friendly, works for both web and email)
    try:
        newsletter_html = render_newsletter(template_data, "newsletter_template.html")
        print("Newsletter rendered successfully")
    except Exception as e:
        print(f"Error rendering newsletter: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Save to docs directory
    docs_dir = Path(config['storage']['docs_dir'])
    docs_dir.mkdir(parents=True, exist_ok=True)

    newsletter_filename = f"{year}-week{target_week:02d}.html"
    output_file = docs_dir / newsletter_filename

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(newsletter_html)

    print(f"Newsletter saved: {output_file}")

    # Update index.html to point to latest newsletter
    update_index_html(docs_dir, newsletter_filename, year, target_week)

    # Update archive.json with new newsletter
    update_archive_json(docs_dir, year, target_week, newsletter_filename, game_count)

    # Summary
    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Week: {target_week}")
    print(f"  Games: {game_count}")
    print(f"  Newsletter file: {output_file}")
    print(f"  File size: {output_file.stat().st_size:,} bytes")
    if github_pages_url:
        print(f"  Image URLs: Absolute ({github_pages_url}/images/...)")
    else:
        print(f"  Image URLs: Relative (images/...)")
    print(f"{'='*60}")
    print(f"\nNewsletter formatted successfully!")
    print(f"Open in browser: file://{output_file.absolute()}")


if __name__ == "__main__":
    main()
