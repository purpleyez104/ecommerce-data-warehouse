#!/usr/bin/env python3
"""Execute one independently testable M6 model, quality, serving, or reconciliation stage."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


def _checked_date(value: str, name: str) -> str:
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"invalid {name}: {value}") from exc
    return value


def _checked_id(value: str, name: str) -> str:
    if not SAFE_ID.fullmatch(value):
        raise ValueError(f"unsafe {name}: {value}")
    return value


def build_commands(args: argparse.Namespace, work_dir: Path) -> list[list[str]]:
    """返回无 Shell 拼接的命令列表，所有动态参数均经过白名单校验。"""
    business_date = _checked_date(args.business_date, "business_date")
    batch_id = _checked_id(args.batch_id, "batch_id")
    python = sys.executable
    spark_sql = os.environ.get("SPARK_SQL", "/data/module/spark/bin/spark-sql")
    spark_submit = os.environ.get("SPARK_SUBMIT", "/data/module/spark/bin/spark-submit")
    semantic = ROOT / "hive/model/model_contract.json"
    physical = ROOT / "hive/model/model_physical_contract.json"

    def render(script: str, output: str, *extra: str) -> list[str]:
        return [python, str(ROOT / "spark/scripts" / script), *extra, "--output", str(work_dir / output)]

    if args.stage == "model_ready":
        return [
            render("render_model_gate_sql.py", "model_gate.sql", "--semantic-contract", str(semantic), "--physical-contract", str(physical)),
            [spark_sql, "-f", str(work_dir / "model_gate.sql")],
        ]
    if args.stage == "dim_dwd":
        return [
            render("render_dim_snapshot_sql.py", "dim.sql", "--semantic-contract", str(semantic), "--physical-contract", str(physical), "--snapshot-date", business_date, "--batch-id", batch_id),
            [spark_sql, "-f", str(work_dir / "dim.sql")],
            render("render_product_scd2_sql.py", "product.sql", "--semantic-contract", str(semantic), "--physical-contract", str(physical), "--batch-id", batch_id),
            [spark_sql, "-f", str(work_dir / "product.sql")],
            render("render_dwd_sql.py", "dwd.sql", "--semantic-contract", str(semantic), "--physical-contract", str(physical), "--batch-id", batch_id),
            [spark_sql, "-f", str(work_dir / "dwd.sql")],
            render("render_model_gate_sql.py", "model_gate.sql", "--semantic-contract", str(semantic), "--physical-contract", str(physical)),
            [spark_sql, "-f", str(work_dir / "model_gate.sql")],
        ]
    if args.stage == "dws_ads":
        as_of_date = _checked_date(getattr(args, "as_of_date", None) or business_date, "as_of_date")
        if as_of_date < business_date:
            raise ValueError("as_of_date must not precede business_date")
        return [
            render("render_aggregate_sql.py", "aggregate.sql", "--as-of-date", as_of_date, "--batch-id", batch_id),
            [spark_sql, "-f", str(work_dir / "aggregate.sql")],
        ]
    if args.stage == "quality":
        run_id = _checked_id(args.run_id, "run_id")
        inject_failure_rule_id = getattr(args, "inject_failure_rule_id", None)
        injection_args = []
        if inject_failure_rule_id is not None:
            injection_args = [
                "--inject-failure-rule-id",
                _checked_id(inject_failure_rule_id, "inject_failure_rule_id"),
            ]
        return [
            render(
                "render_quality_result_sql.py", "quality.sql", "--run-id", run_id,
                "--batch-id", batch_id, *injection_args,
            ),
            [spark_sql, "-f", str(work_dir / "quality.sql")],
        ]
    start_date = _checked_date(args.data_start_date, "data_start_date")
    if start_date > business_date:
        raise ValueError("data_start_date must not exceed business_date")
    connector = os.environ.get("DORIS_CONNECTOR_JAR")
    if not connector:
        raise ValueError("DORIS_CONNECTOR_JAR is required")
    contract = ROOT / "doris/serving_contract.json"
    doris_java_home = os.environ.get(
        "DORIS_JAVA_HOME", "/usr/lib/jvm/java-8-openjdk-amd64"
    )
    # 当前 Spark 3.5.9 集群的全局 KryoSerializer 会在小型聚合的最终
    # DirectTaskResult 解码时稳定触发 EOFException。Serving 作业在任务级
    # 使用 Spark 默认 JavaSerializer，避免扩大到全局配置和其他离线任务。
    serving_serializer = "spark.serializer=org.apache.spark.serializer.JavaSerializer"
    if args.stage == "doris":
        # Doris Connector 26.0.0 的 Spark 3.x 官方兼容基线为 Java 8。
        # 仅约束 Doris 写入的 YARN 容器，避免改变集群默认 Java 与其他任务。
        return [
            render("render_doris_range_load.py", "doris_load.py", "--contract", str(contract), "--start-date", start_date, "--end-date", business_date, "--batch-id", batch_id),
            [
                spark_submit,
                "--conf", f"spark.yarn.appMasterEnv.JAVA_HOME={doris_java_home}",
                "--conf", f"spark.executorEnv.JAVA_HOME={doris_java_home}",
                "--conf", serving_serializer,
                "--jars", connector,
                str(work_dir / "doris_load.py"),
            ],
        ]
    _checked_id(args.run_id, "run_id")
    return [
        render("render_doris_reconciliation.py", "reconciliation.py", "--contract", str(contract), "--start-date", start_date, "--end-date", business_date),
        [
            spark_submit,
            "--conf", serving_serializer,
            "--jars", connector,
            str(work_dir / "reconciliation.py"),
        ],
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("model_ready", "dim_dwd", "dws_ads", "quality", "doris", "reconciliation"))
    parser.add_argument("--business-date", required=True)
    parser.add_argument("--as-of-date")
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--data-start-date")
    parser.add_argument("--inject-failure-rule-id")
    args = parser.parse_args()
    if args.inject_failure_rule_id and args.stage != "quality":
        parser.error("--inject-failure-rule-id is only valid for quality")
    if args.stage in {"quality", "reconciliation"} and not args.run_id:
        parser.error(f"{args.stage} requires --run-id")
    if args.stage in {"doris", "reconciliation"} and not args.data_start_date:
        parser.error(f"{args.stage} requires --data-start-date")
    work_dir = ROOT / "runtime/scheduler" / args.batch_id / args.stage
    # Scheduler 重试复用相同 batch_id；Renderer 覆盖确定性脚本，业务表自身按分区或唯一键幂等。
    work_dir.mkdir(parents=True, exist_ok=True)
    try:
        for command in build_commands(args, work_dir):
            completed = subprocess.run(command, cwd=ROOT, check=False)
            if completed.returncode != 0:
                return completed.returncode
    except (OSError, ValueError) as exc:
        print(f"{args.stage.upper()}_FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"{args.stage.upper()}_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
