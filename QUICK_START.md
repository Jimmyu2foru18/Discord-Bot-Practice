# 🤖 South Park Stream Bot - Quick Start Guide

## What This Bot Does

This Discord bot joins voice channels and shares a **South Park 24/7 stream** <mcreference link="https://veplay.top/stream/3b146825-9e54-4e17-b96e-c172ced342ad" index="0">0</mcreference> as screen share. Once started, it will stay in the voice channel streaming until you manually remove it or use the leave command.

## 🚀 Quick Setup (3 Steps)

### Step 1: Get a Discord Bot Token
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" → Give it a name (e.g., "South Park Bot")
3. Go to "Bot" section → Click "Add Bot"
4. Copy the **Token** (keep this secret!)

### Step 2: Run Setup
**Option A: Automatic Setup**
```bash
python setup.py
```

**Option B: Manual Setup**
1. Install dependencies: `pip install -r requirements.txt`
2. Edit `config.py` and replace `YOUR_BOT_TOKEN_HERE` with your actual token

### Step 3: Start the Bot
**Windows Users:**
- Double-click `start_bot.bat`

**All Users:**
```bash
python bot.py
# OR
python start_bot.py
```

## 🎮 How to Use

1. **Join a voice channel** in your Discord server
2. **Type `!join`** in any text channel
3. **Bot joins and starts streaming** South Park 24/7
4. **Type `!leave`** to stop the stream
5. **Type `!status`** to check if bot is streaming

## 📁 File Overview

| File | Purpose |
|------|----------|
| `bot.py` | Main bot application (basic version) |
| `advanced_bot.py` | Enhanced bot with better UI and features |
| `config.py` | Bot settings and token |
| `requirements.txt` | Python dependencies |
| `setup.py` | Automated setup script |
| `start_bot.py` | Smart launcher with error checking |
| `start_bot.bat` | Windows batch file for easy starting |
| `README.md` | Detailed documentation |
| `QUICK_START.md` | This file - quick setup guide |

## 🔧 Bot Commands

- `!join` - Join your voice channel and start streaming
- `!leave` - Leave voice channel and stop streaming  
- `!status` - Check current streaming status

## ⚙️ Configuration Options

Edit `config.py` to customize:

```python
BOT_TOKEN = 'your_token_here'     # Your Discord bot token
COMMAND_PREFIX = '!'              # Change command prefix
STREAM_FPS = 30                   # Stream frame rate
BROWSER_WIDTH = 1920              # Stream resolution width
BROWSER_HEIGHT = 1080             # Stream resolution height
HEADLESS_MODE = False             # True = run browser hidden
```

## 🛠️ Troubleshooting

### Bot Won't Start
- ✅ Check your bot token in `config.py`
- ✅ Make sure Python 3.8+ is installed
- ✅ Run `pip install -r requirements.txt`

### Bot Joins But No Stream
- ✅ Install Google Chrome browser
- ✅ Check internet connection
- ✅ Set `HEADLESS_MODE = False` to see browser window

### Permission Errors
- ✅ Bot needs **Connect** and **Speak** permissions
- ✅ Invite bot with proper permissions (see setup guide)

### Stream Quality Issues
- ✅ Lower `STREAM_FPS` in config (try 15 or 20)
- ✅ Reduce resolution (`BROWSER_WIDTH = 1280, BROWSER_HEIGHT = 720`)
- ✅ Check your internet speed

## 🎯 Which Bot File to Use?

- **New users**: Use `bot.py` (simpler, more stable)
- **Advanced users**: Use `advanced_bot.py` (better UI, more features)

## 🔒 Security Notes

- ⚠️ **Never share your bot token publicly**
- ⚠️ Keep `config.py` private
- ✅ Bot only accesses the South Park stream URL
- ✅ No user data is collected or stored

## 🆘 Need Help?

1. **Check the troubleshooting section above**
2. **Read the full `README.md` for detailed info**
3. **Make sure all dependencies are installed**
4. **Verify your Discord bot has proper permissions**

## 🎉 Success!

Once working, your bot will:
- ✅ Join voice channels when you type `!join`
- ✅ Stream South Park 24/7 continuously
- ✅ Stay in channel until manually removed
- ✅ Auto-leave if everyone else leaves
- ✅ Restart streaming when you run the app again

**Enjoy your South Park stream bot!** 🍿📺