#!/usr/bin/env python3
"""
Script 2: Process NFL Game Recaps

This script:
1. Reads all downloaded recap HTML files from week_X/recaps/
2. Extracts the game score and article content
3. Removes navigation, ads, and other unnecessary HTML elements
4. Combines all cleaned recaps into a single file with separators
5. Saves the combined file to week_X/combined.html
"""

import argparse
import sys
from pathlib import Path
from typing import List, Tuple

from bs4 import BeautifulSoup

from utils import (
    load_config,
    get_week_directory_path,
    setup_week_calculator,
    create_base_parser,
    handle_fatal_error,
    handle_recoverable_error
)


def extract_game_info(soup: BeautifulSoup) -> Tuple[str, str]:
    """
    Extract game score and article content from ESPN recap page.

    Args:
        soup: BeautifulSoup object of recap HTML

    Returns:
        Tuple of (game_header, article_content)
    """
    game_header = ""
    article_content = ""

    # Extract game header/score information
    # ESPN typically has this in elements like:
    # - div with class "Gamestrip" or "ScoreCell"
    # - h1 with game matchup information

    # Try to find the game header
    header_candidates = [
        soup.find('h1'),  # Main heading
        soup.find('div', class_='Gamestrip'),
        soup.find('div', class_='ScoreCell'),
        soup.find('header', class_='GameInfo')
    ]

    for candidate in header_candidates:
        if candidate:
            game_header = candidate.get_text(strip=True)
            if game_header:
                break

    # If we still don't have a header, try to construct from title
    if not game_header:
        title = soup.find('title')
        if title:
            game_header = title.get_text(strip=True)

    # Extract the main article content
    # ESPN typically uses:
    # - article tags
    # - div with class "article-body" or "Story__Body"

    article_candidates = [
        soup.find('article'),
        soup.find('div', class_='article-body'),
        soup.find('div', class_='Story__Body'),
        soup.find('div', class_='contentItem__body'),
        soup.find('section', class_='Story')
    ]

    for candidate in article_candidates:
        if candidate:
            # Remove unwanted elements from the article
            for unwanted in candidate.find_all(['script', 'style', 'nav', 'aside', 'footer', 'header']):
                unwanted.decompose()

            # Remove ads and social sharing elements
            for unwanted_class in ['ad-', 'social-', 'related-', 'promo-']:
                for elem in candidate.find_all(class_=lambda x: x and unwanted_class in x):
                    elem.decompose()

            article_content = str(candidate)
            break

    # If we couldn't find article content in structured way, try to find all paragraphs
    if not article_content:
        paragraphs = soup.find_all('p')
        if paragraphs:
            article_content = '\n'.join(str(p) for p in paragraphs)

    return game_header, article_content


def clean_recap(html_file: Path) -> str:
    """
    Clean a single recap HTML file.

    Args:
        html_file: Path to the recap HTML file

    Returns:
        Cleaned HTML string with game info and article
    """
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, 'html.parser')

    game_header, article_content = extract_game_info(soup)

    # Format the cleaned content
    cleaned = f"""
<div class="game-recap">
    <div class="game-header">
        <h2>{game_header}</h2>
    </div>
    <div class="game-article">
        {article_content}
    </div>
</div>
"""

    return cleaned.strip()


def process_all_recaps(recaps_dir: Path) -> List[Tuple[str, str]]:
    """
    Process all recap files in a directory.

    Args:
        recaps_dir: Directory containing recap HTML files

    Returns:
        List of tuples: (filename, cleaned_html)
    """
    recap_files = sorted(recaps_dir.glob("*.html"))

    if not recap_files:
        print(f"Warning: No recap files found in {recaps_dir}")
        return []

    print(f"Found {len(recap_files)} recap files to process")

    processed_recaps = []

    for recap_file in recap_files:
        print(f"  Processing {recap_file.name}...")

        try:
            cleaned = clean_recap(recap_file)
            processed_recaps.append((recap_file.stem, cleaned))
            print(f"    ✓ Cleaned successfully")

        except Exception as e:
            handle_recoverable_error(f"Error processing {recap_file.name}", e)

    return processed_recaps


def combine_recaps(processed_recaps: List[Tuple[str, str]]) -> str:
    """
    Combine multiple cleaned recaps into a single HTML document.

    Args:
        processed_recaps: List of (filename, cleaned_html) tuples

    Returns:
        Combined HTML string
    """
    if not processed_recaps:
        return "<html><body><p>No recaps to process</p></body></html>"

    # Build the combined document
    combined_parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "    <meta charset='utf-8'>",
        "    <title>ReplAI Review - Combined Recaps</title>",
        "    <style>",
        "        .game-recap { margin-bottom: 40px; padding: 20px; border-bottom: 2px solid #ccc; }",
        "        .game-header h2 { color: #013369; margin-bottom: 15px; }",
        "        .game-article { line-height: 1.6; }",
        "        .separator { margin: 40px 0; border-top: 3px solid #013369; }",
        "    </style>",
        "</head>",
        "<body>",
        "    <h1>ReplAI Review - Combined Game Recaps</h1>",
        ""
    ]

    # Add each recap with a separator
    for i, (filename, cleaned_html) in enumerate(processed_recaps):
        combined_parts.append(f"    <!-- Game: {filename} -->")
        combined_parts.append(f"    {cleaned_html}")

        # Add separator between games (but not after the last one)
        if i < len(processed_recaps) - 1:
            combined_parts.append('    <div class="separator"></div>')
            combined_parts.append("")

    combined_parts.extend([
        "</body>",
        "</html>"
    ])

    return "\n".join(combined_parts)


def main():
    """Main execution function."""
    parser = create_base_parser('Process NFL game recap HTML files and combine them')
    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)

    # Determine target week
    target_week, year, _ = setup_week_calculator(config, args.week)

    print(f"Processing week: {target_week}")

    # Locate recaps directory
    week_dir = get_week_directory_path(config, year, target_week)
    recaps_dir = week_dir / config.storage.recap_subdir

    if not recaps_dir.exists():
        handle_fatal_error(
            f"Recaps directory not found: {recaps_dir}",
            FileNotFoundError("Have you run fetch_recaps.py first?")
        )

    print(f"Input directory: {recaps_dir}")

    # Process all recaps
    processed_recaps = process_all_recaps(recaps_dir)

    if not processed_recaps:
        handle_fatal_error(
            "No recaps were successfully processed",
            ValueError("All recap processing attempts failed")
        )

    # Combine recaps
    print("\nCombining recaps...")
    combined_html = combine_recaps(processed_recaps)

    # Save combined file
    output_file = week_dir / config.storage.combined_filename

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(combined_html)

    # Summary
    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Week: {target_week}")
    print(f"  Recaps processed: {len(processed_recaps)}")
    print(f"  Combined file: {output_file}")
    print(f"  File size: {output_file.stat().st_size:,} bytes")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
