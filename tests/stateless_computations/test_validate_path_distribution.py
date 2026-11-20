from pathlib import PurePosixPath

import pytest

from tech_debt._stateless_computations.validate_path_distribution import (
    validate_path_distribution,
)


def test_validate_path_distribution_accepts_complete_disjoint_scopes():
    root = PurePosixPath("/project/src")
    files = {root / "a/first.py", root / "b/second.py"}

    validate_path_distribution([root], [[root / "a"], [root / "b"]], 2, files)


def test_validate_path_distribution_accepts_multiple_source_roots_and_files():
    source = PurePosixPath("/project/src")
    readme = PurePosixPath("/project/README.md")
    files = {source / "first.py", readme}

    validate_path_distribution([source, readme], [[source], [readme]], 2, files)


def test_validate_path_distribution_rejects_invalid_scopes(subtests):
    root = PurePosixPath("/project/src")
    files = {root / "a/first.py", root / "b/second.py"}
    cases = {
        "wrong_count": ([[root]], "exactly parallelism scopes"),
        "empty_scope": ([[], [root]], "is empty"),
        "parent_outside_area": ([[root.parent], [root / "b"]], "outside"),
        "similar_prefix": (
            [[PurePosixPath("/project/src-other")], [root / "b"]],
            "outside",
        ),
        "overlapping_ancestors": ([[root], [root / "a"]], "overlap"),
        "duplicate_scope": ([[root], [root]], "overlap"),
        "missing_file": ([[root / "a"], [root / "empty"]], "omits 1 files"),
    }
    for name, (distribution, message) in cases.items():
        with subtests.test(msg=name), pytest.raises(ValueError, match=message):
            validate_path_distribution([root], distribution, 2, files)
