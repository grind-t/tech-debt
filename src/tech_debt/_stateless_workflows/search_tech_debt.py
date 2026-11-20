import asyncio
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Protocol, overload

from pydantic import TypeAdapter

from tech_debt._entities.defect import Defect
from tech_debt._entities.path_distribution import PathDistribution
from tech_debt._entities.tech_debt_search_prompts import (
    DEDUPLICATE_FINDINGS_PROMPT,
    DISTRIBUTE_PATHS_PROMPT,
    FORMAT_FINDINGS_PROMPT,
    RECHECK_FINDINGS_PROMPT,
    SEARCH_TECH_DEBT_PROMPT,
)


class AgentSession(Protocol):
    @overload
    async def next_turn[Response](
        self, prompt: str, schema: TypeAdapter[Response], /
    ) -> Response: ...

    @overload
    async def next_turn(self, prompt: str, schema: None = None, /) -> str: ...


async def search_tech_debt(
    create_session: Callable[[], AgentSession], paths: Sequence[Path], parallelism: int
) -> list[Defect]:
    """Search technical debt using ``parallelism`` concurrent search sessions."""
    if parallelism < 1:
        raise ValueError("parallelism must be greater than zero")
    if parallelism == 1:
        return await _search_tech_debt_session(create_session(), paths)

    distributor = create_session()
    distribution = await distributor.next_turn(
        DISTRIBUTE_PATHS_PROMPT.format(
            paths=", ".join(map(str, paths)), parallelism=parallelism
        ),
        TypeAdapter(PathDistribution),
    )
    if len(distribution) != parallelism:
        raise ValueError("Path distribution must contain exactly parallelism scopes")

    async with asyncio.TaskGroup() as group:
        searches = [
            group.create_task(_search_tech_debt_session(create_session(), scope))
            for scope in distribution
        ]
    defects = [defect for search in searches for defect in search.result()]
    schema = TypeAdapter(list[Defect])
    deduplicator = create_session()
    return await deduplicator.next_turn(
        DEDUPLICATE_FINDINGS_PROMPT.format(
            findings=schema.dump_json(defects).decode("utf-8")
        ),
        schema,
    )


async def _search_tech_debt_session(
    session: AgentSession, paths: Sequence[Path]
) -> list[Defect]:
    await session.next_turn(
        SEARCH_TECH_DEBT_PROMPT.format(paths=", ".join(map(str, paths)))
    )
    schema = TypeAdapter(list[Defect])
    await session.next_turn(FORMAT_FINDINGS_PROMPT, schema)
    return await session.next_turn(RECHECK_FINDINGS_PROMPT, schema)
