import argparse
import asyncio
import json
import shutil
import subprocess
import sys
from collections.abc import Sequence
from functools import partial
from pathlib import Path

from pydantic import TypeAdapter

from tech_debt._entities.defect import Defect
from tech_debt._stateful_effects.codex_session import CodexSession
from tech_debt._stateless_computations.format_search_error import format_search_error
from tech_debt._stateless_effects.list_codex_models import list_codex_models
from tech_debt._stateless_effects.read_agent_settings import read_agent_settings
from tech_debt._stateless_workflows.search_tech_debt import search_tech_debt


def main() -> None:
    parser = argparse.ArgumentParser(prog="tech-debt")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Check Codex CLI availability and authentication")
    search = commands.add_parser("search", help="Search for technical debt")
    search.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[Path()],
        help="Paths to search (default: .)",
    )
    search.add_argument(
        "--parallelism",
        "-p",
        type=int,
        default=1,
        help="Number of parallel search sessions (default: 1)",
    )
    args = parser.parse_args()

    if args.command == "init":
        _init(parser)
    elif args.command == "search":
        _search(parser, args.paths, args.parallelism)


def _search(
    parser: argparse.ArgumentParser, paths: Sequence[Path], parallelism: int
) -> None:
    if parallelism < 1:
        parser.error("--parallelism must be greater than zero")
    try:
        settings = read_agent_settings()
    except FileNotFoundError:
        parser.exit(status=1, message="Run 'tech-debt init' before searching.\n")
    except ValueError:
        parser.exit(
            status=1,
            message="Invalid agent settings. Run 'tech-debt init' to configure them.\n",
        )
    except OSError:
        parser.exit(status=1, message="Unable to read .tech-debt.toml.\n")

    try:
        defects = asyncio.run(
            search_tech_debt(partial(CodexSession, settings), paths, parallelism)
        )
    except KeyboardInterrupt:
        parser.exit(status=130, message="\nSearch cancelled.\n")
    except (
        OSError,
        RuntimeError,
        ValueError,
        subprocess.CalledProcessError,
        ExceptionGroup,
    ) as error:
        parser.exit(status=1, message=f"Search failed:\n{format_search_error(error)}\n")
    sys.stdout.write(
        TypeAdapter(list[Defect]).dump_json(defects, indent=2).decode("utf-8")
    )
    sys.stdout.write("\n")


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
        "[agent]\n"
        'provider = "codex"\n'
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
