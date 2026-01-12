#!/usr/bin/env python3

"""TLDR Discord Bot - Summarizes channel messages using Gemini AI."""

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

import discord
from discord import Embed
from discord import app_commands
import google.generativeai as genai

import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Discord embed limits
EMBED_DESC_LIMIT = 4096
MAX_EMBEDS_PER_MESSAGE = 10

# Time parsing pattern (e.g., "1h", "30m", "2d")
TIME_PATTERN = re.compile(r"^(\d+)([mhd])$", re.IGNORECASE)


class TimeParseError(Exception):
    """Raised when a time string cannot be parsed."""

    pass


def parse_time_ago(time_str: str) -> timedelta:
    """
    Parse a time string like '1h', '30m', '2d' into a timedelta.

    Args:
        time_str: Time string (e.g., '1h', '30m', '2d')

    Returns:
        timedelta representing the duration

    Raises:
        TimeParseError: If the format is invalid
    """
    match = TIME_PATTERN.match(time_str.strip())
    if not match:
        raise TimeParseError(
            f"Invalid time format: `{time_str}`. Use format like `30m`, `1h`, or `2d`."
        )

    value = int(match.group(1))
    unit = match.group(2).lower()

    if value < 0:
        raise TimeParseError("Time value must be greater than 0.")

    if unit == "m":
        return timedelta(minutes=value)
    elif unit == "h":
        return timedelta(hours=value)
    elif unit == "d":
        return timedelta(days=value)
    else:
        raise TimeParseError(f"Unknown time unit: {unit}")


def split_text_into_chunks(text: str, max_length: int = EMBED_DESC_LIMIT) -> list[str]:
    """
    Split text into chunks that fit within Discord's embed description limit.
    Tries to split at newlines to keep bullet points intact.
    """
    if len(text) <= max_length:
        return [text]

    chunks: list[str] = []
    remaining = text

    while remaining:
        if len(remaining) <= max_length:
            chunks.append(remaining)
            break

        # Find a good split point (prefer newlines)
        split_point = max_length

        # Look for the last newline within the limit
        last_newline = remaining.rfind("\n", 0, max_length)
        if last_newline > max_length // 2:  # Only use if it's not too early
            split_point = last_newline + 1  # Include the newline in current chunk

        chunks.append(remaining[:split_point].rstrip())
        remaining = remaining[split_point:].lstrip()

    return chunks


class TLDRBot(discord.Client):
    """Discord bot that provides TLDR summaries of channel messages."""

    def __init__(self) -> None:
        # Set up intents - we need message content to read messages
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True

        super().__init__(intents=intents)

        # Set up the command tree for slash commands
        self.tree = app_commands.CommandTree(self)

        # Configure Gemini
        genai.configure(api_key=config.GEMINI_API_KEY)
        self.gemini_model = genai.GenerativeModel(config.GEMINI_MODEL)

    async def setup_hook(self) -> None:
        """Called when the bot is starting up. Syncs slash commands."""
        await self.tree.sync()
        logger.info("Slash commands synced")

    async def on_ready(self) -> None:
        """Called when the bot is fully connected and ready."""
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guild(s)")
        logger.info("Bot is ready!")


# Create the bot instance
bot = TLDRBot()


@bot.tree.command(name="tldr", description="Get a summary of messages in this channel within a time range")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(
    start="How far back to start (e.g., '1h', '30m', '2d'). Default: 1h",
    end="How far back to end (e.g., '5m', '0m'). Default: 0m (now)",
    focus="Custom focus for the summary (e.g., 'technical decisions, code changes')",
)
async def tldr_command(
    interaction: discord.Interaction,
    start: Optional[str] = "1h",
    end: Optional[str] = "0m",
    focus: Optional[str] = None,
) -> None:
    """
    Fetch messages within a time range and generate a bullet-point summary.

    Args:
        interaction: The Discord interaction object
        start: How far back to start fetching messages (e.g., '1h', '2d')
        end: How far back to stop fetching messages (e.g., '5m', '0m')
        focus: Custom focus areas for the summary (optional)
    """
    # Defer the response since this might take a while
    await interaction.response.defer(thinking=True)

    try:
        # Parse the time range
        try:
            start_delta = parse_time_ago(start)
            end_delta = parse_time_ago(end)
        except TimeParseError as e:
            await interaction.followup.send(f"❌ {e}")
            return

        # Validate time range
        max_delta = timedelta(days=config.MAX_TIME_RANGE_DAYS)
        if start_delta > max_delta:
            await interaction.followup.send(
                f"❌ Start time cannot be more than {config.MAX_TIME_RANGE_DAYS} days ago."
            )
            return

        if end_delta >= start_delta:
            await interaction.followup.send(
                "❌ End time must be more recent than start time. "
                "For example: `start:1h end:5m` (1 hour ago to 5 minutes ago)"
            )
            return

        # Calculate actual timestamps
        now = datetime.now(timezone.utc)
        start_time = now - start_delta
        end_time = now - end_delta

        # Fetch messages from the channel within the time range
        messages: list[discord.Message] = []
        async for message in interaction.channel.history(
            limit=config.MAX_MESSAGES,
            after=start_time,
            before=end_time,
        ):
            # Only include messages from human users (not bots)
            if not message.author.bot and message.content.strip():
                messages.append(message)

        if not messages:
            await interaction.followup.send(
                "❌ No messages found to summarize. "
                "Make sure there are recent messages from users (not bots) in this channel."
            )
            return

        # Sort in chronological order (oldest first)
        messages.sort(key=lambda m: m.created_at)

        # Format messages for the LLM
        formatted_messages = "\n".join(
            f"{repr(msg.author.display_name)}: {repr(msg.content)}" for msg in messages
        )

        # Determine focus areas (custom or default)
        focus_text = focus if focus else config.DEFAULT_FOCUS

        # Generate summary using Gemini
        prompt = config.SUMMARY_PROMPT.format(
            focus=focus_text,
            messages=formatted_messages,
        )

        logger.info(
            f"Generating summary for {len(messages)} messages in "
            f"#{interaction.channel.name} (requested by {interaction.user})"
        )

        response = await bot.gemini_model.generate_content_async(prompt)

        # Check if we got a valid response
        if not response.text:
            await interaction.followup.send(
                "❌ Failed to generate summary. The AI returned an empty response. "
                "Please try again."
            )
            return

        summary = response.text

        # Build footer text
        footer_text = f"Summarized {len(messages)} messages • {start} → {end}"
        if focus:
            footer_text += f" • Focus: {focus[:50]}{'...' if len(focus) > 50 else ''}"

        # Split summary into chunks if needed
        chunks = split_text_into_chunks(summary)

        # Create embeds for each chunk
        embeds: list[Embed] = []
        for i, chunk in enumerate(chunks[:MAX_EMBEDS_PER_MESSAGE]):
            embed = discord.Embed(
                description=chunk,
                color=discord.Color.blue(),
            )
            # Add title only to first embed
            if i == 0:
                embed.title = "📋 TL;DR Summary"
            # Add footer only to last embed
            if i == len(chunks) - 1 or i == MAX_EMBEDS_PER_MESSAGE - 1:
                embed.set_footer(text=footer_text)
            embeds.append(embed)

        # Send all embeds
        await interaction.followup.send(embeds=embeds)

        logger.info(
            f"Summary sent successfully for #{interaction.channel.name} "
            f"({len(embeds)} embed(s))"
        )

    except discord.Forbidden:
        # Provide context-specific error message
        if interaction.guild is None:
            await interaction.followup.send(
                "❌ I don't have permission to read messages here.\n\n"
                "**For DMs/Group DMs:** Make sure you've authorized the bot with "
                "the `dm_channels.messages.read` scope. You may need to re-authorize the bot."
            )
        else:
            await interaction.followup.send(
                "❌ I don't have permission to read messages in this channel.\n"
                "Make sure I have the **Read Message History** permission."
            )
    except Exception as e:
        logger.exception(f"Error generating summary: {e}")
        await interaction.followup.send(
            f"❌ An error occurred while generating the summary: {str(e)}"
        )


def main() -> None:
    """Entry point for the bot."""
    logger.info("Starting TLDR Bot...")
    bot.run(config.DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    main()

