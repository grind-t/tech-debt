from pathlib import Path

from pydantic import BaseModel, Field


class PathDistribution(BaseModel):
    scopes: list[list[Path]] = Field(
        description=(
            "Balanced, non-overlapping search scopes covering the specified paths."
        ),
        examples=[[["src/orders"], ["src/billing", "src/reports"]]],
    )
