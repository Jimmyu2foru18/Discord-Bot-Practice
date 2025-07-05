# South Park Stream Bot - Fixed Version

## 🛠️ Fixes for "Sandboxing is not allowed" Error

This fixed version addresses the "Sandboxing is not allowed" error that occurs when trying to run the original bot. The error is related to Chrome's sandbox restrictions when embedding the South Park stream.

### Key Improvements:

1. **Enhanced Chrome Detection**: The bot now thoroughly checks if Chrome is installed on your system before attempting to start.

2. **Sandboxing Fixes**: Added critical Chrome options to properly handle sandboxing restrictions:
   - Improved `--no-sandbox` implementation
   - Added `--disable-setuid-sandbox` option
   - Created a dedicated Chrome user data directory

3. **Direct Stream Loading**: Instead of using an iframe (which can trigger sandbox restrictions), the bot now loads the stream URL directly.

4. **Better Error Handling**: More detailed error messages and logging to help diagnose issues.

5. **Fallback Mechanisms**: Multiple methods to initialize Chrome if the primary method fails.

## 🚀 How to Use the Fixed Version

### Prerequisites

- Python 3.8 or higher
- Google Chrome browser installed
- Discord Bot Token (configured in `config.py`)
- Required Python packages (from `requirements.txt`)

### Running the Fixed Bot

1. **Double-click** the `run_fixed_bot.bat` file to start the bot with all the fixes applied.

2. Alternatively, run the bot directly with Python:
   ```
   python fixed_bot.py
   ```

3. Use the same Discord commands as before:
   - `!join` - Join your voice channel and start streaming
   - `!leave` - Leave the voice channel and stop streaming
   - `!status` - Check the current status of the bot
   - `!reconnect` - Force reconnect if there are issues

## 🔍 Troubleshooting

If you still encounter issues:

1. **Ensure Chrome is Installed**: The bot requires Google Chrome to be installed on your system. Download it from [https://www.google.com/chrome/](https://www.google.com/chrome/) if needed.

2. **Check Chrome Version**: Make sure your Chrome is up to date.

3. **Verify Chrome in PATH**: The bot tries to find Chrome in common installation locations, but adding Chrome to your system PATH can help.

4. **Check Logs**: Look for detailed error messages in the console output.

5. **Firewall/Antivirus**: Some security software might block Chrome automation. Try temporarily disabling them for testing.

6. **Manual Chrome Test**: Try opening the stream URL directly in Chrome to ensure it works.

## 📝 Technical Details

The fixed version makes these technical changes:

- Creates a dedicated Chrome user data directory to avoid profile conflicts
- Uses newer headless mode (`--headless=new`) when headless mode is enabled
- Implements multiple fallback mechanisms for Chrome initialization
- Loads the stream URL directly instead of embedding it in an iframe
- Adds comprehensive Chrome installation detection logic
- Improves cleanup procedures to prevent resource leaks

## 🔄 Switching Between Versions

You can easily switch between the original and fixed versions:

- Original version: `python bot.py` or `python improved_bot.py`
- Fixed version: `python fixed_bot.py` or use `run_fixed_bot.bat`

The fixed version is recommended for most users, especially those experiencing the "Sandboxing is not allowed" error.