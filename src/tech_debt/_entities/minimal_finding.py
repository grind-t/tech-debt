from pydantic import BaseModel, ConfigDict


class MinimalFinding(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    description: str
    location: str
