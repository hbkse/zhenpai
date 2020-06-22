from .twitcasting import *
from ..webserver import app

def setup(bot):
    twitcasting_cog = Twitcasting(bot)
    bot.add_cog(twitcasting_cog)

    app.router.add_post('/twitcasting', twitcasting_cog.broadcast)
