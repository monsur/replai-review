# ReplAI Review V2 Architecture

## System Overview

The V2 pipeline is a date-based, three-stage NFL newsletter generation system that can produce newsletters for individual days or entire weeks.

```
┌──────────────────────────────────────────────────────────────────┐
│                    run_all_v2.sh (Orchestration)                 │
│                                                                  │
│  Validates Input → Calculates Week → Chains All 3 Stages         │
└──────────────────────────────────────────────────────────────────┘
         ↓              ↓              ↓
    ┌─────────────┬──────────────┬──────────────┐
    │  Stage 1    │   Stage 2    │   Stage 3    │
    │Fetch Games  │  Generate    │   Publish    │
    │             │Newsletter    │              │
    └─────────────┴──────────────┴──────────────┘
         ↓              ↓              ↓
    ESPN API    AI Provider API   File System
```

## Architecture Components

### 1. Foundation Layer

#### `week_calculator.py`
- **Class:** `DateBasedWeekCalculator`
- **Purpose:** Calculate NFL week from any date in season
- **Key Method:** `get_week_for_date(target_date: datetime) -> int`
- **Logic:**
  - NFL season starts September 4, 2025 (Thursday)
  - Week = (days since start / 7) + 1
  - Clamped to 1-18 range

#### `stage_utils.py`
- **Purpose:** Shared utilities across all stages
- **Functions:**
  - Path construction: `get_week_directory()`, `get_day_subdirectory()`, `get_work_directory()`
  - File path generation: `get_games_file_path()`, `get_newsletter_file_path()`, `get_output_html_filename()`
  - Validation: `parse_date()`, `validate_type()`, `format_game_date()`

### 2. Data Models (`models.py`)

```python
class Game(BaseModel):
    game_id: str
    away_team: str
    away_abbr: str
    away_score: int
    away_record: str
    home_team: str
    home_abbr: str
    home_score: int
    home_record: str
    game_date_iso: str
    game_date_display: str
    stadium: str
    tv_network: str
    summary: str
    badges: List[str]
    recap_url: str

class NewsletterData(BaseModel):
    week: int
    year: int
    games: List[Game]
    ai_provider: str
```

### 3. Stage 1: Fetch Games

**File:** `fetch_games.py`

**Input:** Command-line arguments
- `--date`: YYYYMMDD format (e.g., 20251109)
- `--type`: 'day' or 'week'
- `--config`: Path to config.yaml

**Process:**
1. Calculate week from date using `DateBasedWeekCalculator`
2. Fetch game metadata from ESPN API (`/sports/core/competitions/` endpoint)
3. For each game, fetch recap article asynchronously
4. Filter games by date (day mode) or include all week games (week mode)
5. Parse game data into standardized format
6. Validate with Pydantic models

**Output:** `games.json`
```
tmp/YYYY-weekWW/YYYYMMDD/games.json (day mode)
tmp/YYYY-weekWW/games.json (week mode)
```

**Exit Codes:**
- 0: Success
- 1: No games found
- 2: Error (file, format, API issues)

### 4. Stage 2: Generate Newsletter

**File:** `generate_newsletter.py`

**Input:**
- `games.json` from Stage 1
- `--provider`: claude, openai, or gemini
- `--config`: Path to config.yaml

**Process:**
1. Load and validate games.json structure
2. Load AI prompt template from `newsletter_prompt.txt`
3. Construct prompt:
   - **System prompt:** Instructions for generating summaries and badges
   - **User message:** Formatted game data for all games
4. Call AI provider API with prompt
5. Extract JSON from AI response (handles markdown code blocks)
6. Parse and validate AI output
7. Merge AI data (summary, badges) with original game data
8. Remove `recap_text` to save space
9. Add metadata (timestamp, provider name)

**Output:** `newsletter.json`
```
tmp/YYYY-weekWW/YYYYMMDD/newsletter.json (day mode)
tmp/YYYY-weekWW/newsletter.json (week mode)
```

**Badge Types:**
- `upset`: Significant underdog won
- `nail-biter`: Score differential ≤ 3 points
- `comeback`: Team was down 10+ points and won
- `blowout`: Score differential ≥ 21 points
- `game-of-week`: Most exciting/significant game

### 5. Stage 3: Publish Newsletter

**File:** `publish_newsletter.py`

**Input:**
- `newsletter.json` from Stage 2
- `--output`: docs/ directory for HTML output

**Process:**
1. Load and validate newsletter.json
2. Prepare game data for template:
   - Add team icon paths
   - Classify winner/loser/tie
   - Format badges with CSS classes and emoji labels
   - Format metadata (date, stadium, network)
3. Render HTML using Jinja2 template (`newsletter_template.html`)
4. Calculate statistics (game count, upset count)
5. Update archive.json:
   - Create nested week/entry structure
   - Remove duplicate entries for same date
   - Sort entries chronologically
6. Regenerate index.html from archive.json

**Output:**
```
docs/2025-week09-sun-251109.html (day mode)
docs/2025-week09-mon-251110.html (day mode)
docs/2025-week09.html (week mode)
docs/archive.json (updated)
docs/index.html (regenerated)
```

### 6. Orchestration: run_all_v2.sh

**Purpose:** Chain all 3 stages with validation and error handling

**Process:**
1. Parse command-line arguments
2. Validate date format (YYYYMMDD)
3. Validate type (day/week)
4. Validate provider (if specified)
5. Check config file exists
6. Check Python modules installed
7. Run Stage 1 (fetch_games.py)
   - Exit if no games found (exit code 1)
   - Exit if error (exit code 2)
8. Calculate games.json path from date/week
9. Run Stage 2 (generate_newsletter.py)
   - Exit if error (exit code 2)
10. Run Stage 3 (publish_newsletter.py)
    - Exit if error (exit code 2)
11. Report success with elapsed time

**Features:**
- Color-coded output (INFO, SUCCESS, ERROR, WARNING)
- Input validation with helpful messages
- Error handling at each stage
- Time tracking

## Directory Structure

```
replai-review/
├── week_calculator.py          # Week calculation utility
├── stage_utils.py              # Shared utilities
├── models.py                   # Pydantic models
├── ai_providers.py             # AI provider abstraction
├── fetch_games.py              # Stage 1 script
├── generate_newsletter.py       # Stage 2 script
├── publish_newsletter.py        # Stage 3 script
├── run_all_v2.sh               # Orchestration script
├── newsletter_template.html    # HTML template
├── newsletter_prompt.txt       # AI prompt template
├── config.yaml                 # Configuration
├── fixtures/                   # Test fixtures
│   └── sample_games.json
├── tmp/                        # Working directory
│   └── 2025-week09/
│       ├── games.json          # Week mode
│       ├── newsletter.json
│       ├── 2025-week09.html
│       └── 20251109/           # Day mode
│           ├── games.json
│           ├── newsletter.json
│           └── 2025-week09-sun-251109.html
├── docs/                       # Output directory
│   ├── 2025-week09-sun-251109.html
│   ├── 2025-week09.html
│   ├── index.html
│   ├── archive.json
│   ├── images/                 # Team logos
│   │   ├── PHI.png
│   │   └── DAL.png
│   └── styles/
│       └── style.css
├── test_*.py                   # Unit tests
├── ARCHITECTURE_V2.md          # This file
└── MIGRATION_GUIDE.md          # Migration guide
```

## Data Flow

### Day Mode Example: November 9, 2025

```
User Input:
  ./run_all_v2.sh --date 20251109 --type day
        ↓
DateBasedWeekCalculator:
  20251109 → Week 9
        ↓
Stage 1 - Fetch Games:
  fetch_games.py --date 20251109 --type day
  ESPN API (Week 9 games) → Filter to Nov 9 → 8 games
  Output: tmp/2025-week09/20251109/games.json (8 games)
        ↓
Stage 2 - Generate Newsletter:
  generate_newsletter.py --input tmp/2025-week09/20251109/games.json
  AI Provider → Generate summaries & badges for 8 games
  Output: tmp/2025-week09/20251109/newsletter.json (8 games with summaries)
        ↓
Stage 3 - Publish:
  publish_newsletter.py --input tmp/2025-week09/20251109/newsletter.json
  Render HTML with 8 games
  Update archive.json with day entry
  Output: docs/2025-week09-sun-251109.html
        ↓
Archive Update:
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
          }
        ]
      }
    ]
  }
```

## API Integrations

### ESPN API

**Endpoint:** `https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard`

**Response:** Game metadata with:
- Team names and abbreviations
- Scores and records
- Stadium and broadcast info
- Game dates in ISO format

### AI Provider APIs

Abstracted via `ai_providers.py`:
- **Claude (Anthropic):** `anthropic.Anthropic().messages.create()`
- **OpenAI:** `openai.OpenAI().chat.completions.create()`
- **Gemini (Google):** `google.generativeai.GenerativeModel()`

All return text response with JSON format.

## Error Handling Strategy

### Validation Errors
```
Input → Validate → Fail → Show error message → Exit 3
```

### Runtime Errors
```
Process → Fail → Log error details → Exit 2
```

### No Data Found
```
Fetch → No games → Log warning → Exit 1
```

## Testing Strategy

**Test Files:**
- `test_stage_utils.py` - 60 tests for utility functions
- `test_fetch_games.py` - 25 tests for Stage 1
- `test_generate_newsletter.py` - 26 tests for Stage 2 (requires AI provider)
- `test_publish_newsletter.py` - 23 tests for Stage 3
- `test_orchestration.py` - 24 tests for shell script validation

**Total Coverage:** 158 unit tests

**Fixtures:** `fixtures/sample_games.json` for offline testing

## Performance Considerations

### Parallel Operations
- **Stage 1:** Recap fetching uses ThreadPoolExecutor with max_workers=5
- **Pipeline:** Stages run sequentially (each depends on previous output)

### Data Size
- Typical week: 16 games
- Typical day: 0-2 games
- JSON size without recap_text: ~50KB
- HTML output: ~100KB

### API Limits
- ESPN API: No known rate limits (tested with 5 parallel requests)
- AI Provider: Depends on plan (usually 60+ requests/min for paid tiers)

## Configuration

**config.yaml structure:**
```yaml
ai:
  active_provider: claude  # or openai, gemini
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

## Security Considerations

- **API Keys:** Stored in config.yaml (use environment variables)
- **File Permissions:** HTML output readable by all (public)
- **Input Validation:** All user inputs validated before use
- **Command Injection:** All shell inputs quoted/escaped in orchestration script

## Future Enhancements

1. **Parallel Stage Execution:** Run stages in parallel if Stage 1 outputs are cached
2. **Caching:** Cache ESPN API results with TTL
3. **Incremental Updates:** Update only changed games in archive
4. **Multi-day Batching:** Generate multiple days in one orchestration call
5. **Web UI:** Dashboard for schedule and viewing past newsletters
6. **Email Integration:** Automatic email distribution
7. **Social Media:** Auto-post to Twitter/Bluesky
8. **Database:** Replace file-based storage with database

## Comparison to V1

| Aspect | V1 | V2 |
|--------|----|----|
| **Inputs** | Week numbers | Dates (flexible) |
| **Stages** | 4 (separate archive update) | 3 (built-in archive) |
| **Orchestration** | Manual script chaining | Unified shell script |
| **Directory Structure** | Flat | Nested (supports daily) |
| **Error Handling** | Limited | Comprehensive |
| **Testing** | Fewer tests | 158 unit tests |
| **Date Flexibility** | Fixed (full week) | Flexible (any date) |

## Conclusion

V2 provides a cleaner, more flexible, and well-tested approach to newsletter generation with support for both daily and weekly publishing modes, while maintaining compatibility with the AI provider ecosystem established in V1.
