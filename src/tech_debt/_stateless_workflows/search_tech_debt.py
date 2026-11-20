import asyncio
from collections.abc import Callable, Sequence
from pathlib import PurePath
from typing import Protocol, overload

from pydantic import TypeAdapter

from tech_debt._entities.defect import Defect
from tech_debt._entities.path_distribution import PathDistribution
from tech_debt._entities.search_tech_debt_prompt import (
    ABSOLUTE_PATHS_PROMPT,
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
    create_session: Callable[[], AgentSession],
    paths: Sequence[PurePath],
    parallelism: int,
) -> list[Defect]:
    """Search technical debt using ``parallelism`` concurrent search sessions."""
    if parallelism < 1:
        raise ValueError("parallelism must be greater than zero")
    if parallelism == 1:
        return await _search_tech_debt_session(create_session(), paths)

    distribution = await _distribute_paths(create_session(), paths, parallelism)

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


async def _distribute_paths(
    session: AgentSession, paths: Sequence[PurePath], parallelism: int
) -> PathDistribution:
    distribution_schema = TypeAdapter(PathDistribution)
    distribution = await session.next_turn(
        DISTRIBUTE_PATHS_PROMPT.format(
            paths=", ".join(map(str, paths)), parallelism=parallelism
        ),
        distribution_schema,
    )
    if any(not path.is_absolute() for scope in distribution for path in scope):
        distribution = await session.next_turn(
            ABSOLUTE_PATHS_PROMPT, distribution_schema
        )
        if any(not path.is_absolute() for scope in distribution for path in scope):
            raise ValueError("Path distribution must contain only absolute paths")
    if len(distribution) != parallelism:
        raise ValueError("Path distribution must contain exactly parallelism scopes")

    return distribution


async def _search_tech_debt_session(
    session: AgentSession, paths: Sequence[PurePath]
) -> list[Defect]:
    await session.next_turn(
        SEARCH_TECH_DEBT_PROMPT.format(paths=", ".join(map(str, paths)))
    )
    schema = TypeAdapter(list[Defect])
    await session.next_turn(FORMAT_FINDINGS_PROMPT, schema)
    return await session.next_turn(RECHECK_FINDINGS_PROMPT, schema)
