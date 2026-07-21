import asyncio
from utils.async_utils import queue_task

class MemoryCache:    
    def __init__(self, seconds: int):
        self.__seconds = seconds
        self.__cache2 = {}
        self.__cache = {}
        self.__clear_task = None

    def get(self, key, reset = False):
        value = self.__cache.get(key) or self.__cache2.get(key)
        if value and reset:
            self.__cache[key] = value
        return value

    def set(self, key, value):
        self.__cache[key] = value
        if not self.__clear_task or self.__clear_task.done():
            self.__clear_task = queue_task(self.__clear_limiters())

    def remove(self, key):
        try: self.__cache.pop(key)
        except Exception: pass
        try: self.__cache2.pop(key)
        except Exception: pass

    async def __clear_limiters(self):
        while True:
            try:
                await asyncio.sleep(self.__seconds)
                self.__cache2 = self.__cache
                self.__cache = {}
                if len(self.__cache2) == 0 and len(self.__cache) == 0:
                    self.__clear_task = None
                    return
            except Exception:
                pass