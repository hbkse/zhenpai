from .subscription import Subscription
from typing import List


class _DatabaseSubscriptions:
    def get_sub(self, channel_id: str, webhook_id: str, twitcast_user_id: str) -> Subscription:
        """
        Retrieves a subscription from the database filtered by the provided parameters.
        :param channel_id: the ID of the Discord text channel the subscription belongs to
        :param webhook_id: the ID of the webhook the subscription belongs to.
        :param twitcast_user_id: the ID of the Twitcast user whose live events will post to the webhook.
        :return: a single Subscription record.
        """
        return self.session.query(Subscription)\
            .filter(Subscription.channel_id == channel_id)\
            .filter(Subscription.webhook_id == webhook_id)\
            .filter(Subscription.twitcast_user_id == twitcast_user_id)\
            .first()

    def get_subs_by_channel(self, channel_id: str) -> List[Subscription]:
        """
        Retrieves all subscriptions associated with a Discord text channel.
        :param channel_id: the ID of the Discord text channel.
        :return: list of Subscription records associated with a Discord text channel.
        """
        return self.session.query(Subscription)\
            .filter(Subscription.channel_id == channel_id)\
            .all()

    def get_subs_by_user_id(self, twitcast_user_id: str) -> List[Subscription]:
        """
        Retrieves all subscriptions to a particular Twitcasting user.
        :param twitcast_user_id: the ID of the Twitcasting user.
        :return: list of Subscriptions records associated with a Twitcasting user.
        """
        return self.session.query(Subscription)\
            .filter(Subscription.twitcast_user_id == twitcast_user_id)\
            .all()

    def count_subs_by_user_id(self, twitcast_user_id: str) -> int:
        """
        Counts the number of text channels that have subscribed to a Twitcasting user.
        :param twitcast_user_id: the ID of the Twitcasting user.
        :return: the number of subscribed text channels.
        """
        return self.session.query(Subscription) \
            .filter(Subscription.twitcast_user_id == twitcast_user_id) \
            .count()

    def remove_sub_from_channel_by_user_id(self, channel_id: str, twitcast_user_id: str):
        """
        Removes a subscription to the provided Twitcast user from a Discord text channel.
        :param channel_id: the ID of the Discord text channel
        :param twitcast_user_id: the ID of the Twitcasting user.
        :return:
        """
        self.session.query(Subscription)\
            .filter(Subscription.channel_id == channel_id)\
            .filter(Subscription.twitcast_user_id == twitcast_user_id)\
            .delete()

    def remove_all_subs_from_channel(self, channel_id: str):
        """
        Removes all subscriptions from a Discord text channel.
        :param channel_id: the ID of the text channel.
        :return:
        """
        self.session.query(Subscription)\
            .filter(Subscription.channel_id == channel_id)\
            .delete()

    def add_sub(self, sub: Subscription):
        """
        Adds a subscription to a text channel.
        :param sub: the subscription to add to the database.
        :return:
        """
        self.session.add(sub)

    def update_name_of_twitcast_user(self, twitcast_user_id: str, twitcast_name: str):
        """
        Updates the name of a Twitcasting user in the database.
        :param twitcast_user_id: the ID of the user whose names will be updated.
        :param twitcast_name: the name of the Twitcasting user.
        :return:
        """
        for sub in self.get_subs_by_user_id(twitcast_user_id):
            sub.twitcast_name = twitcast_name

    def update_webhook_id_of_channel(self, channel_id: str, webhook_id: str):
        """
        Updates the webhook ID of a channel. Used when subscriptions are reassigned to another webhook.
        :param channel_id: the ID of a text channel.
        :param webhook_id: the ID of the updated webhook.
        :return:
        """
        for sub in self.get_subs_by_channel(channel_id):
            sub.webhook_id = webhook_id
