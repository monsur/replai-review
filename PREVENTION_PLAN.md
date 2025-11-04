# Newsletter Error Prevention Plan

## What We've Built

### 1. Validation Script (`validate_newsletter.py`)
**Purpose**: Catch errors before publishing

**What it checks**:
- ✅ Player-team matchups (catches wrong QB names)
- ✅ Date formats and day-of-week distribution
- ✅ Score reasonableness
- ✅ Badge consistency (nail-biter vs actual score)
- ✅ Record formats

**How to use**:
```bash
python validate_newsletter.py tmp/2025-week09/newsletter.json
```

**Exit codes**:
- `0` = Success (warnings OK)
- `1` = Failure (errors found)

### 2. Debugging Guide (`DEBUGGING_GUIDE.md`)
Complete analysis of root causes and solutions

## Recommended Workflow

### Before Publishing Each Newsletter

```bash
# 1. Generate newsletter as usual
python fetch_recaps.py --week 9
python process_recaps.py --week 9
source .env && python generate_json.py --week 9

# 2. VALIDATE before formatting
python validate_newsletter.py tmp/2025-week09/newsletter.json

# 3. Review and fix any errors
# - Check ERROR lines carefully
# - Review WARNING lines
# - INFO lines are optional

# 4. If errors found, either:
#    a) Manually edit the JSON file
#    b) Re-run generate_json.py with improved prompt
#    c) Investigate the source ESPN recap

# 5. Once validated, generate the final newsletter
python format_newsletter.py --week 9
```

## Current Week 9 Issues

### Critical Errors Found
```
[ERROR] Game 401772766 - QB 'Daniel Jones' mentioned but plays for NYG, not PIT or IND
[ERROR] Game 401772818 - QB 'Jacoby Brissett' mentioned but plays for NE, not ARI or DAL
[ERROR] Game 401772926 - QB 'Sam Darnold' mentioned but plays for MIN, not SEA or WAS
```

**Root cause**: ESPN's own recap articles have these errors (wrong player names in the text)

**Fix options**:
1. **Manual**: Edit `tmp/2025-week09/newsletter.json` to remove/replace wrong QB names
2. **Regenerate**: Update prompt to warn AI about potential ESPN errors
3. **Research**: Check actual game recaps on NFL.com or other sources for correct QBs

### Recommended Fix for Week 9

You should manually check these games and correct the summaries:
- **Steelers 27-20 Colts**: Who was the Colts QB? (Not Daniel Jones)
- **Cardinals 27-17 Cowboys**: Who was the Cardinals QB? (Not Jacoby Brissett)
- **Seahawks 38-14 Commanders**: Who was the Seahawks QB? (Not Sam Darnold)

## Long-term Prevention

### Phase 1: Immediate (This Week)
- [x] Create validation script
- [ ] Update AI prompt with stricter rules
- [ ] Add pre-publishing checklist

### Phase 2: Short-term (Next 2 Weeks)
- [ ] Investigate ESPN API for structured data
- [ ] Build team roster reference file
- [ ] Add automated testing

### Phase 3: Long-term (Future)
- [ ] Migrate from HTML scraping to API
- [ ] Add confidence scoring
- [ ] Implement feedback loop

## Updated AI Prompt Template

Add to `newsletter_prompt.txt`:

```markdown
CRITICAL VALIDATION:
- ⚠️ ESPN recaps sometimes contain ERRORS (wrong player names, wrong teams)
- Before including any player name, verify they play for one of the two teams
- If you're uncertain about a player-team match, DO NOT include that player
- Focus summaries on verified facts: scores, outcomes, key plays
- Avoid mentioning specific players unless you're certain they played in THIS game
```

## Testing Your Changes

Always test with a previous week that has known-good data:
```bash
# Test with Week 8 (should pass)
python validate_newsletter.py tmp/2025-week08/newsletter.json

# Test with Week 9 (will show errors)
python validate_newsletter.py tmp/2025-week09/newsletter.json
```

## Emergency Fix Process

If you need to publish quickly and validation fails:

1. **Assess severity**:
   - ERRORs = Must fix
   - WARNINGs = Review but may be OK
   - INFO = Optional

2. **Quick manual fixes**:
   ```bash
   # Edit the JSON directly
   nano tmp/2025-week09/newsletter.json

   # Re-validate
   python validate_newsletter.py tmp/2025-week09/newsletter.json
   ```

3. **Document the fix**: Note what you changed for future reference

## Success Metrics

Track these over time:
- Validation errors per newsletter
- Manual fixes required
- Time spent on validation
- User-reported errors after publishing

Goal: Zero critical errors, <5 warnings per newsletter
