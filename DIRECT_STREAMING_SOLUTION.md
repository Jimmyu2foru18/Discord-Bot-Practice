# South Park Direct Streaming Solution

## Overview

We've successfully implemented a solution that allows streaming South Park directly in Discord voice channels without requiring an external Chrome browser. This solution addresses the original request to "stream it in chat not external in chrome" by using Discord's voice capabilities to stream the audio directly from the South Park website.

## What's Been Implemented

### 1. Direct Stream Bot (`direct_stream_bot.py`)

This is the main bot implementation that:

- Extracts the audio stream from South Park episodes using multiple methods
- Streams the audio directly in Discord voice channels
- Provides commands for joining, leaving, checking status, and restarting the stream
- Includes automatic reconnection and stream monitoring

### 2. Launcher Script (`run_direct_stream_bot.bat`)

A user-friendly batch file that:

- Checks for required dependencies (Python, FFmpeg)
- Installs necessary Python packages
- Verifies the configuration file exists
- Starts the bot with proper error handling

### 3. Update Script (`update_bot.bat`)

A maintenance script that:

- Updates all required Python packages to their latest versions
- Verifies FFmpeg installation
- Ensures the bot stays up-to-date with the latest dependencies

### 4. Documentation

- `DIRECT_STREAM_README.md`: Comprehensive guide to setting up and using the bot
- `HOW_TO_USE_DIRECT_STREAM_BOT.md`: Step-by-step tutorial for users
- `AUDIO_TROUBLESHOOTING.md`: Detailed troubleshooting guide for audio streaming issues

## How It Works

### Stream Extraction

The bot uses a multi-layered approach to extract the stream URL:

1. **Primary Method**: Uses yt-dlp to extract the direct stream URL
2. **Secondary Method**: Parses HTML to find video sources
3. **Tertiary Method**: Traverses iframes to find embedded content
4. **Fallback Method**: Uses regex to find m3u8 URLs in the page source

### Audio Streaming

Once the stream URL is extracted, the bot:

1. Connects to a Discord voice channel
2. Uses FFmpeg to process the stream
3. Sends the audio to Discord using discord.py's voice capabilities
4. Continuously monitors the stream and restarts it if necessary

## Advantages Over Previous Solutions

### No External Browser Required

- **Previous Solution**: Required Chrome to be installed and running
- **New Solution**: Works entirely within Discord, no browser needed

### Reduced Resource Usage

- **Previous Solution**: High CPU and memory usage from running Chrome
- **New Solution**: Significantly lower resource usage, only streams audio

### Improved Reliability

- **Previous Solution**: Prone to "Sandboxing is not allowed" errors
- **New Solution**: Avoids browser-related errors entirely

### Better User Experience

- **Previous Solution**: Required manual setup and troubleshooting
- **New Solution**: Simple commands, automatic recovery, better error handling

## Technical Details

### Dependencies

- **discord.py[voice]**: For Discord bot functionality and voice capabilities
- **yt-dlp**: For extracting stream URLs
- **requests & beautifulsoup4**: For HTML parsing
- **ffmpeg-python**: For audio processing
- **FFmpeg**: External dependency for audio conversion

### Stream Processing

The bot uses these FFmpeg options for optimal streaming:

```python
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}
```

These options ensure:
- Automatic reconnection if the stream drops
- Audio-only extraction to reduce bandwidth
- Optimal buffering for smooth playback

## Limitations

- Audio-only streaming (no video)
- Dependent on the South Park website's availability
- Some episodes may be region-locked or unavailable
- Requires FFmpeg to be installed on the system

## Future Improvements

- Add support for video thumbnails in Discord
- Implement episode selection commands
- Add playlist functionality for continuous streaming
- Improve stream quality detection and selection
- Add support for other streaming sources

## Conclusion

This solution successfully fulfills the request to stream South Park directly in Discord chat without requiring an external Chrome browser. It provides a more reliable, resource-efficient, and user-friendly experience while maintaining the core functionality of streaming South Park content to Discord users.