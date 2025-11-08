#!/usr/bin/env python3
"""
Stage 3: Publish Newsletter

This script:
1. Reads newsletter.json from Stage 2 (generate_newsletter.py)
2. Renders HTML using Jinja2 template
3. Saves HTML to docs/ directory with appropriate filename
4. Updates archive.json with newsletter metadata
5. Regenerates index.html

Usage:
    python3 publish_newsletter.py --input tmp/2025-week09/20251109/newsletter.json
    python3 publish_newsletter.py --input tmp/2025-week09/newsletter.json
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from stage_utils import get_output_html_filename


def load_newsletter_file(newsletter_path: Path) -> dict:
    """
    Load and validate newsletter.json from Stage 2.

    Args:
        newsletter_path: Path to newsletter.json file

    Returns:
        Dictionary with metadata and games

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is invalid JSON
        ValueError: If structure is invalid
    """
    if not newsletter_path.exists():
        raise FileNotFoundError(f"Newsletter file not found: {newsletter_path}")

    with open(newsletter_path, 'r') as f:
        data = json.load(f)

    # Validate structure
    if 'metadata' not in data:
        raise ValueError("Missing 'metadata' in newsletter.json")
    if 'games' not in data:
        raise ValueError("Missing 'games' in newsletter.json")

    return data


def prepare_game_for_template(game: dict) -> dict:
    """
    Prepare a single game's data for template rendering.

    Args:
        game: Dictionary with game data from JSON

    Returns:
        Dictionary with template-ready data
    """
    # Team icons
    away_icon = f"images/{game['away_abbr']}.png"
    home_icon = f"images/{game['home_abbr']}.png"

    # Determine winner/loser
    away_score = int(game['away_score'])
    home_score = int(game['home_score'])

    if away_score > home_score:
        away_class = "winner"
        home_class = "loser"
    elif home_score > away_score:
        away_class = "loser"
        home_class = "winner"
    else:
        away_class = "tie"
        home_class = "tie"

    # Format badges
    badge_map = {
        'upset': ('badge-upset', '⬆️ Upset'),
        'nail-biter': ('badge-nailbiter', '🎯 Nail-Biter'),
        'comeback': ('badge-comeback', '🔥 Comeback'),
        'blowout': ('badge-blowout', '💥 Blowout'),
        'game-of-week': ('badge-game-of-week', '🏆 Game of the Week')
    }

    badges = []
    for badge in game.get('badges', []):
        if badge in badge_map:
            css_class, label = badge_map[badge]
            badges.append({'css_class': css_class, 'label': label})

    # Format game metadata
    meta = []
    if game.get('game_date_display'):
        meta.append(f"📅 {game['game_date_display']}")
    if game.get('stadium'):
        meta.append(f"📍 {game['stadium']}")
    if game.get('tv_network'):
        meta.append(f"📺 {game['tv_network']}")

    return {
        'away_team': game['away_team'],
        'away_abbr': game['away_abbr'],
        'away_score': game['away_score'],
        'away_record': game.get('away_record', 'N/A'),
        'away_icon': away_icon,
        'away_class': away_class,
        'home_team': game['home_team'],
        'home_abbr': game['home_abbr'],
        'home_score': game['home_score'],
        'home_record': game.get('home_record', 'N/A'),
        'home_icon': home_icon,
        'home_class': home_class,
        'summary': game.get('summary', ''),
        'recap_url': game.get('recap_url', '#'),
        'badges': badges,
        'meta': meta
    }


def render_html(newsletter: dict, template_file: str) -> str:
    """
    Render newsletter HTML using Jinja2 template.

    Args:
        newsletter: Newsletter data with metadata and games
        template_file: Path to HTML template

    Returns:
        Rendered HTML string
    """
    metadata = newsletter['metadata']
    games = newsletter['games']

    # Prepare games for display
    prepared_games = [prepare_game_for_template(game) for game in games]

    # Sort games chronologically by date
    def game_sort_key(game):
        # Extract day of week from game_date_display
        day_order = {'Thu': 0, 'Fri': 1, 'Sat': 2, 'Sun': 3, 'Mon': 4, 'Tue': 5, 'Wed': 6}
        date_str = game.get('game_date_display', '')
        day = date_str.split()[0] if date_str else 'Sun'
        return day_order.get(day, 3)

    prepared_games.sort(key=game_sort_key)

    # Determine newsletter title
    week = metadata['week']
    type_val = metadata['type']

    if type_val == 'week':
        title = f"Week {week}"
    else:  # day mode
        date_str = metadata['date']
        dt = datetime.strptime(date_str, "%Y%m%d")
        day_name = dt.strftime("%A")  # "Sunday", "Monday", etc.
        title = f"Week {week} {day_name}"

    # Count special game types
    upset_count = sum(1 for g in games if 'upset' in g.get('badges', []))

    # Load template
    template_dir = Path(template_file).parent
    template_name = Path(template_file).name

    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(['html'])
    )
    template = env.get_template(template_name)

    # Render
    html = template.render(
        title=title,
        week=week,
        game_count=len(games),
        upset_count=upset_count,
        games=prepared_games,
        metadata=metadata
    )

    return html


def update_archive(archive_path: Path, metadata: dict, filename: str, game_count: int):
    """
    Update archive.json with new newsletter entry.

    Creates nested structure grouped by week.
    """
    # Load existing archive or create new
    if archive_path.exists():
        with open(archive_path, 'r') as f:
            archive = json.load(f)
    else:
        archive = {'newsletters': []}

    week = metadata['week']
    year = metadata['year']
    date = metadata['date']
    type_val = metadata['type']

    # Find or create week entry
    week_entry = None
    for entry in archive['newsletters']:
        if entry['week'] == week and entry['year'] == year:
            week_entry = entry
            break

    if week_entry is None:
        week_entry = {
            'week': week,
            'year': year,
            'entries': []
        }
        archive['newsletters'].append(week_entry)

    # Create new entry
    if type_val == 'day':
        dt = datetime.strptime(date, "%Y%m%d")
        day_name = dt.strftime("%A")  # "Sunday"
        new_entry = {
            'type': 'day',
            'day': day_name,
            'date': f"{dt.year}-{dt.month:02d}-{dt.day:02d}",
            'filename': filename,
            'game_count': game_count,
            'generated_at': metadata.get('generated_at', datetime.now().isoformat())
        }
    else:  # week mode
        new_entry = {
            'type': 'week',
            'filename': filename,
            'game_count': game_count,
            'generated_at': metadata.get('generated_at', datetime.now().isoformat())
        }

    # Remove existing entry for same type/day if exists
    week_entry['entries'] = [
        e for e in week_entry['entries']
        if not (e['type'] == type_val and e.get('day') == new_entry.get('day'))
    ]

    # Add new entry
    week_entry['entries'].append(new_entry)

    # Sort entries: day entries by day of week, then week entries
    day_order = {'Thursday': 0, 'Friday': 1, 'Saturday': 2, 'Sunday': 3, 'Monday': 4, 'Tuesday': 5, 'Wednesday': 6}

    def entry_sort_key(e):
        if e['type'] == 'day':
            return (0, day_order.get(e['day'], 99))
        else:
            return (1, 0)

    week_entry['entries'].sort(key=entry_sort_key)

    # Sort weeks in descending order (most recent first)
    archive['newsletters'].sort(key=lambda w: (w['year'], w['week']), reverse=True)

    # Save
    with open(archive_path, 'w') as f:
        json.dump(archive, f, indent=2)


def generate_index_html(archive_path: Path, docs_dir: Path) -> None:
    """
    Regenerate index.html from archive.json.
    """
    with open(archive_path, 'r') as f:
        archive = json.load(f)

    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ReplAI Review - NFL Newsletter Archive</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 40px 20px;
        }

        .container {
            max-width: 900px;
            margin: 0 auto;
        }

        .header {
            text-align: center;
            color: white;
            margin-bottom: 50px;
        }

        .header h1 {
            font-size: 3em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }

        .header p {
            font-size: 1.2em;
            opacity: 0.9;
        }

        .week-section {
            background: white;
            padding: 30px;
            margin-bottom: 25px;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            transition: transform 0.3s ease;
        }

        .week-section:hover {
            transform: translateY(-2px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.3);
        }

        .week-title {
            font-size: 1.8em;
            color: #667eea;
            margin-bottom: 20px;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }

        .newsletter-list {
            list-style: none;
        }

        .newsletter-item {
            padding: 12px 0;
            border-bottom: 1px solid #f0f0f0;
        }

        .newsletter-item:last-child {
            border-bottom: none;
        }

        .newsletter-link {
            display: flex;
            justify-content: space-between;
            align-items: center;
            text-decoration: none;
            color: #667eea;
            font-weight: 500;
            transition: color 0.3s ease;
            padding: 8px 0;
        }

        .newsletter-link:hover {
            color: #764ba2;
        }

        .game-count {
            background: #f0f0f0;
            color: #666;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.9em;
            white-space: nowrap;
            margin-left: 15px;
        }

        @media (max-width: 600px) {
            .header h1 {
                font-size: 2em;
            }

            .week-section {
                padding: 20px;
            }

            .newsletter-link {
                flex-direction: column;
                align-items: flex-start;
            }

            .game-count {
                margin-left: 0;
                margin-top: 8px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏈 ReplAI Review</h1>
            <p>AI-Powered NFL Newsletter Archive</p>
        </div>
"""

    for week_entry in archive['newsletters']:
        week = week_entry['week']
        year = week_entry['year']

        html += f"""        <div class="week-section">
            <div class="week-title">Week {week} - {year}</div>
            <ul class="newsletter-list">
"""

        for entry in week_entry['entries']:
            filename = entry['filename']
            game_count = entry['game_count']

            if entry['type'] == 'day':
                day = entry['day']
                date = entry['date']
                label = f"{day}, {date}"
            else:
                label = "Full Week"

            html += f"""                <li class="newsletter-item">
                    <a href="{filename}" class="newsletter-link">
                        <span>{label}</span>
                        <span class="game-count">{game_count} game{'s' if game_count != 1 else ''}</span>
                    </a>
                </li>
"""

        html += """            </ul>
        </div>
"""

    html += """    </div>
</body>
</html>
"""

    index_path = docs_dir / "index.html"
    with open(index_path, 'w') as f:
        f.write(html)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Stage 3: Publish newsletter'
    )
    parser.add_argument(
        '--input',
        type=str,
        required=True,
        help='Path to newsletter.json file from Stage 2'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='Path to config file'
    )

    args = parser.parse_args()

    try:
        input_path = Path(args.input)

        print("=" * 70)
        print("Stage 3: Publish Newsletter")
        print("=" * 70)
        print()

        # Load config
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)

        docs_dir = Path(config['storage']['docs_dir'])
        docs_dir.mkdir(parents=True, exist_ok=True)

        # Load newsletter
        print(f"📖 Loading: {input_path}")
        newsletter = load_newsletter_file(input_path)

        metadata = newsletter['metadata']
        game_count = len(newsletter['games'])

        print(f"✅ Loaded newsletter")
        print(f"   Date: {metadata['date']}, Type: {metadata['type']}, Week: {metadata['week']}")
        print(f"   Games: {game_count}")
        print()

        # Determine output filename
        output_filename = get_output_html_filename(metadata)
        output_path = docs_dir / output_filename

        print(f"📝 Output: {output_filename}")

        # Render HTML
        template_file = config.get('newsletter_template_file', 'newsletter_template.html')
        print(f"🎨 Rendering with template: {template_file}")

        html = render_html(newsletter, template_file)

        # Save HTML
        with open(output_path, 'w') as f:
            f.write(html)

        print(f"✅ Saved HTML: {output_path}")
        print()

        # Update archive
        archive_path = docs_dir / "archive.json"
        print(f"📚 Updating archive: {archive_path}")
        update_archive(archive_path, metadata, output_filename, game_count)
        print(f"✅ Archive updated")

        # Update index
        print(f"🏠 Regenerating index.html")
        generate_index_html(archive_path, docs_dir)
        print(f"✅ Index updated")
        print()

        print("=" * 70)
        print("✅ Newsletter published successfully!")
        print("=" * 70)

        sys.exit(0)

    except FileNotFoundError as e:
        print(f"❌ File not found: {e}", file=sys.stderr)
        sys.exit(2)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()
