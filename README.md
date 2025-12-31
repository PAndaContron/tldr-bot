# TLDR Discord Bot

A Discord bot that summarizes channel messages using Google's Gemini AI. Use the `/tldr` command to get bullet-point summaries of recent conversations.

## Features

- 📋 Summarizes up to 2000 messages at once
- 🤖 Uses Gemini 1.5 Pro for high-quality summaries
- 📝 Outputs clean bullet-point summaries
- 👤 Only includes messages from human users (ignores bots)
- ⚡ Modern slash command interface

## Prerequisites

- Python 3.10 or higher
- A Discord Bot Token
- A Google Gemini API Key

## Setup

### 1. Create a Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" section in the left sidebar
4. Click "Reset Token" to generate a new token — **copy and save this!**
5. Under "Privileged Gateway Intents", enable:
   - **Message Content Intent** (required to read messages)
6. Go to "OAuth2" → "URL Generator"
7. Select scopes: `bot` and `applications.commands`
8. Select bot permissions: `Read Message History`, `Send Messages`, `Use Slash Commands`
9. Copy the generated URL and open it to invite the bot to your server

### 2. Get a Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Click "Create API Key"
3. Copy and save your API key

### 3. Install Dependencies

```bash
cd tldr_bot
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```env
# Discord Bot Token
DISCORD_BOT_TOKEN=your_discord_bot_token_here

# Google Gemini API Key
GEMINI_API_KEY=your_gemini_api_key_here
```

### 5. Run the Bot

```bash
python bot.py
```

You should see output like:
```
2024-XX-XX XX:XX:XX - __main__ - INFO - Starting TLDR Bot...
2024-XX-XX XX:XX:XX - __main__ - INFO - Logged in as YourBot#1234 (ID: 123456789)
2024-XX-XX XX:XX:XX - __main__ - INFO - Bot is ready!
```

## Usage

In any channel where the bot has access, use:

```
/tldr [count]
```

- `count` (optional): Number of messages to summarize (1-2000, default: 50)

### Examples

- `/tldr` — Summarize the last 50 messages
- `/tldr 100` — Summarize the last 100 messages
- `/tldr 500` — Summarize the last 500 messages

## Project Structure

```
tldr_bot/
├── bot.py           # Main bot code with the /tldr command
├── config.py        # Configuration and environment variables
├── requirements.txt # Python dependencies
├── .env             # Your API keys (create this file)
└── README.md        # This file
```

## Troubleshooting

### "Missing required environment variable"
Make sure your `.env` file exists and contains both `DISCORD_BOT_TOKEN` and `GEMINI_API_KEY`.

### Slash command not appearing
- Wait a few minutes — Discord can take up to an hour to sync global commands
- Make sure the bot has the `applications.commands` scope
- Try kicking and re-inviting the bot

### "I don't have permission to read messages"
Ensure the bot has the "Read Message History" permission in the channel.

### Bot shows "Thinking..." but never responds
- Check the console for errors
- Verify your Gemini API key is valid
- The Gemini API may be rate-limited or experiencing issues

## License

MIT

