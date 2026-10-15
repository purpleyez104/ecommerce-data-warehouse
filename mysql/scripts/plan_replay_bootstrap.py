#!/usr/bin/env python3
"""Validate a Replay bootstrap and render a secret-free MySQL load dry-run plan."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GENERATOR_SRC = REPO_ROOT / "mock" / "generator" / "business_generator" / "src"
sys.path.insert(0, str(GENERATOR_SRC))

from business_generator.common import canonical_json  # noqa: E402
from business_generator.contracts import LOAD_TABLE_ORDER, TABLE_COLUMNS, TABLE_ORDER  # noqa: E402
from validate_csv_bundle import (  # noqa: E402
    BundleError,
    render_load_sql,
    validate_csv_files,
    validate_references,
)


DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
PRIMARY_KEYS = {table: columns[0] for table, columns in TABLE_COLUMNS.items()}

# 这些字段代表记录已经发生的业务事实或当前状态更新时间，Bootstrap 中不得越过 Day 60 切换点。
# payment_deadline_at、expires_at、valid_to 等预先约定的未来有效期不属于已发生事实，故不在此列表。
CUTOVER_TIME_COLUMNS = {
    "biz_user": ("registered_at", "created_at", "updated_at"),
    "biz_visitor": ("first_seen_at", "last_seen_at", "created_at", "updated_at"),
    "biz_identity_mapping": ("effective_from", "effective_to", "recorded_at"),
    "biz_category": ("created_at", "updated_at"),
    "biz_spu": ("created_at", "updated_at"),
    "biz_sku": ("created_at", "updated_at"),
    "biz_product_change_event": ("effective_at", "recorded_at"),
    "biz_cart": ("created_at", "updated_at"),
    "biz_cart_item": ("created_at", "updated_at"),
    "biz_cart_merge_record": ("merged_at",),
    "biz_order": ("created_at", "paid_at", "canceled_at", "updated_at"),
    "biz_order_item": ("created_at", "updated_at"),
    "biz_order_status_event": ("occurred_at", "recorded_at"),
    "biz_payment_attempt": ("initiated_at", "succeeded_at", "created_at", "updated_at"),
    "biz_payment_event": ("occurred_at", "recorded_at"),
    "biz_refund_request": ("requested_at", "completed_at", "created_at", "updated_at"),
    "biz_refund_transaction": ("initiated_at", "succeeded_at", "created_at", "updated_at"),
    "biz_refund_event": ("occurred_at", "recorded_at"),
    "biz_coupon_template": ("created_at", "updated_at"),
    "biz_coupon": ("issued_at", "locked_at", "used_at", "updated_at"),
    "biz_coupon_event": ("occurred_at", "recorded_at"),
}


class BootstrapPlanError(ValueError):
    """Replay Bootstrap Contract 无效，不能生成可执行计划。"""


def sha256(path: Path) -> str:
    """流式计算文件 SHA-256，避免把正式 CSV 整体读入内存。"""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path, label: str) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BootstrapPlanError(f"{label}: invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise BootstrapPlanError(f"{label}: root must be an object")
    return payload


def require_datetime(value: object, label: str) -> datetime:
    if not isinstance(value, str):
        raise BootstrapPlanError(f"{label}: expected datetime string")
    try:
        return datetime.strptime(value, DATETIME_FORMAT)
    except ValueError as exc:
        raise BootstrapPlanError(f"{label}: expected yyyy-MM-dd HH:mm:ss.SSS") from exc


def require_iso_datetime(value: object, label: str) -> datetime:
    """解析 Source Contract 的 ISO 时间；与 Replay 的展示格式分开校验。"""
    if not isinstance(value, str):
        raise BootstrapPlanError(f"{label}: expected datetime string")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BootstrapPlanError(f"{label}: invalid ISO datetime") from exc


def require_sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
        raise BootstrapPlanError(f"{label}: expected lowercase SHA-256")
    return value


def require_int(value: object, label: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise BootstrapPlanError(f"{label}: expected integer >= {minimum}")
    return value


def safe_child(root: Path, relative: object, label: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise BootstrapPlanError(f"{label}: expected a non-empty relative path")
    resolved_root = root.resolve()
    path = (root / relative).resolve()
    try:
        path.relative_to(resolved_root)
    except ValueError as exc:
        raise BootstrapPlanError(f"{label}: path escapes replay bundle") from exc
    return path


def verify_file(path: Path, expected_hash: object, label: str) -> None:
    if not path.is_file():
        raise BootstrapPlanError(f"{label}: missing file {path.name}")
    if sha256(path) != require_sha256(expected_hash, f"{label}.sha256"):
        raise BootstrapPlanError(f"{label}: SHA-256 mismatch")


def validate_business_hash(manifest: dict) -> None:
    bootstrap = manifest.get("bootstrap")
    packages = manifest.get("daily_packages")
    if not isinstance(bootstrap, dict) or not isinstance(bootstrap.get("tables"), list):
        raise BootstrapPlanError("replay_manifest.bootstrap.tables must be an array")
    if not isinstance(packages, list):
        raise BootstrapPlanError("replay_manifest.daily_packages must be an array")
    bootstrap_hashes = []
    for index, item in enumerate(bootstrap["tables"]):
        if not isinstance(item, dict) or item.get("table_name") not in TABLE_COLUMNS:
            raise BootstrapPlanError(f"bootstrap.tables[{index}]: invalid table_name")
        bootstrap_hashes.append({
            "table_name": item["table_name"],
            "sha256": require_sha256(item.get("sha256"), f"bootstrap.tables[{index}].sha256"),
        })
    daily_hashes = []
    for index, item in enumerate(packages):
        if not isinstance(item, dict):
            raise BootstrapPlanError(f"daily_packages[{index}]: expected object")
        daily_hashes.append({
            "day_number": require_int(item.get("day_number"), f"daily_packages[{index}].day_number", 1),
            "manifest_sha256": require_sha256(
                item.get("manifest_sha256"), f"daily_packages[{index}].manifest_sha256"
            ),
        })
    expected = hashlib.sha256(
        canonical_json({"bootstrap": bootstrap_hashes, "daily": daily_hashes}).encode("utf-8")
    ).hexdigest()
    if manifest.get("business_hash") != expected:
        raise BootstrapPlanError("replay_manifest.business_hash mismatch")


def validate_root_contract(root: Path, manifest: dict) -> tuple[Path, datetime, datetime]:
    if manifest.get("replay_manifest_version") != 1:
        raise BootstrapPlanError("replay_manifest_version must be 1")
    for field in ("dataset_version", "generator_version", "timezone"):
        if not isinstance(manifest.get(field), str) or not manifest[field]:
            raise BootstrapPlanError(f"replay_manifest.{field}: expected non-empty string")
    require_int(manifest.get("seed"), "replay_manifest.seed")
    history_start = require_datetime(manifest.get("history_start"), "replay_manifest.history_start")
    cutover = require_datetime(manifest.get("cutover_time"), "replay_manifest.cutover_time")
    replay_end = require_datetime(manifest.get("replay_end_exclusive"), "replay_manifest.replay_end_exclusive")
    if cutover != history_start + timedelta(days=60) or replay_end != history_start + timedelta(days=90):
        raise BootstrapPlanError("replay_manifest: expected a 60-day bootstrap and 30-day replay window")
    validate_business_hash(manifest)
    packages = manifest.get("daily_packages")
    days = [item.get("day_number") if isinstance(item, dict) else None for item in packages]
    if days != list(range(61, 91)):
        raise BootstrapPlanError("replay_manifest.daily_packages must contain ordered days 61..90")

    source_bundle = manifest.get("source_bundle")
    if not isinstance(source_bundle, dict) or set(source_bundle) != {"dataset_manifest", "entity_manifest"}:
        raise BootstrapPlanError("replay_manifest.source_bundle has an invalid schema")
    source_documents = {}
    for name, binding in source_bundle.items():
        if not isinstance(binding, dict) or set(binding) != {"path", "sha256"}:
            raise BootstrapPlanError(f"source_bundle.{name} has an invalid schema")
        path = safe_child(root, binding["path"], f"source_bundle.{name}.path")
        verify_file(path, binding["sha256"], name)
        source_documents[name] = load_json(path, path.name)
    dataset = source_documents["dataset_manifest"]
    entity = source_documents["entity_manifest"]
    for field in ("dataset_version", "seed", "timezone"):
        if dataset.get(field) != manifest.get(field) or entity.get(field) != manifest.get(field):
            raise BootstrapPlanError(f"source_bundle: {field} does not match replay manifest")
    for name, document in source_documents.items():
        if require_iso_datetime(document.get("history_start"), f"{name}.history_start") != history_start:
            raise BootstrapPlanError(f"source_bundle: {name}.history_start does not match replay manifest")
    if dataset.get("generator_version") != manifest["generator_version"]:
        raise BootstrapPlanError("source_bundle: generator_version does not match replay manifest")

    bootstrap = manifest.get("bootstrap")
    if not isinstance(bootstrap, dict) or set(bootstrap) != {"path", "tables", "expected_result"}:
        raise BootstrapPlanError("replay_manifest.bootstrap has an invalid schema")
    bootstrap_dir = safe_child(root, bootstrap["path"], "bootstrap.path")
    if bootstrap_dir != (root / "bootstrap").resolve() or not bootstrap_dir.is_dir():
        raise BootstrapPlanError("bootstrap.path must target the bundle bootstrap directory")
    return bootstrap_dir, cutover, replay_end


def validate_table_entries(bootstrap_dir: Path, manifest: dict) -> tuple[list[dict], dict[str, dict]]:
    entries = manifest["bootstrap"]["tables"]
    if len(entries) != len(TABLE_ORDER):
        raise BootstrapPlanError(f"bootstrap.tables must contain exactly {len(TABLE_ORDER)} entries")
    names = [entry.get("table_name") if isinstance(entry, dict) else None for entry in entries]
    if names != TABLE_ORDER:
        raise BootstrapPlanError("bootstrap.tables must follow TABLE_ORDER")
    normalized = {}
    for index, entry in enumerate(entries):
        table = entry["table_name"]
        if entry.get("file") != f"{table}.csv" or Path(str(entry.get("file"))).name != entry.get("file"):
            raise BootstrapPlanError(f"bootstrap.tables[{index}].file is not canonical")
        row_count = require_int(entry.get("row_count"), f"bootstrap.tables[{index}].row_count")
        if entry.get("extract_row_count") != row_count:
            raise BootstrapPlanError(f"{table}: extract_row_count must equal row_count for bootstrap")
        require_sha256(entry.get("sha256"), f"bootstrap.tables[{index}].sha256")
        normalized[table] = {
            "table_name": table,
            "file": entry["file"],
            "row_count": row_count,
            "csv_file_size_bytes": (bootstrap_dir / entry["file"]).stat().st_size,
            "sha256": entry["sha256"],
        }
    try:
        keys = validate_csv_files(bootstrap_dir, normalized)
        validate_references(bootstrap_dir, keys)
    except BundleError as exc:
        raise BootstrapPlanError(str(exc)) from exc
    return entries, normalized


def validate_cutover_boundary(bootstrap_dir: Path, cutover: datetime) -> None:
    for table in TABLE_ORDER:
        with (bootstrap_dir / f"{table}.csv").open("r", encoding="utf-8", newline="") as handle:
            for line_number, row in enumerate(csv.DictReader(handle), start=2):
                for column in CUTOVER_TIME_COLUMNS[table]:
                    value = row[column]
                    if not value:
                        continue
                    observed = require_datetime(value, f"{table}:{line_number}.{column}")
                    if observed >= cutover:
                        raise BootstrapPlanError(
                            f"{table}:{line_number}: {column}={value} is not before cutover"
                        )


def validate_expected_result(bootstrap_dir: Path, manifest: dict, entries: list[dict]) -> None:
    binding = manifest["bootstrap"].get("expected_result")
    if not isinstance(binding, dict) or set(binding) != {"file", "sha256"}:
        raise BootstrapPlanError("bootstrap.expected_result has an invalid schema")
    if binding.get("file") != "expected_result.json":
        raise BootstrapPlanError("bootstrap.expected_result.file must be expected_result.json")
    path = bootstrap_dir / binding["file"]
    verify_file(path, binding.get("sha256"), "bootstrap expected_result")
    result = load_json(path, "expected_result.json")
    expected = {entry["table_name"]: entry["row_count"] for entry in entries}
    if result != {"table_row_counts": expected}:
        raise BootstrapPlanError("expected_result.json: table_row_counts mismatch")


def validate_ods_contract(root: Path, bootstrap_dir: Path, manifest_path: Path, manifest: dict, entries: list[dict]) -> dict:
    contract = load_json(bootstrap_dir / "ods_batch_contract.json", "ods_batch_contract.json")
    binding = contract.get("replay_manifest")
    if not isinstance(binding, dict) or set(binding) != {"path", "sha256"}:
        raise BootstrapPlanError("ods_batch_contract.replay_manifest binding is invalid")
    relative = binding.get("path")
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise BootstrapPlanError("ods_batch_contract.replay_manifest.path must be relative")
    bound_path = (bootstrap_dir / relative).resolve()
    try:
        bound_path.relative_to(root.resolve())
    except ValueError as exc:
        raise BootstrapPlanError("ods_batch_contract.replay_manifest.path escapes replay bundle") from exc
    if bound_path != manifest_path.resolve():
        raise BootstrapPlanError("ods_batch_contract replay manifest path does not target bundle root")
    verify_file(bound_path, binding.get("sha256"), "ods_batch_contract replay manifest")
    cutover = require_datetime(manifest["cutover_time"], "replay_manifest.cutover_time")
    expected_date = (cutover - timedelta(days=1)).date().isoformat()
    if contract.get("dataset_version") != manifest["dataset_version"] or contract.get("mode") != "bootstrap":
        raise BootstrapPlanError("ods_batch_contract: dataset_version/mode mismatch")
    if contract.get("business_date") != expected_date or contract.get("extract_time") != manifest["cutover_time"]:
        raise BootstrapPlanError("ods_batch_contract: business_date/extract_time mismatch")
    if contract.get("window_start") is not None or contract.get("window_end") is not None:
        raise BootstrapPlanError("ods_batch_contract: bootstrap window_start/window_end must be null")
    expected_tables = contract.get("expected_tables")
    if not isinstance(expected_tables, dict) or set(expected_tables) != set(TABLE_ORDER):
        raise BootstrapPlanError("ods_batch_contract.expected_tables has an invalid table set")
    for entry in entries:
        table = entry["table_name"]
        expected = {
            "row_count": entry["row_count"],
            "affected_business_dates": entry["affected_business_dates"],
            "business_date_row_counts": entry["business_date_row_counts"],
        }
        if expected_tables.get(table) != expected:
            raise BootstrapPlanError(f"ods_batch_contract.expected_tables.{table} mismatch")
    return contract


def business_statistics(bootstrap_dir: Path) -> dict[str, int]:
    with (bootstrap_dir / "biz_order.csv").open("r", encoding="utf-8", newline="") as handle:
        counts = Counter(row["order_status"] for row in csv.DictReader(handle))
    return {
        "paid_orders": counts["PAID"],
        "canceled_orders": counts["CANCELED"],
        "created_orders": counts["CREATED"],
    }


def publish_output(output: Path, plan: dict, sql: str) -> None:
    if output.exists():
        raise BootstrapPlanError(f"output already exists; choose a new directory: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f".{output.name}.incomplete-", dir=output.parent))
    try:
        sql_path = work / "load.sql"
        sql_path.write_text(sql, encoding="utf-8", newline="\n")
        plan["sql"] = {"file": sql_path.name, "sha256": sha256(sql_path)}
        (work / "plan.json").write_text(
            json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        os.replace(work, output)
    except Exception:
        shutil.rmtree(work, ignore_errors=True)
        raise


def build_plan(replay_bundle: Path, output: Path) -> dict:
    """完整校验 Bootstrap，并生成不含凭据、不会自动执行的事务计划。"""
    root = replay_bundle.resolve()
    if not root.is_dir():
        raise BootstrapPlanError(f"replay bundle is not a directory: {root}")
    manifest_path = root / "replay_manifest.json"
    manifest = load_json(manifest_path, "replay_manifest.json")
    bootstrap_dir, cutover, _ = validate_root_contract(root, manifest)
    entries, normalized = validate_table_entries(bootstrap_dir, manifest)
    validate_cutover_boundary(bootstrap_dir, cutover)
    validate_expected_result(bootstrap_dir, manifest, entries)
    contract = validate_ods_contract(root, bootstrap_dir, manifest_path, manifest, entries)
    statistics = business_statistics(bootstrap_dir)
    load_plan = {
        "bundle": str(bootstrap_dir),
        "tables": [normalized[table] for table in LOAD_TABLE_ORDER],
        "business_statistics": statistics,
    }
    try:
        sql = render_load_sql(
            load_plan,
            REPO_ROOT / "mysql" / "sql" / "load_csv_bundle.sql",
            REPO_ROOT / "mysql" / "sql" / "source_gate.sql",
        )
    except BundleError as exc:
        raise BootstrapPlanError(str(exc)) from exc
    plan = {
        "plan_version": 1,
        "status": "planned",
        "dry_run": True,
        "execution_authorized": False,
        "database_contacted": False,
        "dataset_version": manifest["dataset_version"],
        "seed": manifest["seed"],
        "business_hash": manifest["business_hash"],
        "replay_manifest_sha256": sha256(manifest_path),
        "history_start": manifest["history_start"],
        "cutover_time": manifest["cutover_time"],
        "batch_id": contract.get("batch_id"),
        "bootstrap_row_count": sum(entry["row_count"] for entry in entries),
        "load_table_order": LOAD_TABLE_ORDER,
        "tables": [
            {
                "table_name": table,
                "file": normalized[table]["file"],
                "row_count": normalized[table]["row_count"],
                "sha256": normalized[table]["sha256"],
                "primary_key": PRIMARY_KEYS[table],
            }
            for table in LOAD_TABLE_ORDER
        ],
        "transaction": {
            "single_session": True,
            "advisory_lock": True,
            "target_must_be_empty": True,
            "source_gate_before_commit": True,
        },
    }
    publish_output(output, plan, sql)
    return plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay-bundle", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true", help="Required safety lock; no database client is invoked")
    args = parser.parse_args(argv)
    if not args.dry_run:
        print("ERROR: --dry-run is required; database execution is not implemented or authorized", file=sys.stderr)
        return 2
    try:
        plan = build_plan(args.replay_bundle, args.output)
    except (BootstrapPlanError, OSError, UnicodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(plan, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
