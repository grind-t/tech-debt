from typing import Literal

from pydantic import BaseModel, Field


class AgentSettings(BaseModel):
    provider: Literal["codex"] = "codex"
    model: str = Field(min_length=1)
    reasoning_effort: str = Field(min_length=1)
