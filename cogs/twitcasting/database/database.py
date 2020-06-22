from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import logging
from contextlib import contextmanager

Base = declarative_base()

from cogs.twitcasting import constants
from ._subscription import _DatabaseSubscriptions


class TwitcastDatabase(_DatabaseSubscriptions):

    def __init__(self):
        if not os.path.exists(constants.DB_FOLDER_NAME):
            os.makedirs(constants.DB_FOLDER_NAME)

        self.engine = create_engine(f'sqlite:///{constants.DB_PATH}')

        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        Base.metadata.create_all(self.engine)

        self.commit()

    def commit(self):
        """
        Commits any queued changes to the database.
        :return:
        """
        self.session.commit()

    def close(self):
        """
        Closes the engine.
        :return:
        """
        self.engine.dispose()
