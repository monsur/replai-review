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


def load_team_icons(icons_file: str = "team_icons.json") -> dict:
    """
    Load team icons from JSON file.

    Args:
        icons_file: Path to the team icons JSON file

    Returns:
        Dictionary of team icons data
    """
    with open(icons_file, 'r', encoding='utf-8') as f:
        return json.load(f)


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


def generate_newsletter(
    ai_provider,
    prompt: str,
    recap_content: str,
    team_icons: dict
) -> str:
    """
    Generate newsletter using AI provider.

    Args:
        ai_provider: AIProvider instance
        prompt: System prompt for the AI
        recap_content: Combined recap content
        team_icons: Dictionary of team icons data

    Returns:
        Generated newsletter HTML
    """
    print("Generating newsletter with AI...")
    print(f"Input size: {len(recap_content):,} characters")

    # Create the user message with team icons data
    user_message = f"""
Here are the NFL game recaps from this week. Please generate a newsletter following the guidelines in the system prompt.

TEAM ICONS DATA (use icon_file_path for each team abbreviation):
{json.dumps(team_icons, indent=2)}

GAME RECAPS:
{recap_content}
"""

    # Generate the newsletter
    newsletter = ai_provider.generate(prompt, user_message)

    print(f"Generated newsletter: {len(newsletter):,} characters")

    return newsletter


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
    <title>NFL ReplAI - Week {week}</title>
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
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            border-bottom: 2px solid #013369;
            padding-bottom: 12px;
        }}
        .matchup {{
            font-size: 1.3em;
            font-weight: bold;
            color: #013369;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .team-icon {{
            width: 28px;
            height: 28px;
            object-fit: contain;
        }}
        .score {{
            font-size: 1.5em;
            font-weight: bold;
            color: #333;
        }}
        .summary {{
            font-size: 0.95em;
            line-height: 1.6;
            color: #333;
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

    # Locate combined recaps file
    week_dir = Path(config['storage']['base_dir']) / f"week_{target_week}"
    combined_file = week_dir / config['storage']['combined_filename']

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

    # Load team icons
    try:
        team_icons = load_team_icons()
        print(f"Loaded {len(team_icons)} team icons")
    except FileNotFoundError:
        print("Warning: team_icons.json not found, proceeding without icons")
        team_icons = {}
    except Exception as e:
        print(f"Warning: Error loading team icons: {e}")
        team_icons = {}

    # Generate newsletter
    try:
        newsletter_content = generate_newsletter(
            ai_provider,
            prompt,
            recap_content,
            team_icons
        )
    except Exception as e:
        print(f"Error generating newsletter: {e}")
        sys.exit(1)

    # Wrap in complete HTML if needed
    complete_html = wrap_newsletter_html(newsletter_content, target_week)

    # Save newsletter
    output_file = week_dir / config['storage']['newsletter_filename']

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(complete_html)

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
