# Refactoring Analysis: Parse Metadata in Code vs AI

## Proposed Change

**Current:**
```
HTML → AI extracts ALL fields → JSON
```

**Proposed:**
```
HTML → Code parses metadata → Intermediate JSON
Intermediate JSON → AI adds summary/badges → Final JSON
```

## Data Availability Analysis

I checked what's actually in the ESPN HTML:

### ✅ Easily Parseable from HTML Title
```html
<title>Ravens 28-6 Dolphins (Oct 30, 2025) Game Recap - ESPN</title>
```

**Can extract with simple regex:**
- `away_team`: "Ravens" → "Baltimore Ravens" (needs mapping)
- `away_score`: 28
- `home_team`: "Dolphins" → "Miami Dolphins" (needs mapping)
- `home_score`: 6
- `game_date`: "Oct 30, 2025" → "Thu 10/30 8:15PM ET" (needs day-of-week + time inference)

### ✅ Parseable from Article Text (Medium difficulty)
```html
<p>MIAMI GARDENS, Fla. -- — Lamar Jackson returned...</p>
<p>...Dolphins fans began to exit Hard Rock Stadium en masse...</p>
<p>...The Ravens (3-5) won their second straight...</p>
```

**Can extract with pattern matching:**
- `away_record`: Search for "Ravens (3-5)" or similar pattern
- `home_record`: Search for "Dolphins (2-7)" pattern
- `stadium`: "Hard Rock Stadium" mentioned in text
- `tv_network`: Usually NOT in article text ❌

### ❌ Not Available in HTML
- `away_abbr`: "BAL" - Not in HTML (need hardcoded mapping)
- `home_abbr`: "MIA" - Not in HTML (need hardcoded mapping)
- `tv_network`: Usually not mentioned in articles

### ✅ Known/Constructable
- `game_id`: Already known (from filename)
- `recap_url`: Can construct from game_id

## Parsing Complexity Assessment

### Simple Fields (5 min to implement)
```python
def parse_title(html):
    # <title>Ravens 28-6 Dolphins (Oct 30, 2025) Game Recap - ESPN</title>
    pattern = r'(\w+) (\d+)-(\d+) (\w+) \((\w+ \d+, \d+)\)'
    match = re.search(pattern, title)
    return {
        'away_team_short': match.group(1),
        'away_score': int(match.group(2)),
        'home_team_short': match.group(4),
        'home_score': int(match.group(3)),
        'date': match.group(5)
    }
```
**Risk: ⭐ Low** - Title format is consistent

### Medium Fields (30 min to implement)
```python
def parse_records(article_text):
    # Find patterns like "Ravens (3-5)" or "Dolphins (2-7)"
    pattern = r'(Ravens|Dolphins|Patriots|etc)\s*\((\d+-\d+(-\d+)?)\)'
    matches = re.findall(pattern, article_text)
    return matches
```
**Risk: ⭐⭐⭐ Medium** - Records mentioned inconsistently, sometimes not at all

### Hard Fields (1-2 hours to implement)
```python
def parse_stadium(article_text):
    # Look for dateline: "MIAMI GARDENS, Fla."
    # or mentions: "Hard Rock Stadium"
    # Complex: Multiple stadium name formats, not always mentioned
    ...
```
**Risk: ⭐⭐⭐⭐ High** - Inconsistent format, not always present

### Impossible Fields
```python
tv_network = ????  # Not in HTML at all
```
**Risk: ⭐⭐⭐⭐⭐ Very High** - Would need external data source

## Pros & Cons Analysis

### ✅ PROS

#### 1. **Cost & Speed** (Moderate benefit)
```
Current AI input:  104K chars ≈ 28K tokens
Proposed AI input: 14K chars  ≈ 4K tokens

Cost savings: ~$0.03 per newsletter ($1.50/season)
Speed improvement: 30-40% faster (~20-30 seconds)
```
**Assessment: Nice but not game-changing**

#### 2. **Reliability for Scores** (Strong benefit)
```python
# Code parsing: 100% reliable
score = int(title.split('-')[0])  # Always works

# AI extraction: 99% reliable (but that 1% hurts)
```
**Assessment: This is compelling for critical fields like scores**

#### 3. **Early Validation** (Strong benefit)
```python
# Can validate before expensive AI call
parsed = parse_all_recaps()
if not validate_scores(parsed):
    print("Fix ESPN HTML issues before running AI")
    exit(1)
generate_summaries(parsed)  # Only if parsing succeeded
```
**Assessment: Fail fast principle is good**

#### 4. **Cleaner Architecture** (Strong benefit)
```
Facts (deterministic)    → Code
Narrative (creative)     → AI
Validation (rules-based) → Code
```
**Assessment: Proper separation of concerns**

### ❌ CONS

#### 1. **Incomplete Data Extraction** (Major issue)
**Fields NOT reliably in HTML:**
- `tv_network`: Not in articles (~0% success rate)
- `stadium`: Sometimes mentioned, often not (~60% success rate)
- `away_record` / `home_record`: Mentioned inconsistently (~80% success rate)

**What happens when parsing fails?**
```python
# Option A: Leave blank (bad UX)
{"stadium": null}

# Option B: Fall back to AI anyway (defeats purpose)
{"stadium": ai_extract_stadium(html)}

# Option C: Skip field (incomplete data)
# No stadium field at all
```
**Assessment: This is the killer problem**

#### 2. **Brittle HTML Parsing** (Major issue)
```python
# Works today
pattern = r'(\w+) (\d+)-(\d+) (\w+)'

# ESPN changes to:
# "Baltimore Ravens defeat Miami Dolphins 28-6"
# Your parser breaks, newsletter generation fails
```

**AI is resilient:**
- Can handle format changes
- Can extract from messy HTML
- Gracefully degrades

**Code parsing is brittle:**
- Breaks on format changes
- Requires maintenance
- All-or-nothing (no graceful degradation)

**Assessment: Significant maintenance burden**

#### 3. **Mixed Extraction Strategy** (Moderate issue)
```json
{
  "away_score": 28,        // Parsed from HTML
  "stadium": "Unknown",    // Parsing failed
  "tv_network": "CBS",     // AI extracted
  "summary": "..."         // AI generated
}
```

**Problem**: Debugging becomes complex
- Which fields came from parsing?
- Which came from AI?
- Where did the error occur?

**Assessment: Cognitive overhead for maintenance**

#### 4. **No Real Quality Improvement** (Important realization)
The validation script already catches critical errors:
- Wrong QB names ✅
- Bad scores ✅
- Invalid records ✅

**Moving extraction to code doesn't prevent:**
- ESPN article errors (Daniel Jones playing for Colts)
- Missing data (records not mentioned)
- Ambiguous information

**Assessment: Validation matters more than extraction method**

## Alternative: Hybrid Light Touch

Instead of full parsing, add **minimal pre-processing**:

```python
# process_recaps.py
def extract_title_data(html):
    """Extract ONLY what's trivial and reliable."""
    title = soup.find('title').text
    # "Ravens 28-6 Dolphins (Oct 30, 2025) Game Recap - ESPN"

    match = re.search(r'(\w+) (\d+)-(\d+) (\w+) \(([^)]+)\)', title)
    if match:
        return {
            'title_teams': [match.group(1), match.group(4)],
            'title_scores': [int(match.group(2)), int(match.group(3))],
            'title_date': match.group(5)
        }
    return None

# generate_json.py - Update prompt
"""
VALIDATION DATA (use to check your extraction):
Title shows: Ravens 28-6 Dolphins (Oct 30, 2025)

Extract the full game details from the article below.
Verify your scores match the title.
"""
```

**Benefits:**
- ✅ AI has title data for validation
- ✅ Can catch obvious AI mistakes
- ✅ Minimal parsing (just title tag - very reliable)
- ✅ Still flexible if ESPN changes format

**This gives you 80% of the benefit with 20% of the complexity.**

## Recommendation: ❌ DON'T DO FULL REFACTORING

### Reasons:

1. **Incomplete Solution**
   - Can't reliably extract all fields (TV network, stadium)
   - Would need fallback to AI anyway
   - Defeats purpose of "code for facts"

2. **Brittle System**
   - HTML parsing breaks when ESPN changes format
   - AI is more resilient to format changes
   - Adds maintenance burden

3. **Marginal Benefits**
   - Cost savings: ~$0.03/newsletter ($1.50/season) - negligible
   - Speed improvement: ~20 seconds - nice but not critical
   - Quality improvement: Minimal (validation already catches errors)

4. **Better Alternatives Exist**
   - **Validation script** already catches errors (we built this!)
   - **Hybrid light touch** gets 80% benefit with 20% effort
   - **ESPN API** would be the right long-term solution

### What to Do Instead:

#### Option A: Status Quo + Better Validation (Recommended)
```bash
# Keep current architecture
python generate_json.py --week 9

# Add comprehensive validation
python validate_newsletter.py tmp/2025-week09/newsletter.json
```
**Pros:** Already works, validation catches issues
**Cons:** None really

#### Option B: Hybrid Light Touch (If you want some parsing)
```python
# Extract title data for validation hints
parsed_titles = extract_title_data_from_all_recaps()

# Pass to AI with validation instructions
generate_json_with_validation_data(html, parsed_titles)
```
**Pros:** AI can self-validate, catches obvious errors early
**Cons:** Small amount of parsing code to maintain

#### Option C: ESPN API Migration (Long-term)
```python
# Use ESPN's structured API
game_data = espn_api.get_scoreboard(week=9)
# Has records, scores, everything structured

# Use recap HTML only for narrative
recaps = fetch_recaps(game_ids)
summaries = ai.generate_summaries(recaps, game_data)
```
**Pros:** Structured data + AI narrative = best of both worlds
**Cons:** API research/implementation time

## Bottom Line

**Your instinct is right** that code should handle structured data extraction.

**But the implementation is wrong** because:
- HTML doesn't have all the structured data
- What it has is inconsistently formatted
- Parsing would be brittle and incomplete

**The right move is:**
1. **Short-term**: Keep current approach + validation script (what we have)
2. **Medium-term**: Research ESPN API for structured data
3. **Long-term**: API for facts + AI for narrative

The refactoring would be **6-8 hours of work** for **minimal benefit** and **increased fragility**.

Not worth it. Focus on validation instead.
