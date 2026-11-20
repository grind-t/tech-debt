from typing import Protocol, overload

from pydantic import BaseModel


class ExecutePrompt(Protocol):
    @overload
    async def __call__[Response: BaseModel](
        self, prompt: str, schema: type[Response], /
    ) -> Response: ...

    @overload
    async def __call__(self, prompt: str, schema: None = None, /) -> str: ...


async def search_tech_debt(execute_prompt: ExecutePrompt, parallelism: int) -> None:
    """Search technical debt using ``parallelism`` concurrent search sessions."""
