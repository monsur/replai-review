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

    # Add ESPN recap link if available
    recap_link = ""
    if 'recap_url' in game and game['recap_url']:
        recap_link = f' <a href="{game["recap_url"]}" class="recap-link" target="_blank">Read full recap →</a>'

    return f"""    <div class="game">
        <div class="game-header">
            <div class="matchup">
                <img src="{away_icon}" alt="{game['away_abbr']}" class="team-icon">
                <span class="team-name">{game['away_team']}</span>
                <span class="score">{game['away_score']}</span>
                <span class="at">@</span>
                <span class="score">{game['home_score']}</span>
                <span class="team-name">{game['home_team']}</span>
                <img src="{home_icon}" alt="{game['home_abbr']}" class="team-icon">
            </div>
        </div>
        <div class="summary">
            {game['summary']}{recap_link}
        </div>
    </div>"""


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

        # Create complete newsletter HTML
        newsletter_html = f"""<h1>ReplAI Review - Week {week}</h1>

{games_html}"""

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
        body {{
            font-family: Arial, sans-serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{
            color: #013369;
            text-align: center;
            margin-bottom: 40px;
            font-size: 2.5em;
        }}
        .game {{
            background-color: white;
            padding: 25px;
            margin-bottom: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .game-header {{
            margin-bottom: 15px;
            border-bottom: 2px solid #013369;
            padding-bottom: 12px;
        }}
        .matchup {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            font-size: 1.1em;
        }}
        .team-icon {{
            width: 28px;
            height: 28px;
            object-fit: contain;
        }}
        .team-name {{
            font-weight: bold;
            color: #013369;
        }}
        .score {{
            font-size: 1.3em;
            font-weight: bold;
            color: #333;
        }}
        .at {{
            color: #666;
            font-size: 0.9em;
        }}
        .summary {{
            font-size: 0.95em;
            line-height: 1.6;
            color: #333;
        }}
        .recap-link {{
            display: inline-block;
            margin-left: 8px;
            color: #013369;
            text-decoration: none;
            font-size: 0.9em;
            font-weight: 600;
        }}
        .recap-link:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="newsletter">
        {newsletter_content}
    </div>
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
