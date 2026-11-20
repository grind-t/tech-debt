SEARCH_TECH_DEBT_PROMPT = "Search technical debt within these project paths: {paths}"
RECHECK_FINDINGS_PROMPT = (
    "Recheck all findings and remove false positives "
    "and any findings you are uncertain about"
)
FORMAT_FINDINGS_PROMPT = "Format the findings according to the provided schema"

tech_debt_search_prompts: list[str] = [
    SEARCH_TECH_DEBT_PROMPT,
    RECHECK_FINDINGS_PROMPT,
    FORMAT_FINDINGS_PROMPT,
]
