import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import overload

from pydantic import BaseModel


@overload
def execute_codex_prompt[Response: BaseModel](
    prompt: str, schema: type[Response]
) -> Response: ...


@overload
def execute_codex_prompt(prompt: str, schema: None = None) -> str: ...


def execute_codex_prompt[Response: BaseModel](
    prompt: str, schema: type[Response] | None = None
) -> Response | str:
    """Run Codex and return text or a response validated by the supplied model."""
    with TemporaryDirectory(prefix="tech-debt-codex-") as directory:
        response_path = Path(directory) / "response.json"
        command = ["codex", "exec", "--sandbox", "read-only"]
        if schema is not None:
            schema_path = Path(directory) / "schema.json"
            schema_path.write_text(
                json.dumps(schema.model_json_schema()), encoding="utf-8"
            )
            command.extend(["--output-schema", str(schema_path)])
        command.extend(["--output-last-message", str(response_path), "-"])

        subprocess.run(
            command,
            input=prompt,
            text=True,
            encoding="utf-8",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=True,
        )

        response = response_path.read_text(encoding="utf-8")
        return response if schema is None else schema.model_validate_json(response)
