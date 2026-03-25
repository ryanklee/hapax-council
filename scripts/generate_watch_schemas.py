"""Generate JSON Schema files from watch_receiver Pydantic models.

Writes one .schema.json per model into schemas/watch/ and creates a VERSION
file if it doesn't already exist.

Usage:
    uv run python scripts/generate_watch_schemas.py
"""

from __future__ import annotations

import json
from pathlib import Path

from agents.watch_receiver import (
    GesturePayload,
    HealthSummaryPayload,
    PhoneContextPayload,
    SensorPayload,
    SensorReading,
    VoiceTriggerPayload,
)

MODELS = [
    SensorPayload,
    SensorReading,
    VoiceTriggerPayload,
    GesturePayload,
    HealthSummaryPayload,
    PhoneContextPayload,
]

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas" / "watch"


def main() -> None:
    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)

    for model in MODELS:
        schema = model.model_json_schema()
        out = SCHEMA_DIR / f"{model.__name__}.schema.json"
        out.write_text(json.dumps(schema, indent=2) + "\n")
        print(f"  wrote {out.relative_to(SCHEMA_DIR.parent.parent)}")

    version_file = SCHEMA_DIR / "VERSION"
    if not version_file.exists():
        version_file.write_text("1.0.0\n")
        print(f"  wrote {version_file.relative_to(SCHEMA_DIR.parent.parent)}")
    else:
        print(f"  VERSION already exists: {version_file.read_text().strip()}")


if __name__ == "__main__":
    main()
