from copy import deepcopy

import pytest
from pydantic import TypeAdapter, ValidationError

from tech_debt._entities.defect import Defect


def _example():
    return {
        "description": "Duplicated totals calculation",
        "location": "src/orders.py",
        "type": "Duplicated Code",
        "characteristic": "Maintainability",
        "subcharacteristic": "Modifiability",
        "risks": {
            "most_likely": {
                "event": "A maintainer changes totals",
                "consequence": "Each change requires repeated edits",
                "likelihood": "High",
                "severity": "Minor",
            },
            "worst_credible": None,
        },
    }


def _schema_nodes(schema):
    yield schema
    for keyword in ("$defs", "properties"):
        for child in schema.get(keyword, {}).values():
            yield from _schema_nodes(child)
    if "items" in schema:
        yield from _schema_nodes(schema["items"])
    for child in schema.get("anyOf", []):
        yield from _schema_nodes(child)


def test_defect_schema_is_ready_for_codex_without_normalization():
    schema = TypeAdapter(list[Defect]).json_schema()

    for node in _schema_nodes(schema):
        assert "default" not in node
        if "$ref" in node:
            assert list(node) == ["$ref"]
        if node.get("type") == "object":
            assert node["additionalProperties"] is False
            assert set(node["required"]) == set(node["properties"])

    fields = schema["$defs"]["Defect"]["properties"]
    assert "Maintainability" in fields["characteristic"]["enum"]
    assert fields["characteristic"]["description"]
    assert fields["characteristic"]["examples"] == ["Maintainability"]
    risks = schema["$defs"]["_DefectRisks"]
    assert risks["description"]
    assert risks["examples"][0]["most_likely"]["likelihood"] == "High"
    assert {"type": "null"} in risks["properties"]["worst_credible"]["anyOf"]


def test_defect_accepts_explicit_null_worst_credible():
    defect = Defect.model_validate(_example())

    assert defect.risks.worst_credible is None


def test_defect_requires_worst_credible():
    example = _example()
    del example["risks"]["worst_credible"]

    with pytest.raises(ValidationError, match="worst_credible"):
        Defect.model_validate(example)


def test_defect_forbids_extra_fields_at_every_object_level(subtests):
    for path in ((), ("risks",), ("risks", "most_likely")):
        with subtests.test(path=path):
            example = deepcopy(_example())
            target = example
            for name in path:
                target = target[name]
            target["unexpected"] = True

            with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
                Defect.model_validate(example)


def test_defect_still_rejects_mismatched_quality_classification():
    example = _example()
    example["characteristic"] = "Security"

    with pytest.raises(ValidationError, match="does not belong"):
        Defect.model_validate(example)
