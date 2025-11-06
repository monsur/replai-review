# Automated Workflow Strategy: Handling Validation Failures

## Validation Failure Scenarios

### Severity Levels

**ERROR (Exit Code 1):**
- Wrong player-team matchups (QB playing for wrong team)
- Invalid data formats
- Missing critical fields
- **Action: Block publishing, require manual intervention**

**WARNING (Exit Code 0):**
- Suspicious patterns (unusual score, questionable record)
- Missing optional fields
- Badge mismatches
- **Action: Allow publishing with notification**

**INFO (Exit Code 0):**
- Missing optional metadata
- Suggestions for improvement
- **Action: Log only, no blocking**

## Recommended Automated Workflow

### Strategy: Fail Gracefully with Notification

```bash
#!/bin/bash
# automated_newsletter.sh

WEEK=$1
YEAR=2025

echo "🏈 Generating newsletter for Week $WEEK..."

# Step 1: Fetch recaps
python fetch_recaps.py --week $WEEK
if [ $? -ne 0 ]; then
    echo "❌ Failed to fetch recaps"
    exit 1
fi

# Step 2: Process recaps
python process_recaps.py --week $WEEK
if [ $? -ne 0 ]; then
    echo "❌ Failed to process recaps"
    exit 1
fi

# Step 3: Generate JSON with AI
source .env
python generate_json.py --week $WEEK
if [ $? -ne 0 ]; then
    echo "❌ Failed to generate JSON"
    exit 1
fi

# Step 4: VALIDATE
NEWSLETTER_FILE="tmp/${YEAR}-week$(printf '%02d' $WEEK)/newsletter.json"
python validate_newsletter.py "$NEWSLETTER_FILE" 2>&1 | tee validation_report.txt
VALIDATION_EXIT_CODE=$?

if [ $VALIDATION_EXIT_CODE -eq 1 ]; then
    echo ""
    echo "🚨 VALIDATION FAILED 🚨"
    echo ""

    # Strategy A: Auto-attempt fixes
    echo "Attempting automatic fixes..."
    python auto_fix_newsletter.py "$NEWSLETTER_FILE" 2>&1 | tee auto_fix_report.txt

    # Re-validate after auto-fix
    python validate_newsletter.py "$NEWSLETTER_FILE" 2>&1 | tee validation_report_v2.txt
    VALIDATION_EXIT_CODE=$?

    if [ $VALIDATION_EXIT_CODE -eq 1 ]; then
        # Still failing after auto-fix
        echo "❌ Auto-fix failed. Manual intervention required."

        # Send notification
        python send_notification.py \
            --type "validation_failed" \
            --week $WEEK \
            --report validation_report_v2.txt \
            --fix-report auto_fix_report.txt

        # Save draft for manual review
        cp "$NEWSLETTER_FILE" "tmp/${YEAR}-week$(printf '%02d' $WEEK)/newsletter_draft_needs_review.json"

        # Exit with failure (don't publish)
        exit 1
    else
        echo "✅ Auto-fix succeeded!"
        # Continue to publishing
    fi
fi

# Step 5: Format newsletter (only if validation passed)
echo "✅ Validation passed. Generating newsletter..."
python format_newsletter.py --week $WEEK

echo "🎉 Newsletter generated successfully!"
exit 0
```

## Auto-Fix Strategies

### Implement `auto_fix_newsletter.py`

```python
#!/usr/bin/env python3
"""
Automatic fixes for common validation errors.
"""

import json
import sys
from pathlib import Path

def auto_fix_newsletter(newsletter_path):
    """Apply automatic fixes where possible."""
    with open(newsletter_path, 'r') as f:
        data = json.load(f)

    fixes_applied = []

    for game in data['games']:
        game_id = game.get('game_id', 'unknown')

        # Fix 1: Remove player mentions that don't match teams
        summary = game.get('summary', '')
        away_abbr = game.get('away_abbr', '')
        home_abbr = game.get('home_abbr', '')

        # Known QB-Team mismatches (update this list)
        QB_TEAMS = {
            'Daniel Jones': 'NYG',
            'Aaron Rodgers': 'NYJ',
            'Sam Darnold': 'MIN',
            # ... (full list)
        }

        for qb_name, correct_team in QB_TEAMS.items():
            if qb_name in summary and correct_team not in [away_abbr, home_abbr]:
                # Remove the player mention
                summary = summary.replace(f"<strong>{qb_name}</strong>", "the quarterback")
                fixes_applied.append(f"Game {game_id}: Removed {qb_name} (wrong team)")

        game['summary'] = summary

        # Fix 2: Correct badge mismatches
        away_score = game.get('away_score', 0)
        home_score = game.get('home_score', 0)
        diff = abs(away_score - home_score)
        badges = game.get('badges', [])

        # Remove nail-biter if diff > 3
        if 'nail-biter' in badges and diff > 3:
            badges.remove('nail-biter')
            fixes_applied.append(f"Game {game_id}: Removed incorrect 'nail-biter' badge ({diff}pt game)")

        # Add nail-biter if diff <= 3
        if diff <= 3 and 'nail-biter' not in badges:
            badges.append('nail-biter')
            fixes_applied.append(f"Game {game_id}: Added missing 'nail-biter' badge ({diff}pt game)")

        # Remove blowout if diff < 21
        if 'blowout' in badges and diff < 21:
            badges.remove('blowout')
            fixes_applied.append(f"Game {game_id}: Removed incorrect 'blowout' badge ({diff}pt game)")

        game['badges'] = badges

        # Fix 3: Set records to "N/A" if they seem wrong
        week = data.get('week', 0)
        for team_type in ['away', 'home']:
            record = game.get(f'{team_type}_record', '')
            if record and record != 'N/A':
                parts = record.split('-')
                if len(parts) >= 2:
                    total_games = sum(int(p) for p in parts)
                    # If total games >= week, record might be wrong
                    if total_games >= week and week > 1:
                        game[f'{team_type}_record'] = 'N/A'
                        fixes_applied.append(
                            f"Game {game_id}: Set {team_type}_record to N/A "
                            f"(suspicious: {record} in week {week})"
                        )

    # Save fixed version
    with open(newsletter_path, 'w') as f:
        json.dump(data, f, indent=2)

    return fixes_applied

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python auto_fix_newsletter.py <newsletter.json>")
        sys.exit(1)

    newsletter_path = Path(sys.argv[1])

    print("Attempting automatic fixes...")
    fixes = auto_fix_newsletter(newsletter_path)

    if fixes:
        print(f"\n✅ Applied {len(fixes)} fixes:")
        for fix in fixes:
            print(f"  - {fix}")
        sys.exit(0)
    else:
        print("\n⚠️  No automatic fixes available")
        sys.exit(1)
```

## Notification Strategies

### Option 1: Email Notification

```python
#!/usr/bin/env python3
"""
Send notification when validation fails.
"""

import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import argparse

def send_email_notification(week, report_file, fix_report_file=None):
    """Send email with validation report."""

    # Read reports
    with open(report_file, 'r') as f:
        validation_report = f.read()

    fix_report = ""
    if fix_report_file:
        with open(fix_report_file, 'r') as f:
            fix_report = f.read()

    # Email content
    subject = f"🚨 Newsletter Week {week} Validation Failed"

    body = f"""
Newsletter validation failed for Week {week}.

VALIDATION REPORT:
{'='*70}
{validation_report}

"""

    if fix_report:
        body += f"""
AUTO-FIX REPORT:
{'='*70}
{fix_report}

"""

    body += f"""
NEXT STEPS:
1. Review the validation report above
2. Check the draft file: tmp/2025-week{week:02d}/newsletter_draft_needs_review.json
3. Either:
   a) Manually fix the JSON file
   b) Re-run generate_json.py with corrected ESPN recaps
   c) Update auto_fix_newsletter.py with new fix rules

Then re-run validation:
python validate_newsletter.py tmp/2025-week{week:02d}/newsletter.json

QUICK FIXES:
- Wrong QB names: Edit summary field to remove incorrect players
- Wrong records: Update away_record/home_record fields
- Badge issues: Adjust badges array

Questions? Check DEBUGGING_GUIDE.md
"""

    # Send email (configure with your settings)
    sender_email = "newsletter-bot@yourdomain.com"
    receiver_email = "you@yourdomain.com"

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    # Use environment variables for credentials
    import os
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_user = os.getenv('SMTP_USER')
    smtp_password = os.getenv('SMTP_PASSWORD')

    if smtp_user and smtp_password:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        print(f"✅ Email sent to {receiver_email}")
    else:
        print("⚠️  Email credentials not configured. Report saved to file only.")
        print(body)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--type', required=True)
    parser.add_argument('--week', type=int, required=True)
    parser.add_argument('--report', required=True)
    parser.add_argument('--fix-report')

    args = parser.parse_args()

    if args.type == "validation_failed":
        send_email_notification(args.week, args.report, args.fix_report)
```

### Option 2: Slack Notification

```python
def send_slack_notification(week, report_file):
    """Send Slack notification."""
    import os
    import requests

    webhook_url = os.getenv('SLACK_WEBHOOK_URL')
    if not webhook_url:
        print("⚠️  SLACK_WEBHOOK_URL not configured")
        return

    with open(report_file, 'r') as f:
        report = f.read()

    # Extract error count
    error_count = report.count('[ERROR]')
    warning_count = report.count('[WARNING]')

    message = {
        "text": f"🚨 Newsletter Week {week} Validation Failed",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🏈 Week {week} Newsletter Validation Failed"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Errors:* {error_count}\n*Warnings:* {warning_count}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"```{report[:2000]}```"  # Slack limit
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Action Required:* Manual review needed before publishing"
                }
            }
        ]
    }

    response = requests.post(webhook_url, json=message)
    if response.status_code == 200:
        print("✅ Slack notification sent")
    else:
        print(f"❌ Slack notification failed: {response.status_code}")
```

### Option 3: Create GitHub Issue (if using GitHub)

```python
def create_github_issue(week, report_file):
    """Create GitHub issue for manual intervention."""
    import os
    import requests

    github_token = os.getenv('GITHUB_TOKEN')
    repo = os.getenv('GITHUB_REPO')  # e.g., "username/football"

    if not github_token or not repo:
        print("⚠️  GitHub credentials not configured")
        return

    with open(report_file, 'r') as f:
        report = f.read()

    issue_data = {
        "title": f"Newsletter Week {week} Validation Failed - Manual Review Needed",
        "body": f"""
## Validation Report

```
{report}
```

## Next Steps

1. Review validation errors above
2. Check draft: `tmp/2025-week{week:02d}/newsletter_draft_needs_review.json`
3. Apply fixes manually or update auto-fix rules
4. Re-run validation

## Resources

- [Debugging Guide](./DEBUGGING_GUIDE.md)
- [Prevention Plan](./PREVENTION_PLAN.md)
""",
        "labels": ["newsletter", "validation-failed", "needs-review"]
    }

    url = f"https://api.github.com/repos/{repo}/issues"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    response = requests.post(url, json=issue_data, headers=headers)
    if response.status_code == 201:
        issue_url = response.json()['html_url']
        print(f"✅ GitHub issue created: {issue_url}")
    else:
        print(f"❌ Failed to create issue: {response.status_code}")
```

## Decision Tree

```
Validation Runs
    │
    ├─ Exit Code 0 (SUCCESS or WARNINGS only)
    │   └─> Continue to format_newsletter.py
    │       └─> Publish
    │
    └─ Exit Code 1 (ERRORS found)
        │
        ├─> Run auto_fix_newsletter.py
        │   │
        │   ├─ Fixes Applied Successfully
        │   │   └─> Re-validate
        │   │       ├─ Now passing → Continue to publish
        │   │       └─ Still failing → Manual intervention
        │   │
        │   └─ No Fixes Available
        │       └─> Manual intervention
        │
        └─> Manual Intervention Process:
            1. Send notification (email/Slack/GitHub)
            2. Save draft with "_needs_review" suffix
            3. Exit with error code 1 (block publishing)
            4. Human reviews and fixes
            5. Human re-runs validation
            6. Human manually publishes when ready
```

## GitHub Actions Example

```yaml
# .github/workflows/newsletter.yml
name: Generate Newsletter

on:
  schedule:
    # Run Tuesday at 10am EST (after Monday night games)
    - cron: '0 15 * * 2'
  workflow_dispatch:
    inputs:
      week:
        description: 'Week number'
        required: true
        type: number

jobs:
  generate:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Generate newsletter
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          SMTP_USER: ${{ secrets.SMTP_USER }}
          SMTP_PASSWORD: ${{ secrets.SMTP_PASSWORD }}
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
        run: |
          WEEK=${{ github.event.inputs.week || 'auto' }}
          bash automated_newsletter.sh $WEEK
        continue-on-error: true
        id: generate

      - name: Upload artifacts on failure
        if: steps.generate.outcome == 'failure'
        uses: actions/upload-artifact@v3
        with:
          name: failed-newsletter-week-${{ github.event.inputs.week }}
          path: |
            validation_report.txt
            auto_fix_report.txt
            tmp/*/newsletter_draft_needs_review.json

      - name: Create issue on failure
        if: steps.generate.outcome == 'failure'
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('validation_report.txt', 'utf8');
            github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: `Newsletter Week ${{ github.event.inputs.week }} Failed Validation`,
              body: `## Validation Report\n\`\`\`\n${report}\n\`\`\``,
              labels: ['newsletter', 'validation-failed']
            });

      - name: Publish newsletter
        if: steps.generate.outcome == 'success'
        run: |
          # Copy to your publishing location
          # Upload to S3, send via email, etc.
          echo "Newsletter published successfully!"
```

## Summary: Best Practice Workflow

1. **Run validation after JSON generation**
2. **On validation failure:**
   - Attempt automatic fixes
   - Re-validate
   - If still failing:
     - Send notification (email/Slack/GitHub issue)
     - Save draft for manual review
     - Block publishing (exit 1)
3. **On validation success:**
   - Continue to format and publish
4. **Human intervention:**
   - Review errors
   - Apply manual fixes
   - Re-run validation
   - Manually publish when ready

This gives you:
- ✅ Automated workflow for 90% of cases
- ✅ Safety net (won't publish bad data)
- ✅ Clear notification when intervention needed
- ✅ Easy recovery path
