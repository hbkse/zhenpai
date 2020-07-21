from .notifications import Notifications
from ..webserver import app


def setup(bot):
    notifications_cog = Notifications(bot)
    bot.add_cog(notifications_cog)

    app.router.add_post('/twitcasting', notifications_cog.tc_broadcast)
