from .users import Users

async def setup(bot):
    await bot.add_cog(Users(bot))