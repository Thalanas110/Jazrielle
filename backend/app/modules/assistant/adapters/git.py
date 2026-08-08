import subprocess
from pathlib import Path
from typing import Protocol


class GitAdapter(Protocol):
    def status(self, repository: Path) -> str: ...


class LocalGitAdapter:
    def status(self, repository: Path) -> str:
        result = subprocess.run(
            ["git", "-C", str(repository), "status", "--short", "--branch"],
            shell=False,
            check=False,
            capture_output=True,
            text=True,
        )
        return (result.stdout or result.stderr).strip()
