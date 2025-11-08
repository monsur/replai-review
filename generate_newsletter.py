#!/usr/bin/env python3
"""
Stage 2: Generate Newsletter with AI

This script:
1. Reads games.json from Stage 1 (fetch_games.py)
2. Sends game metadata + recap text to AI provider
3. AI generates summaries and badges for each game
4. Merges AI output with game data
5. Validates using Pydantic models
6. Saves to newsletter.json (same directory as games.json)

Usage:
    python3 generate_newsletter.py --input tmp/2025-week09/20251109/games.json
    python3 generate_newsletter.py --input tmp/2025-week09/games.json --provider openai
"""

import argparse
import json
import sys
import re
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

import yaml
from pydantic import ValidationError

from ai_providers import create_ai_provider
from models import NewsletterData, Game
from stage_utils import (
    get_newsletter_file_path,
    parse_date,
    validate_type,
)


def load_games_file(games_path: Path) -> dict:
    """
    Load and validate games.json from Stage 1.

    Args:
        games_path: Path to games.json file

    Returns:
        Dictionary with metadata and games

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is invalid JSON
        ValueError: If structure is invalid
    """
    if not games_path.exists():
        raise FileNotFoundError(f"Games file not found: {games_path}")

    with open(games_path, 'r') as f:
        data = json.load(f)

    # Validate structure
    if 'metadata' not in data:
        raise ValueError("Missing 'metadata' in games.json")
    if 'games' not in data:
        raise ValueError("Missing 'games' in games.json")

    return data


def load_prompt_template(prompt_file: str) -> str:
    """
    Load the newsletter generation prompt from file.

    Args:
        prompt_file: Path to the prompt template file

    Returns:
        Prompt text as a string

    Raises:
        FileNotFoundError: If prompt file doesn't exist
    """
    with open(prompt_file, 'r', encoding='utf-8') as f:
        return f.read().strip()


def extract_json_from_response(raw_response: str) -> str:
    """
    Extract JSON from AI response, handling common wrapping formats.

    AI providers often wrap JSON in markdown code blocks like:
    ```json
    { ... }
    ```

    This function strips those wrappers and returns clean JSON.

    Args:
        raw_response: Raw response from AI

    Returns:
        Clean JSON string

    Raises:
        ValueError: If no valid JSON can be extracted
    """
    # Strip leading/trailing whitespace
    content = raw_response.strip()

    # Pattern 1: Markdown code block with json language specifier
    pattern1 = r'^```json\s*\n(.*)\n```\s*$'
    match = re.match(pattern1, content, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Pattern 2: Markdown code block without language specifier
    pattern2 = r'^```\s*\n(.*)\n```\s*$'
    match = re.match(pattern2, content, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Pattern 3: Backticks inline
    pattern3 = r'^`(.*)`\s*$'
    match = re.match(pattern3, content, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Pattern 4: Look for first { and last }
    if '{' in content and '}' in content:
        start_idx = content.find('{')
        end_idx = content.rfind('}')
        if start_idx < end_idx:
            extracted = content[start_idx:end_idx + 1]
            if extracted.count('{') >= extracted.count('}'):
                return extracted.strip()

    # If nothing worked, raise error
    raise ValueError("Could not extract JSON from AI response")


def construct_ai_prompt(games: list, prompt_template: str) -> tuple:
    """
    Construct the AI prompt from games data.

    Args:
        games: List of game dictionaries
        prompt_template: The system prompt template

    Returns:
        Tuple of (system_prompt, user_message)
    """
    # System prompt from template
    system_prompt = prompt_template

    # Build user message with all games
    games_text = []
    for i, game in enumerate(games, 1):
        game_text = f"""
GAME {i}: {game['game_id']}
Away Team: {game['away_team']} ({game['away_abbr']}) - {game['away_score']} - Record: {game['away_record']}
Home Team: {game['home_team']} ({game['home_abbr']}) - {game['home_score']} - Record: {game['home_record']}
Date: {game['game_date_display']}
Stadium: {game['stadium']}
TV Network: {game['tv_network']}

RECAP ARTICLE:
{game['recap_text']}
"""
        games_text.append(game_text)

    user_message = f"""
Here are {len(games)} NFL games from Week {games[0].get('week', '?')}. For each game, the metadata (scores, records, teams, etc.) is already provided from ESPN's API.

Your task: Generate ONLY the summary and badges for each game.

{'-' * 70}
{''.join(games_text)}
{'-' * 70}
"""

    return system_prompt, user_message


def merge_ai_output(games: list, ai_output: dict) -> list:
    """
    Merge AI-generated summaries and badges with game data.

    Args:
        games: Original game data from Stage 1
        ai_output: AI output with summaries and badges

    Returns:
        Merged list of games with both API data and AI data
    """
    ai_games = ai_output.get('games', [])

    # Create lookup by game_id
    ai_lookup = {g['game_id']: g for g in ai_games}

    merged = []
    for game in games:
        game_id = game['game_id']

        if game_id in ai_lookup:
            ai_data = ai_lookup[game_id]

            # Start with original game data
            merged_game = game.copy()

            # Remove recap_text to save space
            merged_game.pop('recap_text', None)

            # Add AI fields
            merged_game['summary'] = ai_data.get('summary', '')
            merged_game['badges'] = ai_data.get('badges', [])

            merged.append(merged_game)
        else:
            print(f"⚠️  Warning: No AI output for game {game_id}")
            # Include game anyway with empty summary
            merged_game = game.copy()
            merged_game.pop('recap_text', None)
            merged_game['summary'] = ''
            merged_game['badges'] = []
            merged.append(merged_game)

    return merged


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Stage 2: Generate newsletter with AI'
    )
    parser.add_argument(
        '--input',
        type=str,
        required=True,
        help='Path to games.json file from Stage 1'
    )
    parser.add_argument(
        '--provider',
        type=str,
        help='AI provider: claude, openai, or gemini (default from config)'
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
        print("Stage 2: Generate Newsletter with AI")
        print("=" * 70)
        print()

        # Load config
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)

        # Load games
        print(f"📖 Loading: {input_path}")
        games_data = load_games_file(input_path)

        metadata = games_data['metadata']
        games = games_data['games']

        print(f"✅ Loaded {len(games)} games")
        print(f"   Date: {metadata['date']}, Type: {metadata['type']}, Week: {metadata['week']}")
        print()

        # Load prompt template
        prompt_file = config.get('newsletter_prompt_file', 'newsletter_prompt.txt')
        prompt_template = load_prompt_template(prompt_file)

        # Construct AI prompt
        system_prompt, user_message = construct_ai_prompt(games, prompt_template)

        print(f"📝 Constructing AI prompt...")
        print(f"   System prompt: {len(system_prompt):,} chars")
        print(f"   User message: {len(user_message):,} chars")
        print()

        # Create AI provider
        provider_name = args.provider or config['ai']['active_provider']
        ai_provider = create_ai_provider(provider_name, config)

        print(f"🤖 Using AI provider: {provider_name}")
        print("⏳ Generating summaries and badges...")

        # Generate summaries and badges
        raw_response = ai_provider.generate(system_prompt, user_message)

        print(f"✅ Received response: {len(raw_response):,} characters")
        print()

        # Extract JSON from response
        print("🔍 Parsing AI response...")
        json_string = extract_json_from_response(raw_response)
        print(f"✅ Extracted JSON: {len(json_string):,} characters")

        # Parse JSON
        ai_output = json.loads(json_string)
        ai_games = ai_output.get('games', [])

        print(f"✅ Parsed {len(ai_games)} game outputs")
        print()

        # Merge AI output with game data
        print("🔄 Merging AI summaries with game data...")
        enriched_games = merge_ai_output(games, ai_output)

        # Validate using Pydantic models
        print("✓ Validating data with Pydantic...")
        validated_newsletter = NewsletterData(
            week=metadata['week'],
            year=metadata['year'],
            games=[Game(**g) for g in enriched_games],
            ai_provider=provider_name
        )
        print(f"✅ Validation passed!")
        print(f"   - {validated_newsletter.game_count} games")
        print(f"   - {validated_newsletter.upset_count} upsets")
        print()

        # Prepare output data
        output_data = {
            'metadata': {
                **metadata,
                'generated_at': datetime.now(ZoneInfo('UTC')).isoformat(),
                'ai_provider': provider_name
            },
            'games': enriched_games
        }

        # Save to file
        output_file = input_path.parent / "newsletter.json"

        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)

        print("=" * 70)
        print(f"✅ Saved to: {output_file}")
        print("=" * 70)

        sys.exit(0)

    except FileNotFoundError as e:
        print(f"❌ File not found: {e}", file=sys.stderr)
        sys.exit(2)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}", file=sys.stderr)
        sys.exit(2)
    except ValidationError as e:
        print(f"❌ Validation error:", file=sys.stderr)
        for error in e.errors():
            field = ' -> '.join(str(x) for x in error['loc'])
            message = error['msg']
            print(f"   {field}: {message}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()
