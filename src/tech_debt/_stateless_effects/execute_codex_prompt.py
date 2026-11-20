import asyncio
import json
import subprocess
from contextlib import suppress
from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import overload

from pydantic import BaseModel

from tech_debt._stateless_workflows.search_tech_debt import ExecutePrompt


@overload
async def execute_codex_prompt[Response: BaseModel](
    prompt: str, schema: type[Response], *, session_id: str | None = None
) -> tuple[Response, ExecutePrompt]: ...


@overload
async def execute_codex_prompt(
    prompt: str, schema: None = None, *, session_id: str | None = None
) -> tuple[str, ExecutePrompt]: ...


async def execute_codex_prompt[Response: BaseModel](
    prompt: str, schema: type[Response] | None = None, *, session_id: str | None = None
) -> tuple[Response | str, ExecutePrompt]:
    """Return Codex's response and a callable continuing the same session."""
    with TemporaryDirectory(prefix="tech-debt-codex-") as directory:
        response_path = Path(directory) / "response.json"
        command = ["codex", "exec", "--sandbox", "read-only"]
        if session_id is not None:
            command.append("resume")
        command.append("--json")
        if schema is not None:
            schema_path = Path(directory) / "schema.json"
            await asyncio.to_thread(
                schema_path.write_text,
                json.dumps(schema.model_json_schema()),
                encoding="utf-8",
            )
            command.extend(["--output-schema", str(schema_path)])
        command.extend(["--output-last-message", str(response_path)])
        if session_id is not None:
            command.append(session_id)
        command.append("-")

        process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        communication = asyncio.create_task(process.communicate(prompt.encode("utf-8")))
        try:
            stdout, stderr = await asyncio.shield(communication)
        except asyncio.CancelledError:
            if process.returncode is None:
                with suppress(ProcessLookupError):
                    process.kill()
            await communication
            raise

        returncode = await process.wait()
        if returncode != 0:
            raise subprocess.CalledProcessError(
                returncode, command, stderr=stderr.decode("utf-8", errors="replace")
            )

        for line in stdout.decode("utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get("type") == "thread.started":
                thread_id = event.get("thread_id")
                if not isinstance(thread_id, str) or not thread_id:
                    raise RuntimeError("Codex returned an invalid session ID")
                session_id = thread_id
        if session_id is None:
            raise RuntimeError("Codex did not return a session ID")

        response = await asyncio.to_thread(response_path.read_text, encoding="utf-8")
        result = response if schema is None else schema.model_validate_json(response)
        next_turn: ExecutePrompt = partial(execute_codex_prompt, session_id=session_id)
        return result, next_turn
