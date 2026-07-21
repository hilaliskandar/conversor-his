from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .models import DocumentDiagnosis


def write_manifest(diagnosis: DocumentDiagnosis, output_path: Path) -> None:
    data = asdict(diagnosis)
    data["source_path"] = str(diagnosis.source_path)
    data["generated_at"] = datetime.now(timezone.utc).isoformat()
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
