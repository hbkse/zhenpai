from sqlalchemy import Column, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from database.database import Base


class User(Base):
    __tablename__ = 'users'

    user_id = Column(Integer, primary_key=True)

    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete")

    def __init__(self,
                 user_id: int
    ):
        self.user_id = user_id
