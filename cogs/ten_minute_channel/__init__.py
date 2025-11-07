from .ten_minute_channel import TenMinuteChannel

async def setup(bot):
    await bot.add_cog(TenMinuteChannel(bot))
