"""
Unit tests for fetch_games.py

Run with:
    python -m unittest test_fetch_games.py -v
"""

import unittest
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from fetch_games import (
    format_game_date,
    parse_game_from_api,
    filter_games_by_date,
    strip_html_tags,
)


class TestFormatGameDate(unittest.TestCase):
    """Test format_game_date function."""

    def test_basic_iso_date_sunday_morning(self):
        """Test formatting Sunday morning game."""
        # 2025-11-09T13:00Z (1 PM UTC) = 9 AM ET (UTC-4)
        result = format_game_date("2025-11-09T13:00Z")
        self.assertIn("Sun", result)
        self.assertIn("11/9", result)
        self.assertIn("ET", result)

    def test_sunday_afternoon_game(self):
        """Test formatting Sunday afternoon game."""
        # 2025-11-09T17:00Z (5 PM UTC) = 1 PM ET (UTC-4)
        result = format_game_date("2025-11-09T17:00Z")
        self.assertIn("Sun", result)
        self.assertIn("11/9", result)
        self.assertIn("ET", result)

    def test_monday_night_football(self):
        """Test formatting Monday Night Football."""
        # 2025-11-10T21:00Z (9 PM UTC) = 5 PM ET (UTC-4)
        result = format_game_date("2025-11-10T21:00Z")
        self.assertIn("Mon", result)
        self.assertIn("11/10", result)
        self.assertIn("ET", result)

    def test_invalid_format(self):
        """Test that invalid format raises ValueError."""
        with self.assertRaises(ValueError):
            format_game_date("not-a-date")


class TestStripHtmlTags(unittest.TestCase):
    """Test strip_html_tags function."""

    def test_simple_html(self):
        """Test stripping simple HTML tags."""
        html = "<p>Hello <b>world</b></p>"
        result = strip_html_tags(html)
        self.assertEqual(result, "Hello world")

    def test_html_with_multiple_spaces(self):
        """Test that multiple spaces are normalized."""
        html = "<p>Hello    <b>world</b></p>"
        result = strip_html_tags(html)
        self.assertEqual(result, "Hello world")

    def test_complex_html(self):
        """Test stripping complex HTML."""
        html = "<div><p>The <strong>game</strong> was <em>amazing</em>.</p></div>"
        result = strip_html_tags(html)
        self.assertIn("game", result)
        self.assertIn("amazing", result)
        self.assertNotIn("<", result)
        self.assertNotIn(">", result)

    def test_empty_html(self):
        """Test with empty HTML."""
        result = strip_html_tags("<p></p>")
        self.assertEqual(result, "")


class TestParseGameFromApi(unittest.TestCase):
    """Test parse_game_from_api function."""

    def setUp(self):
        """Set up test fixtures."""
        self.sample_event = {
            'id': '401547891',
            'date': '2025-11-09T13:00Z',
            'competitions': [{
                'competitors': [
                    {
                        'team': {
                            'displayName': 'Dallas Cowboys',
                            'abbreviation': 'DAL'
                        },
                        'score': '23',
                        'records': [{'summary': '4-5'}]
                    },
                    {
                        'team': {
                            'displayName': 'Philadelphia Eagles',
                            'abbreviation': 'PHI'
                        },
                        'score': '28',
                        'records': [{'summary': '8-1'}]
                    }
                ],
                'venue': {'fullName': 'AT&T Stadium'},
                'broadcasts': [{'names': ['FOX']}]
            }]
        }

    def test_parse_valid_game(self):
        """Test parsing valid game event."""
        game = parse_game_from_api(self.sample_event)

        self.assertEqual(game['game_id'], '401547891')
        self.assertEqual(game['away_team'], 'Philadelphia Eagles')
        self.assertEqual(game['away_abbr'], 'PHI')
        self.assertEqual(game['away_score'], 28)
        self.assertEqual(game['home_team'], 'Dallas Cowboys')
        self.assertEqual(game['home_abbr'], 'DAL')
        self.assertEqual(game['home_score'], 23)
        self.assertEqual(game['away_record'], '8-1')
        self.assertEqual(game['home_record'], '4-5')
        self.assertEqual(game['stadium'], 'AT&T Stadium')
        self.assertEqual(game['tv_network'], 'FOX')

    def test_parse_game_without_records(self):
        """Test parsing game without team records."""
        self.sample_event['competitions'][0]['competitors'][0]['records'] = []
        self.sample_event['competitions'][0]['competitors'][1]['records'] = []

        game = parse_game_from_api(self.sample_event)

        self.assertEqual(game['away_record'], 'N/A')
        self.assertEqual(game['home_record'], 'N/A')

    def test_parse_game_without_venue(self):
        """Test parsing game without venue."""
        del self.sample_event['competitions'][0]['venue']

        game = parse_game_from_api(self.sample_event)

        self.assertEqual(game['stadium'], 'N/A')

    def test_parse_game_without_broadcast(self):
        """Test parsing game without broadcast info."""
        self.sample_event['competitions'][0]['broadcasts'] = []

        game = parse_game_from_api(self.sample_event)

        self.assertEqual(game['tv_network'], 'N/A')

    def test_game_has_required_fields(self):
        """Test that parsed game has all required fields."""
        game = parse_game_from_api(self.sample_event)

        required_fields = [
            'game_id', 'away_team', 'away_abbr', 'away_score', 'away_record',
            'home_team', 'home_abbr', 'home_score', 'home_record',
            'game_date_iso', 'game_date_display', 'stadium', 'tv_network', 'recap_url'
        ]

        for field in required_fields:
            self.assertIn(field, game, f"Missing required field: {field}")


class TestFilterGamesByDate(unittest.TestCase):
    """Test filter_games_by_date function."""

    def setUp(self):
        """Set up test fixtures."""
        self.games = [
            {
                'game_id': '1',
                'away_abbr': 'PHI',
                'home_abbr': 'DAL',
                'game_date_iso': '2025-11-09T13:00Z'  # November 9, 9 AM ET
            },
            {
                'game_id': '2',
                'away_abbr': 'KC',
                'home_abbr': 'BUF',
                'game_date_iso': '2025-11-09T17:00Z'  # November 9, 1 PM ET
            },
            {
                'game_id': '3',
                'away_abbr': 'NYJ',
                'home_abbr': 'MIA',
                'game_date_iso': '2025-11-10T21:00Z'  # November 10, 5 PM ET
            }
        ]

    def test_filter_single_date(self):
        """Test filtering games for a single date."""
        filtered = filter_games_by_date(self.games, "20251109")

        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered[0]['game_id'], '1')
        self.assertEqual(filtered[1]['game_id'], '2')

    def test_filter_different_date(self):
        """Test filtering games for a different date."""
        filtered = filter_games_by_date(self.games, "20251110")

        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]['game_id'], '3')

    def test_filter_no_games(self):
        """Test filtering returns empty list when no games match."""
        filtered = filter_games_by_date(self.games, "20251111")

        self.assertEqual(len(filtered), 0)

    def test_filter_preserves_game_data(self):
        """Test that filtering preserves all game data."""
        filtered = filter_games_by_date(self.games, "20251109")

        for game in filtered:
            self.assertIn('game_id', game)
            self.assertIn('away_abbr', game)
            self.assertIn('home_abbr', game)
            self.assertIn('game_date_iso', game)


class TestGamesJsonStructure(unittest.TestCase):
    """Test the games.json file structure."""

    def setUp(self):
        """Load sample games.json fixture."""
        fixture_path = Path("fixtures/sample_games.json")
        with open(fixture_path, 'r') as f:
            self.data = json.load(f)

    def test_has_metadata(self):
        """Test that games.json has metadata."""
        self.assertIn('metadata', self.data)
        self.assertIn('games', self.data)

    def test_metadata_has_required_fields(self):
        """Test that metadata has all required fields."""
        metadata = self.data['metadata']

        required_fields = ['date', 'type', 'week', 'year', 'fetched_at']
        for field in required_fields:
            self.assertIn(field, metadata, f"Missing metadata field: {field}")

    def test_metadata_values(self):
        """Test metadata values."""
        metadata = self.data['metadata']

        self.assertEqual(metadata['date'], '20251109')
        self.assertEqual(metadata['type'], 'day')
        self.assertEqual(metadata['week'], 9)
        self.assertEqual(metadata['year'], 2025)

    def test_games_is_list(self):
        """Test that games is a list."""
        self.assertIsInstance(self.data['games'], list)

    def test_games_have_required_fields(self):
        """Test that all games have required fields."""
        required_fields = [
            'game_id', 'away_team', 'away_abbr', 'away_score', 'away_record',
            'home_team', 'home_abbr', 'home_score', 'home_record',
            'game_date_iso', 'game_date_display', 'stadium', 'tv_network',
            'recap_url', 'recap_text'
        ]

        for game in self.data['games']:
            for field in required_fields:
                self.assertIn(field, game, f"Game {game['game_id']} missing field: {field}")

    def test_game_scores_are_ints(self):
        """Test that game scores are integers."""
        for game in self.data['games']:
            self.assertIsInstance(game['away_score'], int)
            self.assertIsInstance(game['home_score'], int)


class TestIntegration(unittest.TestCase):
    """Integration tests for fetch_games workflow."""

    def test_sample_fixture_is_valid(self):
        """Test that sample fixture is valid JSON."""
        fixture_path = Path("fixtures/sample_games.json")
        self.assertTrue(fixture_path.exists(), "Fixture file not found")

        with open(fixture_path, 'r') as f:
            data = json.load(f)

        # Should not raise exception
        self.assertIn('metadata', data)
        self.assertIn('games', data)
        self.assertGreater(len(data['games']), 0)

    def test_fixture_contains_valid_games(self):
        """Test that fixture contains properly formatted games."""
        fixture_path = Path("fixtures/sample_games.json")
        with open(fixture_path, 'r') as f:
            data = json.load(f)

        for game in data['games']:
            # Test game has basic structure
            self.assertIn('away_abbr', game)
            self.assertIn('home_abbr', game)
            self.assertIn('away_score', game)
            self.assertIn('home_score', game)

            # Test scores are reasonable
            self.assertGreaterEqual(game['away_score'], 0)
            self.assertGreaterEqual(game['home_score'], 0)
            self.assertLessEqual(game['away_score'], 100)
            self.assertLessEqual(game['home_score'], 100)


if __name__ == '__main__':
    unittest.main()
