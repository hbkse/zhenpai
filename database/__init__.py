from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

from .database import Database

DB = Database()