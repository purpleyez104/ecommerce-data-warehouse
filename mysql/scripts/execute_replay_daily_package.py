#!/usr/bin/env python3
"""Execute one validated replay package through the MySQL CLI.

默认不接触数据库。调用方必须同时给出 ``--execute`` 与匹配的
``--confirm-day``，密码只从 ``MYSQL_PASSWORD`` 读取并写入权限收紧的临时
defaults file，不进入参数、日志或结果文件。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from replay_daily_package import ReplayPlanError, build_plan, sha256
from replay_runtime import (
    expected_set_sql,
    mysql_command,
    mysql_timeout_seconds,
    parse_gate_output,
    query_ledger,
    source_gate_rule_ids,
)


def execute(replay_bundle: Path, day: int, output: Path, mysql_client: str) -> dict:
    if output.exists():
        raise ReplayPlanError(f"output already exists; choose a new directory: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    # Windows Sandbox 的系统 TEMP 可能只读；临时执行材料与结果放在同一已授权父目录。
    with tempfile.TemporaryDirectory(prefix=".mysql-replay-", dir=output.parent) as temp_name:
        temp = Path(temp_name)
        plan_dir = temp / "plan"
        plan = build_plan(replay_bundle, day, plan_dir)
        defaults = temp / "mysql.cnf"
        command, target = mysql_command(defaults, mysql_client)
        timeout = mysql_timeout_seconds()
        sql_path = plan_dir / "replay.sql"
        gate_source = Path(__file__).resolve().parents[1] / "sql" / "source_gate.sql"
        gate_text = gate_source.read_text(encoding="utf-8")
        if sha256(gate_source) != plan["source_gate"]["sha256"]:
            raise ReplayPlanError("source_gate.sql changed after planning")
        expected_rule_ids = source_gate_rule_ids(gate_text)
        already_applied = query_ledger(command, plan, timeout)
        if already_applied:
            completed = subprocess.run(
                command,
                input=(expected_set_sql(plan) + gate_text).encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
            )
            application_status = "already_applied"
        else:
            with sql_path.open("rb") as sql_input:
                completed = subprocess.run(
                    command,
                    stdin=sql_input,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=timeout,
                )
            application_status = "applied"
        if completed.returncode != 0:
            # MySQL Client 不会在 stderr 回显 defaults file 中的密码。保留受限长度的
            # 错误文本，避免真实 Runtime 只剩退出码而无法定位 SQL/Gate 失败点。
            error_text = completed.stderr.decode("utf-8", errors="replace").strip()
            if len(error_text) > 2000:
                error_text = error_text[-2000:]
            detail = f": {error_text}" if error_text else ""
            raise ReplayPlanError(f"mysql client failed with exit code {completed.returncode}{detail}")

        gate_output = temp / "source-gate.out"
        gate_output.write_bytes(completed.stdout)
        gate = parse_gate_output(gate_output, expected_rule_ids)
        if not query_ledger(command, plan, timeout):
            raise ReplayPlanError("replay_batch_ledger row is missing after successful execution")

        output.mkdir()
        persisted_gate = output / "source-gate.out"
        persisted_gate.write_bytes(gate_output.read_bytes())
        result = {
            "result_version": 1,
            "status": "executed",
            "day_number": day,
            "batch_id": plan["batch_id"],
            "dataset_version": plan["dataset_version"],
            "business_hash": plan["business_hash"],
            "package_manifest_sha256": plan["package_manifest_sha256"],
            "sql_sha256": sha256(sql_path),
            "source_gate_sha256": plan["source_gate"]["sha256"],
            "operation_count": plan["operation_count"],
            "database_contacted": True,
            "committed_after_source_gate": True,
            "application_status": application_status,
            "target_fingerprint": target,
            "rule_count": gate["rule_count"],
            "violation_count": gate["violation_count"],
            "source_gate_output_sha256": sha256(persisted_gate),
        }
        (output / "result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay-bundle", required=True, type=Path)
    parser.add_argument("--day", required=True, type=int, choices=range(61, 91), metavar="61..90")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm-day", type=int)
    parser.add_argument("--mysql-client", default="mysql", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if not args.execute or args.confirm_day != args.day:
        print("ERROR: --execute and matching --confirm-day are required", file=sys.stderr)
        return 2
    try:
        result = execute(args.replay_bundle, args.day, args.output, args.mysql_client)
    except (OSError, ReplayPlanError, subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
