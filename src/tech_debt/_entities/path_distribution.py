from pathlib import PurePath
from typing import Annotated

from pydantic import Field

type PathDistribution = Annotated[
    list[list[PurePath]],
    Field(
        description=(
            "Balanced, non-overlapping search scopes covering the specified paths."
        ),
        examples=[[["src/orders"], ["src/billing", "src/reports"]]],
    ),
]
