from tech_debt._stateless_effects.read_env import read_env
from tech_debt._stateless_workflows.greet import greet as _greet


def greet() -> str:
    """Greet the name from the ``TECH_DEBT_NAME`` environment variable."""
    return _greet(read_env)


__all__ = ["greet"]
