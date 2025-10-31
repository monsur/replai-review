# Team Icons Integration Plan

## What's Been Done

1. ✅ Updated `newsletter_playground.html` with:
   - CSS for `.team-icon` class (28x28px icons)
   - Updated `.matchup` to use flexbox with icons
   - Example HTML showing icons inline with team names

2. ✅ Added `team_icons.json` with base64-encoded PNG icons for all teams

## What Needs to Be Done

### 1. Update `newsletter_prompt.txt`

Add instructions for the AI to include team icons in the matchup line:

```
TEAM ICONS:
You have access to team icons via the team_icons data structure.
For each team in the matchup, include their icon inline:

<img src="{team_icons[TEAM_ABB].icon_data_uri}" alt="{TEAM_ABB}" class="team-icon">

Example matchup with icons:
<div class="matchup">
    <img src="{away_team_icon_uri}" alt="NYJ" class="team-icon">
    <span>New York Jets</span>
    <span>@</span>
    <img src="{home_team_icon_uri}" alt="CIN" class="team-icon">
    <span>Cincinnati Bengals</span>
</div>
```

### 2. Update `generate_newsletter.py`

Load team_icons.json and pass it to the AI:

```python
def load_team_icons(icons_file: str = "team_icons.json") -> dict:
    """Load team icons from JSON file."""
    with open(icons_file, 'r', encoding='utf-8') as f:
        return json.load(f)

# In main():
team_icons = load_team_icons()

# Modify the user_message to include team icons:
user_message = f"""
Here are the NFL game recaps from this week. Please generate a newsletter following the guidelines in the system prompt.

TEAM ICONS DATA (use icon_data_uri for each team):
{json.dumps(team_icons, indent=2)}

GAME RECAPS:
{recap_content}
"""
```

### 3. Update Wrapper CSS in `generate_newsletter.py`

Add the team icon CSS to the wrapper:

```python
.team-icon {{
    width: 28px;
    height: 28px;
    object-fit: contain;
}}
```

And update `.matchup`:

```python
.matchup {{
    display: flex;
    align-items: center;
    gap: 8px;
}}
```

## Testing

Once implemented:
1. Run `python generate_newsletter.py --week 8`
2. Check that `output/week_8/newsletter.html` shows team icons next to team names
3. Verify icons are properly sized and aligned

## Team Abbreviation Mapping

Common abbreviations in `team_icons.json`:
- NYJ = New York Jets
- CIN = Cincinnati Bengals
- BUF = Buffalo Bills
- MIA = Miami Dolphins
- NE = New England Patriots
- etc.

The AI will need to map team names from ESPN recaps to these abbreviations.
