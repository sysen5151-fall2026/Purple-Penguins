"""Summarize pricing benchmark CSVs and compare them with Innoslate results."""

from __future__ import annotations

import argparse
import csv
import statistics
from pathlib import Path
from typing import Iterable


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_REFERENCE = (
    ROOT_DIR / "results" / "chapter10-4" / "innoslate_reference.csv"
)
SUMMARY_FIELDS = [
    "scenario",
    "mode",
    "stage",
    "status",
    "run_count",
    "minimum_duration_s",
    "maximum_duration_s",
    "mean_duration_s",
    "median_duration_s",
    "sample_standard_deviation_s",
]
COMPARISON_FIELDS = [
    "scenario_id",
    "architecture",
    "record_type",
    "source",
    "run_count",
    "minimum_duration_s",
    "maximum_duration_s",
    "mean_duration_s",
    "median_duration_s",
    "sample_standard_deviation_s",
    "reference_scenario_id",
    "reference_mean_duration_s",
    "mean_delta_s",
    "mean_delta_percent",
    "comparability_note",
]
ACTUAL_SCENARIOS = (
    {
        "scenario_id": "ACTUAL-LOCAL",
        "scenario": "actual_in_memory_dictionary",
        "mode": "local",
        "architecture": "In-memory dictionary",
        "reference_scenario_id": "S.2",
        "comparability_note": (
            "Not a database query; compare with S.2 only as a limited local "
            "lookup proxy."
        ),
    },
    {
        "scenario_id": "ACTUAL-LLM",
        "scenario": "experimental_llm_pricing",
        "mode": "llm",
        "architecture": "Experimental LLM price estimates",
        "reference_scenario_id": "S.3",
        "comparability_note": (
            "Experimental unverified estimates; S.3 is not present in the "
            "current Innoslate export."
        ),
    },
)


def summarize_rows(rows: Iterable[dict[str, str]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, str, str], list[float]] = {}
    for row in rows:
        duration_value = row.get("duration_ns", "")
        if not duration_value:
            continue
        key = (
            row.get("scenario", ""),
            row.get("mode", ""),
            row.get("stage", ""),
            row.get("status", ""),
        )
        grouped.setdefault(key, []).append(int(duration_value) / 1_000_000_000)

    summaries: list[dict[str, object]] = []
    for (scenario, mode, stage, status), values in sorted(grouped.items()):
        summaries.append(
            {
                "scenario": scenario,
                "mode": mode,
                "stage": stage,
                "status": status,
                "run_count": len(values),
                "minimum_duration_s": min(values),
                "maximum_duration_s": max(values),
                "mean_duration_s": statistics.mean(values),
                "median_duration_s": statistics.median(values),
                "sample_standard_deviation_s": (
                    statistics.stdev(values) if len(values) > 1 else ""
                ),
            }
        )
    return summaries


def build_comparison_rows(
    summaries: list[dict[str, object]],
    reference_rows: list[dict[str, str]],
) -> list[dict[str, object]]:
    rows = [
        _simulation_comparison_row(reference)
        for reference in reference_rows
    ]
    for actual in ACTUAL_SCENARIOS:
        workflow_summary = next(
            (
                summary
                for summary in summaries
                if summary["scenario"] == actual["scenario"]
                and summary["mode"] == actual["mode"]
                and summary["stage"] == "pricing_workflow_total"
                and summary["status"] == "success"
            ),
            None,
        )
        reference_mean = _reference_mean(
            reference_rows,
            str(actual["reference_scenario_id"]),
        )
        measured_mean = (
            float(workflow_summary["mean_duration_s"])
            if workflow_summary is not None
            else None
        )
        delta = (
            measured_mean - reference_mean
            if measured_mean is not None and reference_mean is not None
            else None
        )
        rows.append(
            {
                "scenario_id": actual["scenario_id"],
                "architecture": actual["architecture"],
                "record_type": "measured_application",
                "source": "Recipe Roulette benchmark CSV",
                "run_count": (
                    workflow_summary["run_count"]
                    if workflow_summary is not None
                    else ""
                ),
                "minimum_duration_s": (
                    workflow_summary["minimum_duration_s"]
                    if workflow_summary is not None
                    else ""
                ),
                "maximum_duration_s": (
                    workflow_summary["maximum_duration_s"]
                    if workflow_summary is not None
                    else ""
                ),
                "mean_duration_s": (
                    measured_mean if measured_mean is not None else ""
                ),
                "median_duration_s": (
                    workflow_summary["median_duration_s"]
                    if workflow_summary is not None
                    else ""
                ),
                "sample_standard_deviation_s": (
                    workflow_summary["sample_standard_deviation_s"]
                    if workflow_summary is not None
                    else ""
                ),
                "reference_scenario_id": actual["reference_scenario_id"],
                "reference_mean_duration_s": (
                    reference_mean if reference_mean is not None else ""
                ),
                "mean_delta_s": delta if delta is not None else "",
                "mean_delta_percent": (
                    delta / reference_mean * 100
                    if delta is not None and reference_mean
                    else ""
                ),
                "comparability_note": actual["comparability_note"],
            }
        )
    return rows


def _simulation_comparison_row(
    reference: dict[str, str],
) -> dict[str, object]:
    return {
        "scenario_id": reference.get("scenario_id", ""),
        "architecture": reference.get("architecture", ""),
        "record_type": "innoslate_simulation",
        "source": reference.get("source", ""),
        "run_count": reference.get("runs", ""),
        "minimum_duration_s": reference.get("minimum_duration_s", ""),
        "maximum_duration_s": reference.get("maximum_duration_s", ""),
        "mean_duration_s": reference.get("mean_duration_s", ""),
        "median_duration_s": reference.get("median_duration_s", ""),
        "sample_standard_deviation_s": reference.get(
            "sample_standard_deviation_s",
            "",
        ),
        "reference_scenario_id": "",
        "reference_mean_duration_s": "",
        "mean_delta_s": "",
        "mean_delta_percent": "",
        "comparability_note": reference.get("status", ""),
    }


def _reference_mean(
    reference_rows: list[dict[str, str]],
    scenario_id: str,
) -> float | None:
    for row in reference_rows:
        if row.get("scenario_id") == scenario_id and row.get("mean_duration_s"):
            return float(row["mean_duration_s"])
    return None


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def _write_csv(
    path: Path,
    fieldnames: list[str],
    rows: Iterable[dict[str, object]],
) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Summarize pricing stages and compare to Innoslate results."
    )
    parser.add_argument("--input", type=Path, nargs="+", required=True)
    parser.add_argument(
        "--simulation-reference",
        type=Path,
        default=DEFAULT_REFERENCE,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT_DIR / "results" / "chapter10-4" / "analysis",
    )
    args = parser.parse_args(argv)

    all_measurements: list[dict[str, str]] = []
    for path in args.input:
        all_measurements.extend(_read_csv(path))
    summaries = summarize_rows(all_measurements)
    reference_rows = _read_csv(args.simulation_reference)
    comparisons = build_comparison_rows(summaries, reference_rows)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(
        args.output_dir / "stage-summary.csv",
        SUMMARY_FIELDS,
        summaries,
    )
    _write_csv(
        args.output_dir / "scenario-comparison.csv",
        COMPARISON_FIELDS,
        comparisons,
    )
    print(f"Stage summary: {args.output_dir / 'stage-summary.csv'}")
    print(f"Scenario comparison: {args.output_dir / 'scenario-comparison.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
