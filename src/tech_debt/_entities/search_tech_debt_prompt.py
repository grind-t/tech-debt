DISTRIBUTE_PATHS_PROMPT = (
    "Divide these project paths into {parallelism} balanced, non-overlapping "
    "search scopes covering all specified paths: {paths}"
)
SEARCH_TECH_DEBT_PROMPT = "Search technical debt within these project paths: {paths}"
FORMAT_FINDINGS_PROMPT = "Format the findings according to the provided schema"
RECHECK_FINDINGS_PROMPT = (
    "Recheck all findings and remove false positives "
    "and any findings you are uncertain about"
)
DEDUPLICATE_FINDINGS_PROMPT = (
    "Find and remove semantically duplicate defects: {findings}"
)
