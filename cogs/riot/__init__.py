from .riot import Riot

async def setup(bot):
    await bot.add_cog(Riot(bot))
