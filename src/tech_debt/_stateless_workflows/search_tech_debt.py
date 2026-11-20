from typing import Protocol, overload

from pydantic import BaseModel


class ExecutePrompt(Protocol):
    @overload
    def __call__[Response: BaseModel](
        self, prompt: str, schema: type[Response], /
    ) -> Response: ...

    @overload
    def __call__(self, prompt: str, schema: None = None, /) -> str: ...


def search_tech_debt(execute_prompt: ExecutePrompt) -> None:
    pass
