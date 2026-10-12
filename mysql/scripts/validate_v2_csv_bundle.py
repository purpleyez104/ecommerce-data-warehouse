#!/usr/bin/env python3
"""Validate a V2 Business Generator CSV bundle without contacting MySQL."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GENERATOR_SRC = REPO_ROOT / "mock" / "generator" / "business_generator" / "src"
sys.path.insert(0, str(GENERATOR_SRC))

from business_generator.contracts import LOAD_TABLE_ORDER, TABLE_COLUMNS  # noqa: E402


PRIMARY_KEYS = {
    table: columns[0] for table, columns in TABLE_COLUMNS.items()
}

FOREIGN_KEYS = {
    "biz_identity_mapping": (("visitor_id", "biz_visitor"), ("user_id", "biz_user")),
    "biz_spu": (("category_id", "biz_category"),),
    "biz_sku": (("spu_id", "biz_spu"),),
    "biz_cart": (("user_id", "biz_user"), ("visitor_id", "biz_visitor")),
    "biz_cart_item": (("cart_id", "biz_cart"), ("sku_id", "biz_sku")),
    "biz_cart_merge_record": (("visitor_cart_id", "biz_cart"), ("user_cart_id", "biz_cart"), ("user_id", "biz_user")),
    "biz_coupon": (("template_id", "biz_coupon_template"), ("user_id", "biz_user")),
    "biz_order": (("user_id", "biz_user"), ("visitor_id", "biz_visitor"), ("coupon_id", "biz_coupon")),
    "biz_order_item": (("order_id", "biz_order"), ("sku_id", "biz_sku"), ("spu_id", "biz_spu"), ("category_id", "biz_category")),
    "biz_order_status_event": (("order_id", "biz_order"),),
    "biz_payment_attempt": (("order_id", "biz_order"),),
    "biz_payment_event": (("payment_attempt_id", "biz_payment_attempt"),),
    "biz_refund_request": (("order_id", "biz_order"), ("order_item_id", "biz_order_item")),
    "biz_refund_transaction": (("refund_request_id", "biz_refund_request"),),
    "biz_refund_event": (("refund_request_id", "biz_refund_request"), ("refund_txn_id", "biz_refund_transaction")),
    "biz_coupon_event": (("coupon_id", "biz_coupon"), ("order_id", "biz_order")),
}

IDENTITY_FIELDS = (
    "dataset_version",
    "seed",
    "history_start",
    "history_end",
    "timezone",
)

DATASET_MANIFEST_FIELDS = {
    "dataset_manifest_version",
    "dataset_version",
    "generator_version",
    "seed",
    "history_start",
    "history_end",
    "history_days",
    "timezone",
    "generated_at",
    "tables",
    "business_statistics",
    "traffic_statistics",
    "distribution_statistics",
    "entity_manifest",
}

ENTITY_MANIFEST_FIELDS = {
    "entity_manifest_version",
    "dataset_version",
    "source_generator_version",
    "seed",
    "history_start",
    "history_end",
    "timezone",
    "entities",
}

ENTITY_ROW_FIELDS = {
    "users": {"user_id", "registered_at"},
    "visitors": {"visitor_id", "first_seen_at"},
    "identity_mappings": {
        "visitor_id",
        "user_id",
        "session_id",
        "identity_version",
        "effective_from",
        "effective_to",
    },
    "skus": {"sku_id", "spu_id", "category_id", "available_from"},
}

NULLABLE_COLUMNS = {
    "biz_identity_mapping": {"session_id", "effective_to"},
    "biz_cart": {"user_id", "visitor_id"},
    "biz_order": {"user_id", "visitor_id", "coupon_id", "paid_at", "canceled_at"},
    "biz_order_status_event": {"from_status"},
    "biz_payment_attempt": {"succeeded_at"},
    "biz_payment_event": {"callback_event_id", "from_status"},
    "biz_refund_request": {"refund_quantity", "completed_at"},
    "biz_refund_transaction": {"succeeded_at"},
    "biz_refund_event": {"refund_txn_id", "from_status"},
    "biz_coupon": {"locked_order_id", "used_order_id", "locked_at", "used_at"},
    "biz_coupon_event": {"order_id", "from_status"},
}


class BundleError(ValueError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BundleError(f"{path.name}: invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise BundleError(f"{path.name}: root must be an object")
    return value


def require_int(value: object, label: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise BundleError(f"{label}: expected integer >= {minimum}")
    return value


def validate_manifests(bundle: Path) -> tuple[dict, dict, dict[str, dict]]:
    dataset_path = bundle / "dataset_manifest.json"
    entity_path = bundle / "entity_manifest.json"
    if not dataset_path.is_file() or not entity_path.is_file():
        missing = [p.name for p in (dataset_path, entity_path) if not p.is_file()]
        raise BundleError(f"missing manifest(s): {', '.join(missing)}")
    dataset = load_json(dataset_path)
    entity = load_json(entity_path)
    if set(dataset) != DATASET_MANIFEST_FIELDS:
        raise BundleError("dataset_manifest.json: top-level field set is invalid")
    if set(entity) != ENTITY_MANIFEST_FIELDS:
        raise BundleError("entity_manifest.json: top-level field set is invalid")
    if dataset.get("dataset_manifest_version") != 1:
        raise BundleError("dataset_manifest.json: dataset_manifest_version must be 1")
    if entity.get("entity_manifest_version") != 1:
        raise BundleError("entity_manifest.json: entity_manifest_version must be 1")
    for field in ("dataset_version", "generator_version", "history_start", "history_end", "timezone", "generated_at"):
        if not isinstance(dataset.get(field), str) or not dataset[field]:
            raise BundleError(f"dataset_manifest.json: {field} must be a non-empty string")
    require_int(dataset.get("seed"), "dataset_manifest.json.seed")
    history_days = require_int(dataset.get("history_days"), "dataset_manifest.json.history_days", 1)
    try:
        history_start = datetime.fromisoformat(dataset["history_start"].replace("Z", "+00:00"))
        history_end = datetime.fromisoformat(dataset["history_end"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise BundleError(f"dataset_manifest.json: invalid history datetime: {exc}") from exc
    try:
        invalid_range = history_start > history_end
    except TypeError as exc:
        raise BundleError("dataset_manifest.json: history datetimes must use compatible timezone forms") from exc
    if invalid_range:
        raise BundleError("dataset_manifest.json: history_start must be <= history_end")
    inclusive_days = (history_end.date() - history_start.date()).days + 1
    if inclusive_days != history_days:
        raise BundleError(
            f"dataset_manifest.json: history_days mismatch; expected {inclusive_days}, got {history_days}"
        )
    for name in ("business_statistics", "traffic_statistics", "distribution_statistics"):
        if not isinstance(dataset.get(name), dict):
            raise BundleError(f"dataset_manifest.json: {name} must be an object")
    for name in ("paid_orders", "canceled_orders", "created_orders"):
        require_int(dataset["business_statistics"].get(name), f"business_statistics.{name}")
    for field in ("dataset_version", "source_generator_version", "history_start", "history_end", "timezone"):
        if not isinstance(entity.get(field), str) or not entity[field]:
            raise BundleError(f"entity_manifest.json: {field} must be a non-empty string")
    require_int(entity.get("seed"), "entity_manifest.json.seed")
    if entity.get("source_generator_version") != dataset["generator_version"]:
        raise BundleError("entity_manifest.json: source_generator_version does not match generator_version")
    for field in IDENTITY_FIELDS:
        if dataset.get(field) != entity.get(field):
            raise BundleError(f"entity_manifest.json: {field} does not match dataset manifest")
    binding = dataset.get("entity_manifest")
    if not isinstance(binding, dict) or set(binding) != {"file", "version", "sha256"}:
        raise BundleError("dataset_manifest.json: entity_manifest must contain only file, version, sha256")
    if binding["file"] != entity_path.name or Path(str(binding["file"])).name != binding["file"]:
        raise BundleError("dataset_manifest.json: entity_manifest file must be the basename entity_manifest.json")
    if binding["version"] != 1 or binding["sha256"] != sha256(entity_path):
        raise BundleError("dataset_manifest.json: entity manifest version/hash mismatch")
    tables = dataset.get("tables")
    if not isinstance(tables, list) or len(tables) != len(TABLE_COLUMNS):
        raise BundleError(f"dataset_manifest.json: tables must contain exactly {len(TABLE_COLUMNS)} entries")
    entries: dict[str, dict] = {}
    required = {"table_name", "file", "row_count", "csv_file_size_bytes", "sha256"}
    for index, entry in enumerate(tables):
        if not isinstance(entry, dict) or set(entry) != required:
            raise BundleError(f"dataset_manifest.json: tables[{index}] has an invalid schema")
        table = entry["table_name"]
        if not isinstance(table, str) or table not in TABLE_COLUMNS:
            raise BundleError(f"dataset_manifest.json: tables[{index}] has unknown table_name")
        if table in entries:
            raise BundleError(f"dataset_manifest.json: duplicate table entry: {table}")
        if entry["file"] != f"{table}.csv" or Path(str(entry["file"])).name != entry["file"]:
            raise BundleError(f"{table}: file must be the canonical basename {table}.csv")
        require_int(entry["row_count"], f"{table}.row_count")
        require_int(entry["csv_file_size_bytes"], f"{table}.csv_file_size_bytes", 1)
        if not isinstance(entry["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]):
            raise BundleError(f"{table}.sha256: expected lowercase SHA-256")
        entries[table] = entry
    if set(entries) != set(TABLE_COLUMNS):
        raise BundleError("dataset_manifest.json: table set does not match TABLE_COLUMNS")
    return dataset, entity, entries


def validate_csv_files(bundle: Path, entries: dict[str, dict]) -> dict[str, set[str]]:
    expected_files = {f"{table}.csv" for table in TABLE_COLUMNS}
    actual_files = {path.name for path in bundle.glob("*.csv")}
    missing = sorted(expected_files - actual_files)
    extra = sorted(actual_files - expected_files)
    if missing or extra:
        raise BundleError(f"CSV table set mismatch; missing={missing}, extra={extra}")
    keys: dict[str, set[str]] = {}
    for table in TABLE_COLUMNS:
        path = bundle / f"{table}.csv"
        entry = entries[table]
        if path.stat().st_size != entry["csv_file_size_bytes"]:
            raise BundleError(f"{table}: file size mismatch")
        if sha256(path) != entry["sha256"]:
            raise BundleError(f"{table}: SHA-256 mismatch")
        count = 0
        table_keys: set[str] = set()
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != TABLE_COLUMNS[table]:
                raise BundleError(f"{table}: header mismatch; expected {TABLE_COLUMNS[table]}, got {reader.fieldnames}")
            primary = PRIMARY_KEYS[table]
            for line_number, row in enumerate(reader, start=2):
                if None in row:
                    raise BundleError(f"{table}:{line_number}: row has more fields than the header")
                missing_cells = [column for column in TABLE_COLUMNS[table] if row[column] is None]
                if missing_cells:
                    raise BundleError(f"{table}:{line_number}: missing trailing field(s): {missing_cells}")
                empty_required = [
                    column
                    for column in TABLE_COLUMNS[table]
                    if column not in NULLABLE_COLUMNS.get(table, set()) and row[column] == ""
                ]
                if empty_required:
                    raise BundleError(
                        f"{table}:{line_number}: empty non-nullable column(s): {', '.join(empty_required)}"
                    )
                key = row[primary]
                if not key:
                    raise BundleError(f"{table}:{line_number}: empty primary key {primary}")
                if key in table_keys:
                    raise BundleError(f"{table}:{line_number}: duplicate primary key {key}")
                table_keys.add(key)
                count += 1
        if count != entry["row_count"]:
            raise BundleError(f"{table}: row count mismatch; expected {entry['row_count']}, got {count}")
        keys[table] = table_keys
    return keys


def validate_references(bundle: Path, keys: dict[str, set[str]]) -> None:
    order_item_orders: dict[str, str] = {}
    refund_txn_requests: dict[str, str] = {}
    order_coupons: dict[str, str] = {}
    coupon_orders: dict[str, tuple[str, str, str]] = {}
    for table in LOAD_TABLE_ORDER:
        with (bundle / f"{table}.csv").open("r", encoding="utf-8", newline="") as handle:
            for line_number, row in enumerate(csv.DictReader(handle), start=2):
                for column, target in FOREIGN_KEYS.get(table, ()):
                    value = row[column]
                    if value and value not in keys[target]:
                        raise BundleError(f"{table}:{line_number}: {column}={value} is absent from {target}")
                if table == "biz_product_change_event":
                    target = {"CATEGORY": "biz_category", "SPU": "biz_spu", "SKU": "biz_sku"}.get(row["target_type"])
                    if target is None or row["target_id"] not in keys[target]:
                        raise BundleError(f"{table}:{line_number}: invalid polymorphic target {row['target_type']}:{row['target_id']}")
                elif table == "biz_order_item":
                    order_item_orders[row["order_item_id"]] = row["order_id"]
                elif table == "biz_refund_request" and order_item_orders.get(row["order_item_id"]) != row["order_id"]:
                    raise BundleError(f"{table}:{line_number}: order_item_id does not belong to order_id")
                elif table == "biz_refund_transaction":
                    refund_txn_requests[row["refund_txn_id"]] = row["refund_request_id"]
                elif table == "biz_refund_event" and row["refund_txn_id"] and refund_txn_requests.get(row["refund_txn_id"]) != row["refund_request_id"]:
                    raise BundleError(f"{table}:{line_number}: refund_txn_id does not belong to refund_request_id")
                elif table == "biz_order" and row["coupon_id"]:
                    order_coupons[row["order_id"]] = row["coupon_id"]
                elif table == "biz_coupon":
                    coupon_orders[row["coupon_id"]] = (row["coupon_status"], row["locked_order_id"], row["used_order_id"])
    for order_id, coupon_id in order_coupons.items():
        status, locked, used = coupon_orders[coupon_id]
        if status in {"LOCKED", "USED"} and order_id not in {locked, used}:
            raise BundleError(f"biz_order: coupon {coupon_id} does not point back to order {order_id}")
    for coupon_id, (_, locked, used) in coupon_orders.items():
        order_id = locked or used
        if order_id and order_coupons.get(order_id) != coupon_id:
            raise BundleError(f"biz_coupon: order {order_id} does not point back to coupon {coupon_id}")


def validate_entity_contents(bundle: Path, entity: dict, keys: dict[str, set[str]]) -> None:
    entities = entity.get("entities")
    if not isinstance(entities, dict) or set(entities) != set(ENTITY_ROW_FIELDS):
        raise BundleError("entity_manifest.json: entities field set is invalid")
    with (bundle / "biz_spu.csv").open(encoding="utf-8", newline="") as handle:
        spu_categories = {row["spu_id"]: int(row["category_id"]) for row in csv.DictReader(handle)}
    with (bundle / "biz_user.csv").open(encoding="utf-8", newline="") as handle:
        expected_users = [
            {"user_id": int(row["user_id"]), "registered_at": row["registered_at"]}
            for row in csv.DictReader(handle)
        ]
    with (bundle / "biz_visitor.csv").open(encoding="utf-8", newline="") as handle:
        expected_visitors = [
            {"visitor_id": int(row["visitor_id"]), "first_seen_at": row["first_seen_at"]}
            for row in csv.DictReader(handle)
        ]
    with (bundle / "biz_sku.csv").open(encoding="utf-8", newline="") as handle:
        expected_skus = [
            {
                "sku_id": int(row["sku_id"]),
                "spu_id": int(row["spu_id"]),
                "category_id": spu_categories[row["spu_id"]],
                "available_from": row["created_at"],
            }
            for row in csv.DictReader(handle)
        ]
    expected_entities = {
        "users": ("user_id", expected_users),
        "visitors": ("visitor_id", expected_visitors),
        "skus": ("sku_id", expected_skus),
    }
    for name, (id_field, expected_rows) in expected_entities.items():
        rows = entities.get(name)
        if not isinstance(rows, list):
            raise BundleError(f"entity_manifest.json: entities.{name} must be an array")
        if any(not isinstance(row, dict) or set(row) != ENTITY_ROW_FIELDS[name] for row in rows):
            raise BundleError(f"entity_manifest.json: entities.{name} row schema is invalid")
        try:
            normalized = [
                {field: (int(value) if field.endswith("_id") else value) for field, value in row.items()}
                for row in rows
            ]
        except (TypeError, ValueError) as exc:
            raise BundleError(f"entity_manifest.json: entities.{name} contains invalid values") from exc
        if sorted(normalized, key=lambda row: row[id_field]) != sorted(expected_rows, key=lambda row: row[id_field]):
            raise BundleError(f"entity_manifest.json: entities.{name} does not exactly match Business CSV facts")
    mappings_rows = entities.get("identity_mappings")
    if not isinstance(mappings_rows, list):
        raise BundleError("entity_manifest.json: entities.identity_mappings must be an array")
    if any(not isinstance(row, dict) or set(row) != ENTITY_ROW_FIELDS["identity_mappings"] for row in mappings_rows):
        raise BundleError("entity_manifest.json: entities.identity_mappings row schema is invalid")

    manifest_mappings = {
        (
            str(row["visitor_id"]),
            str(row["user_id"]),
            "" if row["session_id"] is None else str(row["session_id"]),
            str(row["identity_version"]),
            str(row["effective_from"]),
            None if row["effective_to"] is None else str(row["effective_to"]),
        )
        for row in mappings_rows
    }
    csv_mappings = set()
    mapping_path = bundle / "biz_identity_mapping.csv"
    with mapping_path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            csv_mappings.add(
                (
                    row["visitor_id"],
                    row["user_id"],
                    row["session_id"],
                    row["identity_version"],
                    row["effective_from"],
                    row["effective_to"] or None,
                )
            )
    if len(mappings_rows) != len(manifest_mappings) or manifest_mappings != csv_mappings:
        raise BundleError("entity_manifest.json: entities.identity_mappings does not exactly match biz_identity_mapping")


def validate_business_statistics(bundle: Path, dataset: dict) -> None:
    with (bundle / "biz_order.csv").open(encoding="utf-8", newline="") as handle:
        actual = Counter(row["order_status"] for row in csv.DictReader(handle))
    expected = {
        "paid_orders": actual["PAID"],
        "canceled_orders": actual["CANCELED"],
        "created_orders": actual["CREATED"],
    }
    for field, value in expected.items():
        manifest_value = require_int(dataset["business_statistics"].get(field), f"business_statistics.{field}")
        if manifest_value != value:
            raise BundleError(f"business_statistics.{field}: expected {value}, got {manifest_value}")


def validate_bundle(bundle: Path) -> dict:
    bundle = bundle.resolve()
    if not bundle.is_dir():
        raise BundleError(f"bundle is not a directory: {bundle}")
    dataset, entity, entries = validate_manifests(bundle)
    keys = validate_csv_files(bundle, entries)
    validate_references(bundle, keys)
    validate_entity_contents(bundle, entity, keys)
    validate_business_statistics(bundle, dataset)
    return {
        "status": "valid",
        "dataset_manifest_version": 1,
        "dataset_version": dataset["dataset_version"],
        "generator_version": dataset["generator_version"],
        "seed": dataset["seed"],
        "history_start": dataset["history_start"],
        "history_end": dataset["history_end"],
        "timezone": dataset["timezone"],
        "bundle": str(bundle),
        "load_table_order": LOAD_TABLE_ORDER,
        "tables": [entries[table] for table in LOAD_TABLE_ORDER],
        "business_statistics": dataset.get("business_statistics", {}),
    }


def sql_quote(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"


def render_load_sql(plan: dict, template_path: Path, gate_path: Path) -> str:
    template = template_path.read_text(encoding="utf-8")
    variables = expected_variables(plan)
    schema_parts = []
    for table in LOAD_TABLE_ORDER:
        expected = ",".join(TABLE_COLUMNS[table])
        schema_parts.append(
            "SELECT " + sql_quote(table) + " AS table_name, " + sql_quote(expected) + " AS expected_columns"
        )
    schema_assertions = "\nUNION ALL\n".join(schema_parts)
    load_statements = []
    bundle = Path(plan["bundle"])
    for table in LOAD_TABLE_ORDER:
        fields = []
        assignments = []
        nullable = NULLABLE_COLUMNS.get(table, set())
        for column in TABLE_COLUMNS[table]:
            if column in nullable:
                fields.append(f"@v_{column}")
                assignments.append(f"`{column}` = NULLIF(@v_{column}, '')")
            else:
                fields.append(f"`{column}`")
        statement = [
            f"LOAD DATA LOCAL INFILE {sql_quote((bundle / f'{table}.csv').as_posix())}",
            f"INTO TABLE `{table}` CHARACTER SET utf8mb4",
            "FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '\"' ESCAPED BY '\"'",
            "LINES TERMINATED BY '\\r\\n' IGNORE 1 LINES",
            "(" + ", ".join(fields) + ")",
        ]
        if assignments:
            statement.append("SET " + ", ".join(assignments))
        warning_guard = [
            "SET @source_load_warning_count = @@warning_count;",
            "SET @source_load_guard = IF(@source_load_warning_count = 0, 'SELECT NULL WHERE FALSE', 'SELECT * FROM __source_load_conversion_warning__');",
            "PREPARE source_load_guard_stmt FROM @source_load_guard;",
            "EXECUTE source_load_guard_stmt;",
            "DEALLOCATE PREPARE source_load_guard_stmt;",
        ]
        load_statements.append("\n".join(statement) + ";\n" + "\n".join(warning_guard))
    replacements = {
        "__EXPECTED_VARIABLES__": "\n".join(variables),
        "__SCHEMA_ASSERTIONS__": schema_assertions,
        "__LOAD_STATEMENTS__": "\n\n".join(load_statements),
        "__SOURCE_GATE_PATH__": gate_path.resolve().as_posix(),
    }
    for marker, value in replacements.items():
        if marker not in template:
            raise BundleError(f"load SQL template is missing marker {marker}")
        template = template.replace(marker, value)
    return template


def expected_variables(plan: dict) -> list[str]:
    entries = {entry["table_name"]: entry for entry in plan["tables"]}
    variables = [f"SET @expected_{table} = {entries[table]['row_count']};" for table in LOAD_TABLE_ORDER]
    statistics = plan.get("business_statistics", {})
    for name in ("paid_orders", "canceled_orders", "created_orders"):
        variables.append(f"SET @expected_{name} = {require_int(statistics.get(name), f'business_statistics.{name}')};")
    return variables


def render_gate_sql(plan: dict, gate_path: Path) -> str:
    return "\n".join(expected_variables(plan)) + f"\nSOURCE {gate_path.resolve().as_posix()}\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--output", type=Path, help="write the JSON plan to this file as well as stdout")
    parser.add_argument("--render-load-sql", type=Path, help="render one-session load SQL after validation")
    parser.add_argument("--render-gate-sql", type=Path, help="render expected variables plus Source Gate for one session")
    parser.add_argument("--load-template", type=Path, default=REPO_ROOT / "mysql" / "sql" / "load_v2_csv.sql")
    parser.add_argument("--source-gate", type=Path, default=REPO_ROOT / "mysql" / "sql" / "source_gate.sql")
    args = parser.parse_args(argv)
    try:
        plan = validate_bundle(args.bundle)
        rendered = json.dumps(plan, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.write_text(rendered, encoding="utf-8", newline="\n")
        if args.render_load_sql:
            args.render_load_sql.write_text(
                render_load_sql(plan, args.load_template, args.source_gate), encoding="utf-8", newline="\n"
            )
        if args.render_gate_sql:
            args.render_gate_sql.write_text(render_gate_sql(plan, args.source_gate), encoding="utf-8", newline="\n")
    except (BundleError, OSError) as exc:
        print(json.dumps({"status": "invalid", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
