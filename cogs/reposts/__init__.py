from .reposts import Reposts

async def setup(bot):
    await bot.add_cog(Reposts(bot))