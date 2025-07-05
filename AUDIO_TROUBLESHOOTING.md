# Audio Streaming Troubleshooting Guide

This guide helps you resolve common audio streaming issues with the South Park Direct Stream Bot.

## Common Issues and Solutions

### No Audio Playing

#### Problem: Bot joins the voice channel but no audio plays

**Possible causes and solutions:**

1. **Stream URL is invalid or inaccessible**
   - Check if the South Park stream URL in `config.py` is still valid
   - Try updating the URL to a different South Park episode
   - Some episodes may be region-locked or temporarily unavailable

2. **FFmpeg issues**
   - Verify FFmpeg is properly installed: run `where ffmpeg` in command prompt
   - Reinstall FFmpeg if necessary
   - Make sure FFmpeg is in your system PATH

3. **Network issues**
   - Check your internet connection
   - Some networks may block streaming content
   - Try using a different network if possible

4. **Discord voice issues**
   - Check if Discord voice is working properly with other applications
   - Restart Discord client
   - Check Discord voice settings

5. **Bot extraction method failed**
   - The bot uses multiple methods to extract the stream URL
   - Some methods may fail depending on the website structure
   - Try using the `!restart` command to attempt extraction again

### Audio Cuts Out or Stutters

#### Problem: Audio plays but frequently cuts out or stutters

**Possible causes and solutions:**

1. **Internet connection issues**
   - Check your internet speed and stability
   - Close other bandwidth-intensive applications
   - Connect to a wired network if possible

2. **Server load**
   - Discord servers may be experiencing high load
   - Try at a different time or on a different server

3. **Stream source issues**
   - The South Park stream source may be unstable
   - Try a different episode URL

4. **Bot resource limitations**
   - The bot may be running on a system with limited resources
   - Close other resource-intensive applications

### Audio Quality Issues

#### Problem: Audio quality is poor or distorted

**Possible causes and solutions:**

1. **Stream source quality**
   - The original stream may be low quality
   - Try a different episode URL

2. **Discord audio settings**
   - Check Discord voice settings
   - Disable any audio enhancements

3. **FFmpeg options**
   - The bot uses specific FFmpeg options for streaming
   - Advanced users can modify these in the code

## Advanced Troubleshooting

### Checking Stream URL Manually

You can check if the stream URL is valid by:

1. Opening the URL in a web browser
2. Using a media player like VLC to open the stream URL
3. Using yt-dlp directly: `yt-dlp --get-url [STREAM_URL]`

### Debugging FFmpeg

To debug FFmpeg issues:

1. Run FFmpeg manually with the stream URL:
   ```
   ffmpeg -i [STREAM_URL] -f null -
   ```
2. Check for error messages in the output

### Testing Discord Voice Connection

To test if Discord voice is working properly:

1. Join a voice channel and use Discord's built-in voice test
2. Try using another bot that uses voice features
3. Have another user join the same voice channel to verify it's working

## Still Having Issues?

If you're still experiencing problems after trying these solutions:

1. Check the Discord.py documentation for voice client issues
2. Look for updates to the bot or its dependencies
3. Check if the South Park website has changed its structure
4. Try running the bot on a different machine or network

## Reporting Issues

When reporting issues, please include:

1. Exact error messages (if any)
2. Steps to reproduce the problem
3. Your operating system and Python version
4. Any changes you've made to the bot code
5. The South Park episode URL you're trying to stream