# ReplAI Review V2 - NFL Newsletter Pipeline

## Quick Start

### 1. Setup

```bash
# Install dependencies
pip install -q requests beautifulsoup4 pyyaml jinja2 pydantic

# For Claude
pip install -q anthropic

# For OpenAI
pip install -q openai

# For Google Gemini
pip install -q google-generativeai
```

### 2. Configure

Create `config.yaml`:
```yaml
ai:
  active_provider: claude
  providers:
    claude:
      api_key: ${ANTHROPIC_API_KEY}
      model: claude-3-5-sonnet-20241022
    openai:
      api_key: ${OPENAI_API_KEY}
      model: gpt-4o
    gemini:
      api_key: ${GOOGLE_API_KEY}
      model: gemini-2.0-flash

newsletter_prompt_file: newsletter_prompt.txt
template_file: newsletter_template.html
```

### 3. Generate Newsletter

```bash
# Generate for single day
./run_all_v2.sh --date 20251109 --type day

# Generate for entire week
./run_all_v2.sh --date 20251109 --type week

# Use different AI provider
./run_all_v2.sh --date 20251109 --type day --provider openai
```

## Usage Examples

### Example 1: Sunday Games (November 9, 2025)

```bash
./run_all_v2.sh --date 20251109 --type day --provider claude
```

Output:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ReplAI Review - V2 Pipeline
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ℹ  Date: 20251109
ℹ  Type: day
ℹ  Provider: claude
ℹ  Config: ./config.yaml

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STAGE 1: FETCH GAMES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ℹ  Fetching games for date: 20251109 (type: day)
✅ Loaded 8 games
   Date: 20251109, Type: day, Week: 9
✅ Stage 1 complete

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STAGE 2: GENERATE NEWSLETTER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ℹ  Loading games from: tmp/2025-week09/20251109/games.json
✅ Parsed 8 game outputs
✅ Validation passed!
   - 8 games
   - 2 upsets
✅ Stage 2 complete

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STAGE 3: PUBLISH NEWSLETTER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ℹ  Loading newsletter from: tmp/2025-week09/20251109/newsletter.json
✅ Prepared 8 games for rendering
✅ Rendered HTML
✅ Updated archive.json
✅ Regenerated index.html
✅ Stage 3 complete

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ PIPELINE COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Newsletter published successfully!
ℹ  Elapsed time: 1m 23s
ℹ  HTML: docs/
ℹ  Archive: docs/archive.json
```

### Example 2: Week Mode (All Week 9 Games)

```bash
./run_all_v2.sh --date 20251109 --type week --provider openai
```

This generates a single newsletter with all 16 games from the entire week (Thursday through Monday).

Output: `docs/2025-week09.html`

### Example 3: Using Different Provider

```bash
# Use Gemini
./run_all_v2.sh --date 20251109 --type day --provider gemini

# Use custom config
./run_all_v2.sh --date 20251109 --type day --config /etc/replai/config.yaml
```

## Directory Structure

After running the pipeline:

```
replai-review/
├── tmp/
│   └── 2025-week09/
│       ├── games.json (week mode only)
│       ├── newsletter.json (week mode only)
│       ├── 2025-week09.html (week mode only)
│       └── 20251109/
│           ├── games.json (day mode)
│           ├── newsletter.json (day mode)
│           └── 2025-week09-sun-251109.html (day mode)
│
└── docs/
    ├── 2025-week09-sun-251109.html (day mode)
    ├── 2025-week09.html (week mode)
    ├── archive.json
    ├── index.html
    └── images/
        ├── PHI.png
        ├── DAL.png
        └── ... (team icons)
```

## File Outputs

### games.json (Stage 1)

Contains raw game data from ESPN API:

```json
{
  "metadata": {
    "date": "20251109",
    "type": "day",
    "week": 9,
    "year": 2025,
    "fetched_at": "2025-11-08T20:30:00+00:00"
  },
  "games": [
    {
      "game_id": "401547891",
      "away_team": "Philadelphia Eagles",
      "away_abbr": "PHI",
      "away_score": 28,
      "away_record": "8-1",
      "home_team": "Dallas Cowboys",
      "home_abbr": "DAL",
      "home_score": 23,
      "home_record": "4-5",
      "game_date_iso": "2025-11-09T13:00Z",
      "game_date_display": "Sun 11/9 9:00AM ET",
      "stadium": "AT&T Stadium",
      "tv_network": "FOX",
      "recap_url": "https://www.espn.com/nfl/story/...",
      "recap_text": "The Eagles dominated the Cowboys..."
    }
  ]
}
```

### newsletter.json (Stage 2)

Contains AI-generated summaries and badges:

```json
{
  "metadata": {
    "date": "20251109",
    "type": "day",
    "week": 9,
    "year": 2025,
    "fetched_at": "2025-11-08T20:30:00+00:00",
    "generated_at": "2025-11-08T20:35:00+00:00",
    "ai_provider": "claude"
  },
  "games": [
    {
      "game_id": "401547891",
      "away_team": "Philadelphia Eagles",
      "away_abbr": "PHI",
      "away_score": 28,
      "away_record": "8-1",
      "home_team": "Dallas Cowboys",
      "home_abbr": "DAL",
      "home_score": 23,
      "home_record": "4-5",
      "game_date_iso": "2025-11-09T13:00Z",
      "game_date_display": "Sun 11/9 9:00AM ET",
      "stadium": "AT&T Stadium",
      "tv_network": "FOX",
      "recap_url": "https://www.espn.com/nfl/story/...",
      "summary": "<strong>Jalen Hurts</strong> led the Eagles' dominant performance...",
      "badges": ["upset"]
    }
  ]
}
```

### archive.json (Updated in Stage 3)

Maintains history of all newsletters:

```json
{
  "newsletters": [
    {
      "week": 9,
      "year": 2025,
      "entries": [
        {
          "type": "day",
          "date": "2025-11-09",
          "day": "Sunday",
          "filename": "2025-week09-sun-251109.html",
          "game_count": 8
        },
        {
          "type": "day",
          "date": "2025-11-10",
          "day": "Monday",
          "filename": "2025-week09-mon-251110.html",
          "game_count": 1
        }
      ]
    }
  ]
}
```

## Command Reference

### run_all_v2.sh

```bash
./run_all_v2.sh [OPTIONS]

Required:
  --date DATE          Date in YYYYMMDD format (e.g., 20251109)

Optional:
  --type TYPE          Newsletter type: 'day' or 'week' (default: day)
  --provider PROVIDER  AI provider: claude, openai, or gemini
  --config CONFIG      Path to config.yaml (default: ./config.yaml)
  --help              Show help message

Exit Codes:
  0 = Success
  1 = No games found for given date
  2 = Error (file not found, invalid format, etc.)
  3 = Invalid arguments
```

### Individual Stages

Run individual stages if needed:

```bash
# Stage 1: Fetch games
python3 fetch_games.py --date 20251109 --type day

# Stage 2: Generate newsletter
python3 generate_newsletter.py --input tmp/2025-week09/20251109/games.json

# Stage 3: Publish
python3 publish_newsletter.py --input tmp/2025-week09/20251109/newsletter.json
```

## Testing

Run all tests:

```bash
# Run all tests
python -m unittest discover -p "test_*.py" -v

# Run specific test file
python -m unittest test_orchestration.py -v

# Run with coverage (requires coverage package)
coverage run -m unittest discover && coverage report
```

### Test Coverage

- **stage_utils.py** - 60 tests
- **fetch_games.py** - 25 tests
- **generate_newsletter.py** - 26 tests (skipped if no AI provider)
- **publish_newsletter.py** - 23 tests
- **orchestration** - 24 tests

Total: 158 tests

## Troubleshooting

### "No games found" Error

**Cause:** ESPN didn't schedule games for that date.

**Solution:** Try a different date, or use `--type week` to get the entire week.

```bash
# Try a different date
./run_all_v2.sh --date 20251108 --type day

# Or use week mode
./run_all_v2.sh --date 20251109 --type week
```

### "Module not found" Error

**Cause:** Missing Python dependencies.

**Solution:** Install requirements.

```bash
pip install -q requests beautifulsoup4 pyyaml jinja2 pydantic anthropic
```

### "API Key Error" Error

**Cause:** AI provider API key not set or invalid.

**Solution:** Set environment variable or check config.yaml.

```bash
export ANTHROPIC_API_KEY="your-key-here"
./run_all_v2.sh --date 20251109 --type day
```

### "Invalid date format" Error

**Cause:** Date not in YYYYMMDD format.

**Solution:** Use correct format.

```bash
# Correct
./run_all_v2.sh --date 20251109 --type day

# Incorrect - these won't work
./run_all_v2.sh --date 2025-11-09 --type day
./run_all_v2.sh --date 11/9/2025 --type day
```

## File Outputs Details

### HTML Files

Generated in `docs/` directory with responsive design:
- Day mode: `2025-week09-sun-251109.html` (one per day)
- Week mode: `2025-week09.html` (all week in one file)

Features:
- Responsive grid layout
- Team icons and colors
- Game summaries with badges
- Game metadata (stadium, TV network)
- Links to ESPN recaps

### index.html

Automatically generated homepage listing all newsletters:
- Grouped by week
- Shows game count for each day/week
- Responsive design with CSS gradient

## Performance Notes

### Timing (Typical)

- Stage 1 (Fetch): 10-15 seconds (API + scraping)
- Stage 2 (AI Generation): 30-90 seconds (depends on AI provider and model)
- Stage 3 (Publish): 1-2 seconds (rendering + archive update)
- **Total:** 1-2 minutes for full pipeline

### Memory Usage

- Typical: 50-100 MB
- Large week: ~150 MB

### File Sizes

- games.json: ~50-100 KB
- newsletter.json: ~40-80 KB
- HTML file: ~100-150 KB

## Best Practices

1. **Use Day Mode by Default**
   ```bash
   ./run_all_v2.sh --date 20251109 --type day
   ```
   Generates cleaner, focused newsletter per day.

2. **Batch Weeks on Demand**
   ```bash
   ./run_all_v2.sh --date 20251109 --type week
   ```
   For comprehensive weekly summaries.

3. **Cache ESPN Results**
   Once fetched, reuse Stage 1 output for multiple AI providers:
   ```bash
   # Fetch once
   python3 fetch_games.py --date 20251109 --type day

   # Generate with different providers
   python3 generate_newsletter.py --input tmp/2025-week09/20251109/games.json --provider claude
   python3 generate_newsletter.py --input tmp/2025-week09/20251109/games.json --provider openai
   ```

4. **Monitor Archive Size**
   archive.json grows over season. Prune old entries if it gets too large:
   ```bash
   # Keep only last 5 weeks
   python3 -c "
   import json
   with open('docs/archive.json') as f:
       data = json.load(f)
   data['newsletters'] = data['newsletters'][-5:]
   with open('docs/archive.json', 'w') as f:
       json.dump(data, f, indent=2)
   "
   ```

5. **Use Version Control**
   ```bash
   git add docs/archive.json docs/*.html
   git commit -m "Week 9 newsletters"
   ```

## Environment Variables

Optional environment variables (use `config.yaml` instead for production):

```bash
# AI Provider Keys
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
export GOOGLE_API_KEY="AIza..."

# Run pipeline
./run_all_v2.sh --date 20251109 --type day
```

## Getting Help

1. Check error messages - they're designed to be helpful
2. Review `ARCHITECTURE_V2.md` for system design details
3. Review `MIGRATION_GUIDE.md` if upgrading from V1
4. Run tests: `python -m unittest discover -v`
5. Check individual stage docstrings: `python3 fetch_games.py --help`

## Next Steps

After generating your first newsletter:

1. Review the HTML output in `docs/`
2. Check archive.json structure
3. Modify `newsletter_template.html` for custom styling
4. Adjust `newsletter_prompt.txt` for different summary style
5. Setup automation (cron job, GitHub Actions, etc.)

Enjoy your automated NFL newsletters! 🏈📰
