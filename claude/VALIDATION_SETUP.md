# Validation Setup - Complete Guide

## What Was Added

Validation is now integrated into your newsletter generation pipeline!

### Changes Made

1. **`run_all.sh`** - Added validation as Step 4/5 (between JSON generation and HTML formatting)
2. **`validate_newsletter.py`** - Updated to accept `--week` argument for consistency

### Pipeline Flow

```
Step 1/5: Fetch recaps from ESPN
Step 2/5: Process and combine recaps
Step 3/5: Generate JSON with AI
Step 4/5: Validate newsletter data  ← NEW!
Step 5/5: Format HTML newsletter
```

## How It Works

### Locally

```bash
# Run full pipeline (includes validation)
./run_all.sh

# Or specify week
./run_all.sh --week 9

# Or run validation independently
python validate_newsletter.py --week 9
python validate_newsletter.py tmp/2025-week09/newsletter.json  # Direct path also works
```

**What happens on validation failure:**
- Script exits with code 1
- Pipeline stops (HTML newsletter not generated)
- You see the validation errors in your terminal

### In GitHub Actions

```yaml
# Existing workflow continues to work
# It runs: bash run_all.sh
# Which now includes validation!
```

**What happens on validation failure:**
- Workflow fails at "Generate newsletter" step
- GitHub sends you an email notification
- Artifacts (JSON, HTML, logs) are uploaded for debugging
- Newsletter is NOT committed or published

## Validation Checks

The validator catches:

**ERRORS** (block pipeline):
- ❌ QB playing for wrong team (e.g., "Daniel Jones" for Colts)
- ❌ Invalid data formats
- ❌ Negative scores
- ❌ Missing required fields

**WARNINGS** (allow but flag):
- ⚠️ Suspicious team records
- ⚠️ Badge mismatches (nail-biter but 10-point game)
- ⚠️ Unusually high scores
- ⚠️ Missing optional metadata

**INFO** (just notes):
- ℹ️ Records not provided
- ℹ️ Suggestions for badges

## When Validation Fails

### GitHub Actions Scenario

1. You receive email: "Workflow run failed: Generate Weekly NFL Newsletter"
2. Click the link to see the workflow run
3. Look at "Generate newsletter" step logs
4. Scroll to "Step 4/5: Validating newsletter data"
5. See the validation report

**Example error:**
```
[ERROR] Game 401772766 - summary: QB 'Daniel Jones' mentioned
        but plays for NYG, not PIT or IND
```

### What to Do

**Option 1: Quick manual fix**
```bash
# Pull the failed artifacts from GitHub Actions
# Edit tmp/2025-week09/newsletter.json
# Fix the specific error (e.g., remove "Daniel Jones" from summary)
# Re-run validation locally
python validate_newsletter.py --week 9
# If passes, commit and push
```

**Option 2: Regenerate**
```bash
# If the ESPN source data was wrong, regenerate:
./run_all.sh --week 9
# Validation runs automatically
```

**Option 3: Investigate root cause**
```bash
# Check the ESPN recap that had bad data
cat tmp/2025-week09/recaps/401772766.html | grep -i "daniel jones"
# If ESPN's article is wrong, consider:
# - Updating AI prompt to be more careful
# - Adding to known problematic patterns
# - Using ESPN API instead (long-term)
```

## Exit Codes

```bash
python validate_newsletter.py --week 9
echo $?  # Check exit code
```

- `0` = Success (newsletter is valid, may have warnings)
- `1` = Failure (errors found, don't publish)

## Testing Validation

### Test with known-good newsletter
```bash
# Week 8 (should pass)
python validate_newsletter.py --week 8
```

### Test with known-bad newsletter
```bash
# Week 9 (currently has 3 errors)
python validate_newsletter.py --week 9
```

### See all validation output
```bash
python validate_newsletter.py --week 9 2>&1 | tee validation.log
```

## Integration with Existing Workflow

**No changes needed!** Your GitHub Actions workflow:
1. Already runs `bash run_all.sh`
2. Already has `set -e` (exit on error)
3. Already uploads artifacts on failure
4. Already sends email on failure

The validation is now part of that pipeline automatically.

## Future Enhancements

If you want more automation later, see:
- `AUTOMATED_WORKFLOW_STRATEGY.md` - Auto-fix strategies
- `auto_fix_newsletter.py` - Script to auto-fix common issues
- `PREVENTION_PLAN.md` - Long-term prevention strategies

For now: **Simple is good.** Fail fast, email you, investigate case-by-case.

## Quick Reference

```bash
# Generate newsletter (includes validation)
./run_all.sh

# Validate specific week
python validate_newsletter.py --week 9

# Validate specific file
python validate_newsletter.py tmp/2025-week09/newsletter.json

# Auto-detect current week
python validate_newsletter.py
```

## Success Criteria

✅ Validation passes → Newsletter generated → Committed & published
❌ Validation fails → Pipeline stops → Email sent → Manual review
