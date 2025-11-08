# Troubleshooting Guide - ReplAI Review V2

## Common Issues and Solutions

### Input Validation Issues

#### "Missing required argument: --date"

**Error Message:**
```
❌ Error: Missing required argument: --date
```

**Cause:** You didn't provide the required `--date` argument.

**Solution:**
```bash
# Wrong (missing --date)
./run_all_v2.sh --type day

# Correct (include --date)
./run_all_v2.sh --date 20251109 --type day
```

---

#### "Invalid date format"

**Error Message:**
```
❌ Error: Invalid date format: 2025-11-09
Invalid date: Expected YYYYMMDD format (e.g., 20251109)
```

**Cause:** Date not in correct YYYYMMDD format.

**Solution:**
```bash
# Wrong formats
./run_all_v2.sh --date 2025-11-09 --type day    # ISO format
./run_all_v2.sh --date 11/9/2025 --type day     # US format
./run_all_v2.sh --date "Nov 9, 2025" --type day # Text format

# Correct format
./run_all_v2.sh --date 20251109 --type day
```

---

#### "Invalid month"

**Error Message:**
```
❌ Error: Invalid month: 13
```

**Cause:** Month is outside 01-12 range.

**Solution:**
```bash
# Validate month is 01-12
# 20251309 has month 13 (invalid)
./run_all_v2.sh --date 20251109 --type day  # Correct: month 11
```

---

#### "Invalid day"

**Error Message:**
```
❌ Error: Invalid day: 32
```

**Cause:** Day is outside valid range for the month.

**Solution:**
```bash
# November only has 30 days
./run_all_v2.sh --date 20251131 --type day  # Wrong: Nov 31

# Correct dates
./run_all_v2.sh --date 20251130 --type day  # Nov 30
./run_all_v2.sh --date 20251109 --type day  # Nov 9
```

---

#### "Invalid type"

**Error Message:**
```
❌ Error: Invalid type: monthly
Expected 'day' or 'week'
```

**Cause:** Type must be 'day' or 'week'.

**Solution:**
```bash
# Wrong
./run_all_v2.sh --date 20251109 --type monthly
./run_all_v2.sh --date 20251109 --type WEEK

# Correct
./run_all_v2.sh --date 20251109 --type day
./run_all_v2.sh --date 20251109 --type week
```

---

#### "Invalid provider"

**Error Message:**
```
❌ Error: Invalid provider: gpt4
Expected 'claude', 'openai', or 'gemini'
```

**Cause:** Provider must be one of: claude, openai, gemini.

**Solution:**
```bash
# Wrong
./run_all_v2.sh --date 20251109 --type day --provider gpt4
./run_all_v2.sh --date 20251109 --type day --provider CLAUDE

# Correct
./run_all_v2.sh --date 20251109 --type day --provider claude
./run_all_v2.sh --date 20251109 --type day --provider openai
./run_all_v2.sh --date 20251109 --type day --provider gemini
```

---

### File and Configuration Issues

#### "Config file not found"

**Error Message:**
```
❌ Error: Config file not found: ./config.yaml
```

**Cause:** config.yaml doesn't exist in current directory.

**Solution:**
```bash
# Check if config exists
ls -la config.yaml

# Create from template if missing
# Add your API keys
cat > config.yaml <<'EOF'
ai:
  active_provider: claude
  providers:
    claude:
      api_key: ${ANTHROPIC_API_KEY}
      model: claude-3-5-sonnet-20241022
EOF

# Or specify path
./run_all_v2.sh --date 20251109 --type day --config /path/to/config.yaml
```

---

#### "Games file not found"

**Error Message:**
```
❌ Error: Games file not found: tmp/2025-week09/20251109/games.json
```

**Cause:** Stage 1 didn't create games.json (or ran in different directory).

**Solution:**
```bash
# Check current directory
pwd

# Run from replai-review directory
cd /path/to/replai-review
./run_all_v2.sh --date 20251109 --type day

# Or check if Stage 1 completed successfully
ls -la tmp/2025-week09/20251109/
```

---

#### "Newsletter file not found"

**Error Message:**
```
❌ Error: Newsletter file not found: tmp/2025-week09/20251109/newsletter.json
```

**Cause:** Stage 2 didn't create newsletter.json.

**Solution:**
```bash
# Check if newsletter.json exists
ls -la tmp/2025-week09/20251109/

# If missing, check Stage 2 error output above
# Common causes:
# - AI provider API key error (see next section)
# - Invalid JSON from AI response
# - Pydantic validation error
```

---

### Runtime Errors

#### "No games found" (Exit Code 1)

**Error Message:**
```
⚠️  Warning: Pipeline stopped: No games found for 20251114
```

**Cause:** ESPN didn't schedule games for that date.

**Solution:**
```bash
# NFL games are typically Thursday/Sunday/Monday
# Try a Thursday date
./run_all_v2.sh --date 20251106 --type day  # Thursday

# Or use week mode for all week games
./run_all_v2.sh --date 20251109 --type week

# Check the NFL schedule to find game dates
# https://www.espn.com/nfl/schedule
```

---

#### "API Key Error" / Authentication Failed

**Error Message:**
```
❌ Error: Authentication failed
Error: Invalid API key
Error: Unauthorized
```

**Cause:** AI provider API key is missing or invalid.

**Solution:**
```bash
# Set environment variable
export ANTHROPIC_API_KEY="sk-ant-xxx"
export OPENAI_API_KEY="sk-xxx"
export GOOGLE_API_KEY="AIza-xxx"

# Or update config.yaml with your keys
cat config.yaml  # Check API keys are set

# Test API key manually
python3 -c "import anthropic; print('OK')"
# If fails, key is not working
```

---

#### "Invalid JSON from AI response"

**Error Message:**
```
❌ Error: Could not extract JSON from AI response
```

**Cause:** AI provider returned unexpected format.

**Solution:**
```bash
# This can happen if:
# 1. API rate limit hit
# 2. Model changed response format
# 3. Prompt was too complex

# Try again (might be temporary)
./run_all_v2.sh --date 20251109 --type day

# Try with simpler date (fewer games)
./run_all_v2.sh --date 20251110 --type day  # Monday: fewer games

# Try different provider
./run_all_v2.sh --date 20251109 --type day --provider openai

# Check prompt file is valid
cat newsletter_prompt.txt
```

---

#### "Validation error"

**Error Message:**
```
❌ Error: Validation error:
   games -> game -> summary: field required
```

**Cause:** AI response missing required field.

**Solution:**
```bash
# Regenerate with debug output
python3 generate_newsletter.py \
  --input tmp/2025-week09/20251109/games.json \
  --provider claude

# Check response includes all fields:
# - game_id
# - summary (2-4 sentences)
# - badges (0-2 from: upset, nail-biter, comeback, blowout, game-of-week)
```

---

### Python/Module Issues

#### "No module named 'requests'"

**Error Message:**
```
ModuleNotFoundError: No module named 'requests'
```

**Cause:** Python dependencies not installed.

**Solution:**
```bash
# Install all dependencies
pip install -q requests beautifulsoup4 pyyaml jinja2 pydantic

# Install AI provider dependencies
pip install -q anthropic openai google-generativeai

# Verify installation
python3 -c "import requests; print('OK')"
```

---

#### "No module named 'anthropic'"

**Error Message:**
```
ModuleNotFoundError: No module named 'anthropic'
```

**Cause:** Claude provider not installed, or using Claude but package missing.

**Solution:**
```bash
# Install Claude
pip install -q anthropic

# Or use different provider
./run_all_v2.sh --date 20251109 --type day --provider openai
```

---

#### "No module named 'openai'"

**Error Message:**
```
ModuleNotFoundError: No module named 'openai'
```

**Cause:** OpenAI provider not installed.

**Solution:**
```bash
# Install OpenAI
pip install -q openai

# Or use different provider
./run_all_v2.sh --date 20251109 --type day --provider claude
```

---

#### "No module named 'google'"

**Error Message:**
```
ModuleNotFoundError: No module named 'google.generativeai'
```

**Cause:** Google Gemini provider not installed.

**Solution:**
```bash
# Install Gemini
pip install -q google-generativeai

# Or use different provider
./run_all_v2.sh --date 20251109 --type day --provider openai
```

---

### Directory and Permission Issues

#### "Permission denied: ./run_all_v2.sh"

**Error Message:**
```
bash: ./run_all_v2.sh: Permission denied
```

**Cause:** Script is not executable.

**Solution:**
```bash
# Make executable
chmod +x run_all_v2.sh

# Verify
ls -la run_all_v2.sh  # Should show 'x' permission
```

---

#### "No such file or directory: /home/user/replai-review"

**Error Message:**
```
bash: run_all_v2.sh: No such file or directory
```

**Cause:** Script doesn't exist or working directory is wrong.

**Solution:**
```bash
# Check current directory
pwd

# Find replai-review directory
find ~ -name "replai-review" -type d

# Change to correct directory
cd /home/user/replai-review

# Verify script exists
ls -la run_all_v2.sh
```

---

#### "Cannot create directory tmp/2025-week09"

**Error Message:**
```
❌ Error: Cannot create directory tmp/2025-week09
```

**Cause:** Permission denied or disk full.

**Solution:**
```bash
# Check permissions
ls -la | grep "^d"  # Should show 'w' for write

# Check disk space
df -h .

# Try creating manually
mkdir -p tmp/2025-week09

# If disk full, free up space or use different drive
```

---

### Testing Issues

#### Tests fail with "Module not found"

**Error Message:**
```
ModuleNotFoundError: No module named 'fetch_games'
```

**Cause:** Running tests from wrong directory.

**Solution:**
```bash
# Change to replai-review directory
cd /path/to/replai-review

# Run tests from there
python -m unittest discover -p "test_*.py" -v
```

---

#### Some tests skipped

**Output:**
```
test_xyz (test_generate_newsletter.TestStage2) ... skipped: AI provider not configured
Ran 26 tests in 2.3s

OK (skipped=3)
```

**Cause:** Tests are skipped when AI provider not configured.

**Solution:**
```bash
# Set up config.yaml with API keys
# Then run tests again
python -m unittest discover -p "test_*.py" -v
```

---

### Performance Issues

#### "Pipeline is slow" or "API timeout"

**Error Message:**
```
HTTPError: 504 Server Error: Gateway Timeout
```

**Cause:**
- Network connection slow
- AI provider slow
- Too many parallel requests

**Solution:**
```bash
# Try again (might be temporary)
./run_all_v2.sh --date 20251109 --type day

# Use different provider (might be faster)
./run_all_v2.sh --date 20251109 --type day --provider openai

# Check internet connection
ping google.com

# Check AI provider status
# Claude: status.anthropic.com
# OpenAI: status.openai.com
# Google: status.cloud.google.com
```

---

#### "Memory error" or "Out of memory"

**Error Message:**
```
MemoryError
Error: Cannot allocate memory
```

**Cause:**
- Processing too much data
- Memory leak
- System has limited RAM

**Solution:**
```bash
# Check available memory
free -h

# Close other applications
# Try with fewer games (day mode instead of week)
./run_all_v2.sh --date 20251109 --type day

# Monitor memory while running
while true; do free -h; sleep 1; done &
./run_all_v2.sh --date 20251109 --type day
```

---

## Debugging Workflow

When something goes wrong:

1. **Read the error message carefully** - it usually tells you the problem
2. **Check exit code:**
   ```bash
   ./run_all_v2.sh --date 20251109 --type day
   echo $?  # 0=success, 1=no games, 2=error, 3=invalid args
   ```

3. **Check which stage failed** - read the section headers in output

4. **Run individual stage for more details:**
   ```bash
   # Stage 1 debug
   python3 fetch_games.py --date 20251109 --type day

   # Stage 2 debug
   python3 generate_newsletter.py --input tmp/2025-week09/20251109/games.json

   # Stage 3 debug
   python3 publish_newsletter.py --input tmp/2025-week09/20251109/newsletter.json
   ```

5. **Check files exist:**
   ```bash
   ls -la tmp/2025-week09/20251109/
   ls -la docs/
   ```

6. **Look for log files or verbose output:**
   ```bash
   # Run with bash debug mode
   bash -x run_all_v2.sh --date 20251109 --type day 2>&1 | tee debug.log
   ```

7. **Run tests to verify setup:**
   ```bash
   python -m unittest discover -p "test_*.py" -v
   ```

---

## Getting Help

### If You Get Stuck

1. **Check relevant docs:**
   - `README_V2.md` - Usage guide
   - `ARCHITECTURE_V2.md` - System design
   - `MIGRATION_GUIDE.md` - Upgrading from V1

2. **Run tests:**
   ```bash
   python -m unittest discover -p "test_*.py" -v
   ```

3. **Check script permissions:**
   ```bash
   chmod +x run_all_v2.sh
   chmod +x fetch_games.py generate_newsletter.py publish_newsletter.py
   ```

4. **Try with minimal example:**
   ```bash
   # Use sample fixture without API
   python3 -c "
   import json
   with open('fixtures/sample_games.json') as f:
       print(json.dumps(json.load(f), indent=2)[:500])
   "
   ```

---

## Frequently Asked Questions

**Q: How do I know which games are scheduled?**
A: Check ESPN NFL schedule at https://www.espn.com/nfl/schedule or look at season_week_dates in code comments.

**Q: Can I generate multiple days at once?**
A: Not in a single command, but you can script it:
```bash
for date in 20251109 20251110; do
  ./run_all_v2.sh --date $date --type day
done
```

**Q: How do I keep generated files?**
A: They're automatically saved in `docs/` and `tmp/`. Use version control:
```bash
git add docs/ tmp/
git commit -m "Week 9 newsletters"
```

**Q: Can I modify the template?**
A: Yes! Edit `newsletter_template.html` and regenerate:
```bash
python3 publish_newsletter.py --input tmp/2025-week09/20251109/newsletter.json
```

**Q: Can I use it offline?**
A: Yes, if you've already fetched data. Use fixture files for testing.

---

## Still Having Issues?

1. Verify all dependencies are installed
2. Check all required files exist (config.yaml, templates, etc.)
3. Review error message and check this guide
4. Run tests: `python -m unittest discover -v`
5. Check documentation in relevant README files

Good luck! 🏈📰
