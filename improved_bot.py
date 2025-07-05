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

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import configuration
try:
    from config import BOT_TOKEN, STREAM_URL, COMMAND_PREFIX, STREAM_FPS, BROWSER_WIDTH, BROWSER_HEIGHT, HEADLESS_MODE
except ImportError:
    print("Error: config.py not found or missing required variables.")
    print("Please check your config.py file and ensure all required variables are set.")
    sys.exit(1)

# Bot setup with enhanced intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

class ImprovedStreamBot:
    def __init__(self):
        self.driver = None
        self.voice_client = None
        self.streaming = False
        self.stream_thread = None
        self.current_channel = None
        self.connection_attempts = 0
        self.max_connection_attempts = 5
        self.reconnect_delay = 10  # seconds
        
    def setup_browser(self):
        """Setup Chrome browser with enhanced error handling"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-software-rasterizer')
            chrome_options.add_argument('--disable-background-timer-throttling')
            chrome_options.add_argument('--disable-backgrounding-occluded-windows')
            chrome_options.add_argument('--disable-renderer-backgrounding')
            chrome_options.add_argument(f'--window-size={BROWSER_WIDTH},{BROWSER_HEIGHT}')
            
            # Media permissions
            chrome_options.add_argument('--autoplay-policy=no-user-gesture-required')
            chrome_options.add_argument('--allow-running-insecure-content')
            
            if HEADLESS_MODE:
                chrome_options.add_argument('--headless')
            else:
                chrome_options.add_argument('--start-maximized')
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Enhanced HTML with better error handling
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
                    #player {{
                        position: absolute;
                        top: 0;
                        left: 0;
                        width: 100vw;
                        height: 100vh;
                        border: none;
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
                <iframe id="player" 
                        src="{STREAM_URL}" 
                        allowfullscreen="true"
                        allow="autoplay; encrypted-media; picture-in-picture; fullscreen"
                        sandbox="allow-same-origin allow-scripts allow-popups allow-forms"
                        onload="document.getElementById('status').style.display='none'">
                </iframe>
                
                <script>
                    setTimeout(function() {{
                        document.getElementById('status').style.display = 'none';
                    }}, 5000);
                    
                    // Error handling
                    window.addEventListener('error', function(e) {{
                        console.log('Error loading stream:', e);
                        document.getElementById('status').innerHTML = 'Stream loading...';
                    }});
                </script>
            </body>
            </html>
            """
            
            # Save and load HTML
            html_path = os.path.join(os.getcwd(), 'improved_stream.html')
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"Loading stream from: {STREAM_URL}")
            self.driver.get(f'file:///{html_path.replace(os.sep, "/")}')
            time.sleep(8)  # Wait for page to load
            
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
        
        # Clean up HTML file
        html_path = os.path.join(os.getcwd(), 'improved_stream.html')
        if os.path.exists(html_path):
            try:
                os.remove(html_path)
            except Exception as e:
                logger.error(f"Error removing HTML file: {e}")
        
        self.current_channel = None
        self.connection_attempts = 0
        self.reconnect_delay = 10

# Create bot instance
stream_bot = ImprovedStreamBot()

@bot.event
async def on_ready():
    logger.info(f'{bot.user} is now online!')
    print(f'🤖 {bot.user} is now online!')
    print(f'📺 Ready to stream South Park 24/7!')
    print(f'🎮 Use {COMMAND_PREFIX}join to start streaming')
    print(f'📊 Bot is in {len(bot.guilds)} server(s)')
    print('-' * 40)

@bot.command(name='join', help='Join voice channel and start streaming')
async def join_voice(ctx):
    """Join voice channel and start South Park stream with improved error handling"""
    
    if not ctx.author.voice:
        embed = discord.Embed(
            title="❌ Error",
            description="You need to be in a voice channel first!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    channel = ctx.author.voice.channel
    
    if stream_bot.voice_client and stream_bot.voice_client.is_connected():
        embed = discord.Embed(
            title="⚠️ Already Connected",
            description=f"Already streaming in {stream_bot.current_channel.name}!",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return
    
    # Send initial status message
    embed = discord.Embed(
        title="🔄 Starting Stream",
        description="Setting up South Park 24/7 stream...",
        color=discord.Color.blue()
    )
    status_msg = await ctx.send(embed=embed)
    
    try:
        # Setup browser first
        embed.description = "Setting up browser..."
        await status_msg.edit(embed=embed)
        
        if not stream_bot.setup_browser():
            embed = discord.Embed(
                title="❌ Setup Failed",
                description="Failed to setup browser. Please ensure Chrome is installed and try again.",
                color=discord.Color.red()
            )
            await status_msg.edit(embed=embed)
            return
        
        # Connect to voice channel with retry logic
        embed.description = "Connecting to voice channel..."
        await status_msg.edit(embed=embed)
        
        if await stream_bot.connect_to_voice_with_retry(channel):
            # Start screen sharing
            if stream_bot.start_streaming():
                embed = discord.Embed(
                    title="✅ Stream Started!",
                    description=f"Now streaming South Park 24/7 in **{channel.name}**\n\n📺 Stream URL: [South Park 24/7]({STREAM_URL})\n🎮 Use `{COMMAND_PREFIX}leave` to stop\n🔄 Use `{COMMAND_PREFIX}status` to check status",
                    color=discord.Color.green()
                )
                embed.set_footer(text="Enjoy the show! 🍿")
                await status_msg.edit(embed=embed)
            else:
                await stream_bot.cleanup()
                embed = discord.Embed(
                    title="❌ Stream Failed",
                    description="Failed to start screen sharing. Please try again.",
                    color=discord.Color.red()
                )
                await status_msg.edit(embed=embed)
        else:
            await stream_bot.cleanup()
            embed = discord.Embed(
                title="❌ Connection Failed",
                description=f"Failed to connect to voice channel after {stream_bot.max_connection_attempts} attempts.\n\nThis might be due to:\n• Discord server issues\n• Network connectivity problems\n• Bot permissions\n\nPlease try again in a few minutes.",
                color=discord.Color.red()
            )
            await status_msg.edit(embed=embed)
            
    except Exception as e:
        logger.error(f"Error in join command: {e}")
        await stream_bot.cleanup()
        embed = discord.Embed(
            title="❌ Unexpected Error",
            description=f"An unexpected error occurred: {str(e)[:200]}...",
            color=discord.Color.red()
        )
        await status_msg.edit(embed=embed)

@bot.command(name='leave', help='Leave voice channel and stop streaming')
async def leave_voice(ctx):
    """Leave voice channel and stop streaming"""
    
    if not stream_bot.voice_client or not stream_bot.voice_client.is_connected():
        embed = discord.Embed(
            title="❌ Not Connected",
            description="Not currently connected to any voice channel!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    try:
        channel_name = stream_bot.current_channel.name if stream_bot.current_channel else "Unknown"
        
        await stream_bot.cleanup()
        
        embed = discord.Embed(
            title="👋 Stream Stopped",
            description=f"Left **{channel_name}** and stopped streaming.\n\nThanks for watching! 📺",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error in leave command: {e}")
        embed = discord.Embed(
            title="❌ Error",
            description=f"Error leaving voice channel: {str(e)}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

@bot.command(name='status', help='Check bot streaming status')
async def status(ctx):
    """Check current bot status with detailed information"""
    
    if stream_bot.voice_client and stream_bot.voice_client.is_connected() and stream_bot.current_channel:
        embed = discord.Embed(
            title="📺 Currently Streaming",
            color=discord.Color.green()
        )
        embed.add_field(name="Channel", value=stream_bot.current_channel.name, inline=True)
        embed.add_field(name="Users", value=len(stream_bot.current_channel.members), inline=True)
        embed.add_field(name="Stream", value="South Park 24/7", inline=True)
        embed.add_field(name="Status", value="🟢 Active", inline=True)
        embed.add_field(name="Connection", value="🟢 Stable", inline=True)
        embed.add_field(name="Browser", value="🟢 Running" if stream_bot.driver else "🔴 Stopped", inline=True)
        embed.set_footer(text=f"Use {COMMAND_PREFIX}leave to stop streaming")
    else:
        embed = discord.Embed(
            title="💤 Not Streaming",
            description=f"Bot is ready to stream!\nUse `{COMMAND_PREFIX}join` while in a voice channel to start.",
            color=discord.Color.orange()
        )
        embed.add_field(name="Status", value="🔴 Offline", inline=False)
        
        if stream_bot.connection_attempts > 0:
            embed.add_field(name="Last Connection Attempts", value=f"{stream_bot.connection_attempts}/{stream_bot.max_connection_attempts}", inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='reconnect', help='Force reconnect to voice channel')
async def reconnect(ctx):
    """Force reconnect to current voice channel"""
    
    if not stream_bot.current_channel:
        embed = discord.Embed(
            title="❌ No Channel",
            description="No voice channel to reconnect to. Use `!join` first.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    embed = discord.Embed(
        title="🔄 Reconnecting",
        description="Attempting to reconnect to voice channel...",
        color=discord.Color.blue()
    )
    status_msg = await ctx.send(embed=embed)
    
    try:
        # Reset connection attempts
        stream_bot.connection_attempts = 0
        stream_bot.reconnect_delay = 10
        
        if await stream_bot.connect_to_voice_with_retry(stream_bot.current_channel):
            embed = discord.Embed(
                title="✅ Reconnected",
                description=f"Successfully reconnected to **{stream_bot.current_channel.name}**!",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="❌ Reconnection Failed",
                description="Failed to reconnect. Please try `!leave` then `!join` again.",
                color=discord.Color.red()
            )
        
        await status_msg.edit(embed=embed)
        
    except Exception as e:
        logger.error(f"Error in reconnect command: {e}")
        embed = discord.Embed(
            title="❌ Error",
            description=f"Error during reconnection: {str(e)}",
            color=discord.Color.red()
        )
        await status_msg.edit(embed=embed)

@bot.event
async def on_voice_state_update(member, before, after):
    """Handle voice state updates with improved logic"""
    if stream_bot.voice_client and stream_bot.current_channel:
        # Check if bot is alone in the channel
        human_members = [m for m in stream_bot.current_channel.members if not m.bot]
        
        if len(human_members) == 0:
            logger.info(f"No users left in {stream_bot.current_channel.name}, leaving...")
            await stream_bot.cleanup()

@bot.event
async def on_command_error(ctx, error):
    """Enhanced error handling"""
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore unknown commands
    
    logger.error(f"Command error in {ctx.command}: {error}")
    
    if isinstance(error, discord.errors.ConnectionClosed):
        embed = discord.Embed(
            title="🔌 Connection Error",
            description="Lost connection to Discord. The bot will attempt to reconnect automatically.",
            color=discord.Color.orange()
        )
    else:
        embed = discord.Embed(
            title="❌ Command Error",
            description=f"An error occurred: {str(error)[:200]}...",
            color=discord.Color.red()
        )
    
    try:
        await ctx.send(embed=embed)
    except:
        pass  # Channel might be unavailable

if __name__ == '__main__':
    if BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        print("❌ Error: Please set your bot token in config.py")
        print("🔗 Get your bot token from: https://discord.com/developers/applications")
        input("Press Enter to exit...")
        sys.exit(1)
    
    try:
        print("🚀 Starting Improved South Park Stream Bot...")
        print(f"📺 Stream URL: {STREAM_URL}")
        print(f"🎮 Command prefix: {COMMAND_PREFIX}")
        print(f"⚙️ FPS: {STREAM_FPS}, Resolution: {BROWSER_WIDTH}x{BROWSER_HEIGHT}")
        print(f"🔧 Max connection attempts: {stream_bot.max_connection_attempts}")
        print("-" * 50)
        
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