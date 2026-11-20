from collections.abc import Sequence
from pathlib import Path, PurePath


def normalize_search_paths(paths: Sequence[PurePath]) -> list[PurePath]:
    """Resolve existing files and directories, including symbolic links."""
    try:
        normalized: list[PurePath] = [
            Path(path).expanduser().resolve(strict=True) for path in paths
        ]
    except OSError as error:
        raise ValueError(f"Cannot resolve search paths: {error}") from error
    return normalized
