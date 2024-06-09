import logging
import os
from dotenv import load_dotenv
import discord
from line import get_stickers
from song_downloader import download
import json
from utils import *

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    filename='logs.log',
)

load_dotenv()
bot = discord.Bot()
TOKEN = os.getenv('DISCORD_TOKEN')


@bot.slash_command(name="ping", description='Test the reactivity of Ugoku!')
async def ping(ctx):
    latency = round(bot.latency*1000, 2)
    logging.debug(f'Pinged latency: {latency}')
    await ctx.respond(f'あわあわあわわわ! {latency}ms')


@bot.slash_command(
    name='get_stickers',
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
async def get_stickers(
    ctx: discord.ApplicationContext,
    id: str | None = None,
    url: int | None = None,
):
    if not id and not url:
        await ctx.respond(f'Please specify an URL or a sticker pack ID.')
    else:
        await ctx.respond(f'Give me a second!')
        if id:
            url = f'https://store.line.me/stickershop/product/{id}'
        path = get_stickers(url)
        await ctx.send(
            file=discord.File(path),
            content=(f"Sorry for the wait <@{ctx.author.id}>! "
                     "Here's the sticker pack you requested.")
        )


@bot.slash_command(
    name='get_songs',
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
async def get_songs(
    ctx: discord.ApplicationContext,
    url,
    format: str = None,
):
    await ctx.respond(f'Give me a second!')
    limit = get_upload_size_limit(ctx.guild.id)
    try:
        results = download(url, bitrate=format)
        if not results:
            await ctx.respond('Track not found on deezer!')
            return
        path = results['path']
        size = os.path.getsize(path)
        logging.info(f'File size: {size}, Path: {path}')

        if size >= limit:
            if format != 'MP3 320' and format != 'MP3 128':
                format = 'MP3 320'
                await ctx.respond('Track too heavy, trying to download with MP3 320...')
                results = download(url, bitrate=format)
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
    except Exception as e:
        await ctx.respond(f'Oh no! Something went wrong, {e}')


@bot.slash_command(
    name='set_upload_limit',
    description='Change the upload limit (in MB)! It must not exceed server upload size limit. Default: 25MB.',
)
@discord.option(
    'size',
    type=discord.SlashCommandOptionType.integer,
    autocomplete=discord.utils.basic_autocomplete(
        [25, 50, 100]),
)
async def set_upload_limit(ctx: discord.ApplicationContext, size: int):
    # Read json file
    with open('config/settings.json', 'r') as json_file:
        settings = json.load(json_file)

    # Change value
    settings['uploadSizeLimit'][str(ctx.guild.id)] = size

    # Write new data
    with open('config/settings.json', 'w') as json_file:
        json.dump(settings, json_file)

    await ctx.respond(
        f'The upload size limit has been set to {size}MB for this server!'
    )


@ bot.slash_command(name='test', description='A temp command to test things.')
async def test(ctx: discord.ApplicationContext):
    await ctx.respond(f'{ctx.guild.id}, {type(ctx.guild.id)}')


bot.run(TOKEN)
