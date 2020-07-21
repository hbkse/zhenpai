from sqlalchemy import Column, Integer
from sqlalchemy.orm import relationship
from database.database import Base


class Guild(Base):
    __tablename__ = 'guilds'

    guild_id = Column(Integer, primary_key=True)

    subscriptions = relationship("Subscription", back_populates="guild", cascade="all, delete")

    def __init__(self,
                 guild_id: int
    ):
        self.guild_id = guild_id
