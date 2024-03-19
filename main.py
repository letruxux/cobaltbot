import discord
import json
import logging
import aiohttp
from dotenv import load_dotenv
from discord.ext import commands
from discord import Color as c
from os import environ
from markdownify import markdownify

load_dotenv()
PUBLIC_SITE_FRIENDLY_URL = "cobalt.tools"
PUBLIC_SITE_URL = "https://cobalt.tools"

intents = discord.Intents.default()
intents.message_content = True

log = logging.getLogger("")


class Bot(commands.AutoShardedBot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix=commands.when_mentioned_or("."),
            intents=intents,
            activity=discord.Game(f". | {PUBLIC_SITE_FRIENDLY_URL}"),
            help_command=None,
        )

    async def setup_hook(self) -> None:
        self.session = aiohttp.ClientSession()
        return await super().setup_hook()

    async def close(self):
        await self.session.close()
        await super().close()


class DownloadView(discord.ui.View):
    def __init__(self, url: str, timeout: float | None = 20):
        super().__init__(timeout=timeout)
        self.add_item(discord.ui.Button(label="download", url=url))

    async def expire(self, message: discord.Message):
        await self.wait()
        self.clear_items()
        self.add_item(
            discord.ui.Button(
                label="expired", url="https://cobalt.tools/", disabled=True
            )
        )
        await message.edit(view=self)


bot = Bot()


async def handle_cmd(ctx: commands.Context, url: str, audio: bool):
    resp = await get_video(url, audio=audio)
    data = await resp.json()
    if data.get("status") == "success":
        url = data.get("url")
        view = DownloadView(url)

        message = await ctx.reply(view=view)
        log.info(f"{ctx.author} downloaded {url}")
        await view.expire(message)
    else:
        await ctx.reply(
            f"{markdownify(data.get('text', ""), heading_style='ATX')} (`{resp.status}`)"
        )


async def get_video(url, audio: bool = False):
    data = {
        "url": url,
        "isNoTTWatermark": "true",
        "vQuality": "1080",
        "aFormat": "mp3",
        "vCodec": "h264",
        "filenamePattern": "basic",
        "twitterGif": "true",
    }
    if audio:
        data["isAudioOnly"] = "true"

    async with bot.session.post(
        "https://co.wuk.sh/api/json",
        json=data,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36",
        },
    ) as response:
        return response


@bot.command(aliases=["aud"])
async def audio(ctx: commands.Context, url: str):
    await handle_cmd(ctx, url, audio=True)


@bot.command(aliases=["vid"])
async def video(ctx: commands.Context, url: str):
    await handle_cmd(ctx, url, audio=False)


@bot.command()
async def help(ctx: commands.Context):
    embed = discord.Embed(
        title="info and commands.",
        color=c.random(),
        description=f"@{bot.user.name} is an unofficial bot that uses [cobalt]({PUBLIC_SITE_URL})'s api.\nsee the supported services [here](https://github.com/wukko/cobalt#supported-services)",
    )
    embed.add_field(name=".audio [url]", value="download audio from a link.")
    embed.add_field(
        name=".video [url]",
        value="download video from a link. (will return audio if video not available)",
    )
    await ctx.reply(embed=embed)


@video.error
@audio.error
async def handle_exc(ctx: commands.Context, e: commands.CommandError):
    msg = str(e)
    if isinstance(e, json.JSONDecodeError):
        msg = "api returned a captcha, its not your fault. please contact @letruxux about this"

    await ctx.reply(f"there was an error with your command: `{msg}`")

    # for better debugging
    raise e


bot.run(environ["TOKEN"])
