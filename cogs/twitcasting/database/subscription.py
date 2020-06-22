from sqlalchemy import Column, Integer, String
from .database import Base


class Subscription(Base):
    __tablename__ = 'subscriptions'

    id = Column(Integer, primary_key=True)
    channel_id = Column(String, nullable=False)
    webhook_id = Column(Integer, nullable=False)
    twitcast_user_id = Column(String)
    twitcast_name = Column(String)

    def __init__(self,
                 channel_id,
                 webhook_id,
                 twitcast_user_id,
                 twitcast_name
    ):
        self.channel_id = channel_id
        self.webhook_id = webhook_id
        self.twitcast_user_id = twitcast_user_id
        self.twitcast_name = twitcast_name
