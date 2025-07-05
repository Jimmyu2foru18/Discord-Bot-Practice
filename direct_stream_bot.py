import discord
from discord.ext import commands
import asyncio
import logging
import os
import sys
import time
import yt_dlp
import ffmpeg
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import configuration
try:
    from config import BOT_TOKEN, STREAM_URL, COMMAND_PREFIX
except ImportError:
    print("Error: config.py not found or missing required variables.")
    print("Please check your config.py file and ensure all required variables are set.")
    sys.exit(1)

# Setup Discord bot
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True

# Set permissions integer for voice connection (3238400)
# This includes permissions for Connect (0x100000), Speak (0x200000), Use Voice Activity (0x2000000),
# and other necessary voice permissions
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

# Store the permissions integer for use in voice connections
BOT_PERMISSIONS = 3238400

class DirectStreamBot:
    def __init__(self):
        self.voice_client = None
        self.current_channel = None
        self.connection_attempts = 0
        self.max_connection_attempts = 5
        self.reconnect_delay = 10  # seconds
        self.stream_task = None
        self.is_streaming = False
        self.stream_url = None
        self.stream_start_time = None
        self.ffmpeg_available = self._check_ffmpeg_available()
        self.ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }
        
    def _check_ffmpeg_available(self):
        """Check if FFmpeg is available on the system"""
        try:
            # Try to run ffmpeg -version
            import subprocess
            subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            return True
        except Exception:
            logger.warning("FFmpeg not found or not working properly")
            return False
        
    async def extract_direct_stream_url(self, page_url):
        """Extract the direct stream URL from the South Park stream page"""
        try:
            logger.info(f"Extracting direct stream URL from {page_url}")
            
            # First try using yt-dlp to extract the URL with more options
            try:
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': False,  # Full extraction
                    'skip_download': True,
                    'no_check_certificate': True,
                    'force_generic_extractor': False,
                    'geo_bypass': True,
                    'geo_bypass_country': 'US',
                    'http_headers': {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Referer': 'https://southpark.cc.com/',
                        'Origin': 'https://southpark.cc.com',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'cross-site',
                        'Pragma': 'no-cache',
                        'Cache-Control': 'no-cache',
                    }
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    logger.info("Attempting to extract stream URL with yt-dlp...")
                    info = ydl.extract_info(page_url, download=False)
                    if info:
                        if 'url' in info:
                            logger.info("Successfully extracted stream URL using yt-dlp (direct)")
                            return info['url']
                        elif 'formats' in info and info['formats']:
                            # Get the best audio format
                            formats = sorted(info['formats'], key=lambda x: (
                                x.get('acodec', 'none') != 'none',  # Prefer formats with audio
                                x.get('abr', 0),  # Higher audio bitrate
                                x.get('filesize', 0) if x.get('filesize') else float('inf')  # Smaller file size if available
                            ), reverse=True)
                            
                            for format in formats:
                                if format.get('acodec') != 'none' and format.get('url'):
                                    logger.info(f"Successfully extracted stream URL using yt-dlp (format: {format.get('format_id')}, audio bitrate: {format.get('abr')})")
                                    return format['url']
            except Exception as e:
                logger.warning(f"yt-dlp extraction failed: {e}, trying alternative method")
            
            # If yt-dlp fails, try using requests and BeautifulSoup with improved headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': 'https://southpark.cc.com/',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0',
            }
            
            response = requests.get(page_url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for video sources
            video_tags = soup.find_all('video')
            for video in video_tags:
                # Check for source tags
                sources = video.find_all('source')
                for source in sources:
                    if source.has_attr('src'):
                        src = source['src']
                        if src.endswith('.m3u8') or 'playlist' in src:
                            logger.info(f"Found m3u8 playlist in video source: {src}")
                            return src
                        return source['src']
                
                # Check for src attribute directly on video tag
                if video.has_attr('src'):
                    return video['src']
            
            # Look for iframe sources
            iframe_tags = soup.find_all('iframe')
            for iframe in iframe_tags:
                if iframe.has_attr('src'):
                    iframe_url = iframe['src']
                    # If it's a relative URL, make it absolute
                    if not iframe_url.startswith('http'):
                        parsed_url = urlparse(page_url)
                        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                        iframe_url = base_url + iframe_url
                    
                    logger.info(f"Found iframe, recursively extracting from: {iframe_url}")
                    # Recursively extract from iframe source
                    return await self.extract_direct_stream_url(iframe_url)
            
            # Look for m3u8 URLs in the page source
            m3u8_pattern = r'(https?://[^\s\'\"]+\.m3u8[^\s\'\"]*)'
            m3u8_matches = re.findall(m3u8_pattern, response.text)
            if m3u8_matches:
                logger.info(f"Found m3u8 URL using regex: {m3u8_matches[0]}")
                return m3u8_matches[0]
            
            # Look for JSON data that might contain stream URLs
            json_pattern = r'"(https?://[^\s\'\"]+\.(m3u8|mp4|mp3)[^\s\'\"]*)"'
            json_matches = re.findall(json_pattern, response.text)
            if json_matches:
                logger.info(f"Found media URL in JSON: {json_matches[0][0]}")
                return json_matches[0][0]
            
            # Look for any media URLs
            media_pattern = r'(https?://[^\s\'\"]+\.(mp4|mp3)[^\s\'\"]*)'
            media_matches = re.findall(media_pattern, response.text)
            if media_matches:
                logger.info(f"Found media URL: {media_matches[0][0]}")
                return media_matches[0][0]
            
            # If all else fails, return the original URL
            logger.warning("Could not extract direct stream URL, using original URL")
            return page_url
            
        except Exception as e:
            logger.error(f"Error extracting stream URL: {e}")
            return page_url
    
    async def connect_to_voice_with_retry(self, channel):
        """Connect to voice channel with retry logic and enhanced error handling for Discord 4006 errors"""
        self.connection_attempts = 0
        self.max_connection_attempts = 12  # Further increased max attempts
        self.reconnect_delay = 3  # Start with an even shorter delay
        
        # Track if we've encountered a 4006 error
        encountered_4006 = False
        
        # First, ensure we're not already in a voice channel in this guild
        if channel.guild.voice_client is not None:
            try:
                logger.info(f"Already in a voice channel in this guild, cleaning up first")
                await channel.guild.voice_client.disconnect(force=True)
                await asyncio.sleep(5)  # Even longer delay to ensure proper cleanup
            except Exception as e:
                logger.warning(f"Error during pre-connection cleanup: {e}")
                # If we can't disconnect cleanly, wait longer to let Discord reset
                await asyncio.sleep(7)
                
        # Verify PyNaCl is installed
        try:
            import nacl.secret
            logger.info("PyNaCl is installed and available")
        except ImportError:
            logger.error("PyNaCl is not installed. Voice connections require PyNaCl.")
            logger.error("Please install it with: pip install PyNaCl")
            return False
        
        while self.connection_attempts < self.max_connection_attempts:
            try:
                self.connection_attempts += 1
                logger.info(f"Attempting to connect to voice channel (attempt {self.connection_attempts}/{self.max_connection_attempts})")
                
                # If already connected, disconnect first
                if self.voice_client and self.voice_client.is_connected():
                    logger.info("Disconnecting from current voice channel before reconnecting")
                    await self.voice_client.disconnect(force=True)
                    await asyncio.sleep(3)  # Longer delay to ensure proper cleanup
                
                # Determine connection parameters based on attempt number and error history
                timeout_value = 120.0  # Even longer timeout
                self_deaf_value = True  # Reduce bandwidth usage
                reconnect_value = True  # Default to auto-reconnect
                
                # If we've encountered a 4006 error, use a completely different approach
                if encountered_4006:
                    logger.info("Using 4006 error recovery connection strategy")
                    
                    # For 4006 errors, we need to try different connection parameters
                    # that might help reset Discord's session state
                    if self.connection_attempts % 3 == 0:  # Every 3rd attempt
                        logger.info("Using minimal connection settings for 4006 recovery")
                        timeout_value = 180.0
                        self_deaf_value = False
                        reconnect_value = False
                    elif self.connection_attempts % 3 == 1:  # Every 3rd+1 attempt
                        logger.info("Using alternative connection settings for 4006 recovery")
                        timeout_value = 150.0
                        self_deaf_value = True
                        reconnect_value = True
                    else:  # Every 3rd+2 attempt
                        logger.info("Using standard connection settings for 4006 recovery")
                        timeout_value = 120.0
                        self_deaf_value = True
                        reconnect_value = True
                else:
                    # For first attempt, use more conservative settings
                    if self.connection_attempts == 1:
                        logger.info("Using conservative connection settings for first attempt")
                        timeout_value = 60.0
                        self_deaf_value = True
                    
                    # For last attempt, try with different settings
                    if self.connection_attempts == self.max_connection_attempts:
                        logger.info("Using alternative connection settings for final attempt")
                        timeout_value = 180.0
                        self_deaf_value = False
                
                # Connect to voice channel with improved options and permissions
                logger.info(f"Connecting with timeout={timeout_value}, self_deaf={self_deaf_value}, reconnect={reconnect_value}, permissions={BOT_PERMISSIONS}")
                
                # Use a try-except block specifically for the connection
                try:
                    # First, try to create a voice client with the specified parameters
                    self.voice_client = await channel.connect(
                        timeout=timeout_value,
                        reconnect=reconnect_value,
                        self_deaf=self_deaf_value,
                        self_mute=False,
                        cls=discord.VoiceClient
                    )
                    
                    # Set the voice client's permissions
                    if hasattr(self.voice_client, 'permissions'):
                        self.voice_client.permissions = BOT_PERMISSIONS
                        logger.info(f"Set voice client permissions to {BOT_PERMISSIONS}")
                    else:
                        logger.warning("Could not set voice client permissions directly")
                        
                except discord.errors.ConnectionClosed as cc_error:
                    error_code = getattr(cc_error, 'code', None)
                    logger.error(f"Connection closed during connect with code {error_code}: {cc_error}")
                    
                    # If we get a 4006 error, try a different approach
                    if error_code == 4006:
                        logger.warning("Detected 4006 error during connection, trying alternative approach")
                        encountered_4006 = True
                        
                        # Wait longer before retrying
                        await asyncio.sleep(5)
                        
                        # Try with minimal settings
                        logger.info("Attempting connection with minimal settings")
                        self.voice_client = await channel.connect(
                            timeout=30.0,
                            reconnect=False,
                            self_deaf=True,
                            self_mute=True
                        )
                        
                        # Wait a moment
                        await asyncio.sleep(2)
                        
                        # Disconnect and try again with normal settings
                        await self.voice_client.disconnect(force=True)
                        await asyncio.sleep(5)
                        
                        # Connect again with normal settings
                        self.voice_client = await channel.connect(
                            timeout=timeout_value,
                            reconnect=reconnect_value,
                            self_deaf=self_deaf_value,
                            self_mute=False
                        )
                    else:
                        # Re-raise the exception for other error codes
                        raise
                self.current_channel = channel
                
                # Add a longer delay after connecting to ensure stability
                logger.info(f"Connected to {channel.name}, stabilizing connection...")
                await asyncio.sleep(5)  # Increased stabilization period
                
                # Verify the connection is still active
                if not self.voice_client.is_connected():
                    raise Exception("Connection lost immediately after connecting")
                
                logger.info(f"Successfully connected to {channel.name}")
                self.connection_attempts = 0  # Reset for future reconnects
                self.reconnect_delay = 5  # Reset delay
                return True
                
            except discord.errors.ConnectionClosed as e:
                error_code = getattr(e, 'code', None)
                logger.warning(f"Connection closed (code {error_code}): {e}")
                
                # Special handling for 4006 error (session no longer valid)
                if error_code == 4006:
                    logger.warning("Detected Discord error 4006 - session no longer valid")
                    encountered_4006 = True
                    
                    # For 4006 errors, we need a complete reset of the Discord connection
                    logger.info("Performing complete Discord connection reset for 4006 error")
                    
                    # Force disconnect any lingering connections
                    try:
                        if channel.guild.voice_client:
                            await channel.guild.voice_client.disconnect(force=True)
                        self.voice_client = None
                    except Exception as cleanup_error:
                        logger.warning(f"Error during 4006 cleanup: {cleanup_error}")
                    
                    # Wait longer for Discord to fully reset the session
                    logger.info("Waiting for Discord to reset session state...")
                    await asyncio.sleep(20)  # Even longer cooldown for 4006 errors
                    
                    # Reset connection attempts to give more chances after a 4006 error
                    self.connection_attempts = max(1, self.connection_attempts - 2)
                elif self.connection_attempts < self.max_connection_attempts:
                    logger.info(f"Retrying in {self.reconnect_delay} seconds... (attempt {self.connection_attempts}/{self.max_connection_attempts})")
                    await asyncio.sleep(self.reconnect_delay)
                    # Increase delay for next attempt, but not too much
                    self.reconnect_delay = min(self.reconnect_delay * 1.5, 30)
                else:
                    logger.error("Max connection attempts reached")
                    
            except discord.errors.ClientException as e:
                logger.error(f"Discord client error: {e}")
                
                if "already connected to a voice channel" in str(e).lower():
                    # If we're already connected, consider it a success
                    self.voice_client = channel.guild.voice_client
                    self.current_channel = channel
                    logger.info(f"Already connected to a voice channel in this guild")
                    self.connection_attempts = 0  # Reset for future reconnects
                    return True
                
                # For other client exceptions, wait and retry
                if self.connection_attempts < self.max_connection_attempts:
                    logger.info(f"Client exception, retrying in {self.reconnect_delay} seconds...")
                    await asyncio.sleep(self.reconnect_delay)
                    
            except Exception as e:
                logger.error(f"Unexpected error connecting to voice: {e}")
                
                if self.connection_attempts < self.max_connection_attempts:
                    logger.info(f"Unexpected error, retrying in {self.reconnect_delay} seconds...")
                    await asyncio.sleep(self.reconnect_delay)
        
        # If we've exhausted all attempts, try one last time with different settings
        try:
            logger.warning("All standard connection attempts failed, performing emergency connection procedure")
            
            # Complete cleanup of any lingering connections
            try:
                if channel.guild.voice_client:
                    await channel.guild.voice_client.disconnect(force=True)
                self.voice_client = None
                await asyncio.sleep(15)  # Even longer delay to ensure Discord fully resets
            except Exception as cleanup_error:
                logger.warning(f"Error during emergency cleanup: {cleanup_error}")
                await asyncio.sleep(20)  # Even longer delay if cleanup fails
            
            # If we've encountered a 4006 error, use a completely different approach for final attempt
            if encountered_4006:
                logger.warning("Using special 4006 error recovery for final connection attempt")
                
                # For 4006 errors, we need to try a completely different approach
                # First, try to reset Discord's session state by using a minimal connection
                try:
                    logger.info("Step 1: Attempting minimal connection to reset Discord state...")
                    temp_voice_client = await channel.connect(
                        timeout=30.0,  # Short timeout
                        reconnect=False,  # Don't auto-reconnect
                        self_deaf=True,  # Self-deafen to minimize bandwidth
                        self_mute=True,   # Self-mute to minimize bandwidth
                        cls=discord.VoiceClient
                    )
                    
                    # Set the voice client's permissions
                    if hasattr(temp_voice_client, 'permissions'):
                        temp_voice_client.permissions = BOT_PERMISSIONS
                        logger.info(f"Set temporary voice client permissions to {BOT_PERMISSIONS}")
                    else:
                        logger.warning("Could not set temporary voice client permissions directly")
                    
                    # Wait briefly, then disconnect
                    await asyncio.sleep(2)
                    await temp_voice_client.disconnect(force=True)
                    await asyncio.sleep(5)  # Wait for Discord to process the disconnect
                    
                    logger.info("Step 1 completed: Minimal connection and disconnect successful")
                except Exception as minimal_error:
                    logger.warning(f"Step 1 failed: {minimal_error}")
                    await asyncio.sleep(5)  # Wait a bit before continuing
                
                # Now try a normal connection with different settings
                logger.info("Step 2: Attempting final connection with special settings...")
                self.voice_client = await channel.connect(
                    timeout=240.0,  # Very long timeout
                    reconnect=True,  # Auto-reconnect enabled
                    self_deaf=False,  # Don't self-deafen
                    self_mute=False,   # Don't self-mute
                    cls=discord.VoiceClient
                )
                
                # Set the voice client's permissions
                if hasattr(self.voice_client, 'permissions'):
                    self.voice_client.permissions = BOT_PERMISSIONS
                    logger.info(f"Set voice client permissions to {BOT_PERMISSIONS}")
                else:
                    logger.warning("Could not set voice client permissions directly")
            else:
                # Try with absolute minimal settings
                logger.info("Making final connection attempt with minimal settings...")
                self.voice_client = await channel.connect(
                    timeout=180.0,  # Very long timeout
                    reconnect=False,  # Don't auto-reconnect to avoid potential loops
                    self_deaf=False,  # Don't self-deafen to minimize potential issues
                    self_mute=False,
                    cls=discord.VoiceClient
                )
                
                # Set the voice client's permissions
                if hasattr(self.voice_client, 'permissions'):
                    self.voice_client.permissions = BOT_PERMISSIONS
                    logger.info(f"Set voice client permissions to {BOT_PERMISSIONS}")
                else:
                    logger.warning("Could not set voice client permissions directly")
                
            self.current_channel = channel
            
            # Extra long stabilization period
            logger.info("Final connection established, extended stabilization period...")
            await asyncio.sleep(10)  # Even longer stabilization period
            
            # Verify the connection is still active
            if not self.voice_client.is_connected():
                raise Exception("Final connection lost during stabilization")
                
            logger.info(f"Final attempt succeeded, connected to {channel.name}")
            return True
        except discord.errors.ConnectionClosed as dc_error:
            error_code = getattr(dc_error, 'code', None)
            logger.error(f"Final connection attempt failed with Discord error code {error_code}: {dc_error}")
            return False
        except Exception as e:
            logger.error(f"Final connection attempt failed: {e}")
            return False
    
    async def start_streaming(self):
        """Start streaming audio from the South Park stream"""
        if not self.voice_client or not self.voice_client.is_connected():
            logger.error("Not connected to a voice channel")
            return False
        
        try:
            # Extract the direct stream URL
            self.stream_url = await self.extract_direct_stream_url(STREAM_URL)
            logger.info(f"Using stream URL: {self.stream_url}")
            
            # Validate the stream URL
            if not self.stream_url or not self.stream_url.startswith('http'):
                logger.error(f"Invalid stream URL: {self.stream_url}")
                # Try to extract again with a different approach
                try:
                    logger.info("Attempting to extract stream URL with alternative method...")
                    # Try direct access to the stream URL
                    response = requests.get(STREAM_URL, headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Accept': '*/*',
                        'Origin': 'https://southpark.cc.com',
                        'Referer': 'https://southpark.cc.com/'
                    })
                    
                    # Look for m3u8 URLs in the response
                    m3u8_pattern = r'(https?://[^\s"\']+\.m3u8[^\s"\']*)'
                    m3u8_urls = re.findall(m3u8_pattern, response.text)
                    
                    if m3u8_urls:
                        self.stream_url = m3u8_urls[0]
                        logger.info(f"Found alternative stream URL: {self.stream_url}")
                    else:
                        # If no m3u8 found, try using the original URL directly
                        self.stream_url = STREAM_URL
                        logger.info(f"Using original URL as stream URL: {self.stream_url}")
                except Exception as alt_error:
                    logger.error(f"Alternative extraction failed: {alt_error}")
                    self.stream_url = STREAM_URL
                    logger.info(f"Falling back to original URL: {self.stream_url}")
            
            # Stop any existing stream
            if self.is_streaming:
                await self.stop_streaming()
            
            # Wait a moment to ensure voice connection is stable
            await asyncio.sleep(2)
            
            # Enhanced FFmpeg options for better stability and audio quality
            self.ffmpeg_options = {
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 10 -analyzeduration 10000000 -probesize 10000000 -fflags nobuffer+discardcorrupt+fastseek',
                'options': '-vn -af "volume=1.0" -b:a 128k -ar 48000 -ac 2'
            }
            
            # Create an audio source with error handling
            try:
                logger.info(f"Creating audio source with enhanced options: {self.ffmpeg_options}")
                audio_source = discord.FFmpegPCMAudio(self.stream_url, **self.ffmpeg_options)
                # Add a volume transformer to prevent audio clipping
                audio_source = discord.PCMVolumeTransformer(audio_source, volume=0.8)
            except Exception as audio_error:
                logger.error(f"Error creating audio source with enhanced options: {audio_error}")
                # Try with alternative options as fallback
                logger.info("Trying alternative FFmpeg options...")
                self.ffmpeg_options = {
                    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 15 -timeout 10000000',
                    'options': '-vn -ar 44100 -ac 2'
                }
                try:
                    audio_source = discord.FFmpegPCMAudio(self.stream_url, **self.ffmpeg_options)
                    audio_source = discord.PCMVolumeTransformer(audio_source, volume=0.8)
                except Exception as alt_audio_error:
                    logger.error(f"Error with alternative options: {alt_audio_error}")
                    # Last resort: minimal options
                    logger.info("Using minimal FFmpeg options as last resort")
                    self.ffmpeg_options = {
                        'before_options': '-reconnect 1',
                        'options': '-vn'
                    }
                    audio_source = discord.FFmpegPCMAudio(self.stream_url, **self.ffmpeg_options)
            
            # Start playing with better error handling
            def after_playing(error):
                if error:
                    logger.error(f"Player error: {error}")
                    # Schedule a restart of the stream
                    asyncio.create_task(self._handle_playback_error())
                else:
                    logger.info("Stream ended without error, scheduling restart")
                    # If the stream ends normally, also restart it
                    asyncio.create_task(self._handle_playback_error())
            
            # Log that we're about to start playing
            logger.info(f"Starting playback with stream URL: {self.stream_url}")
            self.voice_client.play(audio_source, after=after_playing)
            self.is_streaming = True
            self.stream_start_time = time.time()
            
            # Start monitoring task
            self.stream_task = asyncio.create_task(self._monitor_stream())
            
            logger.info("Streaming started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error starting stream: {e}")
            # Try one more time with direct URL
            try:
                logger.info("Attempting emergency stream start with direct URL")
                self.stream_url = STREAM_URL
                self.ffmpeg_options = {
                    'before_options': '-reconnect 1',
                    'options': '-vn'
                }
                audio_source = discord.FFmpegPCMAudio(self.stream_url, **self.ffmpeg_options)
                self.voice_client.play(audio_source, after=lambda e: asyncio.create_task(self._handle_playback_error()) if e else None)
                self.is_streaming = True
                self.stream_start_time = time.time()
                self.stream_task = asyncio.create_task(self._monitor_stream())
                logger.info("Emergency stream start successful")
                return True
            except Exception as emergency_error:
                logger.error(f"Emergency stream start failed: {emergency_error}")
                return False
            
    async def _handle_playback_error(self):
        """Handle errors that occur during playback with enhanced recovery"""
        if not self.is_streaming:
            return
            
        logger.info("Handling playback error, attempting to restart stream...")
        await asyncio.sleep(2)  # Wait a moment before restarting
        
        # Check if we're still connected to voice
        if not self.voice_client or not self.voice_client.is_connected():
            logger.warning("Voice client disconnected during playback, attempting to reconnect...")
            try:
                # Try to reconnect to the voice channel
                if self.current_channel:
                    logger.info(f"Reconnecting to channel {self.current_channel.name}")
                    await self.connect_to_voice_with_retry(self.current_channel)
                    await asyncio.sleep(3)  # Wait for connection to stabilize
                else:
                    logger.error("No current channel to reconnect to")
                    return
            except Exception as reconnect_error:
                logger.error(f"Failed to reconnect to voice channel: {reconnect_error}")
                # If we can't reconnect, schedule a delayed attempt
                if self.is_streaming:
                    asyncio.create_task(self._delayed_restart_attempt())
                return
        
        # Check if we need to refresh the stream URL
        current_time = time.time()
        time_since_start = current_time - self.stream_start_time
        
        # If it's been more than 30 minutes, refresh the stream URL
        if time_since_start > 1800:  # 30 minutes
            logger.info("Stream has been running for over 30 minutes, refreshing stream URL")
            try:
                new_stream_url = await self.extract_direct_stream_url(STREAM_URL)
                if new_stream_url and new_stream_url.startswith('http'):
                    self.stream_url = new_stream_url
                    logger.info(f"Refreshed stream URL: {self.stream_url}")
                    self.stream_start_time = current_time  # Reset the timer
            except Exception as refresh_error:
                logger.warning(f"Failed to refresh stream URL: {refresh_error}")
        
        try:
            # Try with enhanced options first
            enhanced_ffmpeg_options = {
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 10 -analyzeduration 10000000 -probesize 10000000 -fflags nobuffer+discardcorrupt+fastseek',
                'options': '-vn -af "volume=1.0" -b:a 128k -ar 48000 -ac 2'
            }
            
            logger.info("Attempting to restart stream with enhanced options")
            audio_source = discord.FFmpegPCMAudio(self.stream_url, **enhanced_ffmpeg_options)
            audio_source = discord.PCMVolumeTransformer(audio_source, volume=0.8)
            
            # Start playing again if still connected and not already playing
            if self.voice_client and self.voice_client.is_connected() and not self.voice_client.is_playing():
                self.voice_client.play(audio_source, after=lambda e: 
                    asyncio.create_task(self._handle_playback_error()) if e else None)
                logger.info("Stream restarted after playback error with enhanced options")
                self.ffmpeg_options = enhanced_ffmpeg_options  # Update the options for future restarts
                return
        except Exception as enhanced_error:
            logger.warning(f"Failed to restart with enhanced options: {enhanced_error}")
        
        try:
            # Fall back to current options
            logger.info("Attempting to restart stream with current options")
            audio_source = discord.FFmpegPCMAudio(self.stream_url, **self.ffmpeg_options)
            audio_source = discord.PCMVolumeTransformer(audio_source, volume=0.8)
            
            # Start playing again if still connected and not already playing
            if self.voice_client and self.voice_client.is_connected() and not self.voice_client.is_playing():
                self.voice_client.play(audio_source, after=lambda e: 
                    asyncio.create_task(self._handle_playback_error()) if e else None)
                logger.info("Stream restarted after playback error with current options")
                return
        except Exception as current_error:
            logger.warning(f"Failed to restart with current options: {current_error}")
        
        try:
            # Last resort: minimal options
            minimal_ffmpeg_options = {
                'before_options': '-reconnect 1',
                'options': '-vn'
            }
            
            logger.info("Attempting to restart stream with minimal options")
            audio_source = discord.FFmpegPCMAudio(self.stream_url, **minimal_ffmpeg_options)
            
            # Start playing again if still connected and not already playing
            if self.voice_client and self.voice_client.is_connected() and not self.voice_client.is_playing():
                self.voice_client.play(audio_source, after=lambda e: 
                    asyncio.create_task(self._handle_playback_error()) if e else None)
                logger.info("Stream restarted after playback error with minimal options")
                self.ffmpeg_options = minimal_ffmpeg_options  # Update the options for future restarts
                return
        except Exception as minimal_error:
            logger.error(f"All restart attempts failed: {minimal_error}")
            # If we can't restart with any options, schedule a delayed attempt
            if self.is_streaming:
                asyncio.create_task(self._delayed_restart_attempt())
    
    async def _monitor_stream(self):
        """Monitor the stream and restart if it stops, with enhanced reconnection logic"""
        check_interval = 5  # Check every 5 seconds initially
        consecutive_failures = 0
        max_consecutive_failures = 7  # Increased tolerance further
        reconnect_attempts = 0
        max_reconnect_attempts = 15
        last_reconnect_time = 0
        reconnect_cooldown = 30  # Reduced cooldown to recover faster
        discord_error_cooldown = 120  # Longer cooldown specifically for Discord errors
        
        # Track Discord-specific errors
        discord_error_count = 0
        last_discord_error_time = 0
        in_discord_error_recovery = False
        
        while self.is_streaming:
            try:
                current_time = time.time()
                
                # Check if we're still connected to voice
                if not self.voice_client or not self.voice_client.is_connected():
                    logger.warning("Voice client disconnected, attempting to reconnect...")
                    
                    # Check if we're in reconnect cooldown
                    if current_time - last_reconnect_time < reconnect_cooldown and reconnect_attempts > 0:
                        logger.info(f"In reconnect cooldown, waiting {reconnect_cooldown - (current_time - last_reconnect_time):.1f} seconds...")
                        await asyncio.sleep(5)
                        continue
                        
                    # Check if we're in Discord error cooldown (longer cooldown)
                    if in_discord_error_recovery and current_time - last_discord_error_time < discord_error_cooldown:
                        logger.info(f"In Discord error recovery cooldown, waiting {discord_error_cooldown - (current_time - last_discord_error_time):.1f} seconds...")
                        await asyncio.sleep(10)
                        continue
                    
                    if self.current_channel:
                        try:
                            reconnect_attempts += 1
                            last_reconnect_time = current_time
                            
                            if reconnect_attempts > max_reconnect_attempts:
                                logger.error(f"Exceeded maximum reconnect attempts ({max_reconnect_attempts}), stopping stream monitor")
                                self.is_streaming = False
                                break
                                
                            logger.info(f"Reconnect attempt {reconnect_attempts}/{max_reconnect_attempts}")
                            
                            # If we're in Discord error recovery mode, use a different approach
                            if in_discord_error_recovery:
                                logger.info("Using Discord error recovery strategy...")
                                # Complete cleanup first
                                await self.cleanup()
                                await asyncio.sleep(3)  # Give Discord some time
                                
                                # Try to reconnect with minimal settings first
                                try:
                                    logger.info("Attempting minimal connection to reset Discord state...")
                                    self.voice_client = await self.current_channel.connect(
                                        timeout=60, 
                                        reconnect=True, 
                                        self_deaf=True,
                                        cls=discord.VoiceClient
                                    )
                                    
                                    # Set the voice client's permissions
                                    if hasattr(self.voice_client, 'permissions'):
                                        self.voice_client.permissions = BOT_PERMISSIONS
                                        logger.info(f"Set voice client permissions to {BOT_PERMISSIONS}")
                                    else:
                                        logger.warning("Could not set voice client permissions directly")
                                        
                                    await asyncio.sleep(2)  # Stabilization period
                                except Exception as minimal_error:
                                    logger.warning(f"Minimal connection attempt failed: {minimal_error}")
                            
                            # Try to reconnect to the voice channel with normal settings
                            connected = await self.connect_to_voice_with_retry(self.current_channel)
                            if connected:
                                # Restart the stream
                                stream_restarted = await self.start_streaming()
                                if stream_restarted:
                                    logger.info("Successfully reconnected and restarted stream")
                                    consecutive_failures = 0
                                    # Reset Discord error recovery if successful
                                    if in_discord_error_recovery:
                                        logger.info("Discord error recovery successful")
                                        in_discord_error_recovery = False
                                        discord_error_count = 0
                                else:
                                    logger.warning("Reconnected to voice but failed to restart stream")
                                    consecutive_failures += 1
                            else:
                                logger.warning("Failed to reconnect to voice channel")
                                consecutive_failures += 1
                        except discord.errors.ConnectionClosed as dc_error:
                            # Handle Discord-specific connection errors
                            error_code = getattr(dc_error, 'code', None)
                            logger.error(f"Discord connection closed with code {error_code}: {dc_error}")
                            
                            # Special handling for 4006 (session no longer valid)
                            if error_code == 4006:
                                logger.warning("Detected Discord error 4006 - session no longer valid")
                                discord_error_count += 1
                                last_discord_error_time = current_time
                                in_discord_error_recovery = True
                                
                                # Force a longer cooldown period
                                await asyncio.sleep(5)
                            
                            consecutive_failures += 1
                        except Exception as e:
                            logger.error(f"Error during reconnection process: {e}")
                            consecutive_failures += 1
                    else:
                        logger.error("No channel to reconnect to, stopping stream monitor")
                        self.is_streaming = False
                        break
                        
                # Check if the stream is still playing
                elif not self.voice_client.is_playing() and not self.voice_client.is_paused():
                    logger.warning("Stream stopped but voice connected, attempting to restart audio only...")
                    try:
                        # Check if we need to refresh the stream URL
                        if consecutive_failures >= 2:
                            try:
                                logger.info("Refreshing stream URL before restart attempt...")
                                new_url = await self.extract_direct_stream_url(STREAM_URL)
                                if new_url and new_url != self.stream_url:
                                    logger.info("Stream URL refreshed successfully")
                                    self.stream_url = new_url
                            except Exception as url_error:
                                logger.error(f"Error refreshing URL: {url_error}")
                        
                        # Create a new audio source
                        audio_source = discord.FFmpegPCMAudio(self.stream_url, **self.ffmpeg_options)
                        audio_source = discord.PCMVolumeTransformer(audio_source, volume=0.8)
                        
                        # Start playing again
                        self.voice_client.play(audio_source, after=lambda e: 
                            asyncio.create_task(self._handle_playback_error()) if e else None)
                        logger.info("Stream audio restarted successfully")
                        consecutive_failures = 0
                        # Reset stream start time
                        self.stream_start_time = time.time()
                    except Exception as e:
                        logger.error(f"Error restarting stream audio: {e}")
                        consecutive_failures += 1
                else:
                    # Stream is playing normally, reset failure counter and reduce reconnect attempts
                    consecutive_failures = 0
                    if reconnect_attempts > 0 and current_time - last_reconnect_time > 300:  # 5 minutes of stability
                        reconnect_attempts = max(0, reconnect_attempts - 1)
                
                # If we've had too many consecutive failures, take a longer break and try more aggressive recovery
                if consecutive_failures >= max_consecutive_failures:
                    logger.warning(f"Too many consecutive failures ({consecutive_failures}), attempting full recovery")
                    
                    # Try to fully clean up and reconnect
                    try:
                        # Complete cleanup
                        await self.cleanup()
                        await asyncio.sleep(7)  # Longer delay for Discord to fully reset
                        
                        # Check if Discord error recovery is needed
                        if discord_error_count >= 3:
                            logger.warning(f"Multiple Discord errors detected ({discord_error_count}), performing deep recovery")
                            # Reset the bot's Discord connection state completely
                            try:
                                # Force disconnect any lingering connections
                                if self.voice_client:
                                    try:
                                        await self.voice_client.disconnect(force=True)
                                    except:
                                        pass
                                self.voice_client = None
                                
                                # Wait longer for Discord to fully reset the session
                                await asyncio.sleep(10)
                                
                                # Reset error tracking
                                in_discord_error_recovery = True
                                last_discord_error_time = time.time()
                                logger.info("Deep recovery: Discord connection state reset")
                            except Exception as deep_error:
                                logger.error(f"Error during deep recovery: {deep_error}")
                        
                        if self.current_channel:
                            logger.info("Attempting full reconnection after cleanup")
                            
                            # Try a minimal connection first if we've had Discord errors
                            if in_discord_error_recovery:
                                try:
                                    logger.info("Recovery: Attempting minimal connection to reset Discord state...")
                                    # Use a very basic connection attempt
                                    self.voice_client = await self.current_channel.connect(timeout=60, reconnect=True, self_deaf=True)
                                    await asyncio.sleep(3)  # Stabilization period
                                    logger.info("Minimal connection successful, proceeding with full connection")
                                except Exception as minimal_error:
                                    logger.warning(f"Minimal connection attempt failed: {minimal_error}")
                                    # Continue anyway to try the normal connection
                            
                            # Try normal connection with retry
                            connected = await self.connect_to_voice_with_retry(self.current_channel)
                            if connected:
                                # Try to refresh the stream URL
                                try:
                                    logger.info("Refreshing stream URL for recovery...")
                                    new_url = await self.extract_direct_stream_url(STREAM_URL)
                                    if new_url:
                                        self.stream_url = new_url
                                        logger.info(f"Refreshed stream URL for recovery: {self.stream_url}")
                                    else:
                                        logger.warning("Could not get new stream URL, using existing one if available")
                                except Exception as e:
                                    logger.error(f"Error refreshing stream URL during recovery: {e}")
                                
                                # Restart streaming
                                await asyncio.sleep(2)  # Short delay before starting stream
                                stream_restarted = await self.start_streaming()
                                if stream_restarted:
                                    logger.info("Full recovery successful")
                                    consecutive_failures = 0
                                    # Reset Discord error recovery if successful
                                    if in_discord_error_recovery:
                                        in_discord_error_recovery = False
                                        discord_error_count = 0
                                        logger.info("Discord error recovery completed successfully")
                                else:
                                    logger.error("Failed to restart stream after full recovery")
                            else:
                                logger.error("Failed to reconnect after full recovery")
                                
                                # If we're in Discord error recovery and still failing, increase cooldown
                                if in_discord_error_recovery:
                                    logger.warning("Discord error recovery failed, increasing cooldown")
                                    last_discord_error_time = time.time()  # Reset the timer for a longer wait
                    except Exception as e:
                        logger.error(f"Error during full recovery: {e}")
                    
                    # Reset consecutive failures counter but not Discord error count
                    consecutive_failures = 0
                
                # Adjust check interval based on stability and error conditions
                if in_discord_error_recovery:
                    # More frequent checks during Discord error recovery
                    check_interval = 2
                elif consecutive_failures > 0:
                    # More frequent checks when there are failures
                    check_interval = 3
                else:
                    # Normal operation - less frequent checks
                    check_interval = 10
                
            except discord.errors.ConnectionClosed as dc_error:
                # Handle Discord-specific connection errors in the main loop
                error_code = getattr(dc_error, 'code', None)
                logger.error(f"Discord connection closed in monitor loop with code {error_code}: {dc_error}")
                
                # Special handling for 4006 (session no longer valid)
                if error_code == 4006:
                    logger.warning("Detected Discord error 4006 in monitor loop - session no longer valid")
                    discord_error_count += 1
                    last_discord_error_time = time.time()
                    in_discord_error_recovery = True
                    
                    # Force a longer cooldown period
                    await asyncio.sleep(5)
                
                consecutive_failures += 1
            except Exception as e:
                logger.error(f"Error in stream monitor: {e}")
                consecutive_failures += 1
                
                # Check if this might be a Discord-related error
                error_str = str(e).lower()
                if "discord" in error_str or "voice" in error_str or "connection" in error_str or "websocket" in error_str:
                    logger.warning("Possible Discord-related error detected in general exception")
                    discord_error_count += 1
                    if discord_error_count >= 2:
                        in_discord_error_recovery = True
                        last_discord_error_time = time.time()
            
            await asyncio.sleep(check_interval)
        
        logger.info("Stream monitor stopped")
        
    async def _delayed_restart_attempt(self):
        """Make a delayed attempt to restart the stream with enhanced recovery"""
        # Use a longer delay for delayed restart to avoid rapid reconnection attempts
        delay = 10  # Start with a 10-second delay
        logger.info(f"Scheduling delayed restart attempt in {delay} seconds...")
        await asyncio.sleep(delay)
        
        if not self.is_streaming:
            return
            
        logger.info("Making delayed restart attempt with enhanced recovery...")
        
        # First, check if we need to refresh the stream URL
        try:
            logger.info("Attempting to refresh stream URL for delayed restart")
            new_stream_url = await self.extract_direct_stream_url(STREAM_URL)
            if new_stream_url and new_stream_url.startswith('http'):
                self.stream_url = new_stream_url
                logger.info(f"Refreshed stream URL for delayed restart: {self.stream_url}")
            else:
                logger.warning("Could not get valid stream URL, using existing one if available")
        except Exception as refresh_error:
            logger.warning(f"Failed to refresh stream URL for delayed restart: {refresh_error}")
        
        # Check if we're still connected to voice
        if not self.voice_client or not self.voice_client.is_connected():
            logger.warning("Voice client disconnected, attempting to reconnect before delayed restart")
            try:
                # Try to reconnect to the voice channel
                if self.current_channel:
                    logger.info(f"Reconnecting to channel {self.current_channel.name}")
                    connected = await self.connect_to_voice_with_retry(self.current_channel)
                    if not connected:
                        logger.error("Failed to reconnect to voice channel for delayed restart")
                        # Try one more time with a longer delay
                        await asyncio.sleep(15)
                        connected = await self.connect_to_voice_with_retry(self.current_channel)
                        if not connected:
                            logger.error("Second reconnection attempt failed, aborting delayed restart")
                            return
                else:
                    logger.error("No channel to reconnect to for delayed restart")
                    return
            except Exception as reconnect_error:
                logger.error(f"Failed to reconnect to voice channel: {reconnect_error}")
                # Schedule another attempt with longer delay if still streaming
                if self.is_streaming:
                    logger.info("Scheduling another delayed restart with longer delay")
                    await asyncio.sleep(20)  # Wait even longer before next attempt
                    asyncio.create_task(self._delayed_restart_attempt())
                return
        
        # Try to restart the stream with progressive options
        restart_attempts = 0
        max_restart_attempts = 3
        
        while restart_attempts < max_restart_attempts and self.is_streaming:
            restart_attempts += 1
            
            try:
                logger.info(f"Delayed restart attempt {restart_attempts}/{max_restart_attempts}")
                
                # Use different options based on attempt number
                if restart_attempts == 1:
                    # First attempt: Try with enhanced options
                    self.ffmpeg_options = {
                        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 15 -analyzeduration 10000000 -probesize 10000000',
                        'options': '-vn -af "volume=1.0" -ar 48000 -ac 2'
                    }
                elif restart_attempts == 2:
                    # Second attempt: Try with moderate options
                    self.ffmpeg_options = {
                        'before_options': '-reconnect 1 -reconnect_streamed 1',
                        'options': '-vn -ar 44100'
                    }
                else:
                    # Last attempt: Try with minimal options
                    self.ffmpeg_options = {
                        'before_options': '-reconnect 1',
                        'options': '-vn'
                    }
                
                # Create a new audio source with current options
                logger.info(f"Creating audio source with options: {self.ffmpeg_options}")
                audio_source = discord.FFmpegPCMAudio(self.stream_url, **self.ffmpeg_options)
                audio_source = discord.PCMVolumeTransformer(audio_source, volume=0.8)
                
                # Start playing again if not already playing
                if self.voice_client and self.voice_client.is_connected() and not self.voice_client.is_playing() and not self.voice_client.is_paused():
                    self.voice_client.play(audio_source, after=lambda e: 
                        asyncio.create_task(self._handle_playback_error()) if e else None)
                    logger.info(f"Stream restarted in delayed attempt {restart_attempts}")
                    return  # Success, exit the loop
                else:
                    logger.warning("Voice client not ready for playback during delayed restart")
                    await asyncio.sleep(5)  # Wait before next attempt
            except Exception as attempt_error:
                logger.warning(f"Delayed restart attempt {restart_attempts} failed: {attempt_error}")
                await asyncio.sleep(5)  # Wait before next attempt
        
        # If all restart attempts failed, try a full reconnect and restart
        if self.is_streaming and self.current_channel:
            try:
                logger.info("All delayed restart attempts failed, attempting full reconnect and restart")
                await self.cleanup()
                await asyncio.sleep(5)  # Wait longer after cleanup
                
                # Try to reconnect with special handling for 4006 errors
                connected = await self.connect_to_voice_with_retry(self.current_channel)
                if connected:
                    logger.info("Full reconnect successful, restarting stream")
                    await asyncio.sleep(5)  # Wait longer for connection to stabilize
                    await self.start_streaming()
                else:
                    logger.error("Full reconnect failed, giving up on delayed restart")
            except Exception as full_reconnect_error:
                logger.error(f"Full reconnect and restart failed: {full_reconnect_error}")
                # One final attempt to restart the bot's voice connection completely
                if self.is_streaming:
                    logger.info("Scheduling emergency voice reconnect")
                    await asyncio.sleep(30)  # Wait much longer before emergency attempt
                    try:
                        await self.cleanup()
                        await asyncio.sleep(10)
                        if self.current_channel:
                            await self.connect_to_voice_with_retry(self.current_channel)
                            await self.start_streaming()
                    except Exception as emergency_error:
                        logger.error(f"Emergency reconnect failed: {emergency_error}")
    
    async def stop_streaming(self):
        """Stop streaming"""
        self.is_streaming = False
        self.stream_start_time = None
        
        # Cancel the monitoring task
        if self.stream_task:
            try:
                self.stream_task.cancel()
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error cancelling stream task: {e}")
            self.stream_task = None
        
        # Stop the voice client
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.stop()
        
        logger.info("Streaming stopped")
    
    async def cleanup(self):
        """Clean up all resources"""
        logger.info("Cleaning up resources...")
        
        # Stop streaming
        await self.stop_streaming()
        
        # Disconnect from voice
        if self.voice_client:
            try:
                if self.voice_client.is_connected():
                    await self.voice_client.disconnect(force=True)
            except Exception as e:
                logger.error(f"Error disconnecting voice client: {e}")
            self.voice_client = None
        
        self.current_channel = None
        self.connection_attempts = 0
        self.reconnect_delay = 10
        self.stream_url = None

# Create bot instance
stream_bot = DirectStreamBot()

@bot.event
async def on_ready():
    logger.info(f'{bot.user} is now online!')
    print(f'🤖 {bot.user} is now online!')
    print(f'📺 Ready to stream South Park directly in Discord!')
    print(f'💬 Type {COMMAND_PREFIX}join in a Discord server to start streaming')

@bot.command(name='join', help='Join voice channel and start streaming South Park')
async def join_voice(ctx):
    # Check if user is in a voice channel
    if not ctx.author.voice:
        await ctx.send("❌ You need to be in a voice channel to use this command!")
        return
        
    voice_channel = ctx.author.voice.channel
    
    # Check if bot is already in this voice channel
    if stream_bot.voice_client and stream_bot.voice_client.is_connected() and stream_bot.current_channel == voice_channel:
        if stream_bot.is_streaming:
            await ctx.send(f"✅ Already streaming in {voice_channel.name}!")
            return
        else:
            # Connected but not streaming
            await ctx.send(f"🔄 Already in {voice_channel.name} but not streaming. Starting stream...")
            stream_started = await stream_bot.start_streaming()
            if stream_started:
                await ctx.send(f"✅ Started streaming South Park in {voice_channel.name}!")
            else:
                await ctx.send("❌ Failed to start streaming. Please try the !restart command.")
            return
    
    # Check if bot is in another voice channel
    if stream_bot.voice_client and stream_bot.voice_client.is_connected():
        await ctx.send(f"🔄 Moving from {stream_bot.current_channel.name} to {voice_channel.name}...")
        await stream_bot.cleanup()
        await asyncio.sleep(2)  # Wait for cleanup to complete
    
    # Send initial message
    setup_msg = await ctx.send(f"🔄 Setting up stream in {voice_channel.name}...")
    
    try:
        # Connect to voice channel with retry
        await setup_msg.edit(content=f"🔄 Connecting to {voice_channel.name}...")
        voice_connected = await stream_bot.connect_to_voice_with_retry(voice_channel)
        
        if not voice_connected:
            await setup_msg.edit(content="❌ Failed to connect to voice channel after multiple attempts.")
            await ctx.send("💡 **Troubleshooting Tips:**\n" +
                          "1. Make sure the bot has permission to join voice channels\n" +
                          "2. Try a different voice channel\n" +
                          "3. Restart Discord and try again")
            return
            
        # Start streaming
        await setup_msg.edit(content="🔄 Starting South Park stream...")
        
        # Extract stream URL with progress updates
        await setup_msg.edit(content="🔄 Extracting South Park stream URL...")
        stream_url = await stream_bot.extract_direct_stream_url(STREAM_URL)
        if not stream_url or stream_url == STREAM_URL:
            await setup_msg.edit(content="⚠️ Could not extract direct stream URL. Using original URL instead.")
        else:
            await setup_msg.edit(content="✅ Successfully extracted stream URL!")
        
        # Start streaming
        await setup_msg.edit(content="🔄 Starting audio stream...")
        stream_started = await stream_bot.start_streaming()
        
        if not stream_started:
            await setup_msg.edit(content="❌ Failed to start streaming. Please try again.")
            await ctx.send("💡 **Troubleshooting Tips:**\n" +
                          "1. Check if FFmpeg is installed correctly\n" +
                          "2. Try the !restart command\n" +
                          "3. Check the South Park stream URL in config.py")
            await stream_bot.cleanup()
            return
            
        await setup_msg.edit(content=f"✅ Successfully joined {voice_channel.name}!")
        await ctx.send("🎵 **Now streaming South Park audio directly in Discord!**\n" +
                      f"Use `{COMMAND_PREFIX}status` to check stream status\n" +
                      f"Use `{COMMAND_PREFIX}restart` if the audio stops\n" +
                      f"Use `{COMMAND_PREFIX}leave` to stop streaming")
        
    except Exception as e:
        logger.error(f"Error in join command: {e}")
        await setup_msg.edit(content=f"❌ An error occurred while joining: {str(e)[:100]}...")
        await ctx.send("💡 **Error Details:**\n" +
                      f"```{str(e)}```\n" +
                      "Please try again or check the bot logs for more information.")
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
        await stream_bot.cleanup()
        
        await leave_msg.edit(content=f"✅ Successfully left {voice_channel.name} and stopped streaming!")
        
    except Exception as e:
        logger.error(f"Error in leave command: {e}")
        await leave_msg.edit(content=f"❌ An error occurred while leaving: {str(e)}")
        # Force cleanup
        await stream_bot.cleanup()

@bot.command(name='status', help='Check bot streaming status and health')
async def status(ctx):
    status_embed = discord.Embed(
        title="South Park Stream Bot Status",
        color=discord.Color.blue(),
        timestamp=ctx.message.created_at
    )
    
    # Check voice connection
    if stream_bot.voice_client and stream_bot.voice_client.is_connected():
        # Calculate latency
        latency = round(stream_bot.voice_client.latency * 1000)
        latency_rating = "🟢 Good" if latency < 100 else "🟡 Fair" if latency < 200 else "🔴 Poor"
        
        status_embed.add_field(
            name="Voice Connection",
            value=f"✅ Connected to **{stream_bot.current_channel.name}**\n" +
                  f"📶 Latency: {latency}ms ({latency_rating})",
            inline=False
        )
        
        # Check streaming status
        if stream_bot.is_streaming:
            # Calculate uptime if stream is active
            if stream_bot.stream_start_time:
                uptime_seconds = int(time.time() - stream_bot.stream_start_time)
                hours, remainder = divmod(uptime_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                uptime_str = f"{hours}h {minutes}m {seconds}s"
            else:
                uptime_str = "Unknown"
                
            status_embed.add_field(
                name="Streaming",
                value=f"✅ Active\n⏱️ Uptime: {uptime_str}",
                inline=True
            )
        else:
            status_embed.add_field(
                name="Streaming",
                value="❌ Inactive\n💡 Use !restart to try again",
                inline=True
            )
    else:
        status_embed.add_field(
            name="Voice Connection",
            value="❌ Not connected to any voice channel\n💡 Use !join to connect",
            inline=False
        )
    
    # Add stream URL and extraction info
    if hasattr(stream_bot, 'stream_url') and stream_bot.stream_url != STREAM_URL:
        status_embed.add_field(
            name="Stream Source",
            value=f"🔗 Original: `{STREAM_URL}`\n" +
                  f"📡 Extracted: `{stream_bot.stream_url[:50]}...`",
            inline=False
        )
    else:
        status_embed.add_field(
            name="Stream Source",
            value=f"🔗 URL: `{STREAM_URL}`\n" +
                  "📡 Direct URL: Not extracted yet",
            inline=False
        )
    
    # Add bot info
    status_embed.add_field(
        name="Bot Info",
        value=f"🤖 Version: 1.0\n" +
              f"🔄 Prefix: {COMMAND_PREFIX}\n" +
              f"⚙️ FFmpeg: {'✅ Available' if stream_bot.ffmpeg_available else '❌ Not found'}",
        inline=True
    )
    
    # Add troubleshooting field
    status_embed.add_field(
        name="Troubleshooting",
        value=f"🔄 !restart - Restart stream\n" +
              f"🚪 !leave - Disconnect bot\n" +
              f"🔌 !join - Connect and stream",
        inline=True
    )
    
    # Add footer with help info
    status_embed.set_footer(text=f"South Park Stream Bot | Use {COMMAND_PREFIX}help for all commands")
    
    await ctx.send(embed=status_embed)

@bot.command(name='restart', help='Restart the stream if it stopped')
async def restart_stream(ctx):
    if not stream_bot.voice_client or not stream_bot.voice_client.is_connected():
        await ctx.send("❌ I'm not in a voice channel! Use !join first.")
        return
        
    restart_msg = await ctx.send("🔄 Restarting South Park stream...")
    
    try:
        # Stop current stream
        await restart_msg.edit(content="🔄 Stopping current stream...")
        await stream_bot.stop_streaming()
        await asyncio.sleep(1)  # Brief pause to ensure cleanup
        
        # Try to refresh the stream URL
        await restart_msg.edit(content="🔄 Refreshing stream URL...")
        try:
            new_stream_url = await stream_bot.extract_direct_stream_url(STREAM_URL)
            if new_stream_url and new_stream_url != STREAM_URL:
                stream_bot.stream_url = new_stream_url
                await restart_msg.edit(content="✅ Stream URL refreshed successfully!")
            else:
                await restart_msg.edit(content="⚠️ Could not refresh stream URL, using previous URL.")
        except Exception as url_error:
            logger.error(f"Error refreshing stream URL: {url_error}")
            await restart_msg.edit(content="⚠️ Error refreshing stream URL, using previous URL.")
        
        # Start streaming again
        await restart_msg.edit(content="🔄 Starting stream...")
        stream_started = await stream_bot.start_streaming()
        
        if stream_started:
            await restart_msg.edit(content="✅ Stream restarted successfully!")
            await ctx.send("🎵 **South Park audio stream is now playing!**\n" +
                          "If you still don't hear anything, try the following:\n" +
                          "1. Leave and rejoin the voice channel\n" +
                          "2. Check your Discord audio settings\n" +
                          "3. Use !leave and then !join to completely reset the connection")
        else:
            await restart_msg.edit(content="❌ Failed to restart stream.")
            await ctx.send("💡 **Troubleshooting Tips:**\n" +
                          "1. Use !leave and then !join to completely reset the connection\n" +
                          "2. Check if FFmpeg is installed correctly\n" +
                          "3. Try a different voice channel")
            
    except Exception as e:
        logger.error(f"Error in restart command: {e}")
        await restart_msg.edit(content=f"❌ An error occurred while restarting: {str(e)[:100]}...")
        await ctx.send("💡 **Error Details:**\n" +
                      f"```{str(e)}```\n" +
                      "Please try using !leave and then !join to completely reset the connection.")

@bot.event
async def on_voice_state_update(member, before, after):
    # If the bot was disconnected from a voice channel
    if member.id == bot.user.id and before.channel and not after.channel:
        logger.info("Bot was disconnected from voice channel")
        # Clean up resources
        await stream_bot.stop_streaming()
        stream_bot.voice_client = None
        stream_bot.current_channel = None
    
    # If the bot is alone in the channel, leave
    elif stream_bot.current_channel and member.id != bot.user.id:
        if before.channel == stream_bot.current_channel:
            # Someone left the channel, check if we're alone
            members = stream_bot.current_channel.members
            if len([m for m in members if not m.bot]) == 0:
                logger.info("No users left in voice channel, leaving...")
                await stream_bot.cleanup()

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
        print("🚀 Starting Direct Stream South Park Bot...")
        print(f"📺 Stream URL: {STREAM_URL}")
        print(f"🎮 Command prefix: {COMMAND_PREFIX}")
        print(f"🔧 Max connection attempts: {stream_bot.max_connection_attempts}")
        print("-" * 50)
        print("This bot streams South Park directly in Discord voice channels!")
        print(f"Type {COMMAND_PREFIX}join in Discord to start streaming.")
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