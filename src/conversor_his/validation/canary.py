# SPDX-License-Identifier: MIT
from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

_ARTICLE_RE = re.compile(r"\bArt\.?\s*(\d+[A-Z]?(?:-[A-Z])?)\b", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class CanaryResult:
    case_id: str
    missing_headings: list[str]
    unexpected_headings: list[str]
    critical_terms_missing: list[str]
    passed: bool


def normalize_article(value: str) -> str:
    compact = re.sub(r"\s+", "", value.upper())
    return compact.replace("ARTIGO", "").replace("ART.", "").replace("ART", "")


def extract_article_headings(text: str) -> list[str]:
    return [normalize_article(match.group(1)) for match in _ARTICLE_RE.finditer(text)]


def evaluate_case(case: dict[str, Any]) -> CanaryResult:
    expected = [normalize_article(str(value)) for value in case.get("headings", [])]
    observed_text = str(case.get("observed_text", ""))
    observed = extract_article_headings(observed_text)
    expected_terms = [str(value) for value in case.get("critical_terms", [])]
    folded = observed_text.casefold()
    missing_terms = [term for term in expected_terms if term.casefold() not in folded]
    missing = sorted(set(expected) - set(observed))
    unexpected = sorted(set(observed) - set(expected))
    return CanaryResult(
        case_id=str(case.get("case_id", "unknown")),
        missing_headings=missing,
        unexpected_headings=unexpected,
        critical_terms_missing=missing_terms,
        passed=not missing and not unexpected and not missing_terms,
    )


def run_canary_suite(input_path: Path, output_dir: Path) -> tuple[Path, Path, bool]:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    cases = payload.get("cases", payload if isinstance(payload, list) else [])
    if not isinstance(cases, list):
        raise TypeError("arquivo canario deve conter uma lista ou a chave 'cases'")
    results = [evaluate_case(case) for case in cases]
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "canary_results.json"
    csv_path = output_dir / "canary_results.csv"
    json_path.write_text(
        json.dumps(
            {
                "case_count": len(results),
                "passed_count": sum(result.passed for result in results),
                "failed_count": sum(not result.passed for result in results),
                "passed": all(result.passed for result in results),
                "results": [asdict(result) for result in results],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "case_id",
                "passed",
                "missing_headings",
                "unexpected_headings",
                "critical_terms_missing",
            ],
        )
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "case_id": result.case_id,
                    "passed": result.passed,
                    "missing_headings": "|".join(result.missing_headings),
                    "unexpected_headings": "|".join(result.unexpected_headings),
                    "critical_terms_missing": "|".join(result.critical_terms_missing),
                }
            )
    return json_path, csv_path, all(result.passed for result in results)


__all__ = ["CanaryResult", "evaluate_case", "extract_article_headings", "run_canary_suite"]
