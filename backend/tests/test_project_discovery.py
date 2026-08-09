from pathlib import Path

from app.modules.assistant.project_discovery import discover_project_directories


def mark_repository(path: Path, *, git_file: bool = False) -> None:
    path.mkdir(parents=True)
    marker = path / ".git"
    if git_file:
        marker.write_text("gitdir: ../.git/worktrees/demo", encoding="utf-8")
    else:
        marker.mkdir()


def test_discover_project_directories_finds_nested_git_repositories(tmp_path):
    root = tmp_path / "development"
    mark_repository(root / "business" / "alpha")
    mark_repository(root / "personal" / "beta", git_file=True)

    assert discover_project_directories(root) == {
        "alpha": (root / "business" / "alpha").resolve(),
        "beta": (root / "personal" / "beta").resolve(),
    }


def test_discover_project_directories_uses_relative_paths_for_duplicate_names(tmp_path):
    root = tmp_path / "development"
    mark_repository(root / "one" / "shared")
    mark_repository(root / "two" / "shared")

    assert discover_project_directories(root) == {
        "one/shared": (root / "one" / "shared").resolve(),
        "two/shared": (root / "two" / "shared").resolve(),
    }


def test_discover_project_directories_prunes_dependencies_hidden_dirs_and_worktrees(tmp_path):
    root = tmp_path / "development"
    mark_repository(root / "valid")
    mark_repository(root / "valid" / "node_modules" / "dependency")
    mark_repository(root / "valid" / ".worktrees" / "branch")
    mark_repository(root / "valid" / ".metadata" / "hidden")

    assert discover_project_directories(root) == {
        "valid": (root / "valid").resolve(),
    }
