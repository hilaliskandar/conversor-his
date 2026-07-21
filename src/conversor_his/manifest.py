from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _json_ready(value: Any) -> Any:
    if is_dataclass(value):
        return _json_ready(asdict(value))
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    return value


def write_manifest(payload: Any, output_path: Path) -> None:
    data = _json_ready(payload)
    data["generated_at"] = datetime.now(timezone.utc).isoformat()
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
