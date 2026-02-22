from __future__ import annotations

from pathlib import Path

from discord.ext import commands

from core.cleanup import reply_and_cleanup


class ReloadCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="reload", description="Reload all cogs")
    async def reload_all(self, ctx: commands.Context) -> None:
        owner_id = getattr(self.bot, "owner_id", None)
        if owner_id is None or ctx.author.id != owner_id:
            await reply_and_cleanup(ctx, "You are not allowed to use this command.")
            return

        loaded = set(self.bot.extensions.keys())
        reloaded: list[str] = []
        loaded_new: list[str] = []
        failed: list[str] = []

        for file in Path("cogs").rglob("*.py"):
            if file.name.startswith("_"):
                continue
            ext = ".".join(file.with_suffix("").parts)
            try:
                if ext in loaded:
                    await self.bot.reload_extension(ext)
                    reloaded.append(ext)
                else:
                    await self.bot.load_extension(ext)
                    loaded_new.append(ext)
            except Exception as exc:
                failed.append(f"{ext}: {exc}")

        try:
            await self.bot.tree.sync()
        except Exception as exc:
            failed.append(f"tree.sync: {exc}")

        message = [
            f"Reloaded: {len(reloaded)}",
            f"Loaded: {len(loaded_new)}",
            f"Failed: {len(failed)}",
        ]
        if failed:
            message.append("Errors:")
            message.extend(failed[:10])

        await reply_and_cleanup(ctx, "\n".join(message))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ReloadCog(bot))
