from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dashboard.modeling import ModelResult, load_model_result_from_registry_entry


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY_PATH = PROJECT_ROOT / "dashboard" / "model_registry.json"


def normalize_key(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def registry_key(coffee_type: str, feature_version: str, model_key: str | None = None) -> str:
    key = f"{normalize_key(coffee_type)}.{normalize_key(feature_version)}"
    if model_key:
        key = f"{key}.{normalize_key(model_key)}"
    return key


def load_registry(registry_path: Path | str = DEFAULT_REGISTRY_PATH) -> dict[str, Any]:
    registry_path = Path(registry_path)
    if not registry_path.exists():
        return {}
    with registry_path.open("r", encoding="utf-8") as registry_file:
        return json.load(registry_file)


def registry_entries_for(
    coffee_type: str,
    feature_version: str,
    registry_path: Path | str = DEFAULT_REGISTRY_PATH,
) -> list[tuple[str, dict[str, Any]]]:
    registry = load_registry(registry_path)
    base_key = registry_key(coffee_type, feature_version)
    prefix = f"{base_key}."

    entries: list[tuple[str, dict[str, Any]]] = []
    for key, entry in registry.items():
        if key.startswith(prefix):
            model_key = normalize_key(key.removeprefix(prefix))
            entries.append((model_key, dict(entry)))

    if entries:
        return sorted(entries, key=registry_entry_sort_key)

    legacy_entry = registry.get(base_key)
    if legacy_entry:
        model_key = normalize_key(str(legacy_entry.get("model_key", "default")))
        return [(model_key, dict(legacy_entry))]

    return []


def load_checkpoint_model(
    coffee_type: str,
    feature_version: str,
    registry_path: Path | str = DEFAULT_REGISTRY_PATH,
    model_key: str | None = None,
) -> ModelResult | None:
    registry_path = Path(registry_path)
    root_dir = registry_path.parent
    entries = registry_entries_for(coffee_type, feature_version, registry_path)

    if model_key:
        normalized_model_key = normalize_key(model_key)
        entries = [(key, entry) for key, entry in entries if key == normalized_model_key]

    for key, entry in entries:
        if not registry_entry_files_exist(entry, root_dir):
            continue
        entry = {
            **entry,
            "model_key": key,
            "recommended": bool(entry.get("recommended", False)),
        }
        try:
            return load_model_result_from_registry_entry(entry, root_dir)
        except (FileNotFoundError, ImportError, ModuleNotFoundError, OSError, AttributeError):
            continue

    return None


def registry_entry_files_exist(entry: dict[str, Any], root_dir: Path) -> bool:
    model_path = entry.get("model_path")
    if not model_path or not (root_dir / model_path).exists():
        return False

    scaler_path = entry.get("scaler_path")
    if scaler_path and not (root_dir / scaler_path).exists():
        return False

    return True


def registry_entry_sort_key(item: tuple[str, dict[str, Any]]) -> tuple[int, float, str]:
    key, entry = item
    metrics = entry.get("metrics", {})
    rmse = metrics.get("test_rmse")
    try:
        rmse_value = float(rmse)
    except (TypeError, ValueError):
        rmse_value = float("inf")
    recommended_rank = 0 if entry.get("recommended") else 1
    return recommended_rank, rmse_value, key
