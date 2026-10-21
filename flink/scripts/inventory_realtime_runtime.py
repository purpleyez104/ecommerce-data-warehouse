#!/usr/bin/env python3
"""只读盘点 Formal Realtime 的 Kafka、YARN 与 HDFS Runtime 资产。

脚本只调用各组件的查询命令，并把结果统一输出为 JSON。连接目标、CLI
位置与 HDFS Root 均由调用方显式传入，避免误用 Pilot 环境或历史恢复点。
任一查询失败时立即停止并返回非零状态。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Sequence
from urllib.parse import urlsplit, urlunsplit


CONTRACT_VERSION = "realtime-runtime-inventory/v1"
SECRET_ASSIGNMENT = re.compile(
    r"(?i)(password|passwd|secret|token|access[_-]?key)\s*([=:])\s*([^\s,;]+)"
)


class InventoryError(RuntimeError):
    """表示参数或只读查询未满足 Inventory Contract。"""


@dataclass(frozen=True)
class CommandResult:
    """单个只读命令的去敏结果。"""

    status: str
    lines: list[str]


def redact(value: str) -> str:
    """去除 URL userinfo 与常见 Secret 赋值，避免查询输出泄露凭据。"""

    def replace_url(match: re.Match[str]) -> str:
        raw_url = match.group(0)
        parsed = urlsplit(raw_url)
        hostname = parsed.hostname or ""
        port = f":{parsed.port}" if parsed.port else ""
        return urlunsplit((parsed.scheme, f"{hostname}{port}", parsed.path, "", ""))

    without_url_secrets = re.sub(r"[a-zA-Z][a-zA-Z0-9+.-]*://[^\s]+", replace_url, value)
    return SECRET_ASSIGNMENT.sub(r"\1\2***", without_url_secrets)


def run_read_only(command: Sequence[str], timeout_seconds: int, env: dict[str, str]) -> CommandResult:
    """执行无 Shell 的只读命令；失败、超时或空命令均立即报错。"""

    if not command or not command[0].strip():
        raise InventoryError("查询命令不能为空")
    try:
        completed = subprocess.run(
            list(command),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            env=env,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise InventoryError(f"只读查询无法执行: {redact(str(exc))}") from exc

    if completed.returncode != 0:
        detail = redact(completed.stderr.strip() or completed.stdout.strip() or "无错误详情")
        raise InventoryError(f"只读查询失败，exit={completed.returncode}: {detail}")
    lines = [redact(line.rstrip()) for line in completed.stdout.splitlines() if line.strip()]
    return CommandResult(status="queried", lines=lines)


def validate_hdfs_root(value: str, label: str) -> str:
    """拒绝根目录和相对路径，限制递归查询的资产边界。"""

    parsed = urlsplit(value)
    path = parsed.path if parsed.scheme else value
    normalized = str(PurePosixPath(path))
    if not path.startswith("/") or normalized in {"/", "."}:
        raise InventoryError(f"{label} 必须是非根目录的绝对 HDFS 路径")
    if parsed.scheme and parsed.scheme != "hdfs":
        raise InventoryError(f"{label} 只允许 hdfs:// URI 或绝对 HDFS Path")
    return value.rstrip("/")


def build_inventory_commands(
    *,
    kafka_topics_command: str,
    yarn_command: str,
    hdfs_command: str,
    bootstrap_server: str,
    topic_namespace: str,
    checkpoint_root: str,
    savepoint_root: str,
) -> dict[str, list[str]]:
    """构造固定的只读命令，供 CLI 和 Contract Test 复用。"""

    topic_pattern = rf"{re.escape(topic_namespace)}\..*"
    return {
        "kafka_list": [
            kafka_topics_command,
            "--bootstrap-server",
            bootstrap_server,
            "--list",
        ],
        "kafka_describe": [
            kafka_topics_command,
            "--bootstrap-server",
            bootstrap_server,
            "--describe",
            "--topic",
            topic_pattern,
        ],
        "yarn_applications": [yarn_command, "application", "-list", "-appStates", "ALL"],
        "checkpoints": [hdfs_command, "dfs", "-ls", "-R", checkpoint_root],
        "savepoints": [hdfs_command, "dfs", "-ls", "-R", savepoint_root],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="只读盘点 Formal Realtime Kafka Topic、YARN Application、Checkpoint 与 Savepoint"
    )
    parser.add_argument("--bootstrap-server", required=True, help="Kafka bootstrap server，不得包含认证信息")
    parser.add_argument("--topic-namespace", required=True, help="仅保留此前缀的 Formal Topic")
    parser.add_argument("--checkpoint-root", required=True, help="Formal Checkpoint HDFS Root")
    parser.add_argument("--savepoint-root", required=True, help="Formal Savepoint HDFS Root")
    parser.add_argument("--kafka-topics-command", required=True, help="kafka-topics.sh 的显式路径")
    parser.add_argument("--yarn-command", required=True, help="yarn CLI 的显式路径")
    parser.add_argument("--hdfs-command", required=True, help="hdfs CLI 的显式路径")
    parser.add_argument("--yarn-conf-dir", help="可选 YARN_CONF_DIR；只传给子进程")
    parser.add_argument("--timeout-seconds", type=int, default=30, help="每个查询的超时，默认 30 秒")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.timeout_seconds <= 0:
            raise InventoryError("--timeout-seconds 必须大于 0")
        if not args.topic_namespace.strip():
            raise InventoryError("--topic-namespace 不能为空")
        if "://" in args.bootstrap_server or "@" in args.bootstrap_server:
            raise InventoryError("--bootstrap-server 只能使用 host:port 列表，不得包含 URL 或认证信息")

        checkpoint_root = validate_hdfs_root(args.checkpoint_root, "--checkpoint-root")
        savepoint_root = validate_hdfs_root(args.savepoint_root, "--savepoint-root")
        child_env = os.environ.copy()
        if args.yarn_conf_dir:
            child_env["YARN_CONF_DIR"] = args.yarn_conf_dir

        commands = build_inventory_commands(
            kafka_topics_command=args.kafka_topics_command,
            yarn_command=args.yarn_command,
            hdfs_command=args.hdfs_command,
            bootstrap_server=args.bootstrap_server,
            topic_namespace=args.topic_namespace,
            checkpoint_root=checkpoint_root,
            savepoint_root=savepoint_root,
        )

        topics = run_read_only(
            commands["kafka_list"],
            args.timeout_seconds,
            child_env,
        )
        topic_prefix = f"{args.topic_namespace}."
        formal_topics = sorted(
            line.strip()
            for line in topics.lines
            if line.strip() == args.topic_namespace or line.strip().startswith(topic_prefix)
        )
        topic_descriptions = run_read_only(
            commands["kafka_describe"],
            args.timeout_seconds,
            child_env,
        )
        yarn = run_read_only(
            commands["yarn_applications"],
            args.timeout_seconds,
            child_env,
        )
        checkpoints = run_read_only(
            commands["checkpoints"],
            args.timeout_seconds,
            child_env,
        )
        savepoints = run_read_only(
            commands["savepoints"],
            args.timeout_seconds,
            child_env,
        )

        result = {
            "contract_version": CONTRACT_VERSION,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "mode": "read_only",
            "runtime_evidence": "inventory_only",
            "targets": {
                "bootstrap_server": redact(args.bootstrap_server),
                "topic_namespace": args.topic_namespace,
                "checkpoint_root": redact(checkpoint_root),
                "savepoint_root": redact(savepoint_root),
            },
            "inventory": {
                "kafka": {
                    "status": topics.status,
                    "matching_topics": formal_topics,
                    "descriptions": topic_descriptions.lines,
                },
                "yarn": asdict(yarn),
                "checkpoints": asdict(checkpoints),
                "savepoints": asdict(savepoints),
            },
        }
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except InventoryError as exc:
        print(f"ERROR: {redact(str(exc))}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
