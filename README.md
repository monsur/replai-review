# ReplAI Review

An automated system for generating AI-powered NFL weekly recaps from ESPN game data. **ReplAI Review** uses artificial intelligence to create concise, informative newsletters for casual sports fans. The system is divided into three independent scripts that can be run separately or chained together.

## Features

- **Automated week detection**: Automatically determines which NFL week to process based on current date
- **Web scraping**: Fetches game recaps from ESPN.com
- **Content processing**: Cleans and combines recap HTML for AI processing
- **AI-powered generation**: Uses AI to create concise, informative newsletters
- **Swappable AI providers**: Easily switch between Claude (Anthropic), OpenAI, and Google Gemini
- **Flexible architecture**: Each script can run independently or be chained together

## Project Structure

```
football/
├── config.yaml                 # Configuration file
├── newsletter_prompt.txt       # AI prompt template (editable)
├── week_calculator.py          # Swappable week calculation module
├── ai_providers.py             # Swappable AI provider system
├── fetch_recaps.py             # Script 1: Fetch game recaps from ESPN
├── process_recaps.py           # Script 2: Clean and combine recaps
├── generate_newsletter.py      # Script 3: Generate newsletter with AI
├── requirements.txt            # Python dependencies
├── README.md                  # This file
├── web/                       # Public-facing files
│   ├── images/               # Team logo images
│   ├── 2025-week08.html     # Generated newsletters
│   └── 2025-week09.html
└── tmp/                       # Temporary processing files
    └── 2025-weekWW/          # Format: YYYY-weekWW (e.g., 2025-week08)
        ├── recaps/            # Downloaded recap HTML files
        ├── combined.html      # Combined and cleaned recaps
        └── newsletter_week_8.json  # AI-generated JSON (debug)
```

## Installation

1. **Clone or download this project**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

   Note: You only need to install the AI provider package you plan to use:
   - Claude: `pip install anthropic`
   - OpenAI: `pip install openai`
   - Gemini: `pip install google-generativeai`

3. **Configure the application**:

   Edit `config.yaml` and update:
   - `nfl_season.year`: Current NFL season year
   - `nfl_season.season_start_date`: First game date of the season
   - `ai.active_provider`: Your preferred AI provider (`claude`, `openai`, or `gemini`)
   - `ai.[provider].api_key`: Your API key (or set as environment variable)

   **API Key Options**:
   - Set in `config.yaml` (e.g., `api_key: "your-key-here"`)
   - Or use environment variables:
     - Claude: `export ANTHROPIC_API_KEY="your-key"`
     - OpenAI: `export OPENAI_API_KEY="your-key"`
     - Gemini: `export GOOGLE_API_KEY="your-key"`

## Usage

### Quick Start (Run All Scripts)

Generate a complete newsletter for the current week:

```bash
# Fetch recaps from ESPN
python fetch_recaps.py

# Clean and combine recaps
python process_recaps.py

# Generate newsletter with AI
python generate_newsletter.py
```

### Script 1: Fetch Recaps

Downloads game recap HTML files from ESPN for a specific week.

```bash
# Auto-detect week (based on current date)
python fetch_recaps.py

# Specify a week manually
python fetch_recaps.py --week 8

# Use custom config file
python fetch_recaps.py --config my_config.yaml
```

**Output**: Creates `tmp/YYYY-weekWW/recaps/` directory (e.g., `tmp/2025-week08/recaps/`) with HTML files for each game.

### Script 2: Process Recaps

Cleans recap HTML files and combines them into a single file.

```bash
# Process current week
python process_recaps.py

# Process specific week
python process_recaps.py --week 8

# Use custom config file
python process_recaps.py --config my_config.yaml
```

**Output**: Creates `tmp/YYYY-weekWW/combined.html` (e.g., `tmp/2025-week08/combined.html`) with cleaned and combined recaps.

### Script 3: Generate Newsletter

Uses AI to generate a formatted newsletter from the combined recaps.

```bash
# Generate newsletter (uses provider from config)
python generate_newsletter.py

# Override AI provider
python generate_newsletter.py --provider openai

# Process specific week
python generate_newsletter.py --week 8

# Combine options
python generate_newsletter.py --week 8 --provider claude
```

**Output**: Creates `web/YYYY-weekWW.html` (e.g., `web/2025-week08.html`) - the final newsletter ready to view or distribute.

### View the Newsletter

Open the generated newsletter in your browser:

```bash
# macOS
open web/2025-week08.html

# Linux
xdg-open web/2025-week08.html

# Windows
start web/2025-week08.html
```

## Configuration

### NFL Season Settings

```yaml
nfl_season:
  year: 2024
  season_start_date: "2024-09-05"  # First game of Week 1
```

Update `season_start_date` at the beginning of each NFL season.

### Storage Settings

```yaml
storage:
  web_dir: "web"      # Public-facing files (newsletters, team logos)
  tmp_dir: "tmp"      # Temporary processing files
  recap_subdir: "recaps"
  combined_filename: "combined.html"
  # Newsletter filename is dynamically generated as: YYYY-weekWW.html
```

### AI Provider Settings

```yaml
ai:
  active_provider: "claude"  # claude, openai, or gemini

  claude:
    api_key: "YOUR_CLAUDE_API_KEY_HERE"
    model: "claude-3-5-sonnet-20241022"
    max_tokens: 4096

  openai:
    api_key: "YOUR_OPENAI_API_KEY_HERE"
    model: "gpt-4o"
    max_tokens: 4096

  gemini:
    api_key: "YOUR_GEMINI_API_KEY_HERE"
    model: "gemini-1.5-pro"
    max_tokens: 4096
```

### Newsletter Prompt

The AI prompt is stored in `newsletter_prompt.txt` and controls all aspects of generation:
- Newsletter tone and style
- Summary length (3-7 sentences, 200 words max)
- HTML structure for each game
- Content formula (star player → game flow → context)
- Score format rules
- Writing style guidelines

**To customize**: Edit `newsletter_prompt.txt` to change any aspect of the newsletter. Changes take effect immediately on the next run.

### Experimenting with Newsletter Format

Use `newsletter_playground.html` to safely experiment with the newsletter format:

1. Open `newsletter_playground.html` in your browser
2. Edit the HTML structure and CSS styling
3. Refresh to see changes instantly
4. Copy changes to the appropriate files:

**If you changed CSS styles:**
- Copy the "WRAPPER SECTION" (between START/END markers)
- Paste into `generate_newsletter.py` → `wrap_newsletter_html()` function → inside the `<style>` tag

**If you changed HTML structure:**
- Copy the game entry template structure
- Paste into `newsletter_prompt.txt` → "STRUCTURE REQUIREMENTS" section

The playground clearly marks which sections go where, making it easy to apply your changes to the right files.

## Week Calculation

The system uses a **date-based week calculator** by default:

- Calculates NFL week based on season start date
- If today is Mon/Tue/Wed, returns the previous week (games just finished)
- If today is Thu/Fri/Sat/Sun, returns current week

**Override week calculation**:
- Use `--week` argument: `python fetch_recaps.py --week 8`
- This is useful for generating newsletters for past weeks or testing

**Future implementations**:
The week calculation logic is isolated in `week_calculator.py` and can be easily swapped with other strategies (e.g., scraping current week from ESPN).

## AI Provider System

The AI provider system is **fully swappable**:

1. **Base class**: `AIProvider` abstract class defines the interface
2. **Implementations**: `ClaudeProvider`, `OpenAIProvider`, `GeminiProvider`
3. **Factory function**: `create_ai_provider()` instantiates the right provider

**Switch providers**:
- In config: Set `ai.active_provider` to `claude`, `openai`, or `gemini`
- Via CLI: Use `--provider` flag with `generate_newsletter.py`

**Add new providers**:
1. Create a new class extending `AIProvider` in `ai_providers.py`
2. Implement the `generate(prompt, content)` method
3. Update the factory function
4. Add configuration to `config.yaml`

## Automation

To run weekly automatically, create a cron job or scheduled task:

```bash
# Example cron job (runs every Tuesday at 9 AM)
0 9 * * 2 cd /path/to/football && python fetch_recaps.py && python process_recaps.py && python generate_newsletter.py
```

Or use a shell script:

```bash
#!/bin/bash
cd /path/to/football
python fetch_recaps.py && \
python process_recaps.py && \
python generate_newsletter.py
echo "Newsletter generated: web/$(date +\%Y)-week$(date +\%U).html"
```

## Troubleshooting

### No recap links found
- **Cause**: Week hasn't been played yet, or ESPN page structure changed
- **Solution**: Check the week number, verify the URL, or manually specify `--week`

### API key errors
- **Cause**: Missing or invalid API key
- **Solution**: Set API key in `config.yaml` or as environment variable

### Import errors
- **Cause**: Missing dependencies
- **Solution**: Install required packages: `pip install -r requirements.txt`

### Week calculation seems off
- **Cause**: Incorrect season start date
- **Solution**: Update `nfl_season.season_start_date` in `config.yaml`

## Advanced Usage

### Custom Newsletter Format

Edit `newsletter_prompt.txt` to customize:
- Summary length (currently 3-7 sentences, 200 words max)
- Tone (currently informational and succinct)
- Additional content (e.g., stats, player highlights, predictions)
- HTML structure and styling instructions

### Process Multiple Weeks

```bash
for week in {5..8}; do
  python fetch_recaps.py --week $week
  python process_recaps.py --week $week
  python generate_newsletter.py --week $week
done
```

### Compare AI Providers

Generate newsletters with different providers for the same week:

```bash
python generate_newsletter.py --week 8 --provider claude
mv web/2025-week08.html web/2025-week08-claude.html

python generate_newsletter.py --week 8 --provider openai
mv web/2025-week08.html web/2025-week08-openai.html

python generate_newsletter.py --week 8 --provider gemini
```

## License

This project is provided as-is for personal use.

## Contributing

Suggestions and improvements welcome! Key areas for enhancement:
- Better HTML parsing for ESPN's dynamic page structure
- Additional AI providers
- Alternative week calculation strategies
- Email distribution integration
- Enhanced newsletter formatting

---

**Questions or Issues?**

Check that:
1. Dependencies are installed: `pip install -r requirements.txt`
2. Config file is properly configured with API keys
3. Season start date is correct for current NFL season
4. You have an active internet connection for scraping ESPN
