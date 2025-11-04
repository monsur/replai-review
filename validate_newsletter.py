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

# Known NFL QBs and their teams (2025 season - update as needed)
QB_TEAMS = {
    # AFC East
    "Josh Allen": "BUF", "Tua Tagovailoa": "MIA", "Aaron Rodgers": "NYJ",
    "Drake Maye": "NE", "Jacoby Brissett": "NE",
    # AFC North
    "Lamar Jackson": "BAL", "Joe Burrow": "CIN", "Deshaun Watson": "CLE",
    "Russell Wilson": "PIT", "Justin Fields": "PIT",
    # AFC South
    "C.J. Stroud": "HOU", "Anthony Richardson": "IND", "Joe Flacco": "IND",
    "Trevor Lawrence": "JAX", "Will Levis": "TEN",
    # AFC West
    "Bo Nix": "DEN", "Patrick Mahomes": "KC", "Justin Herbert": "LAC",
    "Gardner Minshew": "LV", "Aidan O'Connell": "LV",
    # NFC East
    "Dak Prescott": "DAL", "Daniel Jones": "NYG", "Drew Lock": "NYG",
    "Jalen Hurts": "PHI", "Jayden Daniels": "WAS",
    # NFC North
    "Caleb Williams": "CHI", "Jared Goff": "DET", "Jordan Love": "GB",
    "Sam Darnold": "MIN", "J.J. McCarthy": "MIN",
    # NFC South
    "Kirk Cousins": "ATL", "Bryce Young": "CAR", "Andy Dalton": "CAR",
    "Derek Carr": "NO", "Baker Mayfield": "TB",
    # NFC West
    "Kyler Murray": "ARI", "Matthew Stafford": "LAR", "Brock Purdy": "SF",
    "Geno Smith": "SEA"
}


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
        self.validate_player_teams()
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

                # Week number check
                week = self.data.get('week', 0)
                if week > 1 and total >= week:
                    self.errors.append(ValidationError(
                        "WARNING", game_id, f'{team_type}_record',
                        f"Record {record} has {total} games but it's only week {week}"
                    ))

    def validate_player_teams(self):
        """Check player-team matchups make sense."""
        for game in self.data['games']:
            game_id = game.get('game_id', 'unknown')
            summary = game.get('summary', '')
            away_team = game.get('away_abbr', '')
            home_team = game.get('home_abbr', '')

            # Extract player names in <strong> tags
            players = re.findall(r'<strong>(.*?)</strong>', summary)

            for player_name in players:
                # Clean up name
                player_name = player_name.strip()

                # Check if it's a known QB
                if player_name in QB_TEAMS:
                    correct_team = QB_TEAMS[player_name]
                    if correct_team not in [away_team, home_team]:
                        self.errors.append(ValidationError(
                            "ERROR", game_id, "summary",
                            f"QB '{player_name}' mentioned but plays for {correct_team}, "
                            f"not {away_team} or {home_team}"
                        ))

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
    if len(sys.argv) > 1:
        newsletter_file = Path(sys.argv[1])
    else:
        # Default to most recent week
        print("Usage: python validate_newsletter.py <path-to-newsletter.json>")
        print("Example: python validate_newsletter.py tmp/2025-week09/newsletter.json")
        sys.exit(1)

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
