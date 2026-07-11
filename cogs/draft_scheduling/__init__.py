from .draft_scheduling import DraftScheduling

async def setup(bot):
    await bot.add_cog(DraftScheduling(bot))
