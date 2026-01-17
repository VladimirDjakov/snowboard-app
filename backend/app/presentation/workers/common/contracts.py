"""Model contract loaders for workers."""

import json
from pathlib import Path
from typing import Any

_CONTRACTS_ROOT = Path(__file__).resolve().parents[5] / "contracts"
NORMALIZE_CONTRACT_PATH = _CONTRACTS_ROOT / "normalize" / "normalize_contract_v1.json"
POSE_CONTRACT_PATH = _CONTRACTS_ROOT / "pose" / "pose_contract_v1.json"
SKELETON_MAPPING_PATH = _CONTRACTS_ROOT / "pose" / "skeleton_mapping_v1.yaml"


def _read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Contract file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def load_contract(path: Path = NORMALIZE_CONTRACT_PATH) -> dict[str, Any]:
    """
    Load pose model contract (JSON).

    Returns empty dict if the contract file is empty.
    """
    data = _read_text(path)
    if not data:
        return {}
    return json.loads(data)


def load_skeleton_mapping(path: Path = SKELETON_MAPPING_PATH) -> dict[str, Any]:
    """
    Load skeleton mapping (YAML).

    Returns empty dict if the mapping file is empty.
    """
    try:
        import yaml
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "PyYAML is required to load the skeleton mapping. Install it to use pose features."
        ) from exc
    data = _read_text(path)
    if not data:
        return {}
    return yaml.safe_load(data)
