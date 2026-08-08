import subprocess
from pathlib import Path
from typing import Protocol


class ProcessAdapter(Protocol):
    def start(self, command: list[str], working_directory: Path) -> None: ...

    def stop(self, process_name: str) -> None: ...


class WindowsProcessAdapter:
    def start(self, command: list[str], working_directory: Path) -> None:
        subprocess.Popen(command, cwd=str(working_directory), shell=False)

    def stop(self, process_name: str) -> None:
        subprocess.run(
            ["taskkill", "/IM", process_name, "/T", "/F"],
            shell=False,
            check=False,
            capture_output=True,
            text=True,
        )
