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
import json
from pathlib import Path
from pydantic import ValidationError

from ai_providers import create_ai_provider
from models import NewsletterData
from exceptions import AIProviderException, ValidationException
from utils import (
    load_config,
    get_week_directory_path,
    setup_week_calculator,
    create_base_parser,
    handle_fatal_error,
    handle_recoverable_error
)


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
        ValueError: If no JSON can be extracted
    """
    import re

    # Strip leading/trailing whitespace
    content = raw_response.strip()

    # Pattern 1: Markdown code block with json language specifier
    # ```json\n...\n```
    pattern1 = r'^```json\s*\n(.*)\n```\s*$'
    match = re.match(pattern1, content, re.DOTALL)
    if match:
        print("✓ Extracted JSON from markdown code block (```json)")
        return match.group(1).strip()

    # Pattern 2: Markdown code block without language specifier
    # ```\n...\n```
    pattern2 = r'^```\s*\n(.*)\n```\s*$'
    match = re.match(pattern2, content, re.DOTALL)
    if match:
        print("✓ Extracted JSON from markdown code block (```)")
        return match.group(1).strip()

    # Pattern 3: Backticks inline (less common)
    # `{ ... }`
    pattern3 = r'^`(.*)`\s*$'
    match = re.match(pattern3, content, re.DOTALL)
    if match:
        print("✓ Extracted JSON from inline backticks")
        return match.group(1).strip()

    # Pattern 4: Look for first { and last }
    # Sometimes AI adds text before/after JSON
    if '{' in content and '}' in content:
        start_idx = content.find('{')
        end_idx = content.rfind('}')
        if start_idx < end_idx:
            extracted = content[start_idx:end_idx + 1]
            # Verify it's valid JSON structure
            if extracted.count('{') >= extracted.count('}'):
                print("✓ Extracted JSON by finding first { and last }")
                return extracted.strip()

    # If nothing worked, return original (will fail JSON parsing with better error)
    print("⚠️  No wrapping detected, using raw response")
    return content


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
    year: int,
    output_dir: Path
) -> NewsletterData:
    """
    Generate and validate newsletter JSON using AI provider.

    Args:
        ai_provider: AIProvider instance
        prompt: System prompt for the AI
        recap_content: Combined recap content
        week: Week number
        year: Season year
        output_dir: Output directory path

    Returns:
        Validated NewsletterData model

    Raises:
        AIProviderException: If AI generation fails
        ValidationException: If AI output fails validation
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
    try:
        raw_response = ai_provider.generate(prompt, user_message)
        print(f"Generated response: {len(raw_response):,} characters")
    except Exception as e:
        raise AIProviderException(f"AI generation failed: {e}")

    # Extract JSON from response (handles markdown code blocks, etc.)
    try:
        json_string = extract_json_from_response(raw_response)
        print(f"Extracted JSON: {len(json_string):,} characters")
    except Exception as e:
        # Save debug file with raw response
        debug_file = output_dir / "newsletter_debug_extraction_failed.txt"
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(raw_response)
        print(f"⚠️  Could not extract JSON. Raw response saved to {debug_file}")
        raise ValidationException(f"Could not extract JSON from AI response: {e}")

    # Parse JSON
    try:
        json_data = json.loads(json_string)
    except json.JSONDecodeError as e:
        # Save debug file with extracted JSON string
        debug_file = output_dir / "newsletter_debug_invalid.json"
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(json_string)
        print(f"⚠️  Invalid JSON saved to {debug_file} for debugging")
        print(f"   Error at line {e.lineno}, column {e.colno}: {e.msg}")
        raise ValidationException(f"AI returned invalid JSON: {e}")

    # Validate using Pydantic
    try:
        newsletter = NewsletterData(
            week=week,
            year=year,
            games=json_data.get('games', []),
            ai_provider=ai_provider.__class__.__name__
        )

        print(f"✅ Validation successful:")
        print(f"   - {newsletter.game_count} games")
        print(f"   - {newsletter.upset_count} upsets")
        print(f"   - All data validated!")

    except ValidationError as e:
        # Save debug file
        debug_file = output_dir / "newsletter_debug_validation_failed.json"
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(debug_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2)
        print(f"⚠️  Failed validation. Debug file: {debug_file}")

        # Format errors nicely
        error_messages = []
        for error in e.errors():
            field = ' -> '.join(str(x) for x in error['loc'])
            message = error['msg']
            error_messages.append(f"{field}: {message}")

        print(f"❌ Validation errors:")
        for msg in error_messages:
            print(f"   - {msg}")

        raise ValidationException("AI output failed validation", error_messages)

    # Save validated JSON to output directory
    json_output_file = output_dir / "newsletter.json"
    with open(json_output_file, 'w', encoding='utf-8') as f:
        # Use Pydantic's model_dump for proper serialization
        json.dump(newsletter.model_dump(mode='json'), f, indent=2, default=str)
    print(f"Validated JSON saved to: {json_output_file}")

    return newsletter


def main():
    """Main execution function."""
    parser = create_base_parser('Generate NFL newsletter JSON using AI')
    # Add provider-specific argument
    parser.add_argument(
        '--provider',
        choices=['claude', 'openai', 'gemini'],
        help='AI provider to use (overrides config file)'
    )

    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)

    # Determine target week
    target_week, year, _ = setup_week_calculator(config, args.week)

    print(f"Generating JSON for week: {target_week}")

    # Locate combined recaps file in tmp directory
    tmp_week_dir = get_week_directory_path(config, year, target_week)
    combined_file = tmp_week_dir / config.storage.combined_filename

    print(f"Input file: {combined_file}")

    # Read combined recaps
    try:
        recap_content = read_combined_recaps(combined_file)
    except FileNotFoundError as e:
        handle_fatal_error(f"Combined recaps file not found: {combined_file}", e)

    # Determine AI provider
    provider_name = args.provider or config.ai.active_provider
    provider_config = config.get_ai_provider_config(provider_name)

    print(f"AI Provider: {provider_name}")

    # Create AI provider (convert Pydantic model to dict for compatibility)
    try:
        ai_provider = create_ai_provider(provider_name, provider_config.model_dump())
    except (ValueError, ImportError) as e:
        handle_fatal_error(f"Failed to initialize AI provider '{provider_name}'", e)

    # Load prompt from file
    prompt_file = config.newsletter_prompt_file or 'newsletter_prompt.txt'
    try:
        prompt = load_prompt(prompt_file)
    except FileNotFoundError as e:
        handle_fatal_error(f"Prompt file not found: {prompt_file}", e)

    # Generate and validate JSON
    try:
        newsletter_data = generate_json(
            ai_provider,
            prompt,
            recap_content,
            target_week,
            year,
            tmp_week_dir
        )
    except (AIProviderException, ValidationException) as e:
        handle_fatal_error("Failed to generate newsletter JSON", e)

    # Summary
    json_file_path = tmp_week_dir / 'newsletter.json'
    file_size = json_file_path.stat().st_size

    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Week: {target_week}")
    print(f"  AI Provider: {provider_name}")
    print(f"  JSON file: {json_file_path}")
    print(f"  File size: {file_size:,} bytes")
    print(f"  Games validated: {newsletter_data.game_count}")
    print(f"  Upsets: {newsletter_data.upset_count}")
    print(f"{'='*60}")
    print(f"\nJSON generated successfully!")


if __name__ == "__main__":
    main()
