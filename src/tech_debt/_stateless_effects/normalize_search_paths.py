from collections.abc import Sequence
from pathlib import Path, PurePath


def normalize_search_paths(paths: Sequence[PurePath]) -> list[PurePath]:
    """Resolve existing files and directories, including symbolic links."""
    normalized: list[PurePath] = []
    for path in paths:
        resolved = Path(path).resolve(strict=True)
        if not resolved.is_file() and not resolved.is_dir():
            raise ValueError(f"Search path is not a file or directory: {resolved}")
        normalized.append(PurePath(resolved))
    return normalized
