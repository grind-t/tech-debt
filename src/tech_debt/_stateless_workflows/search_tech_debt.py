from typing import Protocol

from pydantic import BaseModel


class ExecutePrompt(Protocol):
    def __call__[Response: BaseModel](
        self, prompt: str, schema: type[Response], /
    ) -> Response: ...


def search_tech_debt(execute_prompt: ExecutePrompt) -> None:
    pass
