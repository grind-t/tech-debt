import argparse
import asyncio
import json
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from tech_debt._stateless_effects.list_codex_models import list_codex_models


def main() -> None:
    parser = argparse.ArgumentParser(prog="tech-debt")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Check Codex CLI availability and authentication")
    args = parser.parse_args()

    if args.command == "init":
        _init(parser)


def _init(parser: argparse.ArgumentParser) -> None:
    executable = shutil.which("codex")
    if executable is None:
        parser.exit(
            status=1,
            message=(
                "Only Codex CLI is currently supported. "
                "Install Codex CLI and ensure 'codex' is available in PATH.\n"
            ),
        )

    checks = (
        (["--version"], "Codex CLI is not working. Check your Codex CLI installation."),
        (
            ["login", "status"],
            "Codex CLI authentication check failed. Run 'codex login' and try again.",
        ),
    )
    for arguments, failure_message in checks:
        try:
            subprocess.run(
                [executable, *arguments],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                check=True,
                timeout=10,
            )
        except subprocess.CalledProcessError:
            parser.exit(status=1, message=f"{failure_message}\n")
        except subprocess.TimeoutExpired:
            parser.exit(status=1, message="Codex CLI check timed out. Try again.\n")
        except OSError:
            parser.exit(
                status=1,
                message="Unable to start Codex CLI. Check your installation.\n",
            )

    try:
        models = asyncio.run(list_codex_models())
    except OSError, RuntimeError, TimeoutError, ValueError:
        parser.exit(
            status=1,
            message="Unable to load Codex models. Check Codex CLI and retry.\n",
        )
    models = [model for model in models if model.supported_reasoning_efforts]
    if not models:
        parser.exit(
            status=1, message="No Codex models with reasoning effort available.\n"
        )

    try:
        model_index = _choose(
            "Select a model for technical debt search",
            [f"{model.display_name} ({model.model})" for model in models],
            default=next(
                (index for index, model in enumerate(models) if model.is_default), 0
            ),
        )
        model = models[model_index]
        efforts = model.supported_reasoning_efforts
        effort_index = _choose(
            "Select reasoning effort",
            [f"{effort.reasoning_effort}: {effort.description}" for effort in efforts],
            default=next(
                (
                    index
                    for index, effort in enumerate(efforts)
                    if effort.reasoning_effort == model.default_reasoning_effort
                ),
                0,
            ),
        )
    except EOFError, KeyboardInterrupt:
        parser.exit(status=1, message="\nInitialization cancelled.\n")

    configuration = (
        "[codex]\n"
        f"model = {json.dumps(model.model)}\n"
        f"reasoning_effort = {json.dumps(efforts[effort_index].reasoning_effort)}\n"
    )
    try:
        Path(".tech-debt.toml").write_text(configuration, encoding="utf-8")
    except OSError:
        parser.exit(status=1, message="Unable to save .tech-debt.toml.\n")
    sys.stdout.write("Configuration saved to .tech-debt.toml.\n")


def _choose(title: str, options: Sequence[str], *, default: int = 0) -> int:
    sys.stdout.write(f"\n{title}:\n")
    for index, option in enumerate(options, start=1):
        sys.stdout.write(f"  {index}. {option}\n")
    while True:
        answer = input(f"Choice [{default + 1}]: ").strip()
        if not answer:
            return default
        try:
            selected = int(answer) - 1
        except ValueError:
            selected = -1
        if 0 <= selected < len(options):
            return selected
        sys.stdout.write(f"Enter a number between 1 and {len(options)}.\n")
