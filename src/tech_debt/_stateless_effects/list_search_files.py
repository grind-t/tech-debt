from collections.abc import Sequence
from pathlib import Path, PurePath


def list_search_files(paths: Sequence[PurePath]) -> dict[PurePath, int]:
    """Collect canonical file paths and sizes without following directory symlinks."""
    roots = [Path(path) for path in paths]
    files: dict[PurePath, int] = {}
    for root in roots:
        if root.is_file():
            files[root] = root.stat().st_size
            continue
        for directory, _, names in root.walk(on_error=_raise_walk_error):
            for name in names:
                file = directory / name
                if file.is_file():
                    resolved = file.resolve(strict=True)
                    if resolved not in files and any(
                        resolved.is_relative_to(source) for source in roots
                    ):
                        files[resolved] = resolved.stat().st_size
    return files


def _raise_walk_error(error: OSError) -> None:
    raise error
