from itertools import combinations
from pathlib import PurePath, PurePosixPath

import pytest

from tech_debt._stateless_computations.distribute_paths import distribute_paths


def _assert_valid_distribution(paths, files, parallelism, distribution):
    assert len(distribution) == parallelism
    for scope in distribution:
        assert scope
        for path in scope:
            assert path.is_absolute()
            assert any(path.is_relative_to(root) for root in paths), path

    for scope, other_scope in combinations(distribution, 2):
        for path in scope:
            for other_path in other_scope:
                assert not path.is_relative_to(other_path), (path, other_path)
                assert not other_path.is_relative_to(path), (other_path, path)

    for file in files:
        assert any(
            file.is_relative_to(path) for scope in distribution for path in scope
        ), file


def test_distribute_paths_splits_oversized_folder_into_subfolders():
    root = PurePosixPath("/project")
    api = root / "orders/api"
    domain = root / "orders/domain"
    billing = root / "billing"
    reports = root / "reports"
    files: dict[PurePath, int] = {
        api / "endpoint.py": 8,
        domain / "order.py": 4,
        billing / "adapter.py": 6,
        reports / "report.py": 2,
    }

    distribution = distribute_paths([root], files, 2)

    _assert_valid_distribution([root], files, 2, distribution)
    assert distribution == [[api, reports], [billing, domain]]  # 10 B / 10 B


def test_distribute_paths_keeps_oversized_file_in_one_scope():
    root = PurePosixPath("/project")
    orders = root / "orders"
    billing = root / "billing"
    reports = root / "reports"
    files: dict[PurePath, int] = {
        orders / "order.py": 12,
        billing / "adapter.py": 6,
        reports / "report.py": 2,
    }

    distribution = distribute_paths([root], files, 2)

    _assert_valid_distribution([root], files, 2, distribution)
    assert distribution == [[orders], [billing, reports]]  # 12 B / 8 B


def test_distribute_paths_keeps_folders_whole_with_a_small_imbalance():
    root = PurePosixPath("/project")
    orders, billing, reports = (
        root / name for name in ("orders", "billing", "reports")
    )
    files: dict[PurePath, int] = {
        orders / "service.py": 8,
        orders / "test_service.py": 1,
        billing / "adapter.py": 5,
        reports / "api.py": 3,
        reports / "models.py": 2,
    }

    distribution = distribute_paths([root], files, 2)

    _assert_valid_distribution([root], files, 2, distribution)
    assert distribution == [[orders], [billing, reports]]  # 9 B / 10 B


def test_distribute_paths_assigns_flat_files_to_the_current_lightest_scope():
    root = PurePosixPath("/project")
    eight, seven, six, five, four = (
        root / f"{size}_bytes.py" for size in (8, 7, 6, 5, 4)
    )
    files: dict[PurePath, int] = {eight: 8, seven: 7, six: 6, five: 5, four: 4}

    distribution = distribute_paths([root], files, 2)

    _assert_valid_distribution([root], files, 2, distribution)
    # Both scopes reach 13 B with two files each. The first gets the last 4 B.
    assert distribution == [[eight, five, four], [seven, six]]


def test_distribute_paths_splits_zero_byte_folder_to_fill_three_scopes():
    root = PurePosixPath("/project")
    singleton = root / "a"
    pair = root / "b" / "nested"
    first, second = pair / "first.py", pair / "second.py"
    files: dict[PurePath, int] = {
        singleton / "nested" / "only.py": 0,
        second: 0,
        first: 0,
    }

    distribution = distribute_paths([root], files, 3)

    _assert_valid_distribution([root], files, 3, distribution)
    assert distribution == [[singleton], [first], [second]]


def test_distribute_paths_is_stable_with_overlapping_and_explicit_roots():
    root = PurePosixPath("/project/src")
    module = root / "module" / "main.py"
    readme = root.parent / "README"
    files: dict[PurePath, int] = {readme: 3, module: 3}
    paths = [root, module.parent, module, readme, root]
    expected = [[readme], [root]]

    distribution = distribute_paths(paths, files, 2)

    _assert_valid_distribution(paths, files, 2, distribution)
    assert distribution == expected
    assert distribute_paths(paths[::-1], dict(reversed(files.items())), 2) == expected


def test_distribute_paths_rejects_more_scopes_than_files():
    root = PurePosixPath("/project")
    files: dict[PurePath, int] = {root / "only.py": 42}

    with pytest.raises(ValueError, match="Cannot create 2 non-empty search scopes"):
        distribute_paths([root], files, 2)
