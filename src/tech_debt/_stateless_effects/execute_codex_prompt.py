import asyncio
import json
import subprocess
from contextlib import suppress
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import overload

from pydantic import BaseModel


@overload
async def execute_codex_prompt[Response: BaseModel](
    prompt: str, schema: type[Response]
) -> Response: ...


@overload
async def execute_codex_prompt(prompt: str, schema: None = None) -> str: ...


async def execute_codex_prompt[Response: BaseModel](
    prompt: str, schema: type[Response] | None = None
) -> Response | str:
    """Run Codex and return text or a response validated by the supplied model."""
    with TemporaryDirectory(prefix="tech-debt-codex-") as directory:
        response_path = Path(directory) / "response.json"
        command = ["codex", "exec", "--sandbox", "read-only"]
        if schema is not None:
            schema_path = Path(directory) / "schema.json"
            await asyncio.to_thread(
                schema_path.write_text,
                json.dumps(schema.model_json_schema()),
                encoding="utf-8",
            )
            command.extend(["--output-schema", str(schema_path)])
        command.extend(["--output-last-message", str(response_path), "-"])

        process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        communication = asyncio.create_task(process.communicate(prompt.encode("utf-8")))
        try:
            _, stderr = await asyncio.shield(communication)
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

        response = await asyncio.to_thread(response_path.read_text, encoding="utf-8")
        return response if schema is None else schema.model_validate_json(response)
