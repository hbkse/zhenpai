from .spotify import Spotify

async def setup(bot):
    await bot.add_cog(Spotify(bot))