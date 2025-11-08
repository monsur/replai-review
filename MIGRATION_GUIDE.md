# Migration Guide: V1 to V2 Pipeline

This guide explains how to migrate from the V1 (week-based) pipeline to the V2 (date-based) pipeline.

## Overview

| Aspect | V1 | V2 |
|--------|----|----|
| **Time Unit** | Weekly | Daily or Weekly |
| **Date Format** | Week number (1-18) | YYYYMMDD (e.g., 20251109) |
| **Directory Structure** | `tmp/2025-week09/` | `tmp/2025-week09/` (week parent) + `tmp/2025-week09/20251109/` (daily runs) |
| **Stages** | 4 (fetch, generate, archive, publish) | 3 (fetch, generate, publish) |
| **Pipeline Command** | Individual stage scripts | `run_all_v2.sh` |
| **Default Type** | Week | Day |

## Key Differences

### 1. Date-Based Instead of Week-Based

**V1:** Week-based (1-18)
```bash
python3 fetch_games.py --week 9 --year 2025
```

**V2:** Date-based (YYYYMMDD)
```bash
python3 fetch_games.py --date 20251109 --type day
```

### 2. Directory Structure

**V1:**
```
tmp/2025-week09/
├── games.json
├── newsletter.json
└── 2025-week09.html
```

**V2 (Day mode):**
```
tmp/2025-week09/
├── 20251109/
│   ├── games.json
│   ├── newsletter.json
│   └── 2025-week09-sun-251109.html
├── 20251110/
│   ├── games.json
│   ├── newsletter.json
│   └── 2025-week09-mon-251110.html
```

**V2 (Week mode):**
```
tmp/2025-week09/
├── games.json
├── newsletter.json
└── 2025-week09.html
```

### 3. Unified Orchestration

**V1:** Run each stage separately
```bash
python3 fetch_games.py --week 9 --year 2025
python3 generate_newsletter.py --input tmp/2025-week09/games.json --provider claude
python3 publish_newsletter.py --input tmp/2025-week09/newsletter.json
python3 update_archive.py --archive docs/archive.json ...
```

**V2:** Single orchestration command
```bash
./run_all_v2.sh --date 20251109 --type day --provider claude
```

### 4. Archive Structure

**V1:** Flat list of weeks
```json
{
  "newsletters": [
    {"week": 9, "year": 2025, "filename": "2025-week09.html", ...}
  ]
}
```

**V2:** Nested structure with day/week entries
```json
{
  "newsletters": [
    {
      "week": 9,
      "year": 2025,
      "entries": [
        {"type": "day", "date": "2025-11-09", "filename": "2025-week09-sun-251109.html", ...},
        {"type": "day", "date": "2025-11-10", "filename": "2025-week09-mon-251110.html", ...}
      ]
    }
  ]
}
```

## Migration Steps

### Step 1: Backup V1 Files

Create a backup of your current V1 work:
```bash
cp -r docs docs_v1_backup
cp -r tmp tmp_v1_backup
```

### Step 2: Switch to V2 Branch

The V2 pipeline is on a separate branch. V1 remains untouched:
```bash
# Your V1 work is still on: git branch (current)
# V2 work is on: refactor/v2-three-stage-pipeline

git checkout refactor/v2-three-stage-pipeline
```

### Step 3: Update Your Workflows

**Before (V1):**
```bash
python3 fetch_games.py --week 9 --year 2025
python3 generate_newsletter.py --input tmp/2025-week09/games.json
python3 publish_newsletter.py --input tmp/2025-week09/newsletter.json
```

**After (V2):**
```bash
./run_all_v2.sh --date 20251109 --type day
```

### Step 4: Test V2 with Sample Data

Test the V2 pipeline with provided fixtures:
```bash
# Run all tests
python -m unittest discover -p "test_*.py" -v

# Test orchestration specifically
python -m unittest test_orchestration.py -v
```

### Step 5: Convert Existing Data (Optional)

To convert V1 archives to V2 format, use this Python script:

```python
import json
from pathlib import Path

# Load V1 archive
with open('docs/archive.json', 'r') as f:
    v1_data = json.load(f)

# Convert to V2 format
v2_data = {"newsletters": []}

for v1_entry in v1_data.get('newsletters', []):
    v2_week = {
        "week": v1_entry['week'],
        "year": v1_entry['year'],
        "entries": [
            {
                "type": "week",
                "filename": v1_entry['filename'],
                "game_count": v1_entry.get('game_count', 0)
            }
        ]
    }
    v2_data["newsletters"].append(v2_week)

# Save V2 archive
with open('docs/archive_v2.json', 'w') as f:
    json.dump(v2_data, f, indent=2)
```

## Exit Codes

The V2 orchestration script uses standard exit codes:

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | No games found for given date |
| 2 | Error (file not found, invalid format, etc.) |
| 3 | Invalid arguments |

## Troubleshooting Migration

### Issue: "No games found"

**Cause:** The date or type is incorrect, or ESPN API returned no games.

**Solution:**
```bash
# Verify date format
./run_all_v2.sh --date 20251109 --type day  # Correct

# Check if games were actually played that day
./run_all_v2.sh --date 20251108 --type day  # Try different date
```

### Issue: "Module not found"

**Cause:** Missing Python dependencies.

**Solution:**
```bash
pip install -q requests beautifulsoup4 pyyaml jinja2 pydantic
# For your chosen AI provider:
pip install -q anthropic    # For Claude
pip install -q openai       # For OpenAI
pip install -q google-generativeai  # For Gemini
```

### Issue: "Config file not found"

**Cause:** config.yaml is missing or in wrong location.

**Solution:**
```bash
# Make sure config.yaml exists in current directory
ls -la config.yaml

# Or specify path explicitly
./run_all_v2.sh --date 20251109 --type day --config /path/to/config.yaml
```

## Feature Comparison

### New Features in V2

- **Daily newsletters:** Generate separate newsletters for each day of the week
- **Unified orchestration:** Single command runs all 3 stages
- **Better date handling:** Support for any date in the season
- **Nested archive:** Better organization of day/week entries
- **Cleaner output:** Color-coded progress reporting

### Maintained Features from V1

- **Multi-AI provider support:** Claude, OpenAI, Gemini
- **Jinja2 templating:** Same template system
- **Team icons:** Team abbreviation-based icon paths
- **Badge system:** Same badge types (upset, nail-biter, comeback, etc.)
- **Archive management:** Automatic archive.json updates

## Rollback to V1

If you need to go back to V1:

```bash
# Switch back to your original branch
git checkout main  # or your main branch

# Restore from backup if needed
cp -r tmp_v1_backup tmp
cp -r docs_v1_backup docs

# Run V1 pipeline
python3 fetch_games.py --week 9 --year 2025
# ... etc.
```

## Questions?

For detailed information about V2 features:
- See `ARCHITECTURE_V2.md` for system design
- See `README_V2.md` for usage examples
- See individual stage documentation (`fetch_games.py`, `generate_newsletter.py`, `publish_newsletter.py`)

## Success Checklist

After migration, verify:

- [ ] V2 branch checked out
- [ ] Python dependencies installed
- [ ] config.yaml exists and is configured
- [ ] Sample tests pass: `python -m unittest discover -p "test_*.py"`
- [ ] Can run orchestration: `./run_all_v2.sh --help`
- [ ] Can run full pipeline: `./run_all_v2.sh --date 20251109 --type day`
- [ ] Archive.json updated with nested structure
- [ ] HTML files generated in docs/
- [ ] index.html shows new format

Good luck with your migration! 🎉
