from collections import defaultdict


class ChangeLog:
    state = []

    @classmethod
    def log(cls, key: str, change: any) -> None:
        cls.state.append([key, *change])

    @classmethod
    def read(cls) -> list[any]:
        values = cls.state
        cls.state = []
        return values