#!/usr/bin/env python3
"""Fail unless one DataX/ODS batch was published for the requested business date."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import date
from pathlib import Path


def verify(batch_state: Path, business_date: str) -> None:
    """同时核对状态和 Batch Plan，避免仅凭一个 published 字符串放行。"""
    date.fromisoformat(business_date)
    state = json.loads(batch_state.read_text(encoding="utf-8"))
    plan_path = batch_state.with_name("batch_plan.json")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    verify_payloads(state, plan, business_date)


def read_hdfs_json(path: str) -> dict:
    """从共享 HDFS Checkpoint 读取 JSON，避免依赖某一 Worker 的本地磁盘。"""
    result = subprocess.run(
        ["hdfs", "dfs", "-cat", path],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def verify_hdfs(checkpoint_dir: str, business_date: str) -> None:
    date.fromisoformat(business_date)
    state = read_hdfs_json(f"{checkpoint_dir}/state.json")
    plan = read_hdfs_json(f"{checkpoint_dir}/batch_plan.json")
    verify_payloads(state, plan, business_date)


def verify_payloads(state: dict, plan: dict, business_date: str) -> None:
    """核对发布状态、Job 数和请求日期是否确实包含在已发布分区中。

    Bootstrap 的 plan.business_date 是 Snapshot 截止日；历史补数可以读取该
    Snapshot 已发布的较早分区，因此不能强制它与请求日期相等。
    """
    if state.get("state") != "published" or state.get("publish_allowed") is not True:
        raise ValueError("ODS batch is not published")
    snapshot_date = plan.get("business_date")
    if not isinstance(snapshot_date, str):
        raise ValueError("ODS batch business_date is missing")
    if date.fromisoformat(snapshot_date) < date.fromisoformat(business_date):
        raise ValueError("ODS batch does not cover a future business_date")
    if not isinstance(plan.get("job_count"), int) or plan["job_count"] != 21:
        raise ValueError("ODS batch must contain exactly 21 DataX jobs")
    affected = plan.get("affected_business_dates")
    if not isinstance(affected, list) or business_date not in affected:
        raise ValueError("business_date is absent from affected partitions")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--batch-state", type=Path)
    source.add_argument("--checkpoint-dir")
    parser.add_argument("--business-date", required=True)
    args = parser.parse_args()
    try:
        if args.checkpoint_dir:
            verify_hdfs(args.checkpoint_dir, args.business_date)
        else:
            verify(args.batch_state, args.business_date)
    except (OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        print(f"ODS_READY_FAIL: {exc}")
        return 1
    print("ODS_READY_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
