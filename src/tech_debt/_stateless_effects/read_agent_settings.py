import tomllib
from pathlib import Path

from tech_debt._entities.agent_settings import AgentSettings


def read_agent_settings() -> AgentSettings:
    """Read and validate settings from .tech-debt.toml in the current directory."""
    with Path(".tech-debt.toml").open("rb") as file:
        configuration = tomllib.load(file)
    return AgentSettings.model_validate(configuration.get("agent", {}))
