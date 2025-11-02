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
├── docs/                      # Public-facing files (GitHub Pages ready)
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

3. **Set up API keys**:

   API keys must be set as environment variables. Create a `.env` file from the template:
   ```bash
   cp .env.template .env
   ```

   Edit `.env` and add your API keys, then source it:
   ```bash
   source .env
   ```

   Or set environment variables directly:
   ```bash
   export ANTHROPIC_API_KEY="your-anthropic-key-here"
   export OPENAI_API_KEY="your-openai-key-here"
   export GOOGLE_API_KEY="your-google-key-here"
   ```

   You only need to set the API key for the provider you're using.

   **Where to get API keys**:
   - Claude: [console.anthropic.com](https://console.anthropic.com/)
   - OpenAI: [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
   - Gemini: [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)

4. **Configure the application**:

   Edit `config.yaml` to update:
   - `nfl_season.year`: Current NFL season year
   - `nfl_season.season_start_date`: First game date of the season
   - `ai.active_provider`: Your preferred AI provider (`claude`, `openai`, or `gemini`)

   **Note**: API keys are NOT stored in `config.yaml` - they must be set as environment variables for security.

## Usage

### Quick Start (Run All Scripts)

Generate a complete newsletter for the current week:

```bash
# Fetch recaps from ESPN
python fetch_recaps.py

# Clean and combine recaps
python process_recaps.py

# Generate JSON with AI
python generate_json.py

# Format JSON into HTML newsletter
python format_newsletter.py
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

### Script 3a: Generate JSON

Uses AI to generate structured JSON data from the combined recaps.

```bash
# Generate JSON (uses provider from config)
python generate_json.py

# Override AI provider
python generate_json.py --provider openai

# Process specific week
python generate_json.py --week 8

# Combine options
python generate_json.py --week 8 --provider claude
```

**Output**: Creates `tmp/YYYY-weekWW/newsletter.json` (e.g., `tmp/2025-week08/newsletter.json`) with structured game data.

### Script 3b: Format Newsletter

Formats the JSON data into a complete HTML newsletter.

```bash
# Format newsletter for current week
python format_newsletter.py

# Format specific week
python format_newsletter.py --week 8

# Use custom JSON file
python format_newsletter.py --json-file tmp/2025-week08/newsletter.json
```

**Output**: Creates `docs/YYYY-weekWW.html` (e.g., `docs/2025-week08.html`) - the final newsletter ready to view or distribute. Also updates `docs/index.html` and `docs/archive.json`.

### View the Newsletter

Open the generated newsletter in your browser:

```bash
# macOS
open docs/2025-week08.html

# Linux
xdg-open docs/2025-week08.html

# Windows
start docs/2025-week08.html
```

### Benefits of the Split Workflow

The newsletter generation is split into two scripts for flexibility:

- **`generate_json.py`**: Calls the AI API to generate structured JSON data
- **`format_newsletter.py`**: Formats the JSON into the final HTML newsletter

**Why this split is useful**:
1. **Regenerate HTML without AI calls**: If you want to tweak the HTML formatting or fix a bug, you can run `format_newsletter.py` alone without calling the AI API again (saving time and API costs)
2. **Manual JSON editing**: You can manually edit the JSON file (fix typos, adjust scores, etc.) before formatting
3. **Testing**: Test HTML formatting changes quickly by reusing existing JSON
4. **Debugging**: Easier to debug issues - is the problem with AI generation or HTML formatting?

Example workflow:
```bash
# Generate JSON once (costs API credits)
python generate_json.py --week 8

# Format to HTML (free, instant)
python format_newsletter.py --week 8

# Made a CSS change? Regenerate HTML instantly:
python format_newsletter.py --week 8

# Need to fix a typo in the JSON? Edit tmp/2025-week08/newsletter.json, then:
python format_newsletter.py --week 8
```

### Customizing the Newsletter Template

The newsletter HTML and CSS are defined in `newsletter_template.html`, making it easy to customize the design without touching Python code.

**Template file**: `newsletter_template.html`
- Uses [Jinja2 templating](https://jinja.palletsprojects.com/) for dynamic content
- Contains all HTML structure and CSS styles
- Edit this file to change colors, fonts, layout, or any visual elements

**After editing the template**, simply regenerate the HTML:
```bash
python format_newsletter.py --week 8
```

No need to regenerate JSON - the template changes apply instantly!

**Template variables available**:
- `week`: NFL week number
- `game_count`: Total number of games
- `upset_count`: Number of upset games
- `games`: Array of game objects with all game data (teams, scores, badges, etc.)

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
  docs_dir: "docs"    # Public-facing files (newsletters, team logos) - GitHub Pages ready
  tmp_dir: "tmp"      # Temporary processing files
  recap_subdir: "recaps"
  combined_filename: "combined.html"
  # Newsletter filename is dynamically generated as: YYYY-weekWW.html
```

### AI Provider Settings

```yaml
ai:
  active_provider: "claude"  # claude, openai, or gemini

  # API keys must be set via environment variables:
  # - ANTHROPIC_API_KEY for Claude
  # - OPENAI_API_KEY for OpenAI
  # - GOOGLE_API_KEY for Gemini

  claude:
    model: "claude-3-5-sonnet-20241022"
    max_tokens: 4096

  openai:
    model: "gpt-4o"
    max_tokens: 4096

  gemini:
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
echo "Newsletter generated: docs/$(date +\%Y)-week$(date +\%U).html"
```

## Troubleshooting

### No recap links found
- **Cause**: Week hasn't been played yet, or ESPN page structure changed
- **Solution**: Check the week number, verify the URL, or manually specify `--week`

### API key errors
- **Cause**: Missing or invalid API key
- **Solution**: Set the required environment variable (ANTHROPIC_API_KEY, OPENAI_API_KEY, or GOOGLE_API_KEY). Use `source .env` if you created a `.env` file.

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
mv docs/2025-week08.html docs/2025-week08-claude.html

python generate_newsletter.py --week 8 --provider openai
mv docs/2025-week08.html docs/2025-week08-openai.html

python generate_newsletter.py --week 8 --provider gemini
```

## GitHub Actions Automation

The project includes a GitHub Actions workflow that automatically generates newsletters weekly.

### Setup

1. **Push your repository to GitHub**

2. **Configure GitHub Secrets** - Go to your repository Settings → Secrets and variables → Actions, and add these secrets:
   - `ANTHROPIC_API_KEY` - Your Claude API key (if using Claude)
   - `OPENAI_API_KEY` - Your OpenAI API key (if using OpenAI)
   - `GOOGLE_API_KEY` - Your Google API key (if using Gemini)

   You only need to add the secret for the AI provider configured in `config.yaml`. The workflow will automatically expose these secrets as environment variables for the Python scripts.

3. **Enable GitHub Pages** (optional but recommended):
   - Go to Settings → Pages
   - Source: Deploy from a branch
   - Branch: `main` / `docs`
   - Your newsletters will be available at: `https://[username].github.io/[repo-name]/`

### How It Works

The workflow (`.github/workflows/generate-newsletter.yml`) runs:
- **Scheduled**: Every Tuesday at 4:00 AM Central Time (10:00 AM UTC)
- **Manual**: Can be triggered manually from the Actions tab in GitHub

When triggered, it will:
1. Fetch game recaps from ESPN
2. Process and combine recaps
3. Generate newsletter JSON using AI
4. Format HTML newsletter
5. Commit the generated files to the repository
6. Push changes back to GitHub

### Manual Trigger

To generate a newsletter manually:
1. Go to the "Actions" tab in your GitHub repository
2. Select "Generate Weekly NFL Newsletter"
3. Click "Run workflow"
4. The workflow will process the last complete week

### Viewing Logs

Check the Actions tab to see workflow runs, logs, and any errors. If generation fails, debug files will be uploaded as artifacts.

### Notes

- The workflow uses the date-based week calculator, so it automatically generates newsletters for the most recently completed week
- If you want to generate a specific week, you'll need to run the scripts locally with the `--week` flag
- The workflow commits with a bot account, so commits will show as "github-actions[bot]"

## Email Distribution (Optional)

The project supports automatic email distribution via **Buttondown** - a simple, developer-friendly newsletter service.

### Why Buttondown?

- **Free for up to 100 subscribers**
- Simple API (perfect for automation)
- Handles subscriber management, unsubscribes, and spam compliance
- Clean, minimal interface
- Embeddable signup forms

### Setup Email Distribution

1. **Sign up for Buttondown**
   - Go to [buttondown.email](https://buttondown.email)
   - Create a free account
   - Choose your newsletter name (e.g., "replai-review")

2. **Get your API key**
   - Go to Settings → API
   - Copy your API key

3. **Add API key to GitHub Secrets**
   - Go to your repository Settings → Secrets and variables → Actions
   - Click "New repository secret"
   - Name: `BUTTONDOWN_API_KEY`
   - Value: Your Buttondown API key

4. **Configure GitHub Pages URL** (required for images in email)
   - Make sure `github_pages_url` is set in your `config.yaml`:
   ```yaml
   github_pages_url: "https://[username].github.io/[repo-name]"
   ```

5. **Done!** The workflow will now automatically email your newsletter to subscribers when it's generated.

### How Email Distribution Works

When the GitHub Actions workflow runs:
1. Generates the newsletter (as usual)
2. If there's a new newsletter AND `BUTTONDOWN_API_KEY` is configured:
   - Sends the newsletter to all Buttondown subscribers
   - Uses the HTML file with absolute image URLs
3. Subscribers receive the email automatically

### Add Signup Form to Your Site

Buttondown provides embeddable signup forms. Add this to your `docs/index.html` or create a separate signup page:

```html
<form
  action="https://buttondown.email/api/emails/embed-subscribe/[your-username]"
  method="post"
  target="popupwindow"
>
  <label for="bd-email">Subscribe to ReplAI Review:</label>
  <input type="email" name="email" id="bd-email" placeholder="Enter your email" required />
  <input type="submit" value="Subscribe" />
</form>
```

Replace `[your-username]` with your Buttondown username.

### Managing Subscribers

All subscriber management happens in Buttondown:
- View subscribers
- Manually add/remove subscribers
- See email statistics (opens, clicks)
- Manage unsubscribes automatically

### Cost

- **Free**: Up to 100 subscribers
- **$9/month**: Up to 1,000 subscribers
- **$29/month**: Up to 10,000 subscribers

Perfect for starting out - upgrade only when you grow!

### Testing Email Sending

To test email distribution without waiting for Tuesday:
1. Go to Actions tab
2. Click "Generate Weekly NFL Newsletter"
3. Click "Run workflow"
4. The workflow will generate the latest newsletter and send it via email (if configured)

**Note:** If a newsletter for the current week already exists, it won't send again (prevents duplicate emails).

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
2. API keys are set as environment variables (use `source .env` or `export` commands)
3. Config file is properly configured with season settings
4. Season start date is correct for current NFL season
5. You have an active internet connection for scraping ESPN
