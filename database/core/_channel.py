from .channel import Channel


class _DatabaseChannels:
    def get_channel(self, channel_id: int) -> Channel:
        return self.session.query(Channel) \
            .filter(Channel.channel_id == channel_id) \
            .first()

    def get_or_add_channel(self, channel_id: int) -> Channel:
        channel = self.session.query(Channel) \
            .filter(Channel.channel_id == channel_id) \
            .first()
        if not channel:
            channel = Channel(channel_id)
            self.session.add(channel)
        return channel

    def delete_channel(self, channel: Channel):
        self.session.delete(channel)
