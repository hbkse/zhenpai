from .voice_logging import VoiceLogging

async def setup(bot):
    await bot.add_cog(VoiceLogging(bot))