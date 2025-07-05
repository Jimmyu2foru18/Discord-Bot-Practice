# Chrome Troubleshooting Guide

## Common Chrome Issues with the South Park Stream Bot

### "Sandboxing is not allowed" Error

This error occurs when Chrome's sandbox restrictions prevent the bot from properly loading the stream. The fixed version (`fixed_bot.py`) should resolve this issue, but if you're still experiencing problems, try these additional steps:

1. **Run Chrome with `--no-sandbox` flag manually** to test if it works:
   ```
   chrome --no-sandbox
   ```
   If this works but the bot still fails, there might be permission issues with how the bot is launching Chrome.

2. **Check Chrome version compatibility**:
   ```
   chrome --version
   ```
   Make sure you have a recent version of Chrome (version 90+).

3. **Clear Chrome user data directory**:
   Delete the `chrome_data` folder in the bot directory if it exists, then try again.

### Chrome Not Found Error

If the bot cannot find Chrome on your system:

1. **Verify Chrome installation**:
   - Windows: Check in `C:\Program Files\Google\Chrome\Application\` or `C:\Program Files (x86)\Google\Chrome\Application\`
   - macOS: Check in `/Applications/Google Chrome.app/`
   - Linux: Try `which google-chrome` or `which chrome`

2. **Add Chrome to PATH**:
   - Windows: Add the Chrome installation directory to your system PATH
   - macOS/Linux: Create a symbolic link to Chrome in `/usr/local/bin/`

3. **Install Chrome if needed**:
   Download and install from [https://www.google.com/chrome/](https://www.google.com/chrome/)

### Chrome Crashes or Exits Unexpectedly

If Chrome starts but then crashes:

1. **Check system resources**:
   - Ensure you have enough RAM available (at least 2GB free)
   - Check disk space (at least 1GB free)

2. **Update Chrome drivers**:
   ```
   pip install --upgrade webdriver-manager
   ```

3. **Try running Chrome in non-headless mode**:
   Edit `config.py` and set `HEADLESS_MODE = False`

4. **Check for conflicting Chrome instances**:
   - Close all running Chrome windows
   - End any Chrome processes in Task Manager/Activity Monitor

### Stream Loads But No Video/Audio

If Chrome starts but the stream doesn't play properly:

1. **Test the stream URL directly**:
   Open the URL from `config.py` in a regular Chrome browser window

2. **Check media permissions**:
   Make sure your system allows Chrome to access audio/video

3. **Try different stream settings**:
   Edit `config.py` and adjust `BROWSER_WIDTH` and `BROWSER_HEIGHT` to smaller values

4. **Check network connectivity**:
   Ensure your network allows access to the streaming site

## Advanced Troubleshooting

### Manual Chrome Driver Installation

If the automatic Chrome driver installation fails:

1. Download the appropriate ChromeDriver version for your Chrome from [https://chromedriver.chromium.org/downloads](https://chromedriver.chromium.org/downloads)

2. Place the ChromeDriver executable in the bot directory

3. Modify `fixed_bot.py` to use the local ChromeDriver:
   ```python
   # Replace this line:
   service = Service(ChromeDriverManager().install())
   
   # With this:
   service = Service("./chromedriver.exe")  # or "./chromedriver" on macOS/Linux
   ```

### Debugging Chrome Startup

To see detailed Chrome startup logs:

1. Edit `fixed_bot.py` and add these options:
   ```python
   chrome_options.add_argument('--enable-logging')
   chrome_options.add_argument('--v=1')
   ```

2. Check the Chrome logs (usually in `~/chrome_debug.log` or in the temp directory)

### System-Specific Solutions

#### Windows

- Run the bot as Administrator
- Check Windows Defender or antivirus settings
- Verify WebDriver is not blocked by Windows SmartScreen

#### macOS

- Check System Preferences > Security & Privacy for blocked applications
- Allow Chrome automation in accessibility settings

#### Linux

- Install additional dependencies: `sudo apt-get install -y xvfb libgconf-2-4`
- Try running with Xvfb: `xvfb-run python fixed_bot.py`

## Still Having Issues?

If you've tried all these steps and still encounter problems:

1. Check the console output for specific error messages
2. Search for the exact error message online
3. Try running with minimal Chrome options to isolate the issue
4. Consider using a different browser automation tool like Firefox/Geckodriver