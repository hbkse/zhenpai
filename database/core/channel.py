from sqlalchemy import Column, Integer
from sqlalchemy.orm import relationship
from database.database import Base


class Channel(Base):
    __tablename__ = 'channels'

    channel_id = Column(Integer, primary_key=True)

    subscriptions = relationship("Subscription", back_populates="channel", cascade="all, delete")

    def __init__(self,
                 channel_id: int
    ):
        self.channel_id = channel_id
