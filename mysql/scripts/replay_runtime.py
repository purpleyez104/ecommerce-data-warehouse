"""Daily Replay 的 MySQL 运行、Ledger 与 Source Gate 公共边界。"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from replay_daily_package import ReplayPlanError


SAFE_DATABASE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
SAFE_USER = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]*")
RULE_PATTERN = re.compile(r"^-- RULE: ([a-z0-9_.]+)$", re.MULTILINE)
EXPECTED_RULE_COUNT = 45
DEFAULT_MYSQL_TIMEOUT_SECONDS = 300


def required_env(name: str) -> str:
    """读取必需环境变量，并拒绝会破坏 Client 配置的换行。"""
    value = os.environ.get(name, "")
    if not value:
        raise ReplayPlanError(f"{name} is required")
    if "\n" in value or "\r" in value:
        raise ReplayPlanError(f"{name} must not contain a newline")
    return value


def mysql_timeout_seconds() -> int:
    """返回有界 MySQL Client 超时，避免网络或锁等待无限挂起。"""
    raw = os.environ.get("MYSQL_CLIENT_TIMEOUT_SECONDS", str(DEFAULT_MYSQL_TIMEOUT_SECONDS))
    if not raw.isdigit() or not 1 <= int(raw) <= 3600:
        raise ReplayPlanError("MYSQL_CLIENT_TIMEOUT_SECONDS must be between 1 and 3600")
    return int(raw)


def target_fingerprint(host: str, port: str, database: str, user: str) -> str:
    """生成去敏目标身份，防止 Resume 把旧证据用于另一个实例或数据库。"""
    identity = json.dumps([host, port, database, user], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def current_target_fingerprint() -> str:
    """从当前环境计算去敏目标身份，不建立数据库连接。"""
    return target_fingerprint(
        required_env("MYSQL_HOST"),
        required_env("MYSQL_PORT"),
        required_env("MYSQL_DATABASE"),
        required_env("MYSQL_USER"),
    )


def mysql_command(defaults: Path, mysql_client: str) -> tuple[list[str], str]:
    """构造密码不进入 argv 的命令，并返回目标身份指纹。"""
    host = required_env("MYSQL_HOST")
    port = required_env("MYSQL_PORT")
    database = required_env("MYSQL_DATABASE")
    user = required_env("MYSQL_USER")
    password = required_env("MYSQL_PASSWORD")
    if not port.isdigit() or not 1 <= int(port) <= 65535:
        raise ReplayPlanError("MYSQL_PORT must be between 1 and 65535")
    if SAFE_DATABASE.fullmatch(database) is None:
        raise ReplayPlanError("MYSQL_DATABASE must be a safe SQL identifier")
    if SAFE_USER.fullmatch(user) is None:
        raise ReplayPlanError("MYSQL_USER contains unsupported characters")
    client_path = shutil.which(mysql_client)
    if client_path is None:
        raise ReplayPlanError("mysql client is required")
    escaped = password.replace("\\", "\\\\").replace('"', '\\"')
    defaults.write_text(
        f'[client]\nuser={user}\npassword="{escaped}"\n', encoding="utf-8", newline="\n"
    )
    try:
        os.chmod(defaults, 0o600)
    except OSError:
        pass
    return [
        client_path,
        f"--defaults-extra-file={defaults}",
        "--protocol=TCP",
        f"--host={host}",
        f"--port={port}",
        f"--database={database}",
        "--batch",
        "--skip-column-names",
        "--raw",
    ], target_fingerprint(host, port, database, user)


def source_gate_rule_ids(source: str) -> frozenset[str]:
    """从 Source Gate 的声明提取精确规则集合。"""
    rule_ids = RULE_PATTERN.findall(source)
    if len(rule_ids) != EXPECTED_RULE_COUNT or len(set(rule_ids)) != EXPECTED_RULE_COUNT:
        raise ReplayPlanError("source_gate.sql must declare exactly 45 unique rule ids")
    return frozenset(rule_ids)


def parse_gate_output(path: Path, expected_rule_ids: frozenset[str]) -> dict:
    """验证输出恰好覆盖正式 Rule ID 集合，且所有规则零违规。"""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise ReplayPlanError(f"cannot read source gate output: {exc}") from exc
    rows: list[tuple[str, int]] = []
    for line_number, line in enumerate(lines, start=1):
        if not line:
            continue
        fields = line.split("\t")
        if len(fields) != 2:
            raise ReplayPlanError(f"source gate line {line_number} must contain two columns")
        try:
            violation_count = int(fields[1])
        except ValueError as exc:
            raise ReplayPlanError(f"source gate line {line_number} has invalid count") from exc
        if violation_count < 0:
            raise ReplayPlanError(f"source gate line {line_number} has negative count")
        rows.append((fields[0], violation_count))
    actual_ids = [rule_id for rule_id, _ in rows]
    if len(actual_ids) != len(expected_rule_ids) or set(actual_ids) != expected_rule_ids:
        raise ReplayPlanError("source gate rule id set does not match source_gate.sql")
    violation_total = sum(count for _, count in rows)
    if violation_total:
        raise ReplayPlanError(f"source gate has {violation_total} violations")
    return {"rule_count": len(rows), "violation_count": violation_total}


def ledger_lookup_sql(batch_id: str) -> bytes:
    """以 Hex Literal 查询 Ledger，避免外部文本进入 SQL 字面量。"""
    encoded = batch_id.encode("utf-8").hex()
    return (
        "SELECT day_number,business_hash,package_manifest_sha256,operation_count "
        f"FROM replay_batch_ledger WHERE batch_id=CONVERT(X'{encoded}' USING utf8mb4);\n"
    ).encode("utf-8")


def query_ledger(command: list[str], plan: dict, timeout: int) -> bool:
    """确认 Batch 是否已提交；同一 ID 指向不同内容时拒绝继续。"""
    completed = subprocess.run(
        command,
        input=ledger_lookup_sql(plan["batch_id"]),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise ReplayPlanError(f"cannot query replay_batch_ledger: {detail or completed.returncode}")
    text = completed.stdout.decode("utf-8", errors="strict").strip()
    if not text:
        return False
    expected = [
        str(plan["day_number"]),
        plan["business_hash"],
        plan["package_manifest_sha256"],
        str(plan["operation_count"]),
    ]
    if text.split("\t") != expected:
        raise ReplayPlanError("replay_batch_ledger conflicts with the requested package")
    return True


def expected_set_sql(plan: dict) -> str:
    """把 Planner 已校验的 Expected Result 转成 Source Gate Session 变量。"""
    table_counts = plan["expected_table_row_counts"]
    status_counts = plan["expected_order_status_counts"]
    assignments = [f"@expected_{table}={table_counts[table]}" for table in table_counts]
    assignments.extend(
        [
            f"@expected_paid_orders={status_counts['PAID']}",
            f"@expected_canceled_orders={status_counts['CANCELED']}",
            f"@expected_created_orders={status_counts['CREATED']}",
        ]
    )
    return "SET " + ",".join(assignments) + ";\n"
