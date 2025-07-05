# South Park Direct Stream Bot for Discord

This bot allows you to stream South Park episodes directly in Discord voice channels without requiring external Chrome browser streaming. It extracts the audio stream from the South Park website and plays it directly in your Discord voice channel.

## Features

- **Direct Discord Streaming**: Streams South Park audio directly in Discord voice channels
- **No External Browser**: Doesn't require Chrome or any external browser to be open
- **Automatic Stream Recovery**: Automatically reconnects and restarts the stream if it disconnects
- **Multiple Extraction Methods**: Uses several methods to extract the stream URL for maximum compatibility
- **User-Friendly Commands**: Simple commands for joining, leaving, checking status, and restarting the stream

## Prerequisites

- Python 3.8 or higher
- FFmpeg installed and added to PATH
- Discord Bot Token
- Internet connection

## Setup

1. **Install Python**: Download and install Python 3.8 or higher from [python.org](https://www.python.org/downloads/). Make sure to check "Add Python to PATH" during installation.

2. **Install FFmpeg**: Download FFmpeg from [ffmpeg.org](https://ffmpeg.org/download.html), extract it, and add the bin folder to your system PATH.

3. **Create a Discord Bot**:
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a new application
   - Go to the "Bot" tab and click "Add Bot"
   - Under "Privileged Gateway Intents", enable "Message Content Intent", "Server Members Intent", and "Presence Intent"
   - Copy your bot token

4. **Configure the Bot**:
   - Create a file named `config.py` in the same directory as the bot
   - Add the following content:
     ```python
     BOT_TOKEN = "YOUR_DISCORD_BOT_TOKEN"  # Replace with your actual bot token
     STREAM_URL = "https://southpark.cc.com/episodes/0ncw88/south-park-the-pandemic-special-season-24-ep-1"  # You can change this to any South Park episode URL
     COMMAND_PREFIX = "!"  # You can change this to any prefix you prefer
     ```

5. **Invite the Bot to Your Server**:
   - Go back to the Discord Developer Portal
   - Go to the "OAuth2" tab, then "URL Generator"
   - Select the "bot" scope
   - Select the following permissions: "Send Messages", "Connect", "Speak", "Use Voice Activity", "Read Message History"
   - Copy the generated URL and open it in your browser to invite the bot to your server

## Running the Bot

1. **Using the Batch File (Recommended)**:
   - Double-click the `run_direct_stream_bot.bat` file
   - The batch file will check for required dependencies and start the bot

2. **Manual Method**:
   - Open a command prompt in the bot directory
   - Run `python direct_stream_bot.py`

## Commands

- `!join` - Join your current voice channel and start streaming South Park
- `!leave` - Leave the voice channel and stop streaming
- `!status` - Check the current status of the bot
- `!restart` - Restart the stream if it stopped working

## How It Works

The bot uses several methods to extract the audio stream from the South Park website:

1. **yt-dlp Extraction**: First attempts to use yt-dlp to extract the direct stream URL
2. **HTML Parsing**: If yt-dlp fails, it uses BeautifulSoup to parse the HTML and find video sources
3. **Iframe Traversal**: If the stream is in an iframe, it recursively extracts from the iframe source
4. **Pattern Matching**: As a last resort, it searches for m3u8 URLs in the page source

Once the stream URL is extracted, it uses FFmpeg to convert the stream to audio and plays it in the Discord voice channel using discord.py's voice capabilities.

## Troubleshooting

### Bot doesn't join voice channel

- Make sure the bot has the necessary permissions in your Discord server
- Check that you're in a voice channel before using the `!join` command
- Verify that your bot token in `config.py` is correct

### No audio is playing

- The stream URL might have changed or be inaccessible
- Try using the `!restart` command to restart the stream
- Check that FFmpeg is properly installed and in your PATH
- Try a different South Park episode URL in your `config.py`

### FFmpeg not found

- Download FFmpeg from [ffmpeg.org](https://ffmpeg.org/download.html)
- Extract the files and add the bin folder to your system PATH
- Restart your computer and try again

### Required packages not installing

Manually install the required packages using:

```
pip install -U discord.py[voice] yt-dlp requests beautifulsoup4 ffmpeg-python
```

## Notes

- This bot only streams the audio from South Park episodes, not the video
- The stream quality depends on your internet connection and the South Park website's availability
- Some episodes may not be available for streaming due to regional restrictions or website changes

## Legal Disclaimer

This bot is for educational purposes only. The developers are not responsible for any misuse of this software. Please respect copyright laws and terms of service of the websites you access.