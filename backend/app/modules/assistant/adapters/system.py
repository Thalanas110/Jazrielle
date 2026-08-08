from datetime import datetime
import platform
from typing import Protocol


class SystemAdapter(Protocol):
    def get_time(self) -> str: ...

    def get_date(self) -> str: ...

    def get_system_status(self) -> str: ...


class LocalSystemAdapter:
    def get_time(self) -> str:
        return _format_time(datetime.now().astimezone())

    def get_date(self) -> str:
        value = datetime.now().astimezone()
        return f"{value:%A, %B} {value.day}, {value.year}"

    def get_system_status(self) -> str:
        return f"{platform.system()} {platform.release()} on {platform.node()}"


def _format_time(value: datetime) -> str:
    return value.strftime("%I:%M %p").lstrip("0")
