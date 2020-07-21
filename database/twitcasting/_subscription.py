from .subscription import Subscription
from .twitcast_user import TwitcastUser
from ..core.user import User
from ..core.channel import Channel
from ..core.guild import Guild
from typing import List


class _DatabaseSubscriptions:
    def get_sub(self, user_id: int, channel_id: int, twitcast_user_id: str) -> Subscription:
        """
        Retrieves a subscription associated with a Discord user, Discord text channel and Twitcast user ID.
        :param user_id: the id the of the Discord user.
        :param channel_id: the id of the text channel.
        :param twitcast_user_id: the ID of the Twitcast user.
        :return: a Subscription object that the Discord user created to listen for notifications from the Twitcast
        user on the Discord text channel
        """
        return self.session.query(Subscription) \
            .filter(Subscription.user_id == user_id) \
            .filter(Subscription.channel_id == channel_id) \
            .filter(Subscription.twitcast_user_id == twitcast_user_id) \
            .first()

    def get_subs_by_twitcast_user_id(self, twitcast_user_id: str) -> List[Subscription]:
        """
        Retrieves a subscription associated with a Discord user, Discord text channel and Twitcast user ID.
        :param user_id: the id the of the Discord user.
        :param channel_id: the id of the text channel.
        :param twitcast_user_id: the ID of the Twitcast user.
        :return: a Subscription object that the Discord user created to listen for notifications from the Twitcast
        user on the Discord text channel
        """
        return self.session.query(Subscription) \
            .filter(Subscription.twitcast_user_id == twitcast_user_id) \
            .all()

    def delete_sub(self, sub: Subscription):
        """
        Adds a subscription from a text channel.
        :param sub: the subscription to add to the database.
        :return:
        """
        self.session.delete(sub)

    def delete_subs_by_user_and_guild(self, user_id: str, guild_id: str):
        """
        Removes a subscription to the provided Twitcast user from a Discord text channel.
        :param channel_id: the ID of the Discord text channel
        :param twitcast_user_id: the ID of the Twitcasting user.
        :return:
        """
        self.session.query(Subscription)\
            .filter(Subscription.user_id == user_id)\
            .filter(Subscription.guild_id == guild_id)\
            .delete()

    def add_sub(self, sub: Subscription):
        """
        Adds a subscription to a text channel.
        :param sub: the subscription to add to the database.
        :return:
        """
        self.session.add(sub)
