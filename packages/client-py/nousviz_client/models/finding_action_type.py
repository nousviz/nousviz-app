from enum import Enum


class FindingActionType(str, Enum):
    EXTERNAL = "external"
    MANUAL = "manual"

    def __str__(self) -> str:
        return str(self.value)
