from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
import os

from . import Base
from . import constants
from database.core._user import _DatabaseUsers
from database.core._channel import _DatabaseChannels
from database.core._guild import _DatabaseGuilds
from database.tagging._tag import _DatabaseTags
from database.twitcasting._subscription import _DatabaseSubscriptions
from database.twitcasting._twitcast_user import _DatabaseTwitcastUsers


class Database(_DatabaseUsers, _DatabaseChannels,
               _DatabaseGuilds, _DatabaseTags,
               _DatabaseSubscriptions, _DatabaseTwitcastUsers):
    def __init__(self):
        if not os.path.exists(constants.DB_FOLDER_NAME):
            os.makedirs(constants.DB_FOLDER_NAME)

        self.engine = create_engine(f'sqlite:///{constants.DB_PATH}')

        def _fk_pragma_on_connect(dbapi_con, con_record):
            dbapi_con.execute('pragma foreign_keys=ON')

        event.listen(self.engine, 'connect', _fk_pragma_on_connect)

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
