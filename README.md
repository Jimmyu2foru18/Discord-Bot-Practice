# South Park Stream Discord Bot

A Discord bot that joins voice channels and shares a South Park 24/7 stream as screen share. The bot can be controlled with simple commands and will stay in the voice channel until manually removed.

## Features

- 🎬 Streams South Park 24/7 content to Discord voice channels
- 🤖 Simple command-based control
- 🔄 Persistent streaming until manually stopped
- 📱 Automatic reconnection capability
- ⚙️ Configurable settings

## Prerequisites

1. **Python 3.8+** installed on your system
2. **Google Chrome** browser installed
3. **Discord Bot Token** (see setup instructions below)

## Setup Instructions

### 1. Create a Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name (e.g., "South Park Stream Bot")
3. Go to the "Bot" section in the left sidebar
4. Click "Add Bot"
5. Under "Token", click "Copy" to copy your bot token
6. **Important**: Keep this token secret!

### 2. Bot Permissions

In the Discord Developer Portal:
1. Go to "OAuth2" > "URL Generator"
2. Select these scopes:
   - `bot`
   - `applications.commands`
3. Select these bot permissions:
   - `Connect` (to join voice channels)
   - `Speak` (to stream audio/video)
   - `Send Messages` (to respond to commands)
   - `Read Message History`
4. Copy the generated URL and use it to invite the bot to your server

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the Bot

1. Open `config.py`
2. Replace `'YOUR_BOT_TOKEN_HERE'` with your actual bot token
3. Adjust other settings if needed:
   - `COMMAND_PREFIX`: Change the command prefix (default: `!`)
   - `STREAM_FPS`: Adjust streaming frame rate (default: 30)
   - `HEADLESS_MODE`: Set to `True` to run browser in background

## Usage

### Starting the Bot

```bash
python bot.py
```

### Discord Commands

- `!join` - Bot joins your current voice channel and starts streaming
- `!leave` - Bot leaves the voice channel and stops streaming
- `!status` - Check if bot is currently streaming

### How to Use

1. Join a voice channel in your Discord server
2. Type `!join` in any text channel
3. The bot will join your voice channel and start screen sharing the South Park stream
4. The bot will stay in the channel until:
   - You use the `!leave` command
   - All users leave the voice channel (bot auto-leaves)
   - You manually disconnect the bot

## Troubleshooting

### Common Issues

**Bot won't start:**
- Check that your bot token is correct in `config.py`
- Ensure all dependencies are installed
- Make sure Python 3.8+ is being used

**Bot joins but no stream:**
- Check that Chrome is installed and accessible
- Verify the stream URL is working
- Try setting `HEADLESS_MODE = False` in config to see the browser window

**Permission errors:**
- Ensure the bot has proper permissions in your Discord server
- Check that the bot can connect to voice channels

**Stream quality issues:**
- Adjust `STREAM_FPS` in config (lower = better performance)
- Check your internet connection
- Try reducing `BROWSER_WIDTH` and `BROWSER_HEIGHT`

### Error Messages

- `"Error: config.py not found"` - Make sure config.py exists and has all required variables
- `"Invalid bot token"` - Check your bot token in config.py
- `"You need to be in a voice channel first!"` - Join a voice channel before using `!join`

## Configuration Options

### config.py Settings

```python
# Bot Settings
BOT_TOKEN = 'your_token_here'          # Your Discord bot token
COMMAND_PREFIX = '!'                   # Command prefix for bot commands

# Stream Settings
STREAM_URL = 'stream_url_here'         # The embed URL to stream
STREAM_FPS = 30                        # Streaming frame rate
STREAM_QUALITY = 'high'                # Stream quality setting

# Browser Settings
BROWSER_WIDTH = 1920                   # Browser window width
BROWSER_HEIGHT = 1080                  # Browser window height
HEADLESS_MODE = False                  # Run browser in background
```

## Technical Details

- Uses `discord.py` for Discord integration
- Uses `selenium` with Chrome WebDriver for rendering the stream
- Uses `pyautogui` for screen capture
- Implements threading for non-blocking stream capture

## Security Notes

- Never share your bot token publicly
- Keep your `config.py` file private
- The bot only accesses the specified stream URL
- No user data is collected or stored

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Ensure all dependencies are properly installed
3. Verify your Discord bot permissions
4. Check that the stream URL is accessible

## License

This project is for educational and personal use only. Respect Discord's Terms of Service and the content provider's terms when using this bot.