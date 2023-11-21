from .vxtwitter import VxTwitter

async def setup(bot):
    await bot.add_cog(VxTwitter(bot))