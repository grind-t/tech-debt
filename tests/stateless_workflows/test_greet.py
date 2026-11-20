from tech_debt._stateless_workflows.greet import greet


def test_greet() -> None:
    assert greet({"TECH_DEBT_NAME": "Alice"}.get) == "Hello, Alice!"


def test_greet_default() -> None:
    assert greet({}.get) == "Hello, World!"
