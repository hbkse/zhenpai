from .spotify import Spotify


def setup(bot):
    bot.add_cog(Spotify(bot))
