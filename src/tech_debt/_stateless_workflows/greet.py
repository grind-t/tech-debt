from collections.abc import Callable

from tech_debt._stateless_computations.format_greeting import format_greeting


def greet(read_env: Callable[[str], str | None]) -> str:
    """Greet the name from the ``TECH_DEBT_NAME`` variable returned by ``read_env``."""
    name = read_env("TECH_DEBT_NAME")
    return format_greeting("World" if name is None else name)
