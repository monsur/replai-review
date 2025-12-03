#!/bin/bash
# ReplAI Review - Run All Scripts
#
# This script runs all four scripts in sequence to generate a complete ReplAI Review newsletter.
# Usage:
#   ./run_all.sh                    # Auto-detect week
#   ./run_all.sh 8                  # Specify week number (positional)
#   ./run_all.sh 8 openai           # Specify week and AI provider (positional)
#   ./run_all.sh --week 8           # Specify week number (flag-based)
#   ./run_all.sh --week 8 --provider openai  # Flag-based with provider

set -e  # Exit on error

WEEK=""
PROVIDER=""

# Parse arguments - support both positional and flag-based
while [[ $# -gt 0 ]]; do
    case $1 in
        --week)
            WEEK="--week $2"
            shift 2
            ;;
        --provider)
            PROVIDER="--provider $2"
            shift 2
            ;;
        *)
            # Positional argument handling
            if [ -z "$WEEK" ]; then
                WEEK="--week $1"
                shift
            elif [ -z "$PROVIDER" ]; then
                PROVIDER="--provider $1"
                shift
            else
                shift
            fi
            ;;
    esac
done

echo "=================================="
echo "ReplAI Review Generator"
echo "AI-Powered NFL Recaps"
echo "=================================="
echo ""

# Script 1: Fetch game data from ESPN APIs
echo "Step 1/4: Fetching game data from ESPN APIs..."
python3 fetch_game_data.py $WEEK
echo ""

# Script 2: Generate JSON with AI
echo "Step 2/4: Generating summaries and badges with AI..."
python3 generate_json.py $WEEK $PROVIDER
echo ""

# Script 3: Validate newsletter data
# echo "Step 3/4: Validating newsletter data..."
# python3 validate_newsletter.py $WEEK
# echo ""

# Script 4: Format HTML newsletter
echo "Step 4/4: Formatting HTML newsletter..."
python3 format_newsletter.py $WEEK
echo ""

echo "=================================="
echo "✓ ReplAI Review generation complete!"
echo "=================================="
