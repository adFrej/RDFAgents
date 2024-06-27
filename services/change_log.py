from collections import defaultdict


class ChangeLog:
    state = defaultdict(list)

    @classmethod
    def log(cls, key: str, change: any) -> None:
        cls.state[key].append(change)

    @classmethod
    def read(cls, key: str) -> list[any]:
        values = cls.state[key]
        cls.state[key] = []
        return values