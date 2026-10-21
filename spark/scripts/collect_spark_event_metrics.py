#!/usr/bin/env python3
"""Collect stable application and task metrics from one Spark JSON event log."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable


SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


def _events(lines: Iterable[str]) -> Iterable[dict[str, Any]]:
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict) or "Event" not in value:
            raise ValueError(f"invalid Spark event at line {number}")
        yield value


def collect_metrics(lines: Iterable[str]) -> dict[str, Any]:
    """汇总成功 Task 的 I/O、Shuffle、Spill 与执行时间，避免依赖 UI 截图。"""
    result: dict[str, Any] = {
        "application_id": None,
        "application_name": None,
        "start_time_ms": None,
        "end_time_ms": None,
        "duration_ms": None,
        "job_count": 0,
        "failed_job_count": 0,
        "stage_count": 0,
        "task_count": 0,
        "failed_task_count": 0,
        "executor_run_time_ms": 0,
        "executor_cpu_time_ns": 0,
        "input_bytes": 0,
        "input_records": 0,
        "shuffle_read_bytes": 0,
        "shuffle_read_records": 0,
        "shuffle_write_bytes": 0,
        "shuffle_write_records": 0,
        "memory_spill_bytes": 0,
        "disk_spill_bytes": 0,
    }
    for event in _events(lines):
        kind = event["Event"]
        if kind == "SparkListenerApplicationStart":
            result["application_id"] = event.get("App ID")
            result["application_name"] = event.get("App Name")
            result["start_time_ms"] = event.get("Timestamp")
        elif kind == "SparkListenerApplicationEnd":
            result["end_time_ms"] = event.get("Timestamp")
        elif kind == "SparkListenerJobEnd":
            result["job_count"] += 1
            if event.get("Job Result", {}).get("Result") != "JobSucceeded":
                result["failed_job_count"] += 1
        elif kind == "SparkListenerStageCompleted":
            result["stage_count"] += 1
        elif kind == "SparkListenerTaskEnd":
            if event.get("Task End Reason", {}).get("Reason") != "Success":
                result["failed_task_count"] += 1
                continue
            metrics = event.get("Task Metrics", {})
            result["task_count"] += 1
            result["executor_run_time_ms"] += metrics.get("Executor Run Time", 0)
            result["executor_cpu_time_ns"] += metrics.get("Executor CPU Time", 0)
            result["memory_spill_bytes"] += metrics.get("Memory Bytes Spilled", 0)
            result["disk_spill_bytes"] += metrics.get("Disk Bytes Spilled", 0)
            input_metrics = metrics.get("Input Metrics", {})
            result["input_bytes"] += input_metrics.get("Bytes Read", 0)
            result["input_records"] += input_metrics.get("Records Read", 0)
            shuffle_read = metrics.get("Shuffle Read Metrics", {})
            result["shuffle_read_bytes"] += (
                shuffle_read.get("Remote Bytes Read", 0)
                + shuffle_read.get("Local Bytes Read", 0)
            )
            result["shuffle_read_records"] += shuffle_read.get("Total Records Read", 0)
            shuffle_write = metrics.get("Shuffle Write Metrics", {})
            result["shuffle_write_bytes"] += shuffle_write.get("Shuffle Bytes Written", 0)
            result["shuffle_write_records"] += shuffle_write.get("Shuffle Records Written", 0)
    start = result["start_time_ms"]
    end = result["end_time_ms"]
    if not result["application_id"] or not isinstance(start, int) or not isinstance(end, int):
        raise ValueError("Spark event log is missing application boundaries")
    result["duration_ms"] = end - start
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-log", type=Path, required=True)
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--variant", required=True)
    parser.add_argument("--run-index", type=int, required=True)
    parser.add_argument("--measured", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    for value, name in ((args.experiment, "experiment"), (args.variant, "variant")):
        if not SAFE_ID.fullmatch(value):
            parser.error(f"unsafe {name}")
    if args.run_index < 0:
        parser.error("run-index must be non-negative")
    with args.event_log.open(encoding="utf-8") as handle:
        result = collect_metrics(handle)
    result.update({
        "experiment": args.experiment,
        "variant": args.variant,
        "run_index": args.run_index,
        "measured": args.measured,
    })
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        f"SPARK_EVENT_METRICS_PASS application_id={result['application_id']} "
        f"tasks={result['task_count']} duration_ms={result['duration_ms']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
