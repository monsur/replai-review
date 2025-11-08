#!/bin/bash

################################################################################
# ReplAI Review - V2 Pipeline Orchestration
#
# This script chains all 3 stages of the newsletter pipeline:
#   Stage 1: Fetch games from ESPN API
#   Stage 2: Generate summaries and badges with AI
#   Stage 3: Publish HTML and update archive
#
# Usage:
#   ./run_all_v2.sh --date 20251109 --type day
#   ./run_all_v2.sh --date 20251109 --type day --provider openai
#   ./run_all_v2.sh --date 20251109 --type week --provider gemini
#
# Exit codes:
#   0 = Success
#   1 = No games found for given date
#   2 = Error (file not found, invalid format, etc.)
#   3 = Invalid arguments
################################################################################

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/config.yaml"
DOCS_DIR="${SCRIPT_DIR}/docs"

# Default values
PROVIDER=""
TYPE="day"
DATE=""

################################################################################
# Helper Functions
################################################################################

log_info() {
    echo -e "${CYAN}ℹ  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}" >&2
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_section() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

print_usage() {
    cat <<EOF
Usage: run_all_v2.sh [OPTIONS]

Required arguments:
  --date DATE        Date in YYYYMMDD format (e.g., 20251109)
  --type TYPE        Newsletter type: 'day' or 'week' (default: day)

Optional arguments:
  --provider PROVIDER  AI provider: claude, openai, or gemini
  --config CONFIG     Path to config.yaml (default: ./config.yaml)
  --help             Show this help message

Examples:
  ./run_all_v2.sh --date 20251109 --type day
  ./run_all_v2.sh --date 20251109 --type week --provider openai
  ./run_all_v2.sh --date 20251109 --type day --provider gemini

EOF
}

validate_date_format() {
    local date=$1

    # Check if date matches YYYYMMDD format
    if ! [[ $date =~ ^[0-9]{8}$ ]]; then
        log_error "Invalid date format: $date"
        log_error "Expected YYYYMMDD format (e.g., 20251109)"
        return 1
    fi

    # Extract year, month, day
    local year=${date:0:4}
    local month=${date:4:2}
    local day=${date:6:2}

    # Validate month (01-12)
    if ! [[ $month =~ ^(0[1-9]|1[0-2])$ ]]; then
        log_error "Invalid month: $month"
        return 1
    fi

    # Validate day (01-31) - basic check
    if ! [[ $day =~ ^(0[1-9]|[12][0-9]|3[01])$ ]]; then
        log_error "Invalid day: $day"
        return 1
    fi

    return 0
}

validate_type() {
    local type=$1

    case "$type" in
        day|week)
            return 0
            ;;
        *)
            log_error "Invalid type: $type"
            log_error "Expected 'day' or 'week'"
            return 1
            ;;
    esac
}

validate_provider() {
    local provider=$1

    if [[ -z "$provider" ]]; then
        return 0  # Optional
    fi

    case "$provider" in
        claude|openai|gemini)
            return 0
            ;;
        *)
            log_error "Invalid provider: $provider"
            log_error "Expected 'claude', 'openai', or 'gemini'"
            return 1
            ;;
    esac
}

check_python_modules() {
    python3 -c "import requests, bs4, yaml, jinja2, pydantic" 2>/dev/null || {
        log_error "Missing required Python modules"
        log_info "Run: pip install -q requests beautifulsoup4 pyyaml jinja2 pydantic"
        return 1
    }
    return 0
}

################################################################################
# Stage Functions
################################################################################

run_stage_1() {
    local date=$1
    local type=$2

    log_section "STAGE 1: FETCH GAMES"

    log_info "Fetching games for date: $date (type: $type)"

    # Run Stage 1
    python3 "${SCRIPT_DIR}/fetch_games.py" \
        --date "$date" \
        --type "$type" \
        --config "$CONFIG_FILE"

    local exit_code=$?

    if [[ $exit_code -eq 1 ]]; then
        log_warning "No games found for $date"
        return 1
    elif [[ $exit_code -ne 0 ]]; then
        log_error "Stage 1 failed with exit code $exit_code"
        return 2
    fi

    log_success "Stage 1 complete"
    return 0
}

run_stage_2() {
    local games_path=$1
    local provider=$2

    log_section "STAGE 2: GENERATE NEWSLETTER"

    log_info "Loading games from: $games_path"

    # Check if games.json exists
    if [[ ! -f "$games_path" ]]; then
        log_error "Games file not found: $games_path"
        return 2
    fi

    # Build Stage 2 command
    local cmd="python3 \"${SCRIPT_DIR}/generate_newsletter.py\" --input \"$games_path\" --config \"$CONFIG_FILE\""

    if [[ -n "$provider" ]]; then
        cmd="$cmd --provider $provider"
    fi

    log_info "Running: $cmd"
    eval "$cmd"

    local exit_code=$?

    if [[ $exit_code -ne 0 ]]; then
        log_error "Stage 2 failed with exit code $exit_code"
        return 2
    fi

    log_success "Stage 2 complete"
    return 0
}

run_stage_3() {
    local newsletter_path=$1

    log_section "STAGE 3: PUBLISH NEWSLETTER"

    log_info "Loading newsletter from: $newsletter_path"

    # Check if newsletter.json exists
    if [[ ! -f "$newsletter_path" ]]; then
        log_error "Newsletter file not found: $newsletter_path"
        return 2
    fi

    # Ensure docs directory exists
    mkdir -p "$DOCS_DIR"

    # Run Stage 3
    python3 "${SCRIPT_DIR}/publish_newsletter.py" \
        --input "$newsletter_path" \
        --output "$DOCS_DIR"

    local exit_code=$?

    if [[ $exit_code -ne 0 ]]; then
        log_error "Stage 3 failed with exit code $exit_code"
        return 2
    fi

    log_success "Stage 3 complete"
    return 0
}

################################################################################
# Main Execution
################################################################################

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --date)
                DATE="$2"
                shift 2
                ;;
            --type)
                TYPE="$2"
                shift 2
                ;;
            --provider)
                PROVIDER="$2"
                shift 2
                ;;
            --config)
                CONFIG_FILE="$2"
                shift 2
                ;;
            --help)
                print_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                print_usage
                exit 3
                ;;
        esac
    done

    # Validate required arguments
    if [[ -z "$DATE" ]]; then
        log_error "Missing required argument: --date"
        print_usage
        exit 3
    fi

    # Validate inputs
    validate_date_format "$DATE" || exit 3
    validate_type "$TYPE" || exit 3
    validate_provider "$PROVIDER" || exit 3

    # Check config file exists
    if [[ ! -f "$CONFIG_FILE" ]]; then
        log_error "Config file not found: $CONFIG_FILE"
        exit 2
    fi

    # Check Python modules
    check_python_modules || exit 2

    # Print header
    log_section "ReplAI Review - V2 Pipeline"
    log_info "Date: $DATE"
    log_info "Type: $TYPE"
    if [[ -n "$PROVIDER" ]]; then
        log_info "Provider: $PROVIDER"
    fi
    log_info "Config: $CONFIG_FILE"

    # Record start time
    local start_time=$(date +%s)

    # Run Stage 1
    run_stage_1 "$DATE" "$TYPE"
    local stage1_exit=$?

    if [[ $stage1_exit -eq 1 ]]; then
        log_warning "Pipeline stopped: No games found for $DATE"
        exit 1
    elif [[ $stage1_exit -ne 0 ]]; then
        log_error "Pipeline failed at Stage 1"
        exit 2
    fi

    # Determine games.json path
    local games_path

    # Parse date to get year and week
    local year=${DATE:0:4}
    local month=${DATE:4:2}
    local day=${DATE:6:2}

    # Calculate week (this matches stage_utils logic)
    # For 2025, season starts Sept 4 (Thursday)
    local season_start="2025-09-04"
    local target_date="$year-$month-$day"

    # Use Python to calculate week
    local week=$(python3 -c "
from datetime import datetime
from pathlib import Path
import sys
sys.path.insert(0, '${SCRIPT_DIR}')
from week_calculator import DateBasedWeekCalculator

calc = DateBasedWeekCalculator(2025)
target = datetime.strptime('$target_date', '%Y-%m-%d')
week = calc.get_week_for_date(target)
print(week)
" 2>/dev/null)

    if [[ -z "$week" ]]; then
        log_error "Failed to calculate week for date $DATE"
        exit 2
    fi

    # Construct games.json path based on type
    if [[ "$TYPE" == "day" ]]; then
        games_path="${SCRIPT_DIR}/tmp/${year}-week$(printf "%02d" "$week")/${DATE}/games.json"
    else
        games_path="${SCRIPT_DIR}/tmp/${year}-week$(printf "%02d" "$week")/games.json"
    fi

    # Run Stage 2
    run_stage_2 "$games_path" "$PROVIDER"
    if [[ $? -ne 0 ]]; then
        log_error "Pipeline failed at Stage 2"
        exit 2
    fi

    # Determine newsletter.json path
    local newsletter_path="${games_path%/*}/newsletter.json"

    # Run Stage 3
    run_stage_3 "$newsletter_path"
    if [[ $? -ne 0 ]]; then
        log_error "Pipeline failed at Stage 3"
        exit 2
    fi

    # Calculate elapsed time
    local end_time=$(date +%s)
    local elapsed=$((end_time - start_time))
    local minutes=$((elapsed / 60))
    local seconds=$((elapsed % 60))

    # Success message
    log_section "✅ PIPELINE COMPLETE"
    log_success "Newsletter published successfully!"
    log_info "Elapsed time: ${minutes}m ${seconds}s"
    log_info "HTML: ${DOCS_DIR}/"
    log_info "Archive: ${DOCS_DIR}/archive.json"

    exit 0
}

# Run main function
main "$@"
