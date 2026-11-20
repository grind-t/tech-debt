from typing import Literal, Self, get_args

from pydantic import BaseModel, Field, model_validator

type _FunctionalSuitability = Literal[
    "Functional completeness",
    "Functional correctness",
    "Functional appropriateness",
]

type _PerformanceEfficiency = Literal[
    "Time behaviour",
    "Resource utilization",
    "Capacity",
]

type _Compatibility = Literal[
    "Co-existence",
    "Interoperability",
]

type _InteractionCapability = Literal[
    "Appropriateness recognizability",
    "Learnability",
    "Operability",
    "User error protection",
    "User engagement",
    "Inclusivity",
    "User assistance",
    "Self-descriptiveness",
]

type _Reliability = Literal[
    "Faultlessness",
    "Availability",
    "Fault tolerance",
    "Recoverability",
]

type _Security = Literal[
    "Confidentiality",
    "Integrity",
    "Non-repudiation",
    "Accountability",
    "Authenticity",
    "Resistance",
]

type _Maintainability = Literal[
    "Modularity",
    "Reusability",
    "Analysability",
    "Modifiability",
    "Testability",
]

type _Flexibility = Literal[
    "Adaptability",
    "Scalability",
    "Installability",
    "Replaceability",
]

type _Safety = Literal[
    "Operational constraint",
    "Risk identification",
    "Fail safe",
    "Hazard warning",
    "Safe integration",
]

type _Characteristic = Literal[
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

type _Subcharacteristic = (
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
    "Functional suitability": get_args(_FunctionalSuitability.__value__),
    "Performance efficiency": get_args(_PerformanceEfficiency.__value__),
    "Compatibility": get_args(_Compatibility.__value__),
    "Interaction capability": get_args(_InteractionCapability.__value__),
    "Reliability": get_args(_Reliability.__value__),
    "Security": get_args(_Security.__value__),
    "Maintainability": get_args(_Maintainability.__value__),
    "Flexibility": get_args(_Flexibility.__value__),
    "Safety": get_args(_Safety.__value__),
}

_MOST_LIKELY_RISK_EXAMPLE = {
    "event": "A maintainer changes how totals are computed",
    "consequence": (
        "Each change takes three edits and three reviews, "
        "so changes to totals ship slower"
    ),
    "likelihood": "High",
    "severity": "Minor",
}
_WORST_CREDIBLE_RISK_EXAMPLE = {
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
    event: str = Field(
        description="Event that existing tests, checks, and monitoring would miss.",
    )
    consequence: str = Field(
        description=(
            "Impact on users, business, or the speed and reliability "
            "of agents and people working with the system."
        ),
    )
    likelihood: Literal["High", "Medium", "Low"]
    severity: Literal["Blocking", "Critical", "Major", "Minor", "Inconsequential"]


class _DefectRisks(BaseModel):
    most_likely: _Risk = Field(
        description="Most likely consequence of the defect.",
    )
    worst_credible: _Risk | None = Field(
        default=None,
        description="Worst credible consequence, if different from the most likely.",
    )


class Defect(BaseModel):
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
    risks: _DefectRisks = Field(
        examples=[
            {
                "most_likely": _MOST_LIKELY_RISK_EXAMPLE,
                "worst_credible": _WORST_CREDIBLE_RISK_EXAMPLE,
            }
        ]
    )

    @model_validator(mode="after")
    def _validate_subcharacteristic(self) -> Self:
        allowed = _SUBCHARACTERISTICS[self.characteristic]
        if self.subcharacteristic not in allowed:
            raise ValueError(
                f"{self.subcharacteristic!r} does not belong to "
                f"{self.characteristic!r}. Expected one of: {', '.join(allowed)}"
            )
        return self
