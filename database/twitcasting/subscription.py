from sqlalchemy import Column, Integer, String, UniqueConstraint, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class Subscription(Base):
    __tablename__ = 'subscriptions'

    user_id = Column(Integer, ForeignKey('users.user_id'), primary_key=True)
    twitcast_user_id = Column(String, ForeignKey('twitcast_users.twitcast_user_id'), primary_key=True)
    channel_id = Column(Integer, ForeignKey('channels.channel_id'))
    guild_id = Column(Integer, ForeignKey('guilds.guild_id'))\

    user = relationship("User", back_populates="subscriptions")
    twitcast_user = relationship("TwitcastUser", back_populates="subscribers")
    channel = relationship("Channel", back_populates="subscriptions")
    guild = relationship("Guild", back_populates="subscriptions")

    def __init__(self,
                 user_id: int,
                 twitcast_user_id: int,
                 channel_id: int,
                 guild_id: int
    ):
        self.user_id = user_id
        self.twitcast_user_id = twitcast_user_id
        self.channel_id = channel_id
        self.guild_id = guild_id