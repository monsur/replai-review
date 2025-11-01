#!/usr/bin/env python3
"""
Script 3: Generate Newsletter

This script:
1. Reads the combined recap file from week_X/combined.html
2. Sends it to the configured AI provider with a prompt
3. Receives back a formatted HTML newsletter
4. Saves the newsletter to week_X/newsletter.html
"""

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

from ai_providers import create_ai_provider
from week_calculator import create_week_calculator


def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def load_prompt(prompt_file: str) -> str:
    """
    Load the newsletter generation prompt from a text file.

    Args:
        prompt_file: Path to the prompt file

    Returns:
        Prompt text as a string
    """
    with open(prompt_file, 'r', encoding='utf-8') as f:
        return f.read().strip()


def read_combined_recaps(combined_file: Path) -> str:
    """
    Read the combined recaps file.

    Args:
        combined_file: Path to the combined recaps file

    Returns:
        Content of the file as a string
    """
    if not combined_file.exists():
        raise FileNotFoundError(
            f"Combined recaps file not found: {combined_file}\n"
            f"Have you run process_recaps.py first?"
        )

    with open(combined_file, 'r', encoding='utf-8') as f:
        return f.read()


def format_game_html(game: dict) -> str:
    """
    Format a single game's data into HTML.

    Args:
        game: Dictionary with game data

    Returns:
        HTML string for the game
    """
    # Use consistent pattern: images/{TEAM_ABB}.png
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
    badges_html = ""
    if 'badges' in game and game['badges']:
        badge_items = []
        badge_map = {
            'nail-biter': ('badge-nailbiter', '🎯 Nail-Biter'),
            'comeback': ('badge-comeback', '🔥 Comeback'),
            'blowout': ('badge-blowout', '💥 Blowout'),
            'upset': ('badge-upset', '⬆️ Upset'),
            'game-of-week': ('badge-game-of-week', '🏆 Game of the Week')
        }
        for badge in game['badges']:
            if badge in badge_map:
                css_class, label = badge_map[badge]
                badge_items.append(f'<span class="badge {css_class}">{label}</span>')

        if badge_items:
            badges_html = f"""
            <div class="game-badges">
                {' '.join(badge_items)}
            </div>"""

    # Format game metadata
    game_meta_items = []
    if 'game_date' in game and game['game_date']:
        game_meta_items.append(f'<span>📅 {game["game_date"]}</span>')
    if 'stadium' in game and game['stadium']:
        game_meta_items.append(f'<span>📍 {game["stadium"]}</span>')
    if 'tv_network' in game and game['tv_network']:
        game_meta_items.append(f'<span>📺 {game["tv_network"]}</span>')

    game_meta_html = ""
    if game_meta_items:
        game_meta_html = f"""
                <div class="game-meta">
                    {' '.join(game_meta_items)}
                </div>"""

    # Format team records
    away_record = f'<div class="team-record">({game["away_record"]})</div>' if 'away_record' in game and game['away_record'] else ''
    home_record = f'<div class="team-record">({game["home_record"]})</div>' if 'home_record' in game and game['home_record'] else ''

    return f"""        <article class="game">{badges_html}
            <div class="game-header">{game_meta_html}

                <div class="matchup">
                    <div class="team-section {away_class}">
                        <div class="team-logo-container">
                            <img src="{away_icon}" alt="{game['away_team']}" class="team-icon">
                        </div>
                        <div class="team-info">
                            <div class="team-name">{game['away_team']}</div>
                            {away_record}
                        </div>
                        <div class="score">{game['away_score']}</div>
                    </div>

                    <div class="vs-divider">
                        <span class="at-symbol">@</span>
                        <div class="score-divider"></div>
                    </div>

                    <div class="team-section {home_class}">
                        <div class="team-logo-container">
                            <img src="{home_icon}" alt="{game['home_team']}" class="team-icon">
                        </div>
                        <div class="team-info">
                            <div class="team-name">{game['home_team']}</div>
                            {home_record}
                        </div>
                        <div class="score">{game['home_score']}</div>
                    </div>
                </div>
            </div>

            <div class="summary">
                {game['summary']}
            </div>

            <div class="game-footer">
                <a href="{game.get('recap_url', '#')}" class="recap-link" target="_blank" rel="noopener noreferrer">
                    Read Full Recap
                </a>
            </div>
        </article>"""


def generate_newsletter(
    ai_provider,
    prompt: str,
    recap_content: str,
    week: int,
    output_dir: Path
) -> str:
    """
    Generate newsletter using AI provider.

    Args:
        ai_provider: AIProvider instance
        prompt: System prompt for the AI
        recap_content: Combined recap content
        week: Week number
        output_dir: Output directory path

    Returns:
        Generated newsletter HTML
    """
    print("Generating newsletter with AI...")
    print(f"Input size: {len(recap_content):,} characters")

    # Create the user message
    user_message = f"""
Here are the NFL game recaps from this week. Please generate a newsletter following the guidelines in the system prompt.

GAME RECAPS:
{recap_content}
"""

    # Generate the newsletter JSON
    newsletter_json = ai_provider.generate(prompt, user_message)

    print(f"Generated JSON: {len(newsletter_json):,} characters")

    # Save raw JSON response to output directory
    json_output_file = output_dir / f"newsletter_week_{week}.json"
    with open(json_output_file, 'w', encoding='utf-8') as f:
        f.write(newsletter_json)
    print(f"Raw JSON saved to: {json_output_file}")

    # Parse JSON response
    try:
        # Clean up potential markdown code blocks
        json_str = newsletter_json.strip()
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

        # Format games into HTML
        games_html = '\n\n'.join([format_game_html(game) for game in games])

        # Calculate game count and other stats
        game_count = len(games)

        # Count upsets (games with upset badge)
        upset_count = sum(1 for game in games if 'badges' in game and 'upset' in game.get('badges', []))

        # Create complete newsletter HTML with enhanced header
        newsletter_html = f"""    <header class="newsletter-header">
        <h1 class="newsletter-title">🏈 ReplAI Review</h1>
        <div class="newsletter-subtitle">Week {week} - 2025 NFL Season</div>
        <div class="newsletter-meta">
            <span>🎮 {game_count} Games</span>
            <span>⭐ {upset_count} Upsets</span>
        </div>
    </header>

    <main class="games-container">
{games_html}
    </main>"""

        return newsletter_html

    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        # Save the raw JSON for debugging
        debug_file = Path('newsletter_debug.json')
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(newsletter_json)
        print(f"Raw JSON saved to {debug_file} for debugging")
        print(f"Response preview: {newsletter_json[:500]}...")
        sys.exit(1)
    except Exception as e:
        print(f"Error formatting newsletter: {e}")
        sys.exit(1)


def update_index_html(web_dir: Path, newsletter_filename: str, year: int, week: int) -> None:
    """
    Update index.html to point to the latest newsletter if it's newer.

    Args:
        web_dir: Web directory path
        newsletter_filename: New newsletter filename (e.g., "2025-week09.html")
        year: Year of the new newsletter
        week: Week number of the new newsletter
    """
    index_file = web_dir / "index.html"

    if not index_file.exists():
        print(f"Warning: {index_file} not found, skipping index update")
        return

    # Read current index.html
    with open(index_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract current newsletter filename from iframe src
    match = re.search(r'<iframe\s+src="([^"]+)"', content)

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
            f'<iframe src="{current_filename}"',
            f'<iframe src="{newsletter_filename}"'
        )

        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(updated_content)

        print(f"Updated index.html: {current_filename} → {newsletter_filename}")
    else:
        print(f"Index.html already points to week {current_week}, not updating")


def wrap_newsletter_html(newsletter_content: str, week: int) -> str:
    """
    Wrap the AI-generated newsletter in a complete HTML document.

    Args:
        newsletter_content: The newsletter content from AI
        week: NFL week number

    Returns:
        Complete HTML document
    """
    # Check if the AI already provided a complete HTML document
    if newsletter_content.strip().lower().startswith('<!doctype html') or \
       newsletter_content.strip().lower().startswith('<html'):
        return newsletter_content

    # Otherwise, wrap it in a proper HTML structure
    wrapped = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ReplAI Review - Week {week}</title>
    <style>
        /* CSS Variables for Theme */
        :root {{
            --nfl-navy: #013369;
            --nfl-red: #D50A0A;
            --nfl-green: #00B140;
            --background: #f8f9fa;
            --card-bg: #ffffff;
            --text-primary: #1a1a1a;
            --text-secondary: #6c757d;
            --border-light: #e9ecef;
            --accent-gold: #FFB612;
            --winner-color: #00B140;
            --loser-color: #999;
        }}

        /* Dark Mode */
        @media (prefers-color-scheme: dark) {{
            :root {{
                --background: #1a1a1a;
                --card-bg: #2d2d2d;
                --text-primary: #e0e0e0;
                --text-secondary: #a0a0a0;
                --border-light: #404040;
                --nfl-navy: #4A90E2;
            }}
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', 'Helvetica Neue', Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 32px 24px;
            background-color: var(--background);
            color: var(--text-primary);
            line-height: 1.7;
        }}

        /* Enhanced Header */
        .newsletter-header {{
            text-align: center;
            margin-bottom: 48px;
            padding-bottom: 32px;
            border-bottom: 4px solid var(--nfl-navy);
            background: linear-gradient(135deg, var(--nfl-navy) 0%, #024a9c 100%);
            color: white;
            padding: 40px 24px;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(1, 51, 105, 0.2);
        }}

        .newsletter-title {{
            font-size: 3em;
            font-weight: 800;
            margin-bottom: 8px;
            letter-spacing: -0.02em;
        }}

        .newsletter-subtitle {{
            font-size: 1.2em;
            opacity: 0.95;
            font-weight: 400;
            margin-bottom: 8px;
        }}

        .newsletter-meta {{
            font-size: 0.95em;
            opacity: 0.85;
            display: flex;
            justify-content: center;
            gap: 24px;
            flex-wrap: wrap;
            margin-top: 16px;
        }}

        .newsletter-meta span {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}

        /* Game Cards */
        .games-container {{
            display: grid;
            grid-template-columns: 1fr;
            gap: 32px;
        }}

        .game {{
            background-color: var(--card-bg);
            padding: 32px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }}

        .game:hover {{
            transform: translateY(-4px);
            box-shadow: 0 8px 24px rgba(0,0,0,0.12);
        }}

        /* Game Badges */
        .game-badges {{
            display: flex;
            gap: 8px;
            margin-bottom: 16px;
            flex-wrap: wrap;
        }}

        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 16px;
            font-size: 0.75em;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .badge-nailbiter {{
            background-color: #FFF3CD;
            color: #856404;
        }}

        .badge-comeback {{
            background-color: #FFE5E5;
            color: #D50A0A;
        }}

        .badge-blowout {{
            background-color: #E8F4F8;
            color: #0066CC;
        }}

        .badge-upset {{
            background-color: #F3E5F5;
            color: #7B1FA2;
        }}

        .badge-game-of-week {{
            background-color: var(--accent-gold);
            color: #000;
        }}

        /* Game Header */
        .game-header {{
            margin-bottom: 24px;
            padding-bottom: 20px;
            border-bottom: 3px solid var(--border-light);
        }}

        .game-meta {{
            font-size: 0.85em;
            color: var(--text-secondary);
            margin-bottom: 16px;
            display: flex;
            gap: 16px;
            flex-wrap: wrap;
        }}

        .game-meta span {{
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }}

        /* Matchup Display */
        .matchup {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 16px;
            margin-top: 16px;
        }}

        .team-section {{
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 8px;
            flex: 1;
            max-width: 200px;
        }}

        .team-section.winner .team-name {{
            color: var(--winner-color);
            font-weight: 800;
        }}

        .team-section.winner .score {{
            color: var(--winner-color);
        }}

        .team-section.loser .team-name {{
            color: var(--loser-color);
            font-weight: 600;
        }}

        .team-section.loser .score {{
            color: var(--loser-color);
        }}

        .team-logo-container {{
            width: 48px;
            height: 48px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .team-icon {{
            width: 48px;
            height: 48px;
            object-fit: contain;
            filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));
        }}

        .team-info {{
            text-align: center;
        }}

        .team-name {{
            font-weight: 700;
            font-size: 1.1em;
            transition: color 0.3s ease;
        }}

        .team-record {{
            font-size: 0.8em;
            color: var(--text-secondary);
            margin-top: 2px;
        }}

        .score {{
            font-size: 2.5em;
            font-weight: 800;
            font-variant-numeric: tabular-nums;
            line-height: 1;
        }}

        .vs-divider {{
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 8px;
            color: var(--text-secondary);
        }}

        .at-symbol {{
            font-size: 0.9em;
            font-weight: 600;
        }}

        .score-divider {{
            width: 40px;
            height: 2px;
            background-color: var(--border-light);
        }}

        /* Summary */
        .summary {{
            font-size: 1em;
            line-height: 1.7;
            color: var(--text-primary);
            margin-bottom: 20px;
        }}

        .summary strong {{
            color: var(--nfl-navy);
            font-weight: 700;
        }}

        .stat-highlight {{
            background-color: #FFF8E1;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 600;
            white-space: nowrap;
        }}

        @media (prefers-color-scheme: dark) {{
            .stat-highlight {{
                background-color: #4a4a2a;
            }}
        }}

        /* Footer Actions */
        .game-footer {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-top: 20px;
            border-top: 1px solid var(--border-light);
        }}

        .recap-link {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 20px;
            background-color: var(--nfl-navy);
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 600;
            font-size: 0.9em;
            transition: all 0.3s ease;
        }}

        .recap-link:hover {{
            background-color: #024a9c;
            transform: translateX(2px);
        }}

        .recap-link:focus {{
            outline: 3px solid var(--accent-gold);
            outline-offset: 2px;
        }}

        .recap-link::after {{
            content: "→";
            font-size: 1.2em;
        }}

        /* Responsive Design */
        @media (min-width: 1024px) {{
            .games-container {{
                grid-template-columns: repeat(2, 1fr);
            }}
        }}

        @media (max-width: 640px) {{
            body {{
                padding: 16px;
            }}

            .newsletter-title {{
                font-size: 2em;
            }}

            .newsletter-subtitle {{
                font-size: 1em;
            }}

            .game {{
                padding: 20px;
            }}

            .matchup {{
                flex-direction: column;
                gap: 8px;
            }}

            .score {{
                font-size: 2em;
            }}

            .team-name {{
                font-size: 1em;
            }}

            .vs-divider {{
                flex-direction: row;
            }}

            .score-divider {{
                width: 2px;
                height: 40px;
            }}

            .game-footer {{
                flex-direction: column;
                gap: 12px;
                align-items: stretch;
            }}

            .recap-link {{
                justify-content: center;
            }}
        }}

        /* Print Styles */
        @media print {{
            body {{
                background-color: white;
                color: black;
            }}

            .game {{
                break-inside: avoid;
                box-shadow: none;
                border: 1px solid #ddd;
            }}

            .recap-link {{
                background-color: white;
                color: black;
                border: 1px solid black;
            }}
        }}

        /* Focus Styles for Accessibility */
        *:focus {{
            outline: 3px solid var(--accent-gold);
            outline-offset: 2px;
        }}

        /* Loading Animation */
        @keyframes fadeIn {{
            from {{
                opacity: 0;
                transform: translateY(10px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}

        .game {{
            animation: fadeIn 0.5s ease-out;
        }}
    </style>
</head>
<body>
{newsletter_content}
</body>
</html>"""

    return wrapped


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Generate NFL newsletter using AI'
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
        '--provider',
        choices=['claude', 'openai', 'gemini'],
        help='AI provider to use (overrides config file)'
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

    print(f"Generating newsletter for week: {target_week}")

    # Locate combined recaps file in tmp directory
    year = config['nfl_season']['year']
    tmp_week_dir = Path(config['storage']['tmp_dir']) / f"{year}-week{target_week:02d}"
    combined_file = tmp_week_dir / config['storage']['combined_filename']

    print(f"Input file: {combined_file}")

    # Read combined recaps
    try:
        recap_content = read_combined_recaps(combined_file)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Determine AI provider
    provider_name = args.provider or config['ai']['active_provider']
    provider_config = config['ai'][provider_name]

    print(f"AI Provider: {provider_name}")

    # Create AI provider
    try:
        ai_provider = create_ai_provider(provider_name, provider_config)
    except (ValueError, ImportError) as e:
        print(f"Error initializing AI provider: {e}")
        sys.exit(1)

    # Load prompt from file
    prompt_file = config.get('newsletter_prompt_file', 'newsletter_prompt.txt')
    try:
        prompt = load_prompt(prompt_file)
    except FileNotFoundError:
        print(f"Error: Prompt file '{prompt_file}' not found")
        sys.exit(1)

    # Generate newsletter
    try:
        newsletter_content = generate_newsletter(
            ai_provider,
            prompt,
            recap_content,
            target_week,
            tmp_week_dir
        )
    except Exception as e:
        print(f"Error generating newsletter: {e}")
        sys.exit(1)

    # Wrap in complete HTML if needed
    complete_html = wrap_newsletter_html(newsletter_content, target_week)

    # Save newsletter to web directory with dynamic filename: YYYY-weekWW.html
    web_dir = Path(config['storage']['web_dir'])
    web_dir.mkdir(parents=True, exist_ok=True)

    newsletter_filename = f"{year}-week{target_week:02d}.html"
    output_file = web_dir / newsletter_filename

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(complete_html)

    # Update index.html to point to latest newsletter
    update_index_html(web_dir, newsletter_filename, year, target_week)

    # Summary
    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Week: {target_week}")
    print(f"  AI Provider: {provider_name}")
    print(f"  Newsletter file: {output_file}")
    print(f"  File size: {output_file.stat().st_size:,} bytes")
    print(f"{'='*60}")
    print(f"\nNewsletter generated successfully!")
    print(f"Open in browser: file://{output_file.absolute()}")


if __name__ == "__main__":
    main()
