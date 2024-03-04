from .saturday import Saturday

async def setup(bot):
    await bot.add_cog(Saturday(bot))