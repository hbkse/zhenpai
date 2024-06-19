import time
import heapq
from collections import OrderedDict

class TTLCache:
    """
    Cache implementation based on OrderedDict that has a max capacity and TTL.
    """
    def __init__(self, capacity: int = 1000, ttl_seconds: int = 86400):
        self.cache = OrderedDict()
        self.expiration_queue = [] # (expiration_time, key)
        self.capacity = capacity
        self.default_ttl_seconds = ttl_seconds

    def _is_key_expired(self, expiration: int):
        return expiration < time.time()

    def _clear_expired(self):
        # while top of queue is expired, pop and del
        while self.expiration_queue and self._is_key_expired(self.expiration_queue[0][0]):
            del self.cache[self.expiration_queue[0][1]]
            heapq.heappop(self.expiration_queue)

    def __contains__(self, key):
        self._clear_expired()
        return key in self.cache
    
    def __getitem__(self, key):
        self._clear_expired()
        if key in self.cache:
            return self.cache[key][0]
        return None

    def __setitem__(self, key, value):
        self._clear_expired()
        if len(self.cache) >= self.capacity:
            # raise exception instead?
            return False

        ttl = time.time() + self.default_ttl_seconds
        self.cache[key] = value
        heapq.heappush(self.expiration_queue, (ttl, key))
        return True