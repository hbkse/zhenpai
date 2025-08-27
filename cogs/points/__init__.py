from .points import Points

async def setup(bot):
    await bot.add_cog(Points(bot))