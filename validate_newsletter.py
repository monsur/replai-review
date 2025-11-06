#!/usr/bin/env python3
"""
Validation script for newsletter data quality.

Run this after generate_json.py to catch common errors before publishing.
"""

import json
import re
import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime



class ValidationError:
    """Represents a validation issue."""
    def __init__(self, severity: str, game_id: str, field: str, message: str):
        self.severity = severity  # "ERROR", "WARNING", "INFO"
        self.game_id = game_id
        self.field = field
        self.message = message

    def __str__(self):
        return f"[{self.severity}] Game {self.game_id} - {self.field}: {self.message}"


class NewsletterValidator:
    """Validates newsletter JSON data."""

    def __init__(self, newsletter_path: Path):
        self.path = newsletter_path
        with open(newsletter_path, 'r') as f:
            self.data = json.load(f)
        self.errors: List[ValidationError] = []

    def validate_all(self) -> List[ValidationError]:
        """Run all validation checks."""
        self.validate_structure()
        self.validate_dates()
        self.validate_records()
        # self.validate_player_teams()  # Disabled - too much work to maintain QB rosters
        self.validate_badges()
        self.validate_scores()
        return self.errors

    def validate_structure(self):
        """Check basic structure is valid."""
        if 'games' not in self.data:
            self.errors.append(ValidationError(
                "ERROR", "N/A", "structure", "Missing 'games' array"
            ))
            return

        if len(self.data['games']) == 0:
            self.errors.append(ValidationError(
                "WARNING", "N/A", "structure", "No games in newsletter"
            ))

    def validate_dates(self):
        """Check game dates are reasonable."""
        week = self.data.get('week', 0)
        date_pattern = r'^(Thu|Fri|Sat|Sun|Mon|Tue|Wed) \d{1,2}/\d{1,2} \d{1,2}:\d{2}(AM|PM) ET$'

        thursday_games = []
        monday_games = []
        sunday_games = []

        for game in self.data['games']:
            game_id = game.get('game_id', 'unknown')
            date = game.get('game_date', '')

            # Check format
            if not re.match(date_pattern, date):
                self.errors.append(ValidationError(
                    "ERROR", game_id, "game_date",
                    f"Invalid date format: '{date}'"
                ))
                continue

            # Track day of week
            day = date.split()[0]
            if day == "Thu":
                thursday_games.append(game_id)
            elif day == "Mon":
                monday_games.append(game_id)
            elif day == "Sun":
                sunday_games.append(game_id)

        # Validate day distribution
        if len(thursday_games) > 2:
            self.errors.append(ValidationError(
                "WARNING", "multiple", "game_date",
                f"Unusual: {len(thursday_games)} Thursday games"
            ))

        if len(monday_games) > 2:
            self.errors.append(ValidationError(
                "WARNING", "multiple", "game_date",
                f"Unusual: {len(monday_games)} Monday games"
            ))

        # Most games should be Sunday
        if len(sunday_games) < 8 and week > 1:
            self.errors.append(ValidationError(
                "WARNING", "multiple", "game_date",
                f"Only {len(sunday_games)} Sunday games - check dates"
            ))

    def validate_records(self):
        """Check team records are valid format."""
        record_pattern = r'^\d{1,2}-\d{1,2}(-\d{1,2})?$'  # X-Y or X-Y-Z for ties

        for game in self.data['games']:
            game_id = game.get('game_id', 'unknown')

            for team_type in ['away', 'home']:
                record = game.get(f'{team_type}_record', '')

                # Skip if N/A or not provided
                if record in ['N/A', '', None]:
                    self.errors.append(ValidationError(
                        "INFO", game_id, f'{team_type}_record',
                        f"Record not provided for {game.get(f'{team_type}_team', 'unknown')}"
                    ))
                    continue

                # Check format
                if not re.match(record_pattern, record):
                    self.errors.append(ValidationError(
                        "ERROR", game_id, f'{team_type}_record',
                        f"Invalid record format: '{record}'"
                    ))
                    continue

                # Check wins+losses match total games
                parts = record.split('-')
                wins = int(parts[0])
                losses = int(parts[1])
                ties = int(parts[2]) if len(parts) > 2 else 0
                total = wins + losses + ties

                # Week number check - teams can play UP TO week number of games
                # (e.g., in week 9, a team can have 9 games if no bye week yet)
                # Only flag if they have MORE games than weeks played
                week = self.data.get('week', 0)
                if week > 1 and total > week:
                    self.errors.append(ValidationError(
                        "WARNING", game_id, f'{team_type}_record',
                        f"Record {record} has {total} games but it's only week {week}"
                    ))

    # Disabled: validate_player_teams() - Too much maintenance to keep QB rosters updated
    # QBs change frequently due to injuries, trades, and backups starting
    # def validate_player_teams(self):
    #     """Check player-team matchups make sense."""
    #     pass

    def validate_badges(self):
        """Check badges match game characteristics."""
        for game in self.data['games']:
            game_id = game.get('game_id', 'unknown')
            away_score = game.get('away_score', 0)
            home_score = game.get('home_score', 0)
            badges = game.get('badges', [])

            diff = abs(away_score - home_score)

            # Check nail-biter badge
            if 'nail-biter' in badges and diff > 3:
                self.errors.append(ValidationError(
                    "WARNING", game_id, "badges",
                    f"'nail-biter' badge but {diff}-point difference"
                ))

            # Check blowout badge
            if 'blowout' in badges and diff < 21:
                self.errors.append(ValidationError(
                    "WARNING", game_id, "badges",
                    f"'blowout' badge but only {diff}-point difference"
                ))

            # Check for missing nail-biter
            if diff <= 3 and 'nail-biter' not in badges:
                self.errors.append(ValidationError(
                    "INFO", game_id, "badges",
                    f"{diff}-point game might deserve 'nail-biter' badge"
                ))

    def validate_scores(self):
        """Check scores are reasonable."""
        for game in self.data['games']:
            game_id = game.get('game_id', 'unknown')
            away_score = game.get('away_score', 0)
            home_score = game.get('home_score', 0)

            # Check for impossibly low scores
            if away_score < 0 or home_score < 0:
                self.errors.append(ValidationError(
                    "ERROR", game_id, "scores",
                    f"Negative score: {away_score}-{home_score}"
                ))

            # Check for unusually high scores
            if away_score > 60 or home_score > 60:
                self.errors.append(ValidationError(
                    "WARNING", game_id, "scores",
                    f"Unusually high score: {away_score}-{home_score}"
                ))

            # Check for ties (rare in NFL)
            if away_score == home_score:
                self.errors.append(ValidationError(
                    "WARNING", game_id, "scores",
                    f"Tied game: {away_score}-{home_score} - verify result"
                ))


def main():
    """Main validation function."""
    import argparse
    import yaml
    from week_calculator import create_week_calculator

    parser = argparse.ArgumentParser(description='Validate newsletter JSON data')
    parser.add_argument('--week', type=int, help='Week number to validate')
    parser.add_argument('path', nargs='?', help='Direct path to newsletter.json (alternative to --week)')

    args = parser.parse_args()

    if args.path:
        # Direct path provided
        newsletter_file = Path(args.path)
    elif args.week:
        # Week number provided - construct path
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        year = config['nfl_season']['year']
        newsletter_file = Path(f"tmp/{year}-week{args.week:02d}/newsletter.json")
    else:
        # Auto-detect week
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        year = config['nfl_season']['year']
        week_calc = create_week_calculator(config['nfl_season']['season_start_date'])
        week = week_calc.get_week()
        newsletter_file = Path(f"tmp/{year}-week{week:02d}/newsletter.json")

    if not newsletter_file.exists():
        print(f"Error: File not found: {newsletter_file}")
        sys.exit(1)

    print(f"Validating {newsletter_file}...\n")

    validator = NewsletterValidator(newsletter_file)
    errors = validator.validate_all()

    # Group by severity
    error_count = sum(1 for e in errors if e.severity == "ERROR")
    warning_count = sum(1 for e in errors if e.severity == "WARNING")
    info_count = sum(1 for e in errors if e.severity == "INFO")

    # Print results
    print("=" * 70)
    print("VALIDATION RESULTS")
    print("=" * 70)

    if errors:
        for severity in ["ERROR", "WARNING", "INFO"]:
            severity_errors = [e for e in errors if e.severity == severity]
            if severity_errors:
                print(f"\n{severity}S ({len(severity_errors)}):")
                print("-" * 70)
                for error in severity_errors:
                    print(f"  {error}")
    else:
        print("\n✅ All validations passed!")

    # Summary
    print("\n" + "=" * 70)
    print(f"SUMMARY: {error_count} errors, {warning_count} warnings, {info_count} info")
    print("=" * 70)

    # Exit with appropriate code
    if error_count > 0:
        print("\n❌ Validation FAILED - fix errors before publishing")
        sys.exit(1)
    elif warning_count > 0:
        print("\n⚠️  Validation passed with warnings - review before publishing")
        sys.exit(0)
    else:
        print("\n✅ Ready to publish!")
        sys.exit(0)


if __name__ == "__main__":
    main()
