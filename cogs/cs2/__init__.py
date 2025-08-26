from .cs2 import CS2

async def setup(bot):
    await bot.add_cog(CS2(bot))
