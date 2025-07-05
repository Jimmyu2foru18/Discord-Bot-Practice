import discord
from discord.ext import commands
import asyncio
import cv2
import numpy as np
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import pyautogui
import threading
import time
import os
from PIL import Image
import io
import subprocess
import sys

# Import configuration
try:
    from config import BOT_TOKEN, STREAM_URL, COMMAND_PREFIX, STREAM_FPS, BROWSER_WIDTH, BROWSER_HEIGHT, HEADLESS_MODE
except ImportError:
    print("Error: config.py not found or missing required variables.")
    print("Please check your config.py file and ensure all required variables are set.")
    sys.exit(1)

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

class StreamBot:
    def __init__(self):
        self.driver = None
        self.voice_client = None
        self.streaming = False
        self.stream_thread = None
        
    def setup_browser(self):
        """Setup Chrome browser with the embed"""
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument(f'--window-size={BROWSER_WIDTH},{BROWSER_HEIGHT}')
        if HEADLESS_MODE:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--start-maximized')
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Create HTML with the embed
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>South Park Stream</title>
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    background: black;
                    overflow: hidden;
                }}
                #player {{
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100vw;
                    height: 100vh;
                }}
            </style>
        </head>
        <body>
            <iframe id="player" 
                    marginheight="0" 
                    marginwidth="0" 
                    src="{STREAM_URL}" 
                    scrolling="no" 
                    allowfullscreen="yes" 
                    allow="encrypted-media; picture-in-picture;" 
                    width="100%" 
                    height="100%" 
                    frameborder="0">
            </iframe>
        </body>
        </html>
        """
        
        # Save HTML file
        html_path = os.path.join(os.getcwd(), 'stream.html')
        with open(html_path, 'w') as f:
            f.write(html_content)
            
        # Load the HTML file
        self.driver.get(f'file:///{html_path}')
        time.sleep(5)  # Wait for page to load
        
    def capture_screen(self):
        """Capture the browser window"""
        if not self.driver:
            return None
            
        try:
            # Get browser window position and size
            window_rect = self.driver.get_window_rect()
            x, y, width, height = window_rect['x'], window_rect['y'], window_rect['width'], window_rect['height']
            
            # Capture the screen area
            screenshot = pyautogui.screenshot(region=(x, y, width, height))
            
            # Convert to numpy array for OpenCV
            frame = np.array(screenshot)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            return frame
        except Exception as e:
            print(f"Error capturing screen: {e}")
            return None
    
    def start_streaming(self):
        """Start the streaming process"""
        self.streaming = True
        self.stream_thread = threading.Thread(target=self._stream_loop)
        self.stream_thread.daemon = True
        self.stream_thread.start()
        
    def _stream_loop(self):
        """Main streaming loop"""
        while self.streaming:
            try:
                frame = self.capture_screen()
                if frame is not None:
                    # Here you would send the frame to Discord
                    # This is a simplified version - actual implementation
                    # would require more complex video streaming setup
                    pass
                time.sleep(1/STREAM_FPS)  # Configurable FPS
            except Exception as e:
                print(f"Streaming error: {e}")
                break
                
    def stop_streaming(self):
        """Stop streaming"""
        self.streaming = False
        if self.stream_thread:
            self.stream_thread.join()
            
    def cleanup(self):
        """Clean up resources"""
        self.stop_streaming()
        if self.driver:
            self.driver.quit()
            
stream_bot = StreamBot()

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print('Bot is ready to join voice channels and stream!')

@bot.command(name='join')
async def join_voice(ctx):
    """Join the voice channel and start streaming"""
    if ctx.author.voice is None:
        await ctx.send("You need to be in a voice channel first!")
        return
        
    channel = ctx.author.voice.channel
    
    if stream_bot.voice_client is not None:
        await ctx.send("Already connected to a voice channel!")
        return
        
    try:
        # Join voice channel
        stream_bot.voice_client = await channel.connect()
        await ctx.send(f"Joined {channel.name} and starting South Park stream!")
        
        # Setup browser and start streaming
        stream_bot.setup_browser()
        stream_bot.start_streaming()
        
    except Exception as e:
        await ctx.send(f"Error joining voice channel: {e}")

@bot.command(name='leave')
async def leave_voice(ctx):
    """Leave the voice channel and stop streaming"""
    if stream_bot.voice_client is None:
        await ctx.send("Not connected to any voice channel!")
        return
        
    try:
        await stream_bot.voice_client.disconnect()
        stream_bot.voice_client = None
        stream_bot.cleanup()
        await ctx.send("Left voice channel and stopped streaming!")
    except Exception as e:
        await ctx.send(f"Error leaving voice channel: {e}")

@bot.command(name='status')
async def status(ctx):
    """Check bot status"""
    if stream_bot.voice_client is not None:
        channel_name = stream_bot.voice_client.channel.name
        await ctx.send(f"Currently streaming South Park in: {channel_name}")
    else:
        await ctx.send("Not currently connected to any voice channel.")

@bot.event
async def on_voice_state_update(member, before, after):
    """Handle voice state updates"""
    # If bot is alone in voice channel, leave
    if stream_bot.voice_client is not None:
        channel = stream_bot.voice_client.channel
        if len([m for m in channel.members if not m.bot]) == 0:
            await stream_bot.voice_client.disconnect()
            stream_bot.voice_client = None
            stream_bot.cleanup()
            print("Left voice channel - no users remaining")

if __name__ == '__main__':
    if BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        print("Error: Please set your bot token in config.py")
        print("Get your bot token from: https://discord.com/developers/applications")
        sys.exit(1)
        
    try:
        print("Starting South Park Stream Bot...")
        print(f"Stream URL: {STREAM_URL}")
        print(f"Command prefix: {COMMAND_PREFIX}")
        bot.run(BOT_TOKEN)
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except discord.LoginFailure:
        print("Error: Invalid bot token. Please check your config.py file.")
    except Exception as e:
        print(f"Error starting bot: {e}")
    finally:
        stream_bot.cleanup()