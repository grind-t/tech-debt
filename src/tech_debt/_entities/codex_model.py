from pydantic import BaseModel, Field


class _ReasoningEffort(BaseModel):
    reasoning_effort: str = Field(alias="reasoningEffort")
    description: str


class CodexModel(BaseModel):
    model: str
    display_name: str = Field(alias="displayName")
    is_default: bool = Field(default=False, alias="isDefault")
    default_reasoning_effort: str = Field(alias="defaultReasoningEffort")
    supported_reasoning_efforts: list[_ReasoningEffort] = Field(
        alias="supportedReasoningEfforts"
    )
