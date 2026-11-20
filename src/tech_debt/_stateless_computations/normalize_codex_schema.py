from copy import deepcopy

from pydantic.json_schema import JsonSchemaValue


def normalize_codex_schema(schema: JsonSchemaValue) -> JsonSchemaValue:
    """Make object fields required and closed without changing the input schema."""
    normalized = deepcopy(schema)
    normalized.pop("default", None)

    for keyword in (
        "properties",
        "$defs",
        "definitions",
        "patternProperties",
        "dependentSchemas",
    ):
        children = normalized.get(keyword)
        if isinstance(children, dict):
            for name, child in children.items():
                if isinstance(child, dict):
                    children[name] = normalize_codex_schema(child)

    for keyword in (
        "items",
        "additionalProperties",
        "contains",
        "not",
        "if",
        "then",
        "else",
        "propertyNames",
        "unevaluatedProperties",
    ):
        child = normalized.get(keyword)
        if isinstance(child, dict):
            normalized[keyword] = normalize_codex_schema(child)

    for keyword in ("anyOf", "allOf", "oneOf", "prefixItems"):
        children = normalized.get(keyword)
        if isinstance(children, list):
            normalized[keyword] = [
                normalize_codex_schema(child) if isinstance(child, dict) else child
                for child in children
            ]

    schema_type = normalized.get("type")
    if (
        schema_type == "object"
        or (isinstance(schema_type, list) and "object" in schema_type)
        or "properties" in normalized
    ):
        normalized["additionalProperties"] = False
        normalized["required"] = list(normalized.get("properties", {}))
    return normalized
