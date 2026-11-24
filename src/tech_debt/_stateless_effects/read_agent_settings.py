import tomllib
from pathlib import Path

from tech_debt._entities.agent_settings import AgentSettings


def read_agent_settings() -> AgentSettings:
    """Prefer settings in the current directory, then use the home directory."""
    config_path = Path(".tech-debt.toml")
    try:
        config_file = config_path.open("rb")
    except FileNotFoundError:
        config_file = (Path.home() / config_path).open("rb")
    with config_file as file:
        configuration = tomllib.load(file)
    return AgentSettings.model_validate(configuration.get("agent", {}))
