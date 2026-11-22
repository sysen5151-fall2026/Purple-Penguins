"""Summarize pricing benchmark CSVs and compare them with Innoslate results."""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from pathlib import Path
from typing import Iterable


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_REFERENCE = (
    ROOT_DIR / "results" / "chapter10-4" / "innoslate_reference.csv"
)
SUMMARY_FIELDS = [
    "scenario",
    "mode",
    "input_dataset_id",
    "stage",
    "status",
    "run_count",
    "sample_count",
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
    "input_dataset_id",
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
        "scenario_id": "ACTUAL-HTML-FIXTURE",
        "scenario": "actual_html_fixture_pricing",
        "mode": "html_fixture",
        "architecture": "Local coursework HTML fixture",
        "reference_scenario_id": "",
        "comparability_note": (
            "Saved local fixture parsing only; excludes retailer HTTP latency "
            "and live product data, so it is not comparable to S.1 simulation."
        ),
    },
    {
        "scenario_id": "ACTUAL-KROGER-API",
        "scenario": "actual_kroger_api_pricing",
        "mode": "kroger",
        "architecture": "Kroger Products API (S.1 source substitution)",
        "reference_scenario_id": "S.1",
        "comparability_note": (
            "Official location-specific retailer API, not literal HTML "
            "scraping; compare with S.1 only as the team-selected source "
            "substitution, not as equivalent webpage latency."
        ),
    },
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
    grouped: dict[
        tuple[str, str, str, str, str],
        list[tuple[str, float]],
    ] = {}
    for row in rows:
        duration_value = row.get("duration_ns", "")
        if not duration_value:
            continue
        key = (
            row.get("scenario", ""),
            row.get("mode", ""),
            row.get("input_dataset_id", ""),
            row.get("stage", ""),
            row.get("status", ""),
        )
        grouped.setdefault(key, []).append(
            (row.get("run_id", ""), int(duration_value) / 1_000_000_000)
        )

    summaries: list[dict[str, object]] = []
    for (scenario, mode, dataset_id, stage, status), samples in sorted(
        grouped.items()
    ):
        values = [duration for _run_id, duration in samples]
        run_ids = {run_id for run_id, _duration in samples if run_id}
        summaries.append(
            {
                "scenario": scenario,
                "mode": mode,
                "input_dataset_id": dataset_id,
                "stage": stage,
                "status": status,
                "run_count": len(run_ids) if run_ids else len(values),
                "sample_count": len(values),
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
        workflow_summaries = [
            summary
            for summary in summaries
            if summary["scenario"] == actual["scenario"]
            and summary["mode"] == actual["mode"]
            and summary["stage"] == "pricing_workflow_total"
            and summary["status"] == "success"
        ]
        if len(workflow_summaries) > 1:
            raise ValueError(
                "Comparison requires one input dataset per measured scenario; "
                f"found multiple for {actual['scenario']}."
            )
        workflow_summary = (
            workflow_summaries[0] if workflow_summaries else None
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
                "input_dataset_id": (
                    workflow_summary["input_dataset_id"]
                    if workflow_summary is not None
                    else ""
                ),
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
        "input_dataset_id": "",
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
    with path.open("x", newline="", encoding="utf-8") as file:
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
        default=ROOT_DIR / "results" / "chapter11" / "analysis",
    )
    args = parser.parse_args(argv)

    all_measurements: list[dict[str, str]] = []
    for path in args.input:
        all_measurements.extend(_read_csv(path))
    summaries = summarize_rows(all_measurements)
    reference_rows = _read_csv(args.simulation_reference)
    comparisons = build_comparison_rows(summaries, reference_rows)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_paths = [
        args.output_dir / "stage-summary.csv",
        args.output_dir / "scenario-comparison.csv",
    ]
    existing_outputs = [path for path in output_paths if path.exists()]
    if existing_outputs:
        print(
            "Refusing to overwrite existing analysis output: "
            + ", ".join(str(path) for path in existing_outputs),
            file=sys.stderr,
        )
        return 2
    _write_csv(
        output_paths[0],
        SUMMARY_FIELDS,
        summaries,
    )
    _write_csv(
        output_paths[1],
        COMPARISON_FIELDS,
        comparisons,
    )
    print(f"Stage summary: {args.output_dir / 'stage-summary.csv'}")
    print(f"Scenario comparison: {args.output_dir / 'scenario-comparison.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
