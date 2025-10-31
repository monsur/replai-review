"""
AI Provider Module

This module provides a swappable system for different AI providers.
Supports Claude (Anthropic), OpenAI, and Google Gemini.

Each provider implements a common interface, making it easy to switch between them.
"""

import os
from abc import ABC, abstractmethod
from typing import Optional


class AIProvider(ABC):
    """
    Abstract base class for AI providers.

    This allows different AI services to be swapped in/out easily.
    """

    @abstractmethod
    def generate(self, prompt: str, content: str) -> str:
        """
        Generate text using the AI model.

        Args:
            prompt: The system prompt/instructions
            content: The user content to process

        Returns:
            Generated text from the AI model
        """
        pass


class ClaudeProvider(AIProvider):
    """
    Claude (Anthropic) AI provider.

    Uses the Anthropic API to generate newsletter content.
    """

    def __init__(self, api_key: str, model: str, max_tokens: int):
        """
        Initialize Claude provider.

        Args:
            api_key: Anthropic API key
            model: Model name (e.g., "claude-3-5-sonnet-20241022")
            max_tokens: Maximum tokens to generate
        """
        self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
        self.model = model
        self.max_tokens = max_tokens

        if not self.api_key:
            raise ValueError(
                "Claude API key not found. Set it in config.yaml or ANTHROPIC_API_KEY env var"
            )

        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError(
                "anthropic package not installed. Install with: pip install anthropic"
            )

    def generate(self, prompt: str, content: str) -> str:
        """Generate text using Claude API."""
        print(f"Using Claude model: {self.model}")

        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=prompt,
            messages=[
                {
                    "role": "user",
                    "content": content
                }
            ]
        )

        return response.content[0].text


class OpenAIProvider(AIProvider):
    """
    OpenAI AI provider.

    Uses the OpenAI API to generate newsletter content.
    """

    def __init__(self, api_key: str, model: str, max_tokens: int):
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            model: Model name (e.g., "gpt-4o")
            max_tokens: Maximum tokens to generate
        """
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
        self.model = model
        self.max_tokens = max_tokens

        if not self.api_key:
            raise ValueError(
                "OpenAI API key not found. Set it in config.yaml or OPENAI_API_KEY env var"
            )

        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError(
                "openai package not installed. Install with: pip install openai"
            )

    def generate(self, prompt: str, content: str) -> str:
        """Generate text using OpenAI API."""
        print(f"Using OpenAI model: {self.model}")

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_completion_tokens=self.max_tokens,
                messages=[
                    {
                        "role": "system",
                        "content": prompt
                    },
                    {
                        "role": "user",
                        "content": content
                    }
                ]
            )

            content = response.choices[0].message.content
            if not content:
                raise ValueError(f"OpenAI returned empty response. Response: {response}")
            return content
        except Exception as e:
            print(f"OpenAI API Error: {e}")
            raise


class GeminiProvider(AIProvider):
    """
    Google Gemini AI provider.

    Uses the Google Gemini API to generate newsletter content.
    """

    def __init__(self, api_key: str, model: str, max_tokens: int):
        """
        Initialize Gemini provider.

        Args:
            api_key: Google API key
            model: Model name (e.g., "gemini-1.5-pro")
            max_tokens: Maximum tokens to generate
        """
        self.api_key = api_key or os.environ.get('GOOGLE_API_KEY')
        self.model = model
        self.max_tokens = max_tokens

        if not self.api_key:
            raise ValueError(
                "Gemini API key not found. Set it in config.yaml or GOOGLE_API_KEY env var"
            )

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(self.model)
        except ImportError:
            raise ImportError(
                "google-generativeai package not installed. Install with: pip install google-generativeai"
            )

    def generate(self, prompt: str, content: str) -> str:
        """Generate text using Gemini API."""
        print(f"Using Gemini model: {self.model}")

        # Gemini combines system prompt and content in a single prompt
        full_prompt = f"{prompt}\n\n{content}"

        response = self.client.generate_content(
            full_prompt,
            generation_config={
                'max_output_tokens': self.max_tokens,
            }
        )

        return response.text


def create_ai_provider(provider_name: str, config: dict) -> AIProvider:
    """
    Factory function to create the appropriate AI provider.

    Args:
        provider_name: Name of the provider ("claude", "openai", or "gemini")
        config: Provider configuration dictionary

    Returns:
        An AIProvider instance

    Raises:
        ValueError: If provider_name is not recognized
    """
    provider_name = provider_name.lower()

    if provider_name == "claude":
        return ClaudeProvider(
            api_key=config.get('api_key'),
            model=config['model'],
            max_tokens=config['max_tokens']
        )
    elif provider_name == "openai":
        return OpenAIProvider(
            api_key=config.get('api_key'),
            model=config['model'],
            max_tokens=config['max_tokens']
        )
    elif provider_name == "gemini":
        return GeminiProvider(
            api_key=config.get('api_key'),
            model=config['model'],
            max_tokens=config['max_tokens']
        )
    else:
        raise ValueError(
            f"Unknown AI provider: {provider_name}. "
            f"Supported providers: claude, openai, gemini"
        )


if __name__ == "__main__":
    # Example usage and testing
    print("AI Provider System")
    print("=" * 60)
    print("\nSupported providers:")
    print("  - claude: Claude (Anthropic)")
    print("  - openai: OpenAI GPT models")
    print("  - gemini: Google Gemini")
    print("\nTo use, call create_ai_provider() with the provider name and config.")
