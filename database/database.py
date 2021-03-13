from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
import os

from . import Base
from . import constants
from database.tagging._tags import _DatabaseTags
from database.twitcasting._subscription import _DatabaseSubscriptions
from ..cogs.reminders.schemas._reminders import _DatabaseReminders


class Database(_DatabaseTags, _DatabaseSubscriptions, _DatabaseReminders):
    def __init__(self):
        if not os.path.exists(constants.DB_FOLDER_NAME):
            os.makedirs(constants.DB_FOLDER_NAME)

        self.engine = create_engine(f'sqlite:///{constants.DB_PATH}')

        self.SessionFactory = sessionmaker(bind=self.engine)
        self.session = self.SessionFactory()

        Base.metadata.create_all(self.engine)

        self.commit()

    def commit(self):
        """
        Commits any queued changes to the database.
        :return:
        """
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise

    def close(self):
        """
        Closes the engine.
        :return:
        """
        self.engine.dispose()
