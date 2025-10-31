#!/bin/bash
# ReplAI Review - Run All Scripts
#
# This script runs all three scripts in sequence to generate a complete ReplAI Review newsletter.
# Usage:
#   ./run_all.sh              # Auto-detect week
#   ./run_all.sh 8            # Specify week number
#   ./run_all.sh 8 openai     # Specify week and AI provider

set -e  # Exit on error

WEEK=""
PROVIDER=""

# Parse arguments
if [ ! -z "$1" ]; then
    WEEK="--week $1"
fi

if [ ! -z "$2" ]; then
    PROVIDER="--provider $2"
fi

echo "=================================="
echo "ReplAI Review Generator"
echo "AI-Powered NFL Recaps"
echo "=================================="
echo ""

# Script 1: Fetch recaps
echo "Step 1/3: Fetching game recaps from ESPN..."
python3 fetch_recaps.py $WEEK
echo ""

# Script 2: Process recaps
echo "Step 2/3: Processing and combining recaps..."
python3 process_recaps.py $WEEK
echo ""

# Script 3: Generate newsletter
echo "Step 3/3: Generating ReplAI Review with AI..."
python3 generate_newsletter.py $WEEK $PROVIDER
echo ""

echo "=================================="
echo "✓ ReplAI Review generation complete!"
echo "=================================="
