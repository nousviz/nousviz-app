from enum import Enum


class FindingSeverity(str, Enum):
    CRITICAL = "critical"
    INFO = "info"
    WARN = "warn"

    def __str__(self) -> str:
        return str(self.value)
