from sqlalchemy import Column, Integer, String
from database import Base


class RemindersTable(Base):
    __tablename__ = 'reminders'

    id = Column(Integer, primary_key=True)
    channel_id = Column(String, nullable=False)
    guild_id = Column(String, nullable=False)
    invoker_id = Column(String, nullable=False)
    time = # time stamp
    message = Column(String) # blob? 
    repeat_count = Column(Integer) 
    repeat_interval = # time span

    def __init__(self,
                 channel_id,
                 guild_id,
                 invoker_id,
                 time,
                 message,
                 repeat_count,
                 repeat_inverval
    ):
        self.channel_id = channel_id
        self.guild_id = guild_id
        self.invoker_id = invoker_id
        self.time = time
        self.message = message
        self.repeat_count = repeat_count
        self.repeat_interval = repeat_interval
