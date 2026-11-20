from collections.abc import Sequence
from pathlib import Path, PurePath


def list_search_files(paths: Sequence[PurePath]) -> frozenset[PurePath]:
    """List canonical files, following only links within the supplied search roots."""
    roots = [Path(path).resolve(strict=True) for path in paths]
    pending = list(roots)
    visited: set[Path] = set()
    files: set[PurePath] = set()
    while pending:
        path = pending.pop().resolve(strict=True)
        if not any(path.is_relative_to(root) for root in roots):
            continue
        if path.is_file():
            files.add(PurePath(path))
        elif path.is_dir() and path not in visited:
            visited.add(path)
            pending.extend(path.iterdir())
    return frozenset(files)
