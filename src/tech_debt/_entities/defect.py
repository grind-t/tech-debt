from typing import Literal, Self, get_args

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

_FunctionalSuitability = Literal[
    "Functional completeness",
    "Functional correctness",
    "Functional appropriateness",
]

_PerformanceEfficiency = Literal[
    "Time behaviour",
    "Resource utilization",
    "Capacity",
]

_Compatibility = Literal[
    "Co-existence",
    "Interoperability",
]

_InteractionCapability = Literal[
    "Appropriateness recognizability",
    "Learnability",
    "Operability",
    "User error protection",
    "User engagement",
    "Inclusivity",
    "User assistance",
    "Self-descriptiveness",
]

_Reliability = Literal[
    "Faultlessness",
    "Availability",
    "Fault tolerance",
    "Recoverability",
]

_Security = Literal[
    "Confidentiality",
    "Integrity",
    "Non-repudiation",
    "Accountability",
    "Authenticity",
    "Resistance",
]

_Maintainability = Literal[
    "Modularity",
    "Reusability",
    "Analysability",
    "Modifiability",
    "Testability",
]

_Flexibility = Literal[
    "Adaptability",
    "Scalability",
    "Installability",
    "Replaceability",
]

_Safety = Literal[
    "Operational constraint",
    "Risk identification",
    "Fail safe",
    "Hazard warning",
    "Safe integration",
]

_Characteristic = Literal[
    "Functional suitability",
    "Performance efficiency",
    "Compatibility",
    "Interaction capability",
    "Reliability",
    "Security",
    "Maintainability",
    "Flexibility",
    "Safety",
]

_Subcharacteristic = (
    _FunctionalSuitability
    | _PerformanceEfficiency
    | _Compatibility
    | _InteractionCapability
    | _Reliability
    | _Security
    | _Maintainability
    | _Flexibility
    | _Safety
)

_SUBCHARACTERISTICS = {
    "Functional suitability": get_args(_FunctionalSuitability),
    "Performance efficiency": get_args(_PerformanceEfficiency),
    "Compatibility": get_args(_Compatibility),
    "Interaction capability": get_args(_InteractionCapability),
    "Reliability": get_args(_Reliability),
    "Security": get_args(_Security),
    "Maintainability": get_args(_Maintainability),
    "Flexibility": get_args(_Flexibility),
    "Safety": get_args(_Safety),
}

_MOST_LIKELY_RISK_EXAMPLE: dict[str, JsonValue] = {
    "event": "A maintainer changes how totals are computed",
    "consequence": (
        "Each change takes three edits and three reviews, "
        "so changes to totals ship slower"
    ),
    "likelihood": "High",
    "severity": "Minor",
}
_WORST_CREDIBLE_RISK_EXAMPLE: dict[str, JsonValue] = {
    "event": (
        "A maintainer changes totals and misses one of the three copies, "
        "and no test compares totals across them"
    ),
    "consequence": (
        "Customers are invoiced amounts that differ from their orders, "
        "and invoices have to be corrected and reissued"
    ),
    "likelihood": "Medium",
    "severity": "Critical",
}


class _Risk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event: str = Field(
        description="The event underlying this risk.",
    )
    consequence: str = Field(
        description=(
            "Impact on users, business, or the speed and reliability "
            "of agents and people working with the system."
        ),
    )
    likelihood: Literal["High", "Medium", "Low", "Not applicable"] = Field(
        description=(
            "Use 'Not applicable' if the event is unrealistic or "
            "already caught by existing tests, checks, CI, or monitoring. "
            "Otherwise, rate its likelihood as High, Medium, or Low."
        ),
    )
    severity: Literal["Blocking", "Critical", "Major", "Minor", "Inconsequential"]


class _DefectRisks(BaseModel):
    """Most likely risk and worst credible risk; use null when they coincide."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "most_likely": _MOST_LIKELY_RISK_EXAMPLE,
                    "worst_credible": _WORST_CREDIBLE_RISK_EXAMPLE,
                }
            ]
        },
    )

    most_likely: _Risk
    worst_credible: _Risk | None = Field(
        description="Worst credible consequence, if different from the most likely.",
    )


class Defect(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(
        description="Brief description of the problem.",
        examples=["Order totals are computed in three places"],
    )
    location: str = Field(
        description="Location of the defect in the project.",
        examples=["src/orders/totals.py, src/billing/invoice.py, src/reports/sales.py"],
    )
    type: str = Field(
        description=(
            "Name of the established problem family this defect belongs to, "
            "from a standard, book, or commonly accepted practice. "
            "Include the source or version where needed."
        ),
        examples=["Duplicated Code (Fowler, Refactoring, 2nd ed.)"],
    )
    characteristic: _Characteristic = Field(
        description="ISO/IEC 25010:2023 quality characteristic degraded by the defect.",
        examples=["Maintainability"],
    )
    subcharacteristic: _Subcharacteristic = Field(
        description="Degraded subcharacteristic of the chosen quality characteristic.",
        examples=["Modifiability"],
    )
    risks: _DefectRisks

    @model_validator(mode="after")
    def _validate_subcharacteristic(self) -> Self:
        allowed = _SUBCHARACTERISTICS[self.characteristic]
        if self.subcharacteristic not in allowed:
            raise ValueError(
                f"{self.subcharacteristic!r} does not belong to "
                f"{self.characteristic!r}. Expected one of: {', '.join(allowed)}"
            )
        return self
