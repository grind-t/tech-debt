import asyncio
from collections.abc import Callable, Mapping, Sequence
from pathlib import PurePath
from typing import Protocol, overload

from pydantic import TypeAdapter

from tech_debt._entities.defect import Defect
from tech_debt._entities.minimal_findings import MinimalFindings
from tech_debt._entities.search_tech_debt_prompt import (
    DEDUPLICATE_FINDINGS_PROMPT,
    FORMAT_FINDINGS_PROMPT,
    SEARCH_TECH_DEBT_PROMPT,
)
from tech_debt._stateless_computations.distribute_paths import distribute_paths


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
    *,
    normalize_paths: Callable[[Sequence[PurePath]], list[PurePath]],
    list_files: Callable[[Sequence[PurePath]], Mapping[PurePath, int]],
) -> list[Defect]:
    """Search technical debt using ``parallelism`` concurrent search sessions."""
    if parallelism < 1:
        raise ValueError("parallelism must be greater than zero")
    if not paths:
        raise ValueError("Search paths must not be empty")
    paths = await asyncio.to_thread(normalize_paths, paths)
    if parallelism == 1:
        return await _search_tech_debt_session(create_session(), paths)

    files = await asyncio.to_thread(list_files, paths)
    distribution = distribute_paths(paths, files, parallelism)

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
    session: AgentSession, paths: Sequence[PurePath]
) -> list[Defect]:
    await session.next_turn(
        SEARCH_TECH_DEBT_PROMPT.format(paths=", ".join(map(str, paths))),
        TypeAdapter(MinimalFindings),
    )
    schema = TypeAdapter(list[Defect])
    return await session.next_turn(FORMAT_FINDINGS_PROMPT, schema)
