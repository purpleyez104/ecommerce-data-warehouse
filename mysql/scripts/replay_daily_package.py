#!/usr/bin/env python3
"""Validate one replay daily package and render a secret-free MySQL dry-run plan."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GENERATOR_SRC = REPO_ROOT / "mock" / "generator" / "business_generator" / "src"
sys.path.insert(0, str(GENERATOR_SRC))

from business_generator.common import canonical_json  # noqa: E402
from business_generator.contracts import LOAD_TABLE_ORDER, TABLE_COLUMNS, TABLE_ORDER  # noqa: E402


PRIMARY_KEYS = {table: columns[0] for table, columns in TABLE_COLUMNS.items()}
LOAD_RANK = {table: index for index, table in enumerate(LOAD_TABLE_ORDER)}
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
OPERATION_FIELDS = {
    "sequence",
    "operation_time",
    "table",
    "operation_type",
    "primary_key",
    "business_date",
    "row",
}
PACKAGE_FIELDS = {
    "package_version",
    "day_number",
    "batch_id",
    "window_start",
    "window_end",
    "operations",
    "expected_result",
    "tables",
}


class ReplayPlanError(ValueError):
    """The replay package cannot safely produce a local execution plan."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path, label: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReplayPlanError(f"{label}: invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ReplayPlanError(f"{label}: root must be an object")
    return value


def require_sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
        raise ReplayPlanError(f"{label}: expected lowercase SHA-256")
    return value


def require_int(value: object, label: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ReplayPlanError(f"{label}: expected integer >= {minimum}")
    return value


def require_datetime(value: object, label: str) -> datetime:
    if not isinstance(value, str):
        raise ReplayPlanError(f"{label}: expected datetime string")
    try:
        return datetime.strptime(value, DATETIME_FORMAT)
    except ValueError as exc:
        raise ReplayPlanError(f"{label}: expected yyyy-MM-dd HH:mm:ss.SSS") from exc


def safe_child(root: Path, relative: object, label: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ReplayPlanError(f"{label}: expected a non-empty relative path")
    root_resolved = root.resolve()
    path = (root / relative).resolve()
    try:
        path.relative_to(root_resolved)
    except ValueError as exc:
        raise ReplayPlanError(f"{label}: path escapes replay bundle") from exc
    return path


def verify_file(path: Path, expected_hash: object, label: str) -> None:
    if not path.is_file():
        raise ReplayPlanError(f"{label}: missing file {path.name}")
    expected = require_sha256(expected_hash, f"{label}.sha256")
    if sha256(path) != expected:
        raise ReplayPlanError(f"{label}: SHA-256 mismatch")


def validate_business_hash(manifest: dict) -> None:
    bootstrap = manifest.get("bootstrap")
    packages = manifest.get("daily_packages")
    if not isinstance(bootstrap, dict) or not isinstance(bootstrap.get("tables"), list):
        raise ReplayPlanError("replay_manifest.bootstrap.tables must be an array")
    if not isinstance(packages, list):
        raise ReplayPlanError("replay_manifest.daily_packages must be an array")
    bootstrap_hashes = []
    table_names = []
    for index, item in enumerate(bootstrap["tables"]):
        if not isinstance(item, dict) or item.get("table_name") not in TABLE_COLUMNS:
            raise ReplayPlanError(f"replay_manifest.bootstrap.tables[{index}] has invalid table_name")
        table_names.append(item["table_name"])
        bootstrap_hashes.append({
            "table_name": item["table_name"],
            "sha256": require_sha256(item.get("sha256"), f"bootstrap.tables[{index}].sha256"),
        })
    if table_names != TABLE_ORDER:
        raise ReplayPlanError("replay_manifest.bootstrap.tables must follow TABLE_ORDER")
    daily_hashes = []
    days = []
    paths = []
    for index, item in enumerate(packages):
        if not isinstance(item, dict):
            raise ReplayPlanError(f"replay_manifest.daily_packages[{index}] must be an object")
        day = require_int(item.get("day_number"), f"daily_packages[{index}].day_number", 1)
        path = item.get("path")
        if not isinstance(path, str) or not path:
            raise ReplayPlanError(f"daily_packages[{index}].path must be a non-empty string")
        days.append(day)
        paths.append(path)
        daily_hashes.append({
            "day_number": day,
            "manifest_sha256": require_sha256(
                item.get("manifest_sha256"), f"daily_packages[{index}].manifest_sha256"
            ),
        })
    if days != list(range(61, 91)):
        raise ReplayPlanError("replay_manifest.daily_packages must contain ordered days 61..90")
    if len(paths) != len(set(paths)):
        raise ReplayPlanError("replay_manifest.daily_packages contains duplicate paths")
    expected = hashlib.sha256(canonical_json({"bootstrap": bootstrap_hashes, "daily": daily_hashes}).encode("utf-8")).hexdigest()
    if manifest.get("business_hash") != expected:
        raise ReplayPlanError("replay_manifest.business_hash mismatch")


def validate_package_manifest(package: dict, package_ref: dict, day: int) -> tuple[datetime, datetime]:
    if set(package) != PACKAGE_FIELDS:
        raise ReplayPlanError("package_manifest.json: field set is invalid")
    if package.get("package_version") != 1 or package.get("day_number") != day:
        raise ReplayPlanError("package_manifest.json: version/day mismatch")
    if package.get("batch_id") == "" or not isinstance(package.get("batch_id"), str):
        raise ReplayPlanError("package_manifest.json: batch_id must be a non-empty string")
    window_start = require_datetime(package.get("window_start"), "package_manifest.window_start")
    window_end = require_datetime(package.get("window_end"), "package_manifest.window_end")
    if window_start >= window_end:
        raise ReplayPlanError("package_manifest.json: window must be non-empty")
    if package_ref.get("window_start") != package["window_start"] or package_ref.get("window_end") != package["window_end"]:
        raise ReplayPlanError("package_manifest.json: window does not match replay manifest")
    operations = package.get("operations")
    expected = package.get("expected_result")
    if not isinstance(operations, dict) or set(operations) != {"file", "row_count", "sha256"}:
        raise ReplayPlanError("package_manifest.operations has an invalid schema")
    if operations.get("file") != "operations.jsonl":
        raise ReplayPlanError("package_manifest.operations.file must be operations.jsonl")
    require_int(operations.get("row_count"), "package_manifest.operations.row_count")
    require_sha256(operations.get("sha256"), "package_manifest.operations.sha256")
    if not isinstance(expected, dict) or set(expected) != {"file", "sha256"} or expected.get("file") != "expected_result.json":
        raise ReplayPlanError("package_manifest.expected_result has an invalid schema")
    require_sha256(expected.get("sha256"), "package_manifest.expected_result.sha256")
    return window_start, window_end


def validate_table_summaries(package: dict, operations: list[dict]) -> None:
    summaries = package.get("tables")
    if not isinstance(summaries, list) or len(summaries) != len(TABLE_ORDER):
        raise ReplayPlanError(f"package_manifest.tables must contain exactly {len(TABLE_ORDER)} entries")
    names = [item.get("table_name") if isinstance(item, dict) else None for item in summaries]
    if names != TABLE_ORDER:
        raise ReplayPlanError("package_manifest.tables must follow TABLE_ORDER")
    actual = {table: 0 for table in TABLE_ORDER}
    for operation in operations:
        actual[operation["table"]] += 1
    for index, item in enumerate(summaries):
        count = require_int(item.get("operation_count"), f"package_manifest.tables[{index}].operation_count")
        if count != actual[item["table_name"]]:
            raise ReplayPlanError(f"{item['table_name']}: operation_count mismatch")


def load_operations(path: Path, expected_count: int, window_start: datetime, window_end: datetime) -> list[dict]:
    operations = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise ReplayPlanError(f"operations.jsonl: cannot read: {exc}") from exc
    if len(lines) != expected_count:
        raise ReplayPlanError(f"operations.jsonl: row_count mismatch; expected {expected_count}, got {len(lines)}")
    order_keys = []
    inserted_keys: set[tuple[str, str]] = set()
    for line_number, line in enumerate(lines, start=1):
        try:
            operation = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ReplayPlanError(f"operations.jsonl:{line_number}: invalid JSON") from exc
        if not isinstance(operation, dict) or set(operation) != OPERATION_FIELDS:
            raise ReplayPlanError(f"operations.jsonl:{line_number}: field set is invalid")
        if operation.get("sequence") != line_number:
            raise ReplayPlanError(f"operations.jsonl:{line_number}: sequence must equal line number")
        table = operation.get("table")
        if table not in TABLE_COLUMNS:
            raise ReplayPlanError(f"operations.jsonl:{line_number}: unknown table {table!r}")
        operation_type = operation.get("operation_type")
        if operation_type not in {"INSERT", "UPDATE"}:
            raise ReplayPlanError(f"operations.jsonl:{line_number}: operation_type must be INSERT or UPDATE")
        operation_time = require_datetime(operation.get("operation_time"), f"operations.jsonl:{line_number}.operation_time")
        if not window_start <= operation_time < window_end:
            raise ReplayPlanError(f"operations.jsonl:{line_number}: operation_time is outside package window")
        primary_key = operation.get("primary_key")
        pk = PRIMARY_KEYS[table]
        if not isinstance(primary_key, dict) or set(primary_key) != {pk} or not isinstance(primary_key[pk], str) or not primary_key[pk]:
            raise ReplayPlanError(f"operations.jsonl:{line_number}: primary_key must contain only non-empty {pk}")
        row = operation.get("row")
        if not isinstance(row, dict) or set(row) != set(TABLE_COLUMNS[table]):
            raise ReplayPlanError(f"operations.jsonl:{line_number}: row fields must exactly match TABLE_COLUMNS[{table!r}]")
        if any(not isinstance(value, str) for value in row.values()):
            raise ReplayPlanError(f"operations.jsonl:{line_number}: all row values must be strings")
        if row[pk] != primary_key[pk]:
            raise ReplayPlanError(f"operations.jsonl:{line_number}: row primary key mismatch")
        key = (table, primary_key[pk])
        if operation_type == "INSERT" and key in inserted_keys:
            raise ReplayPlanError(f"operations.jsonl:{line_number}: duplicate INSERT for {table}.{primary_key[pk]}")
        if operation_type == "INSERT":
            inserted_keys.add(key)
        business_date = operation.get("business_date")
        if not isinstance(business_date, str) or (business_date and re.fullmatch(r"\d{4}-\d{2}-\d{2}", business_date) is None):
            raise ReplayPlanError(f"operations.jsonl:{line_number}: business_date is invalid")
        order_keys.append((operation_time, LOAD_RANK[table], line_number))
        operations.append(operation)
    if order_keys != sorted(order_keys):
        raise ReplayPlanError("operations.jsonl: operations are not in operation_time/FK-safe table order")
    return operations


def sql_value(value: str) -> str:
    if value == "":
        return "NULL"
    return f"CONVERT(X'{value.encode('utf-8').hex()}' USING utf8mb4)"


def render_sql(
    manifest: dict,
    package: dict,
    package_hash: str,
    operations: list[dict],
    expected_counts: dict[str, int],
    expected_order_status_counts: dict[str, int],
    source_gate_sql: str,
) -> str:
    lines = [
        "-- Generated dry-run artifact. Review before any separately authorized database operation.",
        f"-- dataset_version: {manifest.get('dataset_version', '')}",
        f"-- business_hash: {manifest['business_hash']}",
        f"-- day_number: {package['day_number']}",
        f"-- batch_id: {package['batch_id']}",
        f"-- package_manifest_sha256: {package_hash}",
        "SET autocommit = 0;",
        "START TRANSACTION;",
        # Ledger 与业务操作同事务提交。重复 batch_id/day_number 会在任何业务写入前
        # 失败，Executor 随后只读核对既有 Ledger，安全识别同日重跑。
        "INSERT INTO `replay_batch_ledger` "
        "(`batch_id`, `day_number`, `business_hash`, `package_manifest_sha256`, `operation_count`) VALUES ("
        f"{sql_value(package['batch_id'])}, {package['day_number']}, "
        f"{sql_value(manifest['business_hash'])}, {sql_value(package_hash)}, {len(operations)});",
    ]
    for table in TABLE_ORDER:
        lines.append(f"SET @expected_{table} = {expected_counts[table]};")
    lines.extend([
        f"SET @expected_paid_orders = {expected_order_status_counts['PAID']};",
        f"SET @expected_canceled_orders = {expected_order_status_counts['CANCELED']};",
        f"SET @expected_created_orders = {expected_order_status_counts['CREATED']};",
    ])
    for operation in operations:
        table = operation["table"]
        row = operation["row"]
        pk = PRIMARY_KEYS[table]
        if operation["operation_type"] == "INSERT":
            columns = ", ".join(f"`{column}`" for column in TABLE_COLUMNS[table])
            values = ", ".join(sql_value(row[column]) for column in TABLE_COLUMNS[table])
            lines.append(f"INSERT INTO `{table}` ({columns}) VALUES ({values});")
        else:
            assignments = ", ".join(
                f"`{column}` = {sql_value(row[column])}" for column in TABLE_COLUMNS[table] if column != pk
            )
            lines.append(f"UPDATE `{table}` SET {assignments} WHERE `{pk}` = {sql_value(row[pk])};")
    # Source Gate 与回放必须处于同一事务；任一规则失败时 mysql client 非零退出，
    # 未提交事务由服务端回滚，不能留下“数据已写入但 Gate 未通过”的中间状态。
    lines.extend([source_gate_sql.rstrip(), "COMMIT;", ""])
    return "\n".join(lines)


def validate_expected_result(path: Path, package: dict) -> tuple[dict[str, int], dict[str, int]]:
    expected = load_json(path, "expected_result.json")
    if set(expected) != {"window_end", "table_row_counts", "order_status_counts"}:
        raise ReplayPlanError("expected_result.json: field set is invalid")
    if expected.get("window_end") != package["window_end"]:
        raise ReplayPlanError("expected_result.json: window_end mismatch")
    counts = expected.get("table_row_counts")
    if not isinstance(counts, dict) or set(counts) != set(TABLE_ORDER):
        raise ReplayPlanError("expected_result.json: table_row_counts must cover TABLE_ORDER")
    table_counts = {
        table: require_int(counts[table], f"expected_result.table_row_counts.{table}")
        for table in TABLE_ORDER
    }
    status_counts = expected.get("order_status_counts")
    required_statuses = {"CREATED", "PAID", "CANCELED"}
    if not isinstance(status_counts, dict) or set(status_counts) != required_statuses:
        raise ReplayPlanError("expected_result.json: order_status_counts must cover CREATED/PAID/CANCELED")
    validated_status_counts = {
        status: require_int(status_counts[status], f"expected_result.order_status_counts.{status}")
        for status in required_statuses
    }
    if sum(validated_status_counts.values()) != table_counts["biz_order"]:
        raise ReplayPlanError("expected_result.json: order_status_counts must sum to biz_order row count")
    return table_counts, validated_status_counts


def publish_output(output: Path, plan: dict, sql: str) -> None:
    if output.exists():
        raise ReplayPlanError(f"output already exists; choose a new directory: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f".{output.name}.incomplete-", dir=output.parent))
    try:
        sql_path = work / "replay.sql"
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


def build_plan(replay_bundle: Path, day: int, output: Path) -> dict:
    root = replay_bundle.resolve()
    manifest_path = root / "replay_manifest.json"
    manifest = load_json(manifest_path, "replay_manifest.json")
    if manifest.get("replay_manifest_version") != 1:
        raise ReplayPlanError("replay_manifest.json: replay_manifest_version must be 1")
    validate_business_hash(manifest)
    package_ref = next((item for item in manifest["daily_packages"] if item["day_number"] == day), None)
    if package_ref is None:
        raise ReplayPlanError(f"replay_manifest.json: day {day} is not present")
    package_dir = safe_child(root, package_ref["path"], "daily package path")
    package_manifest_path = package_dir / "package_manifest.json"
    verify_file(package_manifest_path, package_ref.get("manifest_sha256"), "package_manifest.json")
    package = load_json(package_manifest_path, "package_manifest.json")
    window_start, window_end = validate_package_manifest(package, package_ref, day)

    contract_path = package_dir / "ods_batch_contract.json"
    contract = load_json(contract_path, "ods_batch_contract.json")
    binding = contract.get("replay_manifest")
    if not isinstance(binding, dict) or set(binding) != {"path", "sha256"}:
        raise ReplayPlanError("ods_batch_contract.json: replay_manifest binding is invalid")
    binding_path = binding.get("path")
    if not isinstance(binding_path, str) or not binding_path or Path(binding_path).is_absolute():
        raise ReplayPlanError("ods_batch_contract replay_manifest.path must be a relative path")
    bound_manifest = (package_dir / binding_path).resolve()
    if bound_manifest != manifest_path.resolve():
        raise ReplayPlanError("ods_batch_contract.json: replay manifest path does not target bundle root")
    verify_file(bound_manifest, binding.get("sha256"), "ods_batch_contract replay manifest")
    for field in ("dataset_version", "batch_id", "window_start", "window_end"):
        expected = package[field] if field != "dataset_version" else manifest.get(field)
        if contract.get(field) != expected:
            raise ReplayPlanError(f"ods_batch_contract.json: {field} mismatch")
    if contract.get("mode") != "incremental" or contract.get("business_date") != package["window_start"][:10]:
        raise ReplayPlanError("ods_batch_contract.json: incremental mode/business_date mismatch")

    operations_path = package_dir / package["operations"]["file"]
    expected_path = package_dir / package["expected_result"]["file"]
    verify_file(operations_path, package["operations"]["sha256"], "operations.jsonl")
    verify_file(expected_path, package["expected_result"]["sha256"], "expected_result.json")
    operations = load_operations(
        operations_path,
        package["operations"]["row_count"],
        window_start,
        window_end,
    )
    validate_table_summaries(package, operations)
    package_hash = sha256(package_manifest_path)
    expected_counts, expected_order_status_counts = validate_expected_result(expected_path, package)
    source_gate_path = REPO_ROOT / "mysql" / "sql" / "source_gate.sql"
    try:
        source_gate_sql = source_gate_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ReplayPlanError(f"source_gate.sql: cannot read: {exc}") from exc
    sql = render_sql(
        manifest,
        package,
        package_hash,
        operations,
        expected_counts,
        expected_order_status_counts,
        source_gate_sql,
    )
    counts = {table: {"INSERT": 0, "UPDATE": 0} for table in TABLE_ORDER}
    for operation in operations:
        counts[operation["table"]][operation["operation_type"]] += 1
    plan = {
        "plan_version": 1,
        "status": "planned",
        "dry_run": True,
        "execution_authorized": False,
        "dataset_version": manifest.get("dataset_version"),
        "business_hash": manifest["business_hash"],
        "day_number": day,
        "batch_id": package["batch_id"],
        "window_start": package["window_start"],
        "window_end": package["window_end"],
        "package_manifest_sha256": package_hash,
        "operation_count": len(operations),
        "operation_counts": counts,
        "expected_table_row_counts": expected_counts,
        "expected_order_status_counts": expected_order_status_counts,
        "source_gate": {"file": "mysql/sql/source_gate.sql", "sha256": sha256(source_gate_path)},
        "requires_previous_day": day - 1,
        "database_contacted": False,
    }
    publish_output(output, plan, sql)
    return plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay-bundle", required=True, type=Path)
    parser.add_argument("--day", required=True, type=int, choices=range(61, 91), metavar="61..90")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true", help="Required safety lock; no database client is invoked")
    args = parser.parse_args(argv)
    if not args.dry_run:
        print("ERROR: --dry-run is required; database execution is not implemented or authorized", file=sys.stderr)
        return 2
    try:
        plan = build_plan(args.replay_bundle, args.day, args.output)
    except (OSError, UnicodeError, ReplayPlanError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(plan, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
