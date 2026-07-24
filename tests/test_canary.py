import json
from pathlib import Path

from conversor_his.validation.canary import evaluate_case, run_canary_suite


def test_canary_preserves_suffixes_and_terms() -> None:
    result = evaluate_case(
        {
            "case_id": "sufixos",
            "headings": ["70-A", "70-B"],
            "critical_terms": ["15%", "m²"],
            "observed_text": "Art. 70-A taxa de 15%. Art. 70-B área de 20 m².",
        }
    )
    assert result.passed is True


def test_canary_fails_on_critical_regression(tmp_path: Path) -> None:
    source = tmp_path / "cases.json"
    source.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "case_id": "ocr",
                        "headings": ["126"],
                        "critical_terms": ["m²"],
                        "observed_text": "Aft. 126 area de 20 m?",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    json_path, csv_path, passed = run_canary_suite(source, tmp_path / "analise")
    assert passed is False
    assert json_path.exists() and csv_path.exists()
