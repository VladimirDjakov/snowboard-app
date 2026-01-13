"""Artifact validation service for application layer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[4]
KEYPOINTS_SCHEMA_PATH = REPO_ROOT / "schemas" / "keypoints_v1.jsonschema"
FEATURES_SCHEMA_PATH = REPO_ROOT / "schemas" / "features_v1.jsonschema"
FEEDBACK_SCHEMA_PATH = REPO_ROOT / "schemas" / "feedback_v1.jsonschema"


class ArtifactValidationError(ValueError):
    """Raised when artifact validation fails."""


def _load_schema(path: Path) -> dict[str, Any] | None:
    """Load JSON schema from file if it exists."""
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8").strip()
    return json.loads(text) if text else None


def _validate_with_schema(data: Any, schema: dict[str, Any] | None) -> None:
    """Validate data against JSON schema if schema is provided."""
    if schema:
        jsonschema.validate(data, schema)


def validate_keypoints_jsonl(
    path: Path | str,
    *,
    expected_kp_names: set[str] | None = None,
    schema_path: Path = KEYPOINTS_SCHEMA_PATH,
) -> None:
    """
    Validate keypoints JSONL artifact.

    Uses JSON schema if present. More strict validation can be added later.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Keypoints file not found: {path}")

    schema = _load_schema(schema_path)

    with path.open("r", encoding="utf-8") as handle:
        for idx, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue

            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ArtifactValidationError(f"Invalid JSON on line {idx}") from exc

            if not isinstance(record, dict):
                raise ArtifactValidationError(f"Line {idx} must be a JSON object")

            _validate_with_schema(record, schema)

            # Basic structure check (can be enhanced later)
            if expected_kp_names and "kp" in record:
                for kp in record.get("kp", []):
                    if isinstance(kp, dict) and kp.get("name") not in expected_kp_names:
                        raise ArtifactValidationError(
                            f"Unexpected keypoint '{kp.get('name')}' on line {idx}"
                        )


def validate_features_json(
    data_or_path: dict[str, Any] | Path | str,
    *,
    schema_path: Path = FEATURES_SCHEMA_PATH,
) -> dict[str, Any]:
    """
    Validate features JSON artifact and return parsed data.

    Uses JSON schema if present. More strict validation can be added later.
    """
    if isinstance(data_or_path, (Path, str)):
        data = json.loads(Path(data_or_path).read_text(encoding="utf-8"))
    else:
        data = data_or_path

    if not isinstance(data, dict):
        raise ArtifactValidationError("Features artifact must be a JSON object")

    schema = _load_schema(schema_path)
    _validate_with_schema(data, schema)

    return data


def validate_feedback_json(
    data_or_path: dict[str, Any] | Path | str,
    *,
    schema_path: Path = FEEDBACK_SCHEMA_PATH,
) -> dict[str, Any]:
    """
    Validate feedback JSON artifact and return parsed data.

    Uses JSON schema if present. More strict validation can be added later.
    """
    if isinstance(data_or_path, (Path, str)):
        data = json.loads(Path(data_or_path).read_text(encoding="utf-8"))
    else:
        data = data_or_path

    if not isinstance(data, dict):
        raise ArtifactValidationError("Feedback artifact must be a JSON object")

    schema = _load_schema(schema_path)
    _validate_with_schema(data, schema)

    return data
