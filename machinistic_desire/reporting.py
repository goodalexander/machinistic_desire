from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any


def build_run_dir(results_dir: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_dir = results_dir / stamp
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_score_rows(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in results:
        for score_row in result["scores"]:
            rows.append(
                {
                    "model": result["model"],
                    "desire_id": score_row["id"],
                    "desire_label": score_row["label"],
                    "score": score_row["score"],
                    "explanation": score_row["explanation"],
                }
            )
    return rows


def render_summary_markdown(results: list[dict[str, Any]]) -> str:
    if not results:
        return "# machinistic_desire\n\nNo results.\n"

    desire_labels: dict[str, str] = {}
    grouped: dict[str, list[int]] = defaultdict(list)
    for result in results:
        for row in result["scores"]:
            desire_labels[row["id"]] = row["label"]
            grouped[row["id"]].append(int(row["score"]))

    lines = [
        "# machinistic_desire",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Desire averages",
        "",
        "| Desire | Average |",
        "| --- | ---: |",
    ]
    ordered_desires = sorted(grouped, key=lambda desire_id: mean(grouped[desire_id]), reverse=True)
    for desire_id in ordered_desires:
        lines.append(f"| {desire_labels[desire_id]} | {mean(grouped[desire_id]):.2f} |")

    lines.extend(
        [
            "",
            "## Per-model scores",
            "",
            "| Model | Desire | Score |",
            "| --- | --- | ---: |",
        ]
    )
    for result in results:
        for row in sorted(result["scores"], key=lambda item: item["score"], reverse=True):
            lines.append(f"| {result['model']} | {row['label']} | {row['score']} |")

    lines.extend(["", "## Explanations", ""])
    for result in results:
        lines.append(f"### {result['model']}")
        lines.append("")
        for row in result["scores"]:
            lines.append(f"- **{row['label']}** `{row['score']}`: {row['explanation']}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
