from .deletelast import DeleteLast

async def setup(bot):
    await bot.add_cog(DeleteLast(bot))
