from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Protocol, overload

from pydantic import BaseModel

from tech_debt._entities.defect import Defect


class AgentSession(Protocol):
    @overload
    async def next_turn[Response: BaseModel](
        self, prompt: str, schema: type[Response], /
    ) -> Response: ...

    @overload
    async def next_turn(self, prompt: str, schema: None = None, /) -> str: ...


async def search_tech_debt(
    create_session: Callable[[], AgentSession], paths: Sequence[Path], parallelism: int
) -> list[Defect]:
    """Search technical debt using ``parallelism`` concurrent search sessions."""
    return []


async def _search_tech_debt_session(
    session: AgentSession, paths: Sequence[Path]
) -> None:
    pass
