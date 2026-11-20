from typing import Final

SEARCH_TECH_DEBT_PROMPT = "Search technical debt within these project paths: {paths}"
RECHECK_FINDINGS_PROMPT = (
    "Recheck all findings and remove false positives "
    "and any findings you are uncertain about"
)
FORMAT_FINDINGS_PROMPT = "Format the findings according to the provided schema"

TECH_DEBT_SEARCH_PROMPTS: Final[tuple[str, ...]] = (
    SEARCH_TECH_DEBT_PROMPT,
    RECHECK_FINDINGS_PROMPT,
    FORMAT_FINDINGS_PROMPT,
)
