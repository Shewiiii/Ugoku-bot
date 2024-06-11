import logging
import os
from dotenv import load_dotenv
import discord
from line import get_stickerpack
from song_downloader import *
from settings import *

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

load_dotenv()
bot = discord.Bot()
TOKEN = os.getenv('DISCORD_TOKEN')


@bot.command(name="ping", description='Test the reactivity of Ugoku!')
async def ping(ctx):
    latency = round(bot.latency*1000, 2)
    logging.info(f'Pinged latency: {latency}')
    await ctx.respond(f'あわあわあわわわ! {latency}ms')


get = bot.create_group("get", "Get stuff with Ugoku!")


@get.command(
    name='stickers',
    description='Download a LINE sticker pack from a given URL or a sticker pack ID.',
)
@discord.option(
    'url',
    type=discord.SlashCommandOptionType.string,
    description='URL of a sticker pack from LINE Store.',
)
@discord.option(
    'id',
    type=discord.SlashCommandOptionType.integer,
    description='Sticker pack ID. Can be found in the url.',
)
@discord.option(
    'gif',
    type=discord.SlashCommandOptionType.boolean,
    description=('Convert animated png to gifs, more widely supported. '
                 'Default: True.'),
    autocomplete=discord.utils.basic_autocomplete(
        [True, False]),
)
@discord.option(
    'loop',
    type=discord.SlashCommandOptionType.string,
    description=('Set how many times an animated sticker should be looped. '
                 'Default: forever.'),
    autocomplete=discord.utils.basic_autocomplete(
        ['never', 'forever']),
)
async def stickers(
    ctx: discord.ApplicationContext,
    id: str | None = None,
    url: int | None = None,
    gif: bool = True,
    loop = 0,
):
    if not id and not url:
        await ctx.respond(f'Please specify a URL or a sticker pack ID.')
    else:
        await ctx.respond(f'Give me a second!')
        if id:
            url = f'https://store.line.me/stickershop/product/{id}'
        zip_file = get_stickerpack(url, gif=gif, loop=loop)
        await ctx.send(
            file=discord.File(zip_file),
            content=(f"Sorry for the wait <@{ctx.author.id}>! "
                     "Here's the sticker pack you requested.")
        )


@get.command(
    name='songs',
    description='Download your favorite songs!',
)
@discord.option(
    'url',
    type=discord.SlashCommandOptionType.string,
    description='Spotify/Deezer URL of a song, an album or a playlist. Separate urls with semi-colons.',
)
@discord.option(
    'format',
    type=discord.SlashCommandOptionType.string,
    description='The format of the files you want to save.',
    autocomplete=discord.utils.basic_autocomplete(
        ['FLAC', 'MP3 320', 'MP3 128']),
)
async def songs(
    ctx: discord.ApplicationContext,
    url,
    format: str | None = None,
):
    await ctx.respond(f'Give me a second!')
    limit = get_setting('uploadSizeLimit', ctx.guild_id, 25*10**6)
    if not format:
        format = get_setting('defaultMusicFormat', ctx.guild_id, 'MP3 320')
    try:
        results = download(url, brfm=format)
        path = results['path']

        # To check if the Deezer account is paid
        ext = os.path.splitext(path)[1][1:]
        if 'zip' != ext and ext not in format.lower():
            raise InvalidARL

        size = os.path.getsize(path)
        logging.info(f'Chosen format: {format}')
        logging.info(f'File size: {size}, Path: {path}')

        if size >= limit:
            if format != 'MP3 320' and format != 'MP3 128':

                await ctx.respond(
                    'Track too heavy, trying '
                    'to download with MP3 320...'
                )
                results = download(url, brfm='MP3 320')

                path = results['path']
                size = os.path.getsize(path)
                logging.info(f'File size: {size}, Path: {path}')
                if size >= limit:
                    await ctx.respond('Track too heavy ￣へ￣')
                    return
            else:
                await ctx.respond('Track too heavy ￣へ￣')
                return
        # SUCESS:
        await ctx.send(
            file=discord.File(path),
            content=(f"Sorry for the wait <@{ctx.author.id}>! "
                     "Here's the song(s) you requested. Enjoy (￣︶￣*))")
        )
    except InvalidARL:
        await ctx.respond(f'The deezer ARL is not valid. Please contact de developer.')
    except TrackNotFound:
        await ctx.respond(f'Track not found on Deezer!')


set = bot.create_group("set", "Change bot settings")


@set.command(
    name='upload-limit',
    description='(Admin only) Change upload limit (in MB)! It must not exceed server upload size limit.',
)
@discord.ext.commands.has_permissions(administrator=True)
@discord.option(
    'size',
    type=discord.SlashCommandOptionType.integer,
    autocomplete=discord.utils.basic_autocomplete(
        [25, 50, 100]),
)
async def upload_limit(ctx: discord.ApplicationContext, size: int):
    await change_settings(
        ctx,
        'uploadSizeLimit',
        size*10**6,
        f'The upload size limit has been set to {size}MB!'
    )


@set.command(
    name='default-music-format',
    description='(Admin only) Change default music format.',
)
@discord.ext.commands.has_permissions(administrator=True)
@discord.option(
    'format',
    type=discord.SlashCommandOptionType.string,
    description='The format of the files you want to save.',
    autocomplete=discord.utils.basic_autocomplete(
        ['FLAC', 'MP3 320', 'MP3 128']),
)
async def default_music_format(
    ctx: discord.ApplicationContext,
    format: str
):
    if format not in ['FLAC', 'MP3 320', 'MP3 128']:
        await ctx.respond('Please select a valid format !')
    else:
        await change_settings(
            ctx,
            'defaultMusicFormat',
            format,
            f'Default music format has been set to {format}!'
        )


bot.run(TOKEN)
