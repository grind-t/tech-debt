from collections.abc import Collection, Sequence
from pathlib import PurePath


def validate_path_distribution(
    paths: Sequence[PurePath],
    distribution: Sequence[Sequence[PurePath]],
    parallelism: int,
    files: Collection[PurePath],
) -> None:
    """Validate canonical scopes against source roots and their file inventory."""
    errors: list[str] = []
    if len(distribution) != parallelism:
        errors.append("Path distribution must contain exactly parallelism scopes")
    for index, scope in enumerate(distribution):
        if not scope:
            errors.append(f"Search scope {index + 1} is empty")
        for path in scope:
            if not path.is_absolute():
                errors.append(
                    f"Path distribution must contain only absolute paths: {path}"
                )
            elif ".." in path.parts:
                errors.append(f"Search path must be normalized: {path}")
            elif not any(path.is_relative_to(root) for root in paths):
                errors.append(
                    f"Search path is outside the original search area: {path}"
                )

    for index, scope in enumerate(distribution):
        for other in distribution[index + 1 :]:
            for path in scope:
                errors.extend(
                    f"Search scopes overlap: {path} and {other_path}"
                    for other_path in other
                    if path.is_relative_to(other_path)
                    or other_path.is_relative_to(path)
                )

    missing = sorted(
        str(file)
        for file in files
        if not any(
            file.is_relative_to(path) for scope in distribution for path in scope
        )
    )
    if missing:
        errors.append(
            f"Distribution omits {len(missing)} files, "
            f"including: {', '.join(missing[:10])}"
        )
    if errors:
        raise ValueError("\n".join(errors))
