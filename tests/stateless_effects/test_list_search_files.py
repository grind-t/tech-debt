from tech_debt._stateless_effects.list_search_files import list_search_files


def test_list_search_files_handles_links_and_cycles_inside_search_roots(tmp_path):
    root = tmp_path / "src"
    nested = root / "nested"
    nested.mkdir(parents=True)
    first, second = root / "first.py", nested / "second.py"
    first.write_text("", encoding="utf-8")
    second.write_text("", encoding="utf-8")
    (root / "alias").symlink_to(nested, target_is_directory=True)
    (nested / "cycle").symlink_to(root, target_is_directory=True)
    outside = tmp_path / "outside.py"
    outside.write_text("", encoding="utf-8")
    (root / "outside").symlink_to(outside)

    result = list_search_files([root, nested])

    assert result == {first.resolve(), second.resolve()}


def test_list_search_files_accepts_explicit_files(tmp_path):
    file = tmp_path / "module.py"
    file.write_text("", encoding="utf-8")

    assert list_search_files([file]) == {file.resolve()}
