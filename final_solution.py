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
import logging
import platform
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import configuration
try:
    from config import BOT_TOKEN, STREAM_URL, COMMAND_PREFIX, STREAM_FPS, BROWSER_WIDTH, BROWSER_HEIGHT, HEADLESS_MODE
except ImportError:
    print("Error: config.py not found or missing required variables.")
    print("Please check your config.py file and ensure all required variables are set.")
    sys.exit(1)

# Setup Discord bot
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

class FinalSolutionBot:
    def __init__(self):
        self.driver = None
        self.voice_client = None
        self.streaming = False
        self.stream_thread = None
        self.current_channel = None
        self.connection_attempts = 0
        self.max_connection_attempts = 5
        self.reconnect_delay = 10  # seconds
        
    def check_chrome_installed(self):
        """Check if Chrome is installed on the system"""
        try:
            # Check for Chrome in common locations based on OS
            if platform.system() == "Windows":
                chrome_paths = [
                    os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), 'Google\\Chrome\\Application\\chrome.exe'),
                    os.path.join(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'), 'Google\\Chrome\\Application\\chrome.exe'),
                    os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google\\Chrome\\Application\\chrome.exe')
                ]
                
                for path in chrome_paths:
                    if os.path.exists(path):
                        logger.info(f"Chrome found at: {path}")
                        return True
                        
                # Try using 'where' command on Windows
                try:
                    result = subprocess.run(['where', 'chrome'], capture_output=True, text=True, check=False)
                    if result.returncode == 0 and result.stdout.strip():
                        logger.info(f"Chrome found via 'where' command: {result.stdout.strip()}")
                        return True
                except Exception:
                    pass
            else:  # macOS or Linux
                chrome_names = ['google-chrome', 'chrome', 'chromium', 'chromium-browser']
                for name in chrome_names:
                    if shutil.which(name):
                        logger.info(f"Chrome/Chromium found: {name}")
                        return True
            
            logger.error("Chrome not found on the system")
            return False
        except Exception as e:
            logger.error(f"Error checking for Chrome: {e}")
            return False
        
    def setup_browser(self):
        """Setup Chrome browser with enhanced error handling and sandboxing fixes"""
        try:
            # First check if Chrome is installed
            if not self.check_chrome_installed():
                logger.error("Chrome is not installed. Please install Google Chrome and try again.")
                return False
                
            chrome_options = Options()
            
            # Critical options to fix sandboxing issues
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-setuid-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            
            # SSL error fixes
            chrome_options.add_argument('--ignore-certificate-errors')
            chrome_options.add_argument('--ignore-ssl-errors')
            chrome_options.add_argument('--allow-running-insecure-content')
            
            # Performance options
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-software-rasterizer')
            chrome_options.add_argument('--disable-background-timer-throttling')
            chrome_options.add_argument('--disable-backgrounding-occluded-windows')
            chrome_options.add_argument('--disable-renderer-backgrounding')
            chrome_options.add_argument(f'--window-size={BROWSER_WIDTH},{BROWSER_HEIGHT}')
            
            # Media permissions
            chrome_options.add_argument('--autoplay-policy=no-user-gesture-required')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Add user data directory to prevent sandboxing issues
            user_data_dir = os.path.join(os.getcwd(), 'chrome_data')
            os.makedirs(user_data_dir, exist_ok=True)
            chrome_options.add_argument(f'--user-data-dir={user_data_dir}')
            
            if HEADLESS_MODE:
                chrome_options.add_argument('--headless=new')  # Use newer headless mode
            else:
                chrome_options.add_argument('--start-maximized')
            
            # Try to use ChromeDriverManager with fallback options
            try:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            except Exception as chrome_error:
                logger.warning(f"Error using ChromeDriverManager: {chrome_error}")
                logger.info("Trying alternative Chrome initialization...")
                
                # Try direct Chrome initialization
                try:
                    self.driver = webdriver.Chrome(options=chrome_options)
                except Exception as direct_error:
                    logger.error(f"Failed to initialize Chrome directly: {direct_error}")
                    return False
            
            # Create a custom HTML wrapper to load the stream
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>South Park 24/7 Stream</title>
                <meta charset="UTF-8">
                <style>
                    * {{
                        margin: 0;
                        padding: 0;
                        box-sizing: border-box;
                    }}
                    body {{
                        background: #000;
                        overflow: hidden;
                        font-family: Arial, sans-serif;
                    }}
                    #player-container {{
                        position: absolute;
                        top: 0;
                        left: 0;
                        width: 100vw;
                        height: 100vh;
                    }}
                    .status {{
                        position: absolute;
                        top: 10px;
                        left: 10px;
                        color: white;
                        background: rgba(0,0,0,0.7);
                        padding: 10px;
                        border-radius: 5px;
                        z-index: 1000;
                    }}
                </style>
            </head>
            <body>
                <div class="status" id="status">Loading South Park Stream...</div>
                <div id="player-container">
                    <!-- Direct embed without iframe sandbox restrictions -->
                    <script>
                        // Create a dynamic script to load the stream
                        window.onload = function() {{
                            // Redirect to the stream URL
                            window.location.href = "{STREAM_URL}";
                            
                            // Fallback if redirect doesn't work
                            setTimeout(function() {{
                                document.getElementById('status').innerHTML = 'Redirecting to stream...';
                            }}, 3000);
                        }};
                        
                        // Error handling
                        window.addEventListener('error', function(e) {{
                            console.log('Error loading stream:', e);
                            document.getElementById('status').innerHTML = 'Error loading stream. Retrying...';
                        }});
                    </script>
                </div>
            </body>
            </html>
            """
            
            # Save and load HTML
            html_path = os.path.join(os.getcwd(), 'final_solution_stream.html')
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"Loading stream from: {STREAM_URL}")
            
            # First try loading the HTML wrapper
            try:
                self.driver.get(f'file:///{html_path.replace(os.sep, "/")}')  
                time.sleep(5)  # Wait for redirect
            except Exception as e:
                logger.warning(f"Error loading HTML wrapper: {e}")
            
            # Then try loading the stream URL directly as fallback
            try:
                self.driver.get(STREAM_URL)
                time.sleep(10)  # Give more time for the stream to load
            except Exception as e:
                logger.error(f"Error loading stream URL directly: {e}")
                return False
            
            if not HEADLESS_MODE:
                self.driver.maximize_window()
                
            logger.info("Browser setup complete!")
            return True
            
        except Exception as e:
            logger.error(f"Error setting up browser: {e}")
            return False
    
    async def connect_to_voice_with_retry(self, channel):
        """Connect to voice channel with retry logic"""
        self.connection_attempts = 0
        
        while self.connection_attempts < self.max_connection_attempts:
            try:
                logger.info(f"Attempting to connect to voice channel (attempt {self.connection_attempts + 1})")
                
                # If already connected, disconnect first
                if self.voice_client and self.voice_client.is_connected():
                    await self.voice_client.disconnect(force=True)
                    await asyncio.sleep(2)
                
                # Connect to voice channel
                self.voice_client = await channel.connect(timeout=30.0, reconnect=True)
                self.current_channel = channel
                
                logger.info(f"Successfully connected to {channel.name}")
                return True
                
            except discord.errors.ConnectionClosed as e:
                logger.warning(f"Connection closed (code {e.code}): {e}")
                self.connection_attempts += 1
                
                if self.connection_attempts < self.max_connection_attempts:
                    logger.info(f"Retrying in {self.reconnect_delay} seconds...")
                    await asyncio.sleep(self.reconnect_delay)
                    # Increase delay for next attempt
                    self.reconnect_delay = min(self.reconnect_delay * 1.5, 60)
                else:
                    logger.error("Max connection attempts reached")
                    
            except Exception as e:
                logger.error(f"Unexpected error connecting to voice: {e}")
                self.connection_attempts += 1
                
                if self.connection_attempts < self.max_connection_attempts:
                    await asyncio.sleep(self.reconnect_delay)
                    
        return False
    
    def start_streaming(self):
        """Start the streaming process"""
        if not self.driver:
            logger.error("Browser not initialized")
            return False
            
        self.streaming = True
        logger.info("Screen sharing started!")
        
        self.stream_thread = threading.Thread(target=self._monitor_stream)
        self.stream_thread.daemon = True
        self.stream_thread.start()
        
        return True
    
    def _monitor_stream(self):
        """Monitor the stream and handle any issues"""
        while self.streaming:
            try:
                if self.driver:
                    # Check if browser is still responsive
                    title = self.driver.title
                    
                    # Check if voice client is still connected
                    if self.voice_client and not self.voice_client.is_connected():
                        logger.warning("Voice client disconnected, attempting reconnect...")
                        # Note: Reconnection should be handled by the main bot logic
                        
                time.sleep(5)  # Check every 5 seconds
            except Exception as e:
                logger.error(f"Stream monitoring error: {e}")
                break
    
    def stop_streaming(self):
        """Stop the streaming process"""
        self.streaming = False
        if self.stream_thread and self.stream_thread.is_alive():
            self.stream_thread.join(timeout=5)
        logger.info("Streaming stopped")
    
    async def cleanup(self):
        """Clean up all resources"""
        logger.info("Cleaning up resources...")
        self.stop_streaming()
        
        if self.voice_client:
            try:
                if self.voice_client.is_connected():
                    await self.voice_client.disconnect(force=True)
            except Exception as e:
                logger.error(f"Error disconnecting voice client: {e}")
            self.voice_client = None
        
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logger.error(f"Error closing browser: {e}")
            self.driver = None
        
        # Clean up Chrome user data directory
        chrome_data_dir = os.path.join(os.getcwd(), 'chrome_data')
        if os.path.exists(chrome_data_dir):
            try:
                shutil.rmtree(chrome_data_dir, ignore_errors=True)
            except Exception as e:
                logger.error(f"Error removing Chrome data directory: {e}")
        
        # Clean up HTML file
        html_path = os.path.join(os.getcwd(), 'final_solution_stream.html')
        if os.path.exists(html_path):
            try:
                os.remove(html_path)
            except Exception as e:
                logger.error(f"Error removing HTML file: {e}")
        
        self.current_channel = None
        self.connection_attempts = 0
        self.reconnect_delay = 10

# Create bot instance
stream_bot = FinalSolutionBot()

@bot.event
async def on_ready():
    logger.info(f'{bot.user} is now online!')
    print(f'🤖 {bot.user} is now online!')
    print(f'📺 Ready to stream South Park 24/7!')
    print(f'💬 Type {COMMAND_PREFIX}join in a Discord server to start streaming')

@bot.command(name='join', help='Join voice channel and start streaming')
async def join_voice(ctx):
    # Check if user is in a voice channel
    if not ctx.author.voice:
        await ctx.send("❌ You need to be in a voice channel to use this command!")
        return
        
    voice_channel = ctx.author.voice.channel
    
    # Check if bot is already in this voice channel
    if stream_bot.voice_client and stream_bot.voice_client.is_connected() and stream_bot.current_channel == voice_channel:
        await ctx.send(f"✅ Already streaming in {voice_channel.name}!")
        return
        
    # Send initial message
    setup_msg = await ctx.send(f"🔄 Setting up stream in {voice_channel.name}...")
    
    try:
        # Connect to voice channel with retry
        await setup_msg.edit(content=f"🔄 Connecting to {voice_channel.name}...")
        voice_connected = await stream_bot.connect_to_voice_with_retry(voice_channel)
        
        if not voice_connected:
            await setup_msg.edit(content="❌ Failed to connect to voice channel after multiple attempts. Please try again later.")
            return
            
        # Setup browser if not already set up
        if not stream_bot.driver:
            await setup_msg.edit(content="🔄 Setting up browser...")
            browser_setup = stream_bot.setup_browser()
            
            if not browser_setup:
                await setup_msg.edit(content="❌ Failed to setup browser. Please ensure Chrome is installed and try again.")
                # Disconnect from voice since browser setup failed
                await stream_bot.cleanup()
                return
        
        # Start streaming
        await setup_msg.edit(content="🔄 Starting stream...")
        stream_started = stream_bot.start_streaming()
        
        if not stream_started:
            await setup_msg.edit(content="❌ Failed to start streaming. Please try again.")
            await stream_bot.cleanup()
            return
            
        await setup_msg.edit(content=f"✅ Successfully joined {voice_channel.name} and started streaming South Park!")
        
    except Exception as e:
        logger.error(f"Error in join command: {e}")
        await setup_msg.edit(content=f"❌ An error occurred: {str(e)}")
        await stream_bot.cleanup()

@bot.command(name='leave', help='Leave voice channel and stop streaming')
async def leave_voice(ctx):
    if not stream_bot.voice_client or not stream_bot.voice_client.is_connected():
        await ctx.send("❌ I'm not in a voice channel!")
        return
        
    voice_channel = stream_bot.current_channel
    
    # Send initial message
    leave_msg = await ctx.send(f"🔄 Leaving {voice_channel.name}...")
    
    try:
        # Stop streaming and disconnect
        stream_bot.stop_streaming()
        await stream_bot.voice_client.disconnect(force=True)
        stream_bot.voice_client = None
        stream_bot.current_channel = None
        
        await leave_msg.edit(content=f"✅ Successfully left {voice_channel.name} and stopped streaming!")
        
    except Exception as e:
        logger.error(f"Error in leave command: {e}")
        await leave_msg.edit(content=f"❌ An error occurred while leaving: {str(e)}")
        # Force cleanup
        await stream_bot.cleanup()

@bot.command(name='status', help='Check bot streaming status')
async def status(ctx):
    status_embed = discord.Embed(
        title="South Park Stream Bot Status",
        color=discord.Color.blue()
    )
    
    # Check voice connection
    if stream_bot.voice_client and stream_bot.voice_client.is_connected():
        status_embed.add_field(
            name="Voice Connection",
            value=f"✅ Connected to {stream_bot.current_channel.name}",
            inline=False
        )
    else:
        status_embed.add_field(
            name="Voice Connection",
            value="❌ Not connected to any voice channel",
            inline=False
        )
    
    # Check browser status
    if stream_bot.driver:
        status_embed.add_field(
            name="Browser",
            value="✅ Running",
            inline=True
        )
    else:
        status_embed.add_field(
            name="Browser",
            value="❌ Not running",
            inline=True
        )
    
    # Check streaming status
    if stream_bot.streaming:
        status_embed.add_field(
            name="Streaming",
            value="✅ Active",
            inline=True
        )
    else:
        status_embed.add_field(
            name="Streaming",
            value="❌ Inactive",
            inline=True
        )
    
    # Add stream URL
    status_embed.add_field(
        name="Stream URL",
        value=f"`{STREAM_URL}`",
        inline=False
    )
    
    # Add footer with command help
    status_embed.set_footer(text=f"Use {COMMAND_PREFIX}join to start streaming or {COMMAND_PREFIX}leave to stop")
    
    await ctx.send(embed=status_embed)

@bot.command(name='reconnect', help='Force reconnect to voice channel')
async def reconnect(ctx):
    if not stream_bot.current_channel:
        await ctx.send("❌ Not currently connected to any voice channel. Use !join first.")
        return
        
    channel = stream_bot.current_channel
    reconnect_msg = await ctx.send(f"🔄 Reconnecting to {channel.name}...")
    
    try:
        # Stop streaming and disconnect
        stream_bot.stop_streaming()
        if stream_bot.voice_client and stream_bot.voice_client.is_connected():
            await stream_bot.voice_client.disconnect(force=True)
            stream_bot.voice_client = None
        
        # Wait a moment before reconnecting
        await asyncio.sleep(2)
        
        # Reconnect to voice channel
        voice_connected = await stream_bot.connect_to_voice_with_retry(channel)
        
        if not voice_connected:
            await reconnect_msg.edit(content="❌ Failed to reconnect to voice channel after multiple attempts.")
            return
            
        # Restart streaming
        if not stream_bot.driver:
            await reconnect_msg.edit(content="🔄 Setting up browser...")
            browser_setup = stream_bot.setup_browser()
            
            if not browser_setup:
                await reconnect_msg.edit(content="❌ Failed to setup browser. Please ensure Chrome is installed.")
                await stream_bot.cleanup()
                return
        
        stream_started = stream_bot.start_streaming()
        
        if not stream_started:
            await reconnect_msg.edit(content="❌ Failed to restart streaming.")
            await stream_bot.cleanup()
            return
            
        await reconnect_msg.edit(content=f"✅ Successfully reconnected to {channel.name} and resumed streaming!")
        
    except Exception as e:
        logger.error(f"Error in reconnect command: {e}")
        await reconnect_msg.edit(content=f"❌ An error occurred during reconnection: {str(e)}")
        await stream_bot.cleanup()

@bot.event
async def on_voice_state_update(member, before, after):
    # If the bot was disconnected from a voice channel
    if member.id == bot.user.id and before.channel and not after.channel:
        logger.info("Bot was disconnected from voice channel")
        # Clean up resources
        stream_bot.stop_streaming()
        stream_bot.voice_client = None
        stream_bot.current_channel = None

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(f"❌ Command not found. Use {COMMAND_PREFIX}help to see available commands.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument: {error.param.name}")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Bad argument: {str(error)}")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Command on cooldown. Try again in {error.retry_after:.2f} seconds.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send(f"❌ I don't have the required permissions: {', '.join(error.missing_perms)}")
    else:
        logger.error(f"Command error: {error}")
        await ctx.send(f"❌ An error occurred: {str(error)}")

if __name__ == '__main__':
    if BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        print("❌ Error: Please set your bot token in config.py")
        print("🔗 Get your bot token from: https://discord.com/developers/applications")
        input("Press Enter to exit...")
        sys.exit(1)
        
    try:
        print("🚀 Starting Final Solution South Park Stream Bot...")
        print(f"📺 Stream URL: {STREAM_URL}")
        print(f"🎮 Command prefix: {COMMAND_PREFIX}")
        print(f"⚙️ FPS: {STREAM_FPS}, Resolution: {BROWSER_WIDTH}x{BROWSER_HEIGHT}")
        print(f"🔧 Max connection attempts: {stream_bot.max_connection_attempts}")
        print("-" * 50)
        
        # Check Chrome installation before starting
        if not stream_bot.check_chrome_installed():
            print("❌ Error: Google Chrome is not installed on this system.")
            print("Please install Chrome from https://www.google.com/chrome/ and try again.")
            input("Press Enter to exit...")
            sys.exit(1)

        bot.run(BOT_TOKEN)
        
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except discord.LoginFailure:
        print("❌ Error: Invalid bot token. Please check your config.py file.")
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        print(f"❌ Error starting bot: {e}")
    finally:
        try:
            asyncio.run(stream_bot.cleanup())
        except:
            pass
        print("🧹 Cleanup complete")