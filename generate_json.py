#!/usr/bin/env python3
"""
Script 3a: Generate Newsletter JSON

This script:
1. Reads the combined recap file from tmp/YYYY-weekWW/combined.html
2. Sends it to the configured AI provider with a prompt
3. Receives back a JSON response with game data
4. Saves the JSON to tmp/YYYY-weekWW/newsletter.json
"""

import argparse
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


def generate_json(
    ai_provider,
    prompt: str,
    recap_content: str,
    week: int,
    output_dir: Path
) -> str:
    """
    Generate newsletter JSON using AI provider.

    Args:
        ai_provider: AIProvider instance
        prompt: System prompt for the AI
        recap_content: Combined recap content
        week: Week number
        output_dir: Output directory path

    Returns:
        Raw JSON string from AI
    """
    print("Generating newsletter JSON with AI...")
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
    json_output_file = output_dir / "newsletter.json"
    with open(json_output_file, 'w', encoding='utf-8') as f:
        f.write(newsletter_json)
    print(f"Raw JSON saved to: {json_output_file}")

    return newsletter_json


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Generate NFL newsletter JSON using AI'
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

    print(f"Generating JSON for week: {target_week}")

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

    # Generate JSON
    try:
        newsletter_json = generate_json(
            ai_provider,
            prompt,
            recap_content,
            target_week,
            tmp_week_dir
        )
    except Exception as e:
        print(f"Error generating JSON: {e}")
        sys.exit(1)

    # Summary
    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Week: {target_week}")
    print(f"  AI Provider: {provider_name}")
    print(f"  JSON file: {tmp_week_dir / 'newsletter.json'}")
    print(f"  File size: {len(newsletter_json):,} characters")
    print(f"{'='*60}")
    print(f"\nJSON generated successfully!")


if __name__ == "__main__":
    main()
