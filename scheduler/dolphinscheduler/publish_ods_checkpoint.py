#!/usr/bin/env python3
"""Publish the local ODS batch evidence to a shared HDFS checkpoint directory."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def publish(batch_output: Path, checkpoint_dir: str) -> None:
    """上传状态与计划文件；后续 Task 可在任意 Worker 上读取同一份证据。"""
    evidence = (batch_output / "state.json", batch_output / "batch_plan.json")
    for path in evidence:
        if not path.is_file():
            raise ValueError(f"missing ODS evidence: {path.name}")
    subprocess.run(["hdfs", "dfs", "-mkdir", "-p", checkpoint_dir], check=True)
    for path in evidence:
        subprocess.run(
            ["hdfs", "dfs", "-put", "-f", str(path), f"{checkpoint_dir}/{path.name}"],
            check=True,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-output", type=Path, required=True)
    parser.add_argument("--checkpoint-dir", required=True)
    args = parser.parse_args()
    try:
        publish(args.batch_output, args.checkpoint_dir)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"ODS_CHECKPOINT_PUBLISH_FAIL: {exc}")
        return 1
    print("ODS_CHECKPOINT_PUBLISH_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
