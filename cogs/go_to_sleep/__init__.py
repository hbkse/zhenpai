from .go_to_sleep import GoToSleep

async def setup(bot):
    await bot.add_cog(GoToSleep(bot))