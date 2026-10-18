#!/usr/bin/env python3
"""顺序执行一段 Daily Replay，并为每一天生成独立的提交后验收证据。

脚本先对整个区间执行静态计划校验，再按日调用单日 Executor。每一天提交后，
使用新的 MySQL 连接重新运行 Source Gate；任一天失败立即停止。已生成但未形成
完整 ``acceptance.json`` 的目录不会自动重放，避免重复写入已提交的数据。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import signal
import sys
import tempfile
from pathlib import Path

from execute_replay_daily_package import execute
from replay_daily_package import ReplayPlanError, build_plan, sha256
from replay_runtime import (
    EXPECTED_RULE_COUNT,
    current_target_fingerprint,
    expected_set_sql,
    mysql_command,
    mysql_timeout_seconds,
    parse_gate_output,
    query_ledger,
    source_gate_rule_ids,
)


def write_json(path: Path, value: object) -> None:
    """以原子替换方式写入不含 Secret 的状态文件。"""
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temp.replace(path)


def run_postcommit_gate(plan: dict, output: Path, mysql_client: str) -> dict:
    """在新连接中执行 Source Gate，并保存可复核的原始结果。"""
    # Planner 的公开 Contract 只记录仓库相对路径和 Hash；本脚本与单日 Executor
    # 同属 mysql/scripts，因此从部署结构解析真实文件，避免把机器绝对路径写入证据。
    gate_source = Path(__file__).resolve().parents[1] / "sql" / "source_gate.sql"
    if not gate_source.is_file() or sha256(gate_source) != plan["source_gate"]["sha256"]:
        raise ReplayPlanError("source_gate.sql is missing or its SHA-256 changed")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".mysql-postcommit-", dir=output.parent) as temp_name:
        temp = Path(temp_name)
        defaults = temp / "mysql.cnf"
        sql_path = temp / "postcommit.sql"
        sql_path.write_text(
            expected_set_sql(plan) + gate_source.read_text(encoding="utf-8"),
            encoding="utf-8",
            newline="\n",
        )
        command, target = mysql_command(defaults, mysql_client)
        with sql_path.open("rb") as sql_input, output.open("wb") as gate_output:
            completed = subprocess.run(
                command,
                stdin=sql_input,
                stdout=gate_output,
                stderr=subprocess.PIPE,
                timeout=mysql_timeout_seconds(),
            )
        if completed.returncode != 0:
            output.unlink(missing_ok=True)
            error_text = completed.stderr.decode("utf-8", errors="replace").strip()
            if len(error_text) > 2000:
                error_text = error_text[-2000:]
            detail = f": {error_text}" if error_text else ""
            raise ReplayPlanError(
                f"postcommit mysql client failed with exit code {completed.returncode}{detail}"
            )
    gate = parse_gate_output(output, source_gate_rule_ids(gate_source.read_text(encoding="utf-8")))
    gate["target_fingerprint"] = target
    return gate


def completed_acceptance(day_dir: Path, day: int, plan: dict) -> dict | None:
    """识别可安全跳过的已验收日；任何不完整状态都拒绝自动续跑。"""
    acceptance_path = day_dir / "acceptance.json"
    if not day_dir.exists():
        return None
    if not acceptance_path.is_file():
        return None
    try:
        acceptance = json.loads(acceptance_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReplayPlanError(f"day {day} acceptance.json is invalid: {exc}") from exc
    expected = {
        "status": "verified",
        "day_number": day,
        "business_hash": plan["business_hash"],
        "package_manifest_sha256": plan["package_manifest_sha256"],
        "source_gate_sha256": plan["source_gate"]["sha256"],
        "rule_count": EXPECTED_RULE_COUNT,
        "violation_count": 0,
        "scope": "mysql_source_replay",
        "target_fingerprint": current_target_fingerprint(),
    }
    for key, value in expected.items():
        if acceptance.get(key) != value:
            raise ReplayPlanError(f"day {day} acceptance.json mismatch: {key}")
    gate_path = day_dir / "postcommit-gate.out"
    if acceptance.get("postcommit_gate_sha256") != sha256(gate_path):
        raise ReplayPlanError(f"day {day} postcommit gate SHA-256 mismatch")
    gate_source = Path(__file__).resolve().parents[1] / "sql" / "source_gate.sql"
    parse_gate_output(gate_path, source_gate_rule_ids(gate_source.read_text(encoding="utf-8")))
    return acceptance


def next_day_already_committed(plan: dict, output: Path, mysql_client: str) -> bool:
    """只读核对无 Acceptance 的下一日是否已在中断前提交。"""
    with tempfile.TemporaryDirectory(prefix=".replay-resume-ledger-", dir=output.parent) as temp_name:
        command, _ = mysql_command(Path(temp_name) / "mysql.cnf", mysql_client)
        return query_ledger(command, plan, mysql_timeout_seconds())


def execute_range(
    replay_bundle: Path,
    start_day: int,
    end_day: int,
    output: Path,
    mysql_client: str,
    resume: bool,
) -> dict:
    """完成整段预检后逐日执行，并在失败点停止。"""
    if start_day > end_day:
        raise ReplayPlanError("start-day must not be greater than end-day")
    if output.exists() and not resume:
        raise ReplayPlanError("output already exists; use --resume only after inspecting it")
    output.parent.mkdir(parents=True, exist_ok=True)
    plans: dict[int, dict] = {}
    with tempfile.TemporaryDirectory(prefix=".replay-range-preflight-", dir=output.parent) as temp_name:
        preflight_root = Path(temp_name)
        for day in range(start_day, end_day + 1):
            plans[day] = build_plan(replay_bundle, day, preflight_root / f"day_{day}")
    output.mkdir(parents=True, exist_ok=True)

    state = {
        "state_version": 1,
        "status": "running",
        "start_day": start_day,
        "end_day": end_day,
        "completed_days": [],
        "next_day": start_day,
        "database_contacted": False,
        "scope": "mysql_source_replay",
        "target_fingerprint": current_target_fingerprint(),
    }
    if resume:
        accepted_days = []
        for day in range(start_day, end_day + 1):
            accepted = completed_acceptance(output / f"day_{day}", day, plans[day])
            if accepted is None:
                break
            accepted_days.append(day)
        if accepted_days:
            last_day = accepted_days[-1]
            next_day = last_day + 1
            incomplete_next = (
                next_day <= end_day
                and (output / f"day_{next_day}").is_dir()
                and not (output / f"day_{next_day}" / "acceptance.json").is_file()
            )
            # 进程可能在下一日事务提交后、Acceptance 落盘前被终止。此时数据库
            # 已领先于最后一份 Acceptance，不能再用旧日 Expected Result 执行 Gate。
            # 先只读核对下一日 Ledger；存在时交给单日 Executor 走 already_applied
            # 恢复路径并补齐 Gate/Acceptance，否则仍验证最后已验收日后再继续。
            committed_next = (
                incomplete_next
                and next_day_already_committed(plans[next_day], output, mysql_client)
            )
            if not committed_next:
                resume_gate = output / f"resume-check-day-{last_day}.out"
                run_postcommit_gate(plans[last_day], resume_gate, mysql_client)
    for day in range(start_day, end_day + 1):
        day_dir = output / f"day_{day}"
        accepted = completed_acceptance(day_dir, day, plans[day]) if resume else None
        if accepted is not None:
            state["completed_days"].append(day)
            state["next_day"] = day + 1 if day < end_day else None
            state["database_contacted"] = True
            write_json(output / "range-state.json", state)
            continue
        day_dir.mkdir(exist_ok=True)
        try:
            state["database_contacted"] = True
            write_json(output / "range-state.json", state)
            execution_dir = day_dir / "execution"
            recovery_index = 1
            while execution_dir.exists():
                execution_dir = day_dir / f"execution-recovery-{recovery_index}"
                recovery_index += 1
            result = execute(replay_bundle, day, execution_dir, mysql_client)
            gate_path = day_dir / "postcommit-gate.out"
            gate = run_postcommit_gate(plans[day], gate_path, mysql_client)
            if gate["target_fingerprint"] != result["target_fingerprint"]:
                raise ReplayPlanError("daily execution and postcommit gate target mismatch")
            acceptance = {
                "acceptance_version": 1,
                "status": "verified",
                "scope": "mysql_source_replay",
                "day_number": day,
                "batch_id": result["batch_id"],
                "business_hash": result["business_hash"],
                "package_manifest_sha256": result["package_manifest_sha256"],
                "operation_count": result["operation_count"],
                "source_gate_sha256": result["source_gate_sha256"],
                "rule_count": gate["rule_count"],
                "violation_count": gate["violation_count"],
                "postcommit_gate_sha256": sha256(gate_path),
                "target_fingerprint": result["target_fingerprint"],
                "application_status": result["application_status"],
            }
            write_json(day_dir / "acceptance.json", acceptance)
        except KeyboardInterrupt:
            state["status"] = "interrupted"
            state["next_day"] = day
            write_json(output / "range-state.json", state)
            raise
        except Exception:
            state["status"] = "failed"
            state["next_day"] = day
            write_json(output / "range-state.json", state)
            raise
        state["completed_days"].append(day)
        state["next_day"] = day + 1 if day < end_day else None
        write_json(output / "range-state.json", state)
    state["status"] = "verified"
    write_json(output / "range-state.json", state)
    return state


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay-bundle", required=True, type=Path)
    parser.add_argument("--start-day", required=True, type=int, choices=range(61, 91))
    parser.add_argument("--end-day", required=True, type=int, choices=range(61, 91))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm-range")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--mysql-client", default="mysql", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    expected_confirmation = f"{args.start_day}-{args.end_day}"
    if not args.execute or args.confirm_range != expected_confirmation:
        print(
            f"ERROR: --execute and --confirm-range {expected_confirmation} are required",
            file=sys.stderr,
        )
        return 2

    def terminate_handler(_signum, _frame):
        """把外部终止转成可记录的失败，而不是遗留 stale running 状态。"""
        raise ReplayPlanError("range execution terminated by signal")

    signal.signal(signal.SIGTERM, terminate_handler)
    try:
        state = execute_range(
            args.replay_bundle,
            args.start_day,
            args.end_day,
            args.output,
            args.mysql_client,
            args.resume,
        )
    except (OSError, ReplayPlanError, subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(state, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
