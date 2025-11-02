"""
Data Models with Validation

This module defines Pydantic models for validating data throughout the system.
All data crossing boundaries (config, AI output, user input) should be validated.
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Optional
from datetime import datetime
from enum import Enum


class GameBadge(str, Enum):
    """Valid game badges for highlighting special games."""
    UPSET = "UPSET"
    CLOSE_GAME = "CLOSE GAME"
    BLOWOUT = "BLOWOUT"
    PRIMETIME = "PRIMETIME"
    OVERTIME = "OVERTIME"
    PLAYOFF_IMPLICATIONS = "PLAYOFF IMPLICATIONS"


class Game(BaseModel):
    """
    Validated game model.

    Validates that game data is complete and reasonable before processing.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )

    game_id: Optional[str] = Field(
        None,
        min_length=1,
        description="Unique game identifier (auto-generated if not provided)"
    )

    away_team: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Away team name"
    )

    away_abbr: str = Field(
        ...,
        min_length=2,
        max_length=5,
        description="Away team abbreviation (e.g., 'NYJ', 'KC')"
    )

    away_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Away team score (0-100)"
    )

    away_record: Optional[str] = Field(
        None,
        pattern=r'^\d+-\d+(-\d+)?$',
        description="Away team record (e.g., '5-3' or '3-4-1')"
    )

    home_team: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Home team name"
    )

    home_abbr: str = Field(
        ...,
        min_length=2,
        max_length=5,
        description="Home team abbreviation (e.g., 'NYJ', 'KC')"
    )

    home_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Home team score (0-100)"
    )

    home_record: Optional[str] = Field(
        None,
        pattern=r'^\d+-\d+(-\d+)?$',
        description="Home team record (e.g., '5-3' or '3-4-1')"
    )

    game_date: Optional[str] = Field(
        None,
        description="Game date (YYYY-MM-DD format)"
    )

    summary: str = Field(
        ...,
        min_length=50,
        max_length=1500,
        description="Game summary (3-10 sentences, 50-1500 characters)"
    )

    badges: List[str] = Field(
        default_factory=list,
        max_length=5,
        description="Game badges (UPSET, CLOSE GAME, etc.)"
    )

    recap_url: Optional[str] = Field(
        None,
        description="URL to the full game recap"
    )

    stadium: Optional[str] = Field(
        None,
        min_length=3,
        max_length=100,
        description="Stadium name where game was played"
    )

    tv_network: Optional[str] = Field(
        None,
        min_length=2,
        max_length=50,
        description="TV network broadcasting the game (e.g., 'CBS', 'NBC', 'ESPN')"
    )

    def model_post_init(self, __context) -> None:
        """Additional validation and auto-generation after model creation."""
        # Validate teams are different
        if self.away_team.lower() == self.home_team.lower():
            raise ValueError(
                f"Away team and home team cannot be the same: '{self.away_team}'"
            )

        # Generate game_id if missing
        if self.game_id is None:
            import re

            # Try to extract from recap_url if available
            if self.recap_url:
                # ESPN URLs have format: .../gameId/401772758
                match = re.search(r'/gameId/(\d+)', self.recap_url)
                if match:
                    self.game_id = match.group(1)
                    return

                # Also try end of URL
                match = re.search(r'/_/gameId/(\d+)', self.recap_url)
                if match:
                    self.game_id = match.group(1)
                    return

            # Generate a simple ID from teams if no URL
            self.game_id = f"{self.away_team.lower().replace(' ', '_')}_at_{self.home_team.lower().replace(' ', '_')}"

    @field_validator('summary')
    @classmethod
    def validate_summary_length(cls, v: str) -> str:
        """Ensure summary has reasonable sentence count."""
        if not v.strip():
            raise ValueError("Summary cannot be empty")

        # Count sentences (rough estimate)
        sentence_endings = v.count('.') + v.count('!') + v.count('?')

        if sentence_endings < 2:
            raise ValueError(
                f"Summary too short ({sentence_endings} sentences detected, need at least 2)"
            )

        if sentence_endings > 15:
            raise ValueError(
                f"Summary too long ({sentence_endings} sentences detected, max 15)"
            )

        return v

    @field_validator('away_team', 'home_team')
    @classmethod
    def validate_team_names(cls, v: str) -> str:
        """Ensure team names are reasonable."""
        if len(v.strip()) < 2:
            raise ValueError(f"Team name too short: '{v}'")

        if v.strip().lower() in ['unknown', 'tbd', 'n/a']:
            raise ValueError(f"Invalid team name: '{v}'")

        return v.strip()


class NewsletterData(BaseModel):
    """
    Validated AI-generated newsletter data.

    This is the output format expected from AI providers.
    """

    week: int = Field(
        ...,
        ge=1,
        le=22,
        description="NFL week number (1-18 regular season, 19-22 playoffs)"
    )

    year: int = Field(
        ...,
        ge=2020,
        le=2035,
        description="NFL season year"
    )

    games: List[Game] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="List of games (typically 13-16 per week)"
    )

    generated_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp of generation"
    )

    ai_provider: Optional[str] = Field(
        None,
        description="AI provider used for generation"
    )

    @field_validator('games')
    @classmethod
    def validate_games_count(cls, v: List[Game]) -> List[Game]:
        """Warn if game count seems unusual."""
        if len(v) < 8:
            # Allow but log warning for weeks with few games (bye weeks, etc.)
            print(f"⚠️  Warning: Only {len(v)} games (typical week has 13-16)")

        if len(v) > 17:
            raise ValueError(
                f"Too many games for a single week: {len(v)} (max 16 regular season + 1 special)"
            )

        return v

    @property
    def game_count(self) -> int:
        """Total number of games."""
        return len(self.games)

    @property
    def upset_count(self) -> int:
        """Number of games marked as upsets."""
        return sum(1 for game in self.games if "UPSET" in game.badges)


class NFLSeasonConfig(BaseModel):
    """NFL season configuration section."""

    year: int = Field(
        ...,
        ge=2020,
        le=2035,
        description="NFL season year"
    )

    season_start_date: str = Field(
        ...,
        pattern=r'^\d{4}-\d{2}-\d{2}$',
        description="Season start date (YYYY-MM-DD)"
    )

    @field_validator('season_start_date')
    @classmethod
    def validate_season_start_date(cls, v: str) -> str:
        """Ensure date is valid and reasonable."""
        try:
            date = datetime.strptime(v, '%Y-%m-%d')

            # NFL season typically starts in September
            if date.month < 8 or date.month > 10:
                print(f"⚠️  Warning: Season start date {v} is unusual (typically September)")

        except ValueError as e:
            raise ValueError(f"Invalid date format: {v} (expected YYYY-MM-DD)")

        return v


class StorageConfig(BaseModel):
    """Storage configuration section."""

    docs_dir: str = Field(default="docs", min_length=1)
    tmp_dir: str = Field(default="tmp", min_length=1)
    recap_subdir: str = Field(default="recaps", min_length=1)
    combined_filename: str = Field(default="combined.html", min_length=1)

    @field_validator('docs_dir', 'tmp_dir', 'recap_subdir', 'combined_filename')
    @classmethod
    def validate_path_components(cls, v: str) -> str:
        """Ensure path components are safe."""
        if '..' in v:
            raise ValueError(f"Path traversal not allowed: '{v}'")

        if v.startswith('/'):
            raise ValueError(f"Absolute paths not allowed: '{v}'")

        return v


class ESPNConfig(BaseModel):
    """ESPN configuration section."""

    scoreboard_url: str = Field(
        ...,
        min_length=10,
        description="ESPN scoreboard base URL"
    )

    @field_validator('scoreboard_url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Ensure URL is reasonable."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError(f"URL must start with http:// or https://: '{v}'")

        if 'espn.com' not in v.lower():
            print(f"⚠️  Warning: ESPN URL doesn't contain 'espn.com': {v}")

        return v


class AIProviderConfig(BaseModel):
    """Individual AI provider configuration."""

    model: str = Field(..., min_length=1, description="Model name")
    max_tokens: int = Field(..., ge=100, le=100000, description="Max tokens to generate")

    @field_validator('max_tokens')
    @classmethod
    def validate_max_tokens(cls, v: int) -> int:
        """Warn if token count seems unusual."""
        if v < 1000:
            print(f"⚠️  Warning: max_tokens={v} is quite low (typical: 4000-8000)")

        if v > 20000:
            print(f"⚠️  Warning: max_tokens={v} is quite high and may be costly")

        return v


class AIConfig(BaseModel):
    """AI configuration section."""

    active_provider: str = Field(
        ...,
        pattern=r'^(claude|openai|gemini)$',
        description="Active AI provider"
    )

    claude: AIProviderConfig
    openai: AIProviderConfig
    gemini: AIProviderConfig


class Config(BaseModel):
    """
    Complete validated configuration model.

    This validates the entire config.yaml structure.
    """

    nfl_season: NFLSeasonConfig
    storage: StorageConfig
    espn: ESPNConfig
    ai: AIConfig

    newsletter_name: Optional[str] = Field(default="ReplAI Review")
    newsletter_tagline: Optional[str] = Field(default="AI-Powered NFL Recaps")
    newsletter_prompt_file: Optional[str] = Field(default="newsletter_prompt.txt")
    github_pages_url: Optional[str] = Field(default="")

    @classmethod
    def from_yaml_dict(cls, config_dict: dict) -> 'Config':
        """
        Load and validate config from YAML dictionary.

        Args:
            config_dict: Dictionary from yaml.safe_load()

        Returns:
            Validated Config instance

        Raises:
            ValidationError: If config is invalid
        """
        return cls(**config_dict)

    def get_ai_provider_config(self, provider_name: Optional[str] = None) -> AIProviderConfig:
        """
        Get configuration for specific AI provider.

        Args:
            provider_name: Provider name (claude/openai/gemini), or None for active provider

        Returns:
            AIProviderConfig for the requested provider
        """
        provider = provider_name or self.ai.active_provider

        if provider == 'claude':
            return self.ai.claude
        elif provider == 'openai':
            return self.ai.openai
        elif provider == 'gemini':
            return self.ai.gemini
        else:
            raise ValueError(f"Unknown provider: {provider}")
