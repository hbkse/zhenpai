from .gotosleep import GoToSleep

async def setup(bot):
    await bot.add_cog(GoToSleep(bot))