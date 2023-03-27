from .remindme import RemindMe

async def setup(bot):
    await bot.add_cog(RemindMe(bot))