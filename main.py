import logging
import os
from discord.ui.item import Item
from dotenv import load_dotenv
import discord
from line import get_stickerpack
from song_downloader import *
from settings import *
from fetch_arls import *
from timer import Timer


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)


load_dotenv()
bot = discord.Bot()
TOKEN = os.getenv('DISCORD_TOKEN')
ARL = os.getenv('DEEZER_ARL')


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
    loop=0,
):
    timer = Timer()

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
        await ctx.edit(content=f'Done ! {timer.round()}')


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
    timer = Timer()

    await ctx.respond(f'Give me a second!')
    arl = get_setting(
        ctx.author.id,
        'publicArl',
        ARL
    )

    if not format:
        format = get_setting(
            ctx.user.id,
            'defaultMusicFormat',
            'MP3 320'
        )
    try:
        downloadObjects, links, format_ = init_dl(
            url=url,
            guild_id=ctx.guild_id,
            arl=arl,
            brfm=format
        )
        if not downloadObjects:
            raise TrackNotFound

        await ctx.edit(
            content=f'Download objects got, {timer.round()}. '
            'Fetching track data...'
        )
        results = await download(
            downloadObjects,
            links,
            format_,
            arl=arl,
            ctx=ctx,
            guild_id=ctx.guild_id,
            timer=timer,
        )
        path = results['path']

        size = os.path.getsize(path)
        ext = os.path.splitext(path)[1][1:]
        # To check if the Deezer account is paid (?)
        if 'zip' != ext and ext not in format.lower():
            raise InvalidARL

        logging.info(f'Chosen format: {format}')
        logging.info(f'File size: {size}, Path: {path}')

        if size >= ctx.guild.filesize_limit:
            if format != 'MP3 320' and format != 'MP3 128':

                await ctx.edit(
                    content='Track too heavy, trying '
                            'to download with MP3 320...'
                )
                downloadObjects, links, format_ = init_dl(
                    url=url,
                    guild_id=ctx.guild_id,
                    arl=arl,
                    brfm='mp3 320'
                )
                results = await download(
                    downloadObjects,
                    links,
                    format_,
                    arl=arl,
                    ctx=ctx,
                    guild_id=ctx.guild_id,
                    timer=timer,
                )

                path = results['path']
                size = os.path.getsize(path)
                logging.info(f'File size: {size}, Path: {path}')
                if size >= ctx.guild.filesize_limit:
                    await ctx.edit(content='Track too heavy ￣へ￣')
                    return
            else:
                await ctx.edit(content='Track too heavy ￣へ￣')
                return
        # SUCESS:
        await ctx.edit(content=f'Download finished, {timer.round()}. Uploading...')
        await ctx.send(
            file=discord.File(path),
            content=(f"Sorry for the wait <@{ctx.author.id}>! "
                     "Here's the song(s) you requested. Enjoy (￣︶￣*))")
        )
        await ctx.edit(content=f'Done ! {timer.round()}')

    except InvalidARL:
        await ctx.edit(content='The Deezer ARL is not valid. '
                       'Please contact the developer or use a custom ARL.')
    except FileNotFoundError:
        await ctx.edit(content='The Deezer ARL is not valid. '
                       'Please contact the developer or use a custom ARL.')
    except TrackNotFound:
        await ctx.edit(content='Track not found on Deezer!')


set = bot.create_group("set", "Change bot settings")


@set.command(
    name='default-music-format',
    description='Change your default music format.',
)
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
        await change_settings(ctx.author.id, 'defaultMusicFormat', format)
        await ctx.respond(f'Your default music format has been set to {format}!')


select = generate_select()


class ArlCountries(discord.ui.View):
    def __init__(
        self,
        *items: Item,
        timeout: float | None = 180,
        disable_on_timeout: bool = False,
        author_id: int
    ):
        super().__init__(*items, timeout=timeout, disable_on_timeout=disable_on_timeout)
        self.author_id = author_id

    @discord.ui.select(
        placeholder="Choose a country!",
        min_values=1,
        max_values=1,
        options=select,
    )
    # the function called when the user is done selecting options
    async def select_callback(self, select, interaction):
        arl = get_arl(select.values[0])
        await change_settings(self.author_id, 'publicArl', arl)
        await interaction.response.send_message(
            f'You are now using a Deezer ARL from {select.values[0]}!'
        )


@set.command(
    name='custom-arl',
    description='Change your Deezer localization!'
)
async def custom_arl(ctx: discord.ApplicationContext):
    await ctx.respond("Select a country.", view=ArlCountries(author_id=ctx.author.id))


@set.command(
    name='default-arl',
    description='Change your Deezer localization!'
)
async def custom_arl(ctx: discord.ApplicationContext):
    await change_settings(ctx.author.id, 'publicArl', ARL)
    await ctx.respond("You are now using the default ARL!")

bot.run(TOKEN)
