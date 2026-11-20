from pathlib import PurePath

from pydantic import TypeAdapter

from tech_debt._entities.path_distribution import PathDistribution


def test_path_distribution_schema_uses_plain_strings_and_preserves_metadata():
    schema = TypeAdapter(PathDistribution).json_schema()

    assert schema["type"] == "array"
    assert schema["items"]["items"] == {"type": "string"}
    assert schema["description"]
    assert schema["examples"]


def test_path_distribution_still_parses_json_paths():
    paths = TypeAdapter(PathDistribution).validate_json('[["src/a"], ["src/b"]]')

    assert paths == [[PurePath("src/a")], [PurePath("src/b")]]
