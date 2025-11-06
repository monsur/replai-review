# Newsletter Data Quality Issues - Root Cause Analysis

## Issues Discovered

### 1. Wrong Team Records
- **Example**: Colts showed as 5-3 instead of actual 7-2
- **Root Cause**: Team records are NOT in the ESPN recap HTML - AI is inferring/guessing them

### 2. Wrong Player Names
- **Example**: "Daniel Jones" (Giants QB) listed as playing for Colts
- **Root Cause**: ESPN's own recap article had errors (incorrect player names in text)

### 3. Wrong Game Dates (FIXED)
- **Example**: Thursday Ravens game showed as Sunday
- **Root Cause**: Date wasn't extracted from page title, AI inferred from "week" context

## Root Causes

### Problem 1: No Structured Data in Recaps
ESPN recap pages contain:
- ✅ Game score
- ✅ Game date (in title)
- ✅ Article text
- ❌ Team records (NOT present)
- ❌ Player rosters (NOT present)
- ❌ Structured game metadata

The AI is **inferring** missing data rather than **extracting** it.

### Problem 2: ESPN Content Errors
ESPN occasionally publishes recaps with:
- Wrong player names in articles
- Copy-paste errors from other games
- AI-generated content mistakes

### Problem 3: No Validation Layer
Current pipeline:
```
ESPN HTML → AI Extraction → JSON → Newsletter
```

No validation step to catch:
- Impossible player-team matchups
- Incorrect records
- Suspicious data patterns

## Solutions

### Short-term Fixes (Immediate)

#### 1. Update AI Prompt to be More Conservative
```markdown
CRITICAL EXTRACTION RULES:
- ONLY extract data that is explicitly stated in the recap
- For team records: Look for phrases like "improved to 7-2" or "now 5-3"
- If a data point is not explicitly mentioned, use these defaults:
  - away_record: "N/A"
  - home_record: "N/A"
- DO NOT infer or calculate records
- DO NOT assume player names without verification in the article
```

#### 2. Add Data Validation Script
Create `validate_newsletter.py` to check:
- Player names match their actual teams (using a roster file)
- Records follow valid format (X-Y or X-Y-Z)
- Dates fall within the correct week range
- Quarterbacks mentioned are real players on those teams

#### 3. Add Manual Review Checklist
Flag games for review when:
- Records are "N/A"
- Player mentioned in summary doesn't match team roster
- Score differential doesn't match badge (e.g., "blowout" but only 7-point margin)

### Medium-term Solutions (Next Sprint)

#### 1. Use ESPN API Instead of Scraping
ESPN has JSON APIs like:
```
https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates=2025&seasontype=2&week=9
```

Benefits:
- Structured data with records, rosters, stats
- No HTML parsing needed
- More reliable than scraped content

#### 2. Maintain Team/Player Reference Data
Create reference files:
- `team_rosters.json` - Current rosters for all teams
- `team_standings.json` - Updated weekly with actual records
- `qb_roster.json` - Quick lookup of starting QBs

Use these to validate extracted data.

#### 3. Implement Two-Source Validation
For critical data (records, player names):
- Extract from ESPN recap
- Verify against ESPN API or NFL.com
- Flag mismatches for manual review

### Long-term Solutions (Future Enhancements)

#### 1. Switch to API-First Approach
```python
# Get game IDs from scoreboard
scoreboard = fetch_espn_scoreboard(week=9)

for game in scoreboard['events']:
    # Get structured game data
    game_data = fetch_game_summary(game['id'])

    # Get narrative recap for AI summary
    recap_html = fetch_game_recap(game['id'])

    # Combine: Use API for facts, recap for storytelling
    newsletter_entry = combine_data(game_data, recap_html)
```

#### 2. Add Confidence Scores
Have AI rate confidence for each extracted field:
```json
{
  "away_record": "7-2",
  "away_record_confidence": 0.95,
  "home_record": "5-3",
  "home_record_confidence": 0.60  // Flag for review
}
```

#### 3. Implement Feedback Loop
After each newsletter:
- Log any corrections made
- Train on common error patterns
- Improve extraction prompts based on mistakes

## Recommended Implementation Order

### Phase 1 (This Week)
1. ✅ Fix date extraction (DONE)
2. ⬜ Update prompt to be more conservative about records
3. ⬜ Add basic validation for player-team matchups
4. ⬜ Create manual review checklist

### Phase 2 (Next Week)
1. ⬜ Explore ESPN API endpoints
2. ⬜ Create reference data files (rosters, standings)
3. ⬜ Build validation script

### Phase 3 (Future)
1. ⬜ Migrate to API-first approach
2. ⬜ Add confidence scoring
3. ⬜ Implement automated testing with known games

## Testing Strategy

### Validation Test Cases
Create test suite with known problematic scenarios:
- Thursday night games (different dates)
- Backup QBs starting (ensure correct names)
- Teams with same records (ensure correct assignment)
- Overtime games (special formatting)

### Smoke Tests Before Publishing
Always check:
- Thursday/Monday games have correct dates (not Sunday)
- Team records add up correctly (wins + losses = games played minus one)
- Star players mentioned play for the teams listed
- Badges match score differentials

## Quick Fix for Current Newsletter

Run this validation:
```bash
# Check for suspicious patterns
grep -E '(Daniel Jones|Aaron Rodgers|Tom Brady)' newsletter.json
# Verify these QBs are with correct teams

# Check all records follow format
grep -oE '"(away|home)_record": "[^"]*"' newsletter.json | sort | uniq -c
# Look for outliers or weird patterns
```
