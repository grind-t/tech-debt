import asyncio
import json
from contextlib import suppress

from pydantic import TypeAdapter

from tech_debt._entities.codex_model import CodexModel


async def list_codex_models() -> list[CodexModel]:
    """Read the model catalog and supported efforts from Codex app-server."""
    process = await asyncio.create_subprocess_exec(
        "codex",
        "app-server",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
        limit=1024 * 1024,
    )
    assert process.stdin is not None
    assert process.stdout is not None
    writer = process.stdin
    reader = process.stdout

    async def request(
        request_id: int, method: str, params: dict[str, object]
    ) -> dict[str, object]:
        writer.write(
            (
                json.dumps({"id": request_id, "method": method, "params": params})
                + "\n"
            ).encode("utf-8")
        )
        await writer.drain()
        while line := await reader.readline():
            message = json.loads(line)
            if message.get("id") != request_id:
                continue
            if "error" in message:
                raise RuntimeError(f"Codex {method} failed")
            return message["result"]
        raise RuntimeError("Codex app-server closed before returning a response")

    async def fetch() -> list[CodexModel]:
        await request(
            0,
            "initialize",
            {"clientInfo": {"name": "tech-debt", "version": "0.1.0"}},
        )
        writer.write(b'{"method":"initialized"}\n')
        await writer.drain()
        models: list[CodexModel] = []
        adapter = TypeAdapter(list[CodexModel])
        cursor = None
        request_id = 1
        while True:
            result = await request(
                request_id,
                "model/list",
                {"limit": 100, "includeHidden": False, "cursor": cursor},
            )
            models.extend(adapter.validate_python(result["data"]))
            cursor = result.get("nextCursor")
            if cursor is None:
                return models
            request_id += 1

    try:
        return await asyncio.wait_for(fetch(), timeout=20)
    finally:
        if process.returncode is None:
            with suppress(ProcessLookupError):
                process.kill()
        await process.communicate()
