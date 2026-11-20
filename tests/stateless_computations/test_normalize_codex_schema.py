from copy import deepcopy

from pydantic import TypeAdapter

from tech_debt._entities.defect import Defect
from tech_debt._stateless_computations.normalize_codex_schema import (
    normalize_codex_schema,
)


def test_normalize_codex_schema_handles_nested_objects_and_preserves_metadata():
    schema = {
        "type": "object",
        "properties": {
            "risks": {
                "type": "array",
                "items": {"$ref": "#/$defs/Risk"},
            },
        },
        "$defs": {
            "Risk": {
                "type": "object",
                "properties": {
                    "event": {"type": "string", "description": "A real event"},
                    "consequence": {
                        "anyOf": [
                            {
                                "type": "object",
                                "properties": {
                                    "severity": {"enum": ["Major", "Minor"]}
                                },
                            },
                            {"type": "null"},
                        ],
                        "default": None,
                    },
                },
                "required": ["event"],
                "examples": [{"event": "Something happens", "default": "Keep this"}],
            }
        },
    }
    original = deepcopy(schema)

    result = normalize_codex_schema(schema)

    assert schema == original
    assert result["required"] == ["risks"]
    assert result["additionalProperties"] is False
    assert result["properties"]["risks"]["items"] == {"$ref": "#/$defs/Risk"}
    risk = result["$defs"]["Risk"]
    assert risk["required"] == ["event", "consequence"]
    assert risk["additionalProperties"] is False
    assert risk["properties"]["event"] == schema["$defs"]["Risk"]["properties"]["event"]
    assert risk["examples"] == schema["$defs"]["Risk"]["examples"]
    consequence = risk["properties"]["consequence"]
    assert "default" not in consequence
    assert consequence["anyOf"][0]["required"] == ["severity"]
    assert consequence["anyOf"][0]["additionalProperties"] is False
    assert consequence["anyOf"][0]["properties"]["severity"]["enum"] == [
        "Major",
        "Minor",
    ]
    assert consequence["anyOf"][1] == {"type": "null"}


def test_normalize_codex_schema_makes_worst_credible_required_but_nullable():
    adapter = TypeAdapter(list[Defect])
    original = adapter.json_schema()

    result = normalize_codex_schema(original)

    for name in ("Defect", "_Risk", "_DefectRisks"):
        definition = result["$defs"][name]
        assert definition["additionalProperties"] is False
        assert definition["required"] == list(definition["properties"])
    risks = result["$defs"]["_DefectRisks"]
    assert {"type": "null"} in risks["properties"]["worst_credible"]["anyOf"]
    assert "default" not in risks["properties"]["worst_credible"]
    assert "worst_credible" not in original["$defs"]["_DefectRisks"]["required"]

    properties = original["$defs"]["Defect"]["properties"]
    example = {name: field["examples"][0] for name, field in properties.items()}
    example["risks"]["worst_credible"] = None
    defects = adapter.validate_python([example])
    assert defects[0].risks.worst_credible is None
