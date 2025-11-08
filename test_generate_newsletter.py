"""
Unit tests for generate_newsletter.py

Run with:
    python -m unittest test_generate_newsletter.py -v
"""

import unittest
import json
import tempfile
from pathlib import Path

from generate_newsletter import (
    extract_json_from_response,
    construct_ai_prompt,
    merge_ai_output,
    load_games_file,
)


class TestExtractJsonFromResponse(unittest.TestCase):
    """Test extract_json_from_response function."""

    def test_markdown_json_code_block(self):
        """Test extracting JSON from markdown code block with json language specifier."""
        response = """```json
{"games": [{"game_id": "123", "summary": "test"}]}
```"""
        result = extract_json_from_response(response)
        self.assertEqual(result, '{"games": [{"game_id": "123", "summary": "test"}]}')

    def test_markdown_code_block_no_language(self):
        """Test extracting JSON from markdown code block without language specifier."""
        response = """```
{"games": [{"game_id": "123"}]}
```"""
        result = extract_json_from_response(response)
        self.assertEqual(result, '{"games": [{"game_id": "123"}]}')

    def test_inline_backticks(self):
        """Test extracting JSON from inline backticks."""
        response = '`{"games": []}`'
        result = extract_json_from_response(response)
        self.assertEqual(result, '{"games": []}')

    def test_bare_json(self):
        """Test extracting bare JSON without any wrapping."""
        response = '{"games": [{"game_id": "123"}]}'
        result = extract_json_from_response(response)
        self.assertEqual(result, '{"games": [{"game_id": "123"}]}')

    def test_json_with_text_before_and_after(self):
        """Test extracting JSON when surrounded by text."""
        response = """Here's the JSON:

{"games": [{"game_id": "123"}]}

That's the complete output."""
        result = extract_json_from_response(response)
        self.assertIn('{"games":', result)
        self.assertIn('"game_id":', result)

    def test_invalid_format_raises_error(self):
        """Test that invalid format raises ValueError."""
        response = "This is not JSON at all"
        with self.assertRaises(ValueError):
            extract_json_from_response(response)

    def test_json_is_valid(self):
        """Test that extracted JSON is valid JSON."""
        response = """```json
{"games": [{"game_id": "1", "summary": "test", "badges": ["upset"]}]}
```"""
        result = extract_json_from_response(response)
        parsed = json.loads(result)  # Should not raise
        self.assertIn('games', parsed)


class TestConstructAiPrompt(unittest.TestCase):
    """Test construct_ai_prompt function."""

    def setUp(self):
        """Set up test fixtures."""
        self.games = [
            {
                'game_id': '401547891',
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
                'recap_text': 'The Eagles dominated the Cowboys.'
            }
        ]

        self.prompt_template = "You are creating a newsletter. Generate summaries and badges."

    def test_returns_tuple(self):
        """Test that function returns a tuple of (system_prompt, user_message)."""
        result = construct_ai_prompt(self.games, self.prompt_template)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    def test_system_prompt_equals_template(self):
        """Test that system prompt equals the template."""
        system_prompt, _ = construct_ai_prompt(self.games, self.prompt_template)
        self.assertEqual(system_prompt, self.prompt_template)

    def test_user_message_contains_games(self):
        """Test that user message contains game information."""
        _, user_message = construct_ai_prompt(self.games, self.prompt_template)

        self.assertIn('401547891', user_message)
        self.assertIn('Philadelphia Eagles', user_message)
        self.assertIn('Dallas Cowboys', user_message)
        self.assertIn('28', user_message)
        self.assertIn('23', user_message)

    def test_user_message_contains_recap(self):
        """Test that user message contains recap text."""
        _, user_message = construct_ai_prompt(self.games, self.prompt_template)
        self.assertIn('The Eagles dominated the Cowboys', user_message)

    def test_multiple_games(self):
        """Test with multiple games."""
        games = self.games + [
            {
                'game_id': '401547892',
                'away_team': 'Kansas City Chiefs',
                'away_abbr': 'KC',
                'away_score': 31,
                'away_record': '9-0',
                'home_team': 'Buffalo Bills',
                'home_abbr': 'BUF',
                'home_score': 28,
                'home_record': '7-2',
                'game_date_display': 'Sun 11/9 1:00PM ET',
                'stadium': 'Highmark Stadium',
                'tv_network': 'CBS',
                'recap_text': 'Kansas City remained undefeated.'
            }
        ]

        _, user_message = construct_ai_prompt(games, self.prompt_template)

        self.assertIn('Kansas City Chiefs', user_message)
        self.assertIn('Buffalo Bills', user_message)


class TestMergeAiOutput(unittest.TestCase):
    """Test merge_ai_output function."""

    def setUp(self):
        """Set up test fixtures."""
        self.games = [
            {
                'game_id': '401547891',
                'away_team': 'Philadelphia Eagles',
                'away_abbr': 'PHI',
                'away_score': 28,
                'home_team': 'Dallas Cowboys',
                'home_abbr': 'DAL',
                'home_score': 23,
                'game_date_display': 'Sun 11/9 9:00AM ET',
                'stadium': 'AT&T Stadium',
                'tv_network': 'FOX',
                'recap_text': 'Long recap text here...'
            },
            {
                'game_id': '401547892',
                'away_team': 'Kansas City Chiefs',
                'away_abbr': 'KC',
                'away_score': 31,
                'home_team': 'Buffalo Bills',
                'home_abbr': 'BUF',
                'home_score': 28,
                'game_date_display': 'Sun 11/9 1:00PM ET',
                'stadium': 'Highmark Stadium',
                'tv_network': 'CBS',
                'recap_text': 'Another recap...'
            }
        ]

        self.ai_output = {
            'games': [
                {
                    'game_id': '401547891',
                    'summary': 'The Eagles dominated the Cowboys with a strong performance.',
                    'badges': ['upset', 'blowout']
                },
                {
                    'game_id': '401547892',
                    'summary': 'Kansas City remained undefeated in a close game.',
                    'badges': ['nail-biter']
                }
            ]
        }

    def test_returns_list(self):
        """Test that function returns a list of games."""
        result = merge_ai_output(self.games, self.ai_output)
        self.assertIsInstance(result, list)

    def test_game_count_preserved(self):
        """Test that all games are in the output."""
        result = merge_ai_output(self.games, self.ai_output)
        self.assertEqual(len(result), len(self.games))

    def test_recap_text_removed(self):
        """Test that recap_text is removed from output."""
        result = merge_ai_output(self.games, self.ai_output)
        for game in result:
            self.assertNotIn('recap_text', game)

    def test_ai_fields_added(self):
        """Test that AI fields are added to games."""
        result = merge_ai_output(self.games, self.ai_output)

        for game in result:
            self.assertIn('summary', game)
            self.assertIn('badges', game)
            self.assertIsInstance(game['summary'], str)
            self.assertIsInstance(game['badges'], list)

    def test_original_fields_preserved(self):
        """Test that original game fields are preserved."""
        result = merge_ai_output(self.games, self.ai_output)

        self.assertEqual(result[0]['away_team'], 'Philadelphia Eagles')
        self.assertEqual(result[0]['away_score'], 28)
        self.assertEqual(result[1]['home_team'], 'Buffalo Bills')
        self.assertEqual(result[1]['home_score'], 28)

    def test_missing_ai_data(self):
        """Test handling when AI output is missing for some games."""
        ai_output = {
            'games': [
                {
                    'game_id': '401547891',
                    'summary': 'Test summary',
                    'badges': []
                }
                # Missing game 401547892
            ]
        }

        result = merge_ai_output(self.games, ai_output)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['summary'], 'Test summary')
        self.assertEqual(result[1]['summary'], '')  # Empty for missing AI data

    def test_empty_ai_output(self):
        """Test handling when AI output is empty."""
        ai_output = {'games': []}
        result = merge_ai_output(self.games, ai_output)

        for game in result:
            self.assertEqual(game['summary'], '')
            self.assertEqual(game['badges'], [])


class TestLoadGamesFile(unittest.TestCase):
    """Test load_games_file function."""

    def test_load_valid_games_file(self):
        """Test loading valid games.json from fixture."""
        fixture_path = Path("fixtures/sample_games.json")
        result = load_games_file(fixture_path)

        self.assertIn('metadata', result)
        self.assertIn('games', result)
        self.assertGreater(len(result['games']), 0)

    def test_file_not_found(self):
        """Test that FileNotFoundError is raised for missing file."""
        with self.assertRaises(FileNotFoundError):
            load_games_file(Path("nonexistent.json"))

    def test_missing_metadata(self):
        """Test that ValueError is raised when metadata is missing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({'games': []}, f)
            temp_path = Path(f.name)

        try:
            with self.assertRaises(ValueError):
                load_games_file(temp_path)
        finally:
            temp_path.unlink()

    def test_missing_games(self):
        """Test that ValueError is raised when games list is missing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({'metadata': {}}, f)
            temp_path = Path(f.name)

        try:
            with self.assertRaises(ValueError):
                load_games_file(temp_path)
        finally:
            temp_path.unlink()

    def test_invalid_json(self):
        """Test that JSONDecodeError is raised for invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("this is not valid json {")
            temp_path = Path(f.name)

        try:
            with self.assertRaises(json.JSONDecodeError):
                load_games_file(temp_path)
        finally:
            temp_path.unlink()


class TestIntegration(unittest.TestCase):
    """Integration tests for generate_newsletter workflow."""

    def test_fixture_data_structure(self):
        """Test that fixture data has correct structure for Stage 2."""
        fixture_path = Path("fixtures/sample_games.json")
        games_data = load_games_file(fixture_path)

        # Check metadata
        self.assertIn('date', games_data['metadata'])
        self.assertIn('type', games_data['metadata'])
        self.assertIn('week', games_data['metadata'])
        self.assertIn('year', games_data['metadata'])

        # Check games
        for game in games_data['games']:
            self.assertIn('game_id', game)
            self.assertIn('away_team', game)
            self.assertIn('home_team', game)
            self.assertIn('away_score', game)
            self.assertIn('home_score', game)
            self.assertIn('recap_text', game)
            self.assertIn('game_date_display', game)

    def test_prompt_construction_with_fixture(self):
        """Test prompt construction with fixture data."""
        fixture_path = Path("fixtures/sample_games.json")
        games_data = load_games_file(fixture_path)

        prompt_template = "You are an AI newsletter generator."
        system_prompt, user_message = construct_ai_prompt(
            games_data['games'],
            prompt_template
        )

        self.assertEqual(system_prompt, prompt_template)
        self.assertIn('NFL', user_message)
        self.assertIn('summary', user_message.lower())


if __name__ == '__main__':
    unittest.main()
