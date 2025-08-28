from .apex import Apex

async def setup(bot):
    await bot.add_cog(Apex(bot))
