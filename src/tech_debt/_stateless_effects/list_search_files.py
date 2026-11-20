from collections.abc import Sequence
from pathlib import Path, PurePath


def list_search_files(paths: Sequence[PurePath]) -> frozenset[PurePath]:
    """List files under canonical roots without following directory symlinks."""
    roots = [Path(path) for path in paths]
    files: set[PurePath] = set()
    for root in roots:
        if root.is_file():
            files.add(root)
            continue
        for directory, _, names in root.walk(on_error=_raise_walk_error):
            for name in names:
                file = directory / name
                if file.is_file():
                    resolved = file.resolve(strict=True)
                    if any(resolved.is_relative_to(source) for source in roots):
                        files.add(resolved)
    return frozenset(files)


def _raise_walk_error(error: OSError) -> None:
    raise error
