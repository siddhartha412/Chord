from __future__ import annotations

import asyncio

import discord
from discord.ext import commands


async def _delete_later(message: discord.Message, delay: int) -> None:
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except (discord.Forbidden, discord.NotFound):
        pass


def make_embed(description: str, title: str | None = None) -> discord.Embed:
    return discord.Embed(title=title, description=description)


async def delete_message_by_id(bot: commands.Bot, channel_id: int | None, message_id: int | None) -> None:
    if not channel_id or not message_id:
        return

    channel = bot.get_channel(channel_id)
    if channel is None or not hasattr(channel, "fetch_message"):
        return

    try:
        message = await channel.fetch_message(message_id)  # type: ignore[attr-defined]
    except (discord.NotFound, discord.Forbidden):
        return

    try:
        await message.delete()
    except (discord.NotFound, discord.Forbidden):
        return


def schedule_message_delete(bot: commands.Bot, message: discord.Message | None) -> None:
    if not message:
        return

    if not getattr(bot, "auto_delete_enabled", False):
        return

    delay = int(getattr(bot, "auto_delete_seconds", 0))
    if delay <= 0:
        return

    bot.loop.create_task(_delete_later(message, delay))


def schedule_command_cleanup(ctx: commands.Context, reply_message: discord.Message | None) -> None:
    schedule_message_delete(ctx.bot, reply_message)

    if ctx.interaction is not None:
        return

    if ctx.message is None:
        return

    schedule_message_delete(ctx.bot, ctx.message)


async def reply_and_cleanup(ctx: commands.Context, content: str) -> discord.Message:
    message = await ctx.reply(embed=make_embed(content))
    schedule_command_cleanup(ctx, message)
    return message
