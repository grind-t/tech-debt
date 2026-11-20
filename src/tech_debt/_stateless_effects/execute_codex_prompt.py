import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from pydantic import BaseModel


def execute_codex_prompt[Response: BaseModel](
    prompt: str, schema: type[Response]
) -> Response:
    """Run Codex and validate its final response with the supplied Pydantic model."""
    with TemporaryDirectory(prefix="tech-debt-codex-") as directory:
        schema_path = Path(directory) / "schema.json"
        response_path = Path(directory) / "response.json"
        schema_path.write_text(json.dumps(schema.model_json_schema()), encoding="utf-8")

        subprocess.run(
            [
                "codex",
                "exec",
                "--sandbox",
                "read-only",
                "--output-schema",
                str(schema_path),
                "--output-last-message",
                str(response_path),
                "-",
            ],
            input=prompt,
            text=True,
            encoding="utf-8",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=True,
        )

        return schema.model_validate_json(response_path.read_text(encoding="utf-8"))
