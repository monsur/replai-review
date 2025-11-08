"""
Unit tests for publish_newsletter.py

Run with:
    python -m unittest test_publish_newsletter.py -v
"""

import unittest
import json
import tempfile
from pathlib import Path
from datetime import datetime

from publish_newsletter import (
    load_newsletter_file,
    prepare_game_for_template,
    update_archive,
    generate_index_html,
)


class TestLoadNewsletterFile(unittest.TestCase):
    """Test load_newsletter_file function."""

    def test_load_valid_newsletter_from_fixture(self):
        """Test loading valid newsletter.json."""
        # First generate a newsletter from the games fixture
        fixture_path = Path("fixtures/sample_games.json")
        with open(fixture_path, 'r') as f:
            games_data = json.load(f)

        # Create newsletter from games
        newsletter_data = {
            'metadata': games_data['metadata'],
            'games': [
                {
                    **game,
                    'summary': 'Test summary',
                    'badges': ['upset']
                }
                for game in games_data['games']
            ]
        }

        # Write to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(newsletter_data, f)
            temp_path = Path(f.name)

        try:
            result = load_newsletter_file(temp_path)
            self.assertIn('metadata', result)
            self.assertIn('games', result)
            self.assertGreater(len(result['games']), 0)
        finally:
            temp_path.unlink()

    def test_file_not_found(self):
        """Test that FileNotFoundError is raised for missing file."""
        with self.assertRaises(FileNotFoundError):
            load_newsletter_file(Path("nonexistent.json"))

    def test_missing_metadata(self):
        """Test that ValueError is raised when metadata is missing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({'games': []}, f)
            temp_path = Path(f.name)

        try:
            with self.assertRaises(ValueError):
                load_newsletter_file(temp_path)
        finally:
            temp_path.unlink()

    def test_missing_games(self):
        """Test that ValueError is raised when games list is missing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({'metadata': {}}, f)
            temp_path = Path(f.name)

        try:
            with self.assertRaises(ValueError):
                load_newsletter_file(temp_path)
        finally:
            temp_path.unlink()


class TestPrepareGameForTemplate(unittest.TestCase):
    """Test prepare_game_for_template function."""

    def setUp(self):
        """Set up test fixtures."""
        self.game = {
            'away_team': 'Philadelphia Eagles',
            'away_abbr': 'PHI',
            'away_score': 28,
            'away_record': '8-1',
            'home_team': 'Dallas Cowboys',
            'home_abbr': 'DAL',
            'home_score': 23,
            'home_record': '4-5',
            'game_date_display': 'Sun 11/9 9:00AM ET',
            'stadium': 'AT&T Stadium',
            'tv_network': 'FOX',
            'summary': 'Great game summary',
            'badges': ['upset'],
            'recap_url': 'https://example.com/recap'
        }

    def test_returns_dict(self):
        """Test that function returns a dictionary."""
        result = prepare_game_for_template(self.game)
        self.assertIsInstance(result, dict)

    def test_includes_team_icons(self):
        """Test that result includes team icons."""
        result = prepare_game_for_template(self.game)
        self.assertEqual(result['away_icon'], 'images/PHI.png')
        self.assertEqual(result['home_icon'], 'images/DAL.png')

    def test_winner_loser_classification(self):
        """Test correct winner/loser classification."""
        result = prepare_game_for_template(self.game)
        self.assertEqual(result['away_class'], 'winner')
        self.assertEqual(result['home_class'], 'loser')

    def test_winner_loser_reversed(self):
        """Test winner/loser when home team wins."""
        game = self.game.copy()
        game['away_score'] = 20
        game['home_score'] = 25

        result = prepare_game_for_template(game)
        self.assertEqual(result['away_class'], 'loser')
        self.assertEqual(result['home_class'], 'winner')

    def test_tie_game(self):
        """Test tie game."""
        game = self.game.copy()
        game['away_score'] = 24
        game['home_score'] = 24

        result = prepare_game_for_template(game)
        self.assertEqual(result['away_class'], 'tie')
        self.assertEqual(result['home_class'], 'tie')

    def test_badges_formatted(self):
        """Test that badges are formatted correctly."""
        result = prepare_game_for_template(self.game)
        self.assertIn('badges', result)
        self.assertEqual(len(result['badges']), 1)
        self.assertIn('css_class', result['badges'][0])
        self.assertIn('label', result['badges'][0])

    def test_metadata_formatted(self):
        """Test that metadata is formatted correctly."""
        result = prepare_game_for_template(self.game)
        self.assertIn('meta', result)
        self.assertEqual(len(result['meta']), 3)
        self.assertIn('📅', result['meta'][0])
        self.assertIn('📍', result['meta'][1])
        self.assertIn('📺', result['meta'][2])

    def test_missing_optional_fields(self):
        """Test handling of missing optional fields."""
        minimal_game = {
            'away_team': 'Team A',
            'away_abbr': 'TA',
            'away_score': 10,
            'home_team': 'Team B',
            'home_abbr': 'TB',
            'home_score': 20,
        }

        result = prepare_game_for_template(minimal_game)
        self.assertEqual(result['away_record'], 'N/A')
        self.assertEqual(result['home_record'], 'N/A')
        self.assertEqual(result['summary'], '')
        self.assertEqual(result['recap_url'], '#')


class TestUpdateArchive(unittest.TestCase):
    """Test update_archive function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.archive_path = Path(self.temp_dir) / "archive.json"

        self.metadata = {
            'date': '20251109',
            'type': 'day',
            'week': 9,
            'year': 2025,
            'generated_at': datetime.now().isoformat()
        }

    def tearDown(self):
        """Clean up."""
        import shutil
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_create_new_archive(self):
        """Test creating a new archive.json."""
        update_archive(self.archive_path, self.metadata, "test.html", 5)

        self.assertTrue(self.archive_path.exists())
        with open(self.archive_path, 'r') as f:
            archive = json.load(f)

        self.assertIn('newsletters', archive)
        self.assertEqual(len(archive['newsletters']), 1)

    def test_archive_has_week_entry(self):
        """Test that archive contains week entry."""
        update_archive(self.archive_path, self.metadata, "test.html", 5)

        with open(self.archive_path, 'r') as f:
            archive = json.load(f)

        week_entry = archive['newsletters'][0]
        self.assertEqual(week_entry['week'], 9)
        self.assertEqual(week_entry['year'], 2025)

    def test_archive_has_day_entry(self):
        """Test that day mode creates day entry."""
        update_archive(self.archive_path, self.metadata, "test.html", 5)

        with open(self.archive_path, 'r') as f:
            archive = json.load(f)

        day_entry = archive['newsletters'][0]['entries'][0]
        self.assertEqual(day_entry['type'], 'day')
        self.assertEqual(day_entry['filename'], 'test.html')
        self.assertEqual(day_entry['game_count'], 5)

    def test_multiple_weeks(self):
        """Test adding multiple weeks to archive."""
        update_archive(self.archive_path, self.metadata, "week9.html", 5)

        metadata2 = self.metadata.copy()
        metadata2['week'] = 10
        update_archive(self.archive_path, metadata2, "week10.html", 6)

        with open(self.archive_path, 'r') as f:
            archive = json.load(f)

        self.assertEqual(len(archive['newsletters']), 2)

    def test_week_mode_entry(self):
        """Test creating week mode entry."""
        metadata = self.metadata.copy()
        metadata['type'] = 'week'
        update_archive(self.archive_path, metadata, "week9.html", 16)

        with open(self.archive_path, 'r') as f:
            archive = json.load(f)

        week_entry = archive['newsletters'][0]['entries'][0]
        self.assertEqual(week_entry['type'], 'week')
        self.assertNotIn('day', week_entry)


class TestGenerateIndexHtml(unittest.TestCase):
    """Test generate_index_html function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.docs_dir = Path(self.temp_dir)
        self.archive_path = self.docs_dir / "archive.json"

        # Create sample archive
        archive = {
            'newsletters': [
                {
                    'week': 9,
                    'year': 2025,
                    'entries': [
                        {
                            'type': 'day',
                            'day': 'Sunday',
                            'date': '2025-11-09',
                            'filename': 'week9-sun.html',
                            'game_count': 8
                        }
                    ]
                }
            ]
        }

        with open(self.archive_path, 'w') as f:
            json.dump(archive, f)

    def tearDown(self):
        """Clean up."""
        import shutil
        if self.docs_dir.exists():
            shutil.rmtree(self.docs_dir)

    def test_creates_index_html(self):
        """Test that index.html is created."""
        generate_index_html(self.archive_path, self.docs_dir)

        index_path = self.docs_dir / "index.html"
        self.assertTrue(index_path.exists())

    def test_index_contains_week_info(self):
        """Test that index.html contains week information."""
        generate_index_html(self.archive_path, self.docs_dir)

        index_path = self.docs_dir / "index.html"
        with open(index_path, 'r') as f:
            content = f.read()

        self.assertIn('Week 9 - 2025', content)
        self.assertIn('week9-sun.html', content)

    def test_index_contains_game_count(self):
        """Test that index.html displays game counts."""
        generate_index_html(self.archive_path, self.docs_dir)

        index_path = self.docs_dir / "index.html"
        with open(index_path, 'r') as f:
            content = f.read()

        self.assertIn('8 game', content)

    def test_index_is_valid_html(self):
        """Test that generated index is valid HTML."""
        generate_index_html(self.archive_path, self.docs_dir)

        index_path = self.docs_dir / "index.html"
        with open(index_path, 'r') as f:
            content = f.read()

        # Check for basic HTML structure
        self.assertIn('<!DOCTYPE html>', content)
        self.assertIn('<html', content)
        self.assertIn('</html>', content)
        self.assertIn('<head>', content)
        self.assertIn('<body>', content)


class TestIntegration(unittest.TestCase):
    """Integration tests for publish_newsletter workflow."""

    def test_prepare_game_with_all_fields(self):
        """Test game preparation with all fields."""
        game = {
            'away_team': 'Philadelphia Eagles',
            'away_abbr': 'PHI',
            'away_score': 28,
            'away_record': '8-1',
            'home_team': 'Dallas Cowboys',
            'home_abbr': 'DAL',
            'home_score': 23,
            'home_record': '4-5',
            'game_date_display': 'Sun 11/9 9:00AM ET',
            'stadium': 'AT&T Stadium',
            'tv_network': 'FOX',
            'summary': 'Eagles dominated Cowboys',
            'badges': ['upset', 'blowout'],
            'recap_url': 'https://example.com'
        }

        result = prepare_game_for_template(game)

        # Verify all essential fields are present
        self.assertIn('away_team', result)
        self.assertIn('home_team', result)
        self.assertIn('away_class', result)
        self.assertIn('home_class', result)
        self.assertIn('badges', result)
        self.assertIn('meta', result)

    def test_badge_formatting(self):
        """Test various badge formats."""
        badges_to_test = ['upset', 'nail-biter', 'comeback', 'blowout', 'game-of-week']

        for badge in badges_to_test:
            game = {
                'away_team': 'Team A',
                'away_abbr': 'TA',
                'away_score': 20,
                'home_team': 'Team B',
                'home_abbr': 'TB',
                'home_score': 10,
                'badges': [badge]
            }

            result = prepare_game_for_template(game)
            self.assertEqual(len(result['badges']), 1)
            self.assertIn('css_class', result['badges'][0])
            self.assertIn('label', result['badges'][0])


if __name__ == '__main__':
    unittest.main()
