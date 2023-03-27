from .codenames import Codenames

async def setup(bot):
    await bot.add_cog(Codenames(bot))