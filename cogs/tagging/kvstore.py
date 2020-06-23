import abc
import logging
import pickle
import redis
from os import path
from typing import Dict
from typing import AnyStr
from typing import List
from typing import Tuple

from . import constants
from . import taggingutils


class TaggingItem(object):
    """
    Thing to be retrieved, can be an image file, a gif, a soundbite, 
    a url with an embed preview, a youtube link, a text document, etc.
    """

    def __init__(self, name: str = None, url: str = None, local_url: str = None, creator_id: int = None):
        self._name = name
        self._url = url
        self._local_url = local_url
        self._creator_id = creator_id

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = value

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, value):
        self._url = value

    @property
    def local_url(self):
        return self._local_url

    @local_url.setter
    def local_url(self, value):
        self._local_url = value

    @property
    def creator_id(self):
        return self._creator_id

    @creator_id.setter
    def creator_id(self, value):
        self._creator_id = value

    def to_dict(self):
        result = {
            key[1:]: getattr(self, key)
            for key in self.__dict__
            if key[0] == '_' and hasattr(self, key)
        }
        return result

    def from_dict(self, data):
        for attr in ('name', 'url', 'local_url', 'creator_id'):
            try:
                value = data[attr]
            except KeyError:
                continue
            else:
                setattr(self, '_' + attr, value)
        return self


class BaseKeyValueStore(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        if (cls is subclass and any("__getitem__" in B.__dict__ for B in subclass.__mro__) and
                any("__setitem__" in B.__dict__ for B in subclass.__mro__) and
                any("__contains__" in B.__dict__ for B in subclass.__mro__)):
            return True
        return NotImplemented

    @abc.abstractmethod
    def __getitem__(self, key: str) -> TaggingItem:
        raise NotImplementedError

    @abc.abstractmethod
    def __setitem__(self, key: str, value: TaggingItem):
        raise NotImplementedError

    @abc.abstractmethod
    def __contains__(self, key: str):
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, key: str) -> TaggingItem:
        raise NotImplementedError

    @abc.abstractmethod
    def put(self, key: str, value: TaggingItem):
        raise NotImplementedError


class DictKeyValueStore(BaseKeyValueStore):
    def __init__(self):
        self.logger = logging.getLogger('zhenpai.tagging')
        self.kvstore: Dict[str, Dict[str, TaggingItem]] = {}  # TODO: load from a pickle file, not sure when we save though
        self.load()

    def __getitem__(self, key: str) -> TaggingItem:
        server_id, tag_name = taggingutils.get_values_from_redis_key(key)
        return self.kvstore[server_id][tag_name]

    def __setitem__(self, key: str, value: TaggingItem):
        server_id, tag_name = taggingutils.get_values_from_redis_key(key)
        if server_id not in self.kvstore:
            self.kvstore[server_id] = {}
        self.kvstore[server_id][tag_name] = value

    def __contains__(self, key: str):
        server_id, tag_name = taggingutils.get_values_from_redis_key(key)
        return tag_name in self.kvstore[server_id]

    def get(self, key: str) -> TaggingItem:
        server_id, tag_name = taggingutils.get_values_from_redis_key(key)
        return self.kvstore[server_id][tag_name]

    def get_paged(self, server_id: str, cursor: int = 0):
        if server_id not in self.kvstore:
            return {}
        return self.kvstore[server_id]

    def put(self, key: str, value: TaggingItem):
        server_id, tag_name = taggingutils.get_values_from_redis_key(key)
        if server_id not in self.kvstore:
            self.kvstore[server_id] = {}
        self.kvstore[server_id][tag_name] = value

    def delete(self, key: str) -> bool:
        server_id, tag_name = taggingutils.get_values_from_redis_key(key)
        try:
            self.kvstore[server_id].pop(tag_name)
        except KeyError:
            return False
        return True

    def load(self):
        try:
            with open(path.join(constants.DB_PATH, constants.DB_FILENAME), 'rb') as handle:
                saved_kvstore = pickle.load(handle)
                self.from_dict(saved_kvstore)
        except (IOError, OSError, EOFError) as e:
            self.logger.warning("Could not load local data. %s", e)

    def save(self):
        try:
            with open(path.join(constants.DB_PATH, constants.DB_FILENAME), 'wb') as handle:
                pickle.dump(self.to_dict(), handle)
        except (IOError, OSError) as e:
            self.logger.error("Could not save current session's tags to disk. %s", e)

    def to_dict(self):
        dict_ = {}
        for server, tags in self.kvstore.items():
            dict_[server] = {}
            for tag_name, v in tags.items():
                dict_[server][tag_name] = v.to_dict()
        return dict_

    def from_dict(self, dict_):
        for server, tags in dict_.items():
            self.kvstore[server] = {}
            for tag_name, v in tags.items():
                self.kvstore[server][tag_name] = TaggingItem().from_dict(v)


class RedisKeyValueStore(BaseKeyValueStore):
    def __init__(self, ip: AnyStr, port: int):
        self.conn = redis.Redis(host=ip, port=port, db=0, charset='utf-8', decode_responses=True)

    def __getitem__(self, key: str) -> TaggingItem:
        values = self.conn.hgetall(key)
        return TaggingItem().from_dict(values)

    def __setitem__(self, key: str, value: TaggingItem):
        self.conn.hset(key, mapping=value.to_dict())

    def __contains__(self, key: str):
        return self.conn.exists(key)

    def get(self, key: str) -> TaggingItem:
        values = self.conn.hgetall(key)
        return TaggingItem().from_dict(values)

    def get_paged(self, server_id: str, count=10, cursor=0) -> Tuple[int, List]:
        return self.conn.scan(cursor=cursor, match="*{0}*".format(server_id), count=count)

    def put(self, key: str, value: TaggingItem):
        self.conn.hset(key, mapping=value.to_dict())

    def delete(self, key: str) -> bool:
        keys_deleted = self.conn.delete(key)
        if keys_deleted > 0:
            return True
        else:
            return False

    def save(self):
        pass
