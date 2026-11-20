import pytest

from tech_debt._stateless_effects.normalize_search_paths import normalize_search_paths


def test_normalize_search_paths_resolves_parents_and_symbolic_links(tmp_path):
    source = tmp_path / "src"
    source.mkdir()
    file = source / "module.py"
    file.write_text("", encoding="utf-8")
    alias = tmp_path / "alias"
    alias.symlink_to(source, target_is_directory=True)

    result = normalize_search_paths([alias / "module.py", source / "../src"])

    assert result == [file.resolve(), source.resolve()]


def test_normalize_search_paths_rejects_missing_paths(tmp_path):
    with pytest.raises(FileNotFoundError):
        normalize_search_paths([tmp_path / "missing"])
