DISTRIBUTE_PATHS_PROMPT = (
    "Divide these project paths into {parallelism} balanced, non-overlapping "
    "search scopes covering all specified paths: {paths}"
)
CORRECT_PATH_DISTRIBUTION_PROMPT = (
    "Correct the path distribution to resolve these validation errors: {errors}"
)
SEARCH_TECH_DEBT_PROMPT = "Search for technical debt in {paths}"
FORMAT_FINDINGS_PROMPT = "Format all findings according to the provided schema."
DEDUPLICATE_FINDINGS_PROMPT = (
    "Find and remove semantically duplicate defects: {findings}"
)
