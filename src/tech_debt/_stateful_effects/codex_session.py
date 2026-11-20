import asyncio
import json
import subprocess
from contextlib import suppress
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import overload

from pydantic import TypeAdapter

from tech_debt._entities.agent_settings import AgentSettings
from tech_debt._stateless_workflows.search_tech_debt import AgentSession


class CodexSession(AgentSession):
    """Run consecutive prompts in one Codex session."""

    def __init__(self, settings: AgentSettings) -> None:
        self._settings = settings
        self._session_id: str | None = None
        self._lock = asyncio.Lock()

    @overload
    async def next_turn[Response](
        self, prompt: str, schema: TypeAdapter[Response]
    ) -> Response: ...

    @overload
    async def next_turn(self, prompt: str, schema: None = None) -> str: ...

    async def next_turn[Response](
        self, prompt: str, schema: TypeAdapter[Response] | None = None
    ) -> Response | str:
        """Start the session or continue it, optionally validating the response."""
        async with self._lock:
            with TemporaryDirectory(prefix="tech-debt-codex-") as directory:
                response_path = Path(directory) / "response.json"
                command = ["codex", "exec", "--sandbox", "read-only"]
                if self._session_id is not None:
                    command.append("resume")
                command.extend(
                    [
                        "--model",
                        self._settings.model,
                        "--config",
                        "model_reasoning_effort="
                        + json.dumps(self._settings.reasoning_effort),
                    ]
                )
                command.append("--json")
                wrapped = False
                if schema is not None:
                    output_schema = schema.json_schema()
                    wrapped = output_schema.get("type") != "object"
                    if wrapped:
                        definitions = output_schema.pop("$defs", {})
                        output_schema = {
                            "type": "object",
                            "properties": {"result": output_schema},
                            "required": ["result"],
                            "additionalProperties": False,
                            "$defs": definitions,
                        }
                    schema_path = Path(directory) / "schema.json"
                    await asyncio.to_thread(
                        schema_path.write_text,
                        json.dumps(output_schema),
                        encoding="utf-8",
                    )
                    command.extend(["--output-schema", str(schema_path)])
                command.extend(["--output-last-message", str(response_path)])
                if self._session_id is not None:
                    command.append(self._session_id)
                command.append("-")

                process = await asyncio.create_subprocess_exec(
                    *command,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                communication = asyncio.create_task(
                    process.communicate(prompt.encode("utf-8"))
                )
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
                        returncode,
                        command,
                        stderr=stderr.decode("utf-8", errors="replace"),
                    )

                for line in stdout.decode("utf-8").splitlines():
                    if not line.strip():
                        continue
                    event = json.loads(line)
                    if event.get("type") == "thread.started":
                        thread_id = event.get("thread_id")
                        if not isinstance(thread_id, str) or not thread_id:
                            raise RuntimeError("Codex returned an invalid session ID")
                        self._session_id = thread_id
                if self._session_id is None:
                    raise RuntimeError("Codex did not return a session ID")

                response = await asyncio.to_thread(
                    response_path.read_text, encoding="utf-8"
                )
                if schema is None:
                    return response
                if wrapped:
                    response = json.dumps(json.loads(response)["result"])
                return schema.validate_json(response)
