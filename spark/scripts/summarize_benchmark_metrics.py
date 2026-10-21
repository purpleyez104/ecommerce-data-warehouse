#!/usr/bin/env python3
"""校验 M7 measured metrics，并按实验/变体输出三次运行的中位数。"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Any


VARIANTS = {
    "partition_pruning": ("baseline", "optimized"),
    "join_strategy": ("sort_merge", "broadcast"),
    "skew_aggregation": ("single_stage", "two_stage"),
}
METRICS = (
    "duration_ms",
    "task_count",
    "stage_count",
    "executor_run_time_ms",
    "executor_cpu_time_ns",
    "input_bytes",
    "input_records",
    "shuffle_read_bytes",
    "shuffle_read_records",
    "shuffle_write_bytes",
    "shuffle_write_records",
    "memory_spill_bytes",
    "disk_spill_bytes",
)


def summarize(paths: list[Path]) -> dict[str, Any]:
    """要求每个变体恰有三个成功 measured runs，并生成可比较的中位数。"""
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for path in paths:
        record = json.loads(path.read_text(encoding="utf-8"))
        key = (record.get("experiment"), record.get("variant"))
        if key[0] not in VARIANTS or key[1] not in VARIANTS[key[0]]:
            raise ValueError(f"unexpected experiment variant in {path}")
        if record.get("measured") is not True:
            raise ValueError(f"non-measured record in {path}")
        if record.get("failed_job_count") or record.get("failed_task_count"):
            raise ValueError(f"failed Spark work in {path}")
        grouped[key].append(record)

    output: dict[str, Any] = {"measured_runs_per_variant": 3, "experiments": {}}
    for experiment, variants in VARIANTS.items():
        experiment_summary: dict[str, Any] = {}
        for variant in variants:
            records = grouped[(experiment, variant)]
            if len(records) != 3 or {record.get("run_index") for record in records} != {1, 2, 3}:
                raise ValueError(f"incomplete measured runs: {experiment}/{variant}")
            experiment_summary[variant] = {
                "application_ids": sorted(record["application_id"] for record in records),
                "median": {
                    metric: median(record[metric] for record in records)
                    for metric in METRICS
                },
            }
        output["experiments"][experiment] = experiment_summary
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = summarize(sorted(args.metrics_dir.glob("*.metrics.json")))
    args.output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print("M7_BENCHMARK_SUMMARY_PASS variants=6 measured_runs=18")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
