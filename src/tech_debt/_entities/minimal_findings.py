from pydantic import BaseModel, ConfigDict

from tech_debt._entities.minimal_finding import MinimalFinding


class MinimalFindings(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    findings: list[MinimalFinding]
