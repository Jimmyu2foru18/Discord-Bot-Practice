# How to Use the South Park Direct Stream Bot

This guide provides step-by-step instructions on how to use the South Park Direct Stream Bot in your Discord server.

## Getting Started

### Step 1: Start the Bot

1. Double-click the `run_direct_stream_bot.bat` file
2. Wait for the bot to start up and connect to Discord
3. You should see a message saying the bot is online

![Bot Started](https://i.imgur.com/example1.png)

### Step 2: Join a Voice Channel

1. Open Discord and join a voice channel
2. Make sure the bot is in your server

![Join Voice Channel](https://i.imgur.com/example2.png)

### Step 3: Start Streaming

1. Type `!join` in any text channel
2. The bot will join your voice channel and start streaming South Park
3. You should hear the audio from the South Park stream

![Start Streaming](https://i.imgur.com/example3.png)

## Commands

### Basic Commands

- `!join` - Join your current voice channel and start streaming
- `!leave` - Leave the voice channel and stop streaming
- `!status` - Check the current status of the bot
- `!restart` - Restart the stream if it stopped working

## Troubleshooting

### Bot Doesn't Join Voice Channel

1. Make sure you're in a voice channel before using `!join`
2. Check that the bot has permission to join voice channels
3. Try restarting the bot

### No Audio Playing

1. Use `!status` to check if the bot is actually streaming
2. Use `!restart` to restart the stream
3. Try `!leave` and then `!join` again

### Bot Disconnects Frequently

1. Check your internet connection
2. Make sure the South Park stream URL in `config.py` is valid
3. Try a different South Park episode URL

## Video Tutorial

For a visual guide, watch our video tutorial:

1. Start the bot using the batch file
2. Join a voice channel in Discord
3. Type `!join` to start streaming
4. Enjoy South Park directly in Discord!

## Tips for Best Experience

- Use a stable internet connection
- Make sure your Discord voice settings are configured correctly
- If the stream stops, use `!restart` to quickly restart it
- The bot will automatically leave if everyone leaves the voice channel

## Need More Help?

If you're still having issues, check the `DIRECT_STREAM_README.md` file for more detailed information and troubleshooting steps.