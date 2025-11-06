# API Call Strategy Comparison

## Cost Analysis

### Assumptions (Claude Haiku-4.5)
- Input: ~7,000 chars/game = 2,000 tokens/game
- Output: ~150 words/game = 200 tokens/game
- Pricing: $1/million input tokens, $5/million output tokens (Haiku rates)

### Single API Call
```
Input:  14 games × 2,000 tokens = 28,000 tokens = $0.028
Output: 14 games × 200 tokens   = 2,800 tokens  = $0.014
Total per newsletter: $0.042 (~4 cents)
```

### Multiple API Calls (14 separate)
```
Input:  14 × 2,000 tokens = 28,000 tokens = $0.028
Output: 14 × 200 tokens   = 2,800 tokens  = $0.014
API overhead: +10-20% for repeated prompt/structure

Total per newsletter: $0.046-0.050 (~5 cents)
Plus: No batch discount on input (repeated prompt)
Actual: ~$0.06-0.08 (~6-8 cents)
```

**Cost difference: ~2-4 cents per newsletter, ~$1-2 per season**

## Speed Analysis

### Single API Call
```
Network latency:    ~200ms
Processing time:    ~30-90 seconds (all games)
Total:             ~30-90 seconds
```

### Multiple API Calls (Sequential)
```
Per game:          ~3-5 seconds
Total:            14 × 3-5 = 42-70 seconds
```

### Multiple API Calls (Parallel - 5 concurrent)
```
Batch 1 (5 games): ~5 seconds
Batch 2 (5 games): ~5 seconds
Batch 3 (4 games): ~5 seconds
Total:            ~15 seconds
```

**Speed winner: Parallel API calls (3-6x faster)**

## Quality Analysis

### Single API Call Advantages
- ✅ Can identify "Game of the Week" intelligently
- ✅ Avoids repetitive language
- ✅ Understands weekly narratives
- ✅ Better comparative judgments

Example:
```
"In the week's most exciting finish, the Bears..."
vs
"In an exciting finish, the Bears..." (doesn't know if it's the best)
```

### Multiple API Calls Advantages
- ✅ More focused summaries (no distraction)
- ✅ Consistent format per game
- ✅ Easier to enforce length limits
- ✅ No "bleeding" between game descriptions

## Reliability Analysis

### Failure Scenarios

**Single Call:**
- API timeout → lose all 14 games ❌
- Rate limit → retry loses 30+ seconds ❌
- Bad output for 1 game → regenerate all 14 ❌
- Context overflow → split and retry manually ❌

**Multiple Calls:**
- API timeout → lose 1 game, have 13 ✅
- Rate limit → retry just the failed games ✅
- Bad output for 1 game → regenerate 1 ✅
- Context overflow → impossible (small context) ✅

**MTBF (Mean Time Between Failures):**
- Single: P(success)^1 = 0.95 = 95% success rate
- Multiple: P(success)^14 = 0.95^14 = 49% success rate (at least one fails)
  - But: Partial success = 13/14 working = 93% effective

## Implementation Complexity

### Single API Call
```python
def generate_all_summaries(games):
    # Simple!
    prompt = build_prompt(games)
    response = ai_provider.generate(prompt)
    return parse_response(response)
```
**Complexity: ⭐ Low**

### Multiple API Calls (Parallel)
```python
async def generate_all_summaries(games):
    # More complex
    tasks = [generate_single(game) for game in games]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Handle failures
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            # Retry logic
            results[i] = await retry_with_backoff(games[i])

    return results
```
**Complexity: ⭐⭐⭐ Medium-High**

## Recommended Strategy: **Hybrid Batching**

```python
def generate_summaries_batched(games, batch_size=5):
    """
    Process games in batches for best balance.

    Batch by time slot:
    - Batch 1: Thursday night (1 game)
    - Batch 2: Early Sunday (6-8 games)
    - Batch 3: Late Sunday (4-5 games)
    - Batch 4: Sunday night (1 game)
    - Batch 5: Monday night (1 game)
    """
    batches = create_time_slot_batches(games)

    all_summaries = []
    for batch in batches:
        # Process each batch as single API call
        summaries = generate_batch(batch)
        all_summaries.extend(summaries)

    return all_summaries
```

### Why Hybrid Wins

**Compared to Single Call:**
- ✅ Better resilience (3-5 batches vs 1)
- ✅ Smaller context per call (less likely to fail)
- ✅ Can retry failed batches without regenerating everything
- ✅ Faster (can parallelize batches)
- ⚖️ Slightly higher cost (~2-3 cents vs 4 cents)

**Compared to Multiple Calls:**
- ✅ Much lower cost (3-5 calls vs 14)
- ✅ Better quality (maintains context within time slots)
- ✅ Simpler orchestration
- ✅ Still allows parallelization
- ⚖️ Less granular error handling

### Implementation

**Batch by time slot for context:**
```python
def create_time_slot_batches(games):
    thursday = [g for g in games if g['date'].startswith('Thu')]
    sunday_early = [g for g in games if g['date'].startswith('Sun') and '1:00PM' in g['date']]
    sunday_late = [g for g in games if g['date'].startswith('Sun') and ('4:' in g['date'] or '8:' in g['date'])]
    monday = [g for g in games if g['date'].startswith('Mon')]

    return [thursday, sunday_early, sunday_late, monday]
```

**Benefits of time-slot batching:**
- Games in same slot often have narrative connections
- Thursday game can be "Game of the Week" candidate
- Sunday batches maintain competitive context
- Natural error boundaries (if Sunday early fails, still have late games)

## Decision Matrix

| Criteria | Single | Multiple | Hybrid |
|----------|--------|----------|--------|
| **Cost** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| **Speed** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Quality** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Reliability** | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Simplicity** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| **Debuggability** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

## Migration Path

If you want to transition:

### Phase 1: Add batching support (keep single as default)
```python
# generate_json.py
parser.add_argument('--batch-size', type=int, default=0,
                   help='Batch size (0 = process all at once)')
```

### Phase 2: Test hybrid approach
```bash
# Try batches of 5
python generate_json.py --week 9 --batch-size 5

# Compare quality with single call
python generate_json.py --week 9 --batch-size 0
```

### Phase 3: Make hybrid the default after validation

### Phase 4: Add parallel processing
```python
# Process batches in parallel
import asyncio
results = await asyncio.gather(*[process_batch(b) for b in batches])
```

## My Recommendation

**Start with: Single API call** (current approach)
- Simplest
- Cheapest
- Good enough quality
- You're already doing this

**Switch to: Hybrid batching** when:
- Newsletter consistently takes >60 seconds
- You hit context window limits (>120K tokens)
- You need better resilience
- Cost difference ($1-2/season) is acceptable

**Only use: Individual calls** if:
- You need <15 second generation
- Reliability is absolutely critical
- You plan to cache/reuse individual summaries
- Cost isn't a concern

The extra $1-2 per season isn't worth the complexity unless you have specific needs.
