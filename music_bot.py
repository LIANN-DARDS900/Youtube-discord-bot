import discord
from discord.ext import commands
import youtube_dl
import asyncio

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

@bot.command(name='play')
async def play(ctx, *, search: str):
    async with ctx.typing():
        info = ytdl.extract_info(f"ytsearch5:{search}", download=False)
        entries = info['entries']
        search_results = [entry['title'] for entry in entries]
        
        if not search_results:
            await ctx.send("No results found.")
            return

        await ctx.send("\n".join([f"{i+1}. {entry['title']}" for i, entry in enumerate(search_results)]))
        
        def check(m):
            return m.author == ctx.author and m.content.isdigit() and 1 <= int(m.content) <= 5

        try:
            msg = await bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await ctx.send('You took too long to respond.')
            return

        choice = int(msg.content) - 1
        url = entries[choice]['webpage_url']

        player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
        ctx.voice_client.stop()
        ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
        await ctx.send(f'Now playing: {player.title}')

@bot.command(name='pause')
async def pause(ctx):
    ctx.voice_client.pause()
    await ctx.send("Paused the music.")

@bot.command(name='resume')
async def resume(ctx):
    ctx.voice_client.resume()
    await ctx.send("Resumed the music.")

@bot.command(name='stop')
async def stop(ctx):
    ctx.voice_client.stop()
    await ctx.send("Stopped the music.")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} - {bot.user.id}')

bot.run('YOUR_BOT_TOKEN')
