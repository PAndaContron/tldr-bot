"""Configuration management for the TLDR Discord bot."""

import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def get_required_env(key: str) -> str:
    """Get a required environment variable or exit with an error."""
    value = os.getenv(key)
    if not value:
        print(f"ERROR: Missing required environment variable: {key}")
        print("Please check your .env file and ensure all required variables are set.")
        sys.exit(1)
    return value


# Bot Configuration
DISCORD_BOT_TOKEN: str = get_required_env("DISCORD_BOT_TOKEN")
GEMINI_API_KEY: str = get_required_env("GEMINI_API_KEY")

# Command Settings
MAX_MESSAGES: int = 10000  # Maximum messages to fetch within time range
MAX_TIME_RANGE_DAYS: int = 3  # Maximum time range allowed
GEMINI_MODEL: str = "gemini-2.5-flash"

# Default focus areas for the summary
DEFAULT_FOCUS: str = """
Analyze the following Discord messages and provide a clear, concise summary in bullet points.
Focus on:
- Key topics discussed
- Important decisions or conclusions
- Notable questions asked
- Any action items mentioned

Format your response as bullet points. Be concise but capture the essential information.
If the conversation is very short or trivial, still provide a brief summary."""

# Prompt for the LLM (use {focus} and {messages} placeholders)
SUMMARY_PROMPT: str = """You are a helpful assistant that summarizes Discord chat conversations.
{focus}
Messages are formatted as "Username: Message content" and are in chronological order (oldest first).

---
MESSAGES:
{messages}
---

Provide your bullet-point summary:"""

