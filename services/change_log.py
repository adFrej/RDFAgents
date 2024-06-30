from collections import defaultdict
import time


class ChangeLog:
    state = []
    last_read = time.time()

    @classmethod
    def log(cls, key: str, change: any) -> None:
        cls.state.append([key, *change])

    @classmethod
    def read(cls) -> list[any]:
        previous_read = cls.last_read
        cls.last_read = time.time()
        values = cls.state
        cls.state = []
        return values, cls.last_read-previous_read