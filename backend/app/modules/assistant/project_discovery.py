import os
from collections import Counter
from pathlib import Path


_PRUNED_DIRECTORY_NAMES = {".git", ".worktrees", "node_modules"}


def discover_project_directories(project_root: Path) -> dict[str, Path]:
    root = project_root.resolve()
    candidates: list[tuple[Path, Path]] = []

    for current, directories, _files in os.walk(root, topdown=True):
        current_path = Path(current).resolve()
        directories[:] = sorted(
            name
            for name in directories
            if name not in _PRUNED_DIRECTORY_NAMES and not name.startswith(".")
        )
        marker = current_path / ".git"
        if current_path != root and (marker.is_dir() or marker.is_file()):
            candidates.append((current_path.relative_to(root), current_path))
            directories[:] = []

    candidates.sort(key=lambda item: item[0].as_posix().casefold())
    name_counts = Counter(relative.name.casefold() for relative, _path in candidates)
    discovered: dict[str, Path] = {}
    for relative, path in candidates:
        name = relative.name.casefold()
        identifier = name if name_counts[name] == 1 else relative.as_posix().casefold()
        if not path.is_relative_to(root):
            raise ValueError(f"Discovered project is outside the project root: {path}")
        discovered[identifier] = path
    return discovered
