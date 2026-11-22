from collections import defaultdict
from collections.abc import Mapping, Sequence
from heapq import heapify, heappop, heappush
from pathlib import PurePath


def distribute_paths(
    paths: Sequence[PurePath],
    files: Mapping[PurePath, int],
    parallelism: int,
) -> list[list[PurePath]]:
    """Balance paths by size in up to ``parallelism`` non-empty scopes."""
    if parallelism < 1:
        raise ValueError("parallelism must be greater than zero")
    if not files:
        return []
    parallelism = min(parallelism, len(files))

    roots = set(paths)
    roots = {root for root in roots if roots.isdisjoint(root.parents)}
    sizes: dict[PurePath, int] = defaultdict(int)
    children: dict[PurePath, set[PurePath]] = defaultdict(set)
    for file, size in files.items():
        sizes[file] = size
        child = file
        for parent in file.parents:
            if child in roots:
                break
            sizes[parent] += size
            children[parent].add(child)
            child = parent

    target = (sum(files.values()) + parallelism - 1) // parallelism
    pending = [(-sizes[root], root) for root in roots if root in sizes]
    heapify(pending)
    parts: list[tuple[int, PurePath]] = []
    while pending:
        negative_size, path = heappop(pending)
        if -negative_size > target or len(parts) + len(pending) + 1 < parallelism:
            branch = path
            descendants = children.get(branch, ())
            # A chain with a single file offers no useful split.
            while len(descendants) == 1:
                branch = next(iter(descendants))
                descendants = children.get(branch, ())
            if descendants:
                for child in descendants:
                    heappush(pending, (-sizes[child], child))
                continue
        parts.append((negative_size, path))

    scopes: list[list[PurePath]] = [[] for _ in range(parallelism)]
    loads = [(0, 0, index) for index in range(parallelism)]
    for negative_size, path in sorted(parts):
        size, count, index = heappop(loads)
        scopes[index].append(path)
        heappush(loads, (size - negative_size, count + 1, index))
    return scopes
