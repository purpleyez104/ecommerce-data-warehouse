"""Build a deterministic 60-day bootstrap and 30-day replay bundle."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import tempfile
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from .common import DT_FORMAT, canonical_json, dt
from .config import DatasetConfig, load_config
from .contracts import LOAD_TABLE_ORDER, TABLE_COLUMNS, TABLE_ORDER
from .generator import generate


REPLAY_MANIFEST_VERSION = 1
PRIMARY_KEYS = {table: columns[0] for table, columns in TABLE_COLUMNS.items()}
LOAD_RANK = {table: index for index, table in enumerate(LOAD_TABLE_ORDER)}
APPEND_ONLY = {
    "biz_product_change_event", "biz_cart_merge_record", "biz_order_status_event",
    "biz_payment_event", "biz_refund_event", "biz_coupon_event",
}
CREATED_AT = {
    "biz_user": "created_at", "biz_visitor": "created_at", "biz_identity_mapping": "recorded_at",
    "biz_category": "created_at", "biz_spu": "created_at", "biz_sku": "created_at",
    "biz_cart": "created_at", "biz_cart_item": "created_at", "biz_order": "created_at",
    "biz_order_item": "created_at", "biz_payment_attempt": "created_at",
    "biz_refund_request": "created_at", "biz_refund_transaction": "created_at",
    "biz_coupon_template": "created_at", "biz_coupon": "issued_at",
}
BUSINESS_TIME = {
    "biz_user": "registered_at", "biz_visitor": "first_seen_at", "biz_identity_mapping": "effective_from",
    "biz_category": "created_at", "biz_spu": "created_at", "biz_sku": "created_at",
    "biz_product_change_event": "effective_at", "biz_cart": "created_at", "biz_cart_item": "created_at",
    "biz_cart_merge_record": "merged_at", "biz_order": "created_at", "biz_order_item": "created_at",
    "biz_order_status_event": "occurred_at", "biz_payment_attempt": "initiated_at",
    "biz_payment_event": "occurred_at", "biz_refund_request": "requested_at",
    "biz_refund_transaction": "initiated_at", "biz_refund_event": "occurred_at",
    "biz_coupon_template": "created_at", "biz_coupon": "issued_at", "biz_coupon_event": "occurred_at",
}
RECORD_TIME = {
    "biz_product_change_event": "recorded_at",
    "biz_cart_merge_record": "merged_at",
    "biz_order_status_event": "recorded_at",
    "biz_payment_event": "recorded_at",
    "biz_refund_event": "recorded_at",
    "biz_coupon_event": "recorded_at",
}


def _parse(value: str) -> datetime:
    return datetime.strptime(value, DT_FORMAT) if value else datetime.min


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, table: str, rows: list[dict[str, str]]) -> dict:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=TABLE_COLUMNS[table], extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)
    date_counts = Counter(row[BUSINESS_TIME[table]][:10] for row in rows if row.get(BUSINESS_TIME[table]))
    return {
        "file": path.name,
        "row_count": len(rows),
        "sha256": _sha256(path),
        "affected_business_dates": sorted(date_counts),
        "business_date_row_counts": dict(sorted(date_counts.items())),
    }


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _sku_initial_prices(skus: list[dict[str, str]], changes: list[dict[str, str]]) -> dict[str, str]:
    prices = {row["sku_id"]: row["sale_price_cents"] for row in skus}
    grouped = defaultdict(list)
    for change in changes:
        if change["target_type"] != "SKU" or change["target_id"] not in prices:
            raise ValueError("product change event must reference a generated SKU")
        grouped[change["target_id"]].append(change)
    for sku_id, items in grouped.items():
        for change in sorted(items, key=lambda item: (item["effective_at"], item["change_id"]), reverse=True):
            before = json.loads(change["before_data"])
            after = json.loads(change["after_data"])
            if "sale_price_cents" not in before or "sale_price_cents" not in after:
                raise ValueError("cannot rebuild SKU price without before/after sale_price_cents")
            prices[sku_id] = str(before["sale_price_cents"])
    return prices


def _initial_row(table: str, row: dict[str, str], sku_prices: dict[str, str]) -> dict[str, str]:
    result = dict(row)
    if table == "biz_order":
        result.update(order_status="CREATED", paid_at="", canceled_at="", updated_at=row["created_at"])
    elif table == "biz_order_item":
        result.update(refund_reserved_cents="0", refunded_cents="0", refunded_quantity="0", updated_at=row["created_at"])
    elif table == "biz_payment_attempt":
        result.update(payment_status="INIT", succeeded_at="", updated_at=row["created_at"])
    elif table == "biz_refund_request":
        result.update(refund_status="REQUESTED", completed_at="", updated_at=row["created_at"])
    elif table == "biz_refund_transaction":
        result.update(refund_txn_status="INIT", succeeded_at="", updated_at=row["created_at"])
    elif table == "biz_coupon":
        result.update(coupon_status="UNUSED", locked_order_id="", used_order_id="", locked_at="", used_at="", updated_at=row["issued_at"])
    elif table == "biz_visitor":
        result.update(last_seen_at=row["first_seen_at"], updated_at=row["created_at"])
    elif table in {"biz_cart", "biz_cart_item"}:
        result["updated_at"] = row["created_at"]
    elif table == "biz_sku":
        result.update(sale_price_cents=sku_prices[row["sku_id"]], updated_at=row["created_at"])
    return result


def _build_actions(all_rows: dict[str, list[dict[str, str]]]) -> list[dict]:
    actions: list[dict] = []

    def add(table: str, kind: str, operation_time: str, *, row=None, key=None, changes=None) -> None:
        actions.append({
            "table": table, "kind": kind, "operation_time": _parse(operation_time),
            "row": dict(row) if row is not None else None, "key": str(key) if key is not None else None,
            "changes": dict(changes) if changes is not None else None, "stable_sequence": len(actions),
        })

    sku_prices = _sku_initial_prices(all_rows["biz_sku"], all_rows["biz_product_change_event"])
    lifecycle = {"biz_order", "biz_order_item", "biz_payment_attempt", "biz_refund_request", "biz_refund_transaction", "biz_coupon", "biz_sku"}
    for table in TABLE_ORDER:
        if table in APPEND_ONLY:
            continue
        for row in all_rows[table]:
            initial = _initial_row(table, row, sku_prices)
            add(table, "INSERT", row[CREATED_AT[table]], row=initial)
            if table not in lifecycle and "updated_at" in row and row["updated_at"] > initial["updated_at"]:
                add(table, "UPDATE", row["updated_at"], key=row[PRIMARY_KEYS[table]], changes=row)
    for table in LOAD_TABLE_ORDER:
        if table not in APPEND_ONLY:
            continue
        for row in all_rows[table]:
            add(table, "INSERT", row[RECORD_TIME[table]], row=row)

    final = {table: {row[PRIMARY_KEYS[table]]: row for row in rows} for table, rows in all_rows.items()}
    for event in all_rows["biz_order_status_event"]:
        if event["event_type"] == "CREATE":
            continue
        changes = {"order_status": event["to_status"], "updated_at": event["occurred_at"]}
        if event["event_type"] == "PAY":
            changes["paid_at"] = event["occurred_at"]
        elif event["event_type"] == "CANCEL":
            changes["canceled_at"] = event["occurred_at"]
        else:
            raise ValueError(f"unsupported order event: {event['event_type']}")
        add("biz_order", "UPDATE", event["occurred_at"], key=event["order_id"], changes=changes)
    for event in all_rows["biz_payment_event"]:
        changes = {"payment_status": event["to_status"], "updated_at": event["occurred_at"]}
        if event["to_status"] == "SUCCESS":
            changes["succeeded_at"] = event["occurred_at"]
        add("biz_payment_attempt", "UPDATE", event["occurred_at"], key=event["payment_attempt_id"], changes=changes)

    items = final["biz_order_item"]
    updated_items: set[str] = set()
    for request in all_rows["biz_refund_request"]:
        if request["updated_at"] != request["created_at"] or request["refund_status"] != "REQUESTED":
            add(
                "biz_refund_request", "UPDATE", request["updated_at"],
                key=request["refund_request_id"], changes=request,
            )
        item = items[request["order_item_id"]]
        if item["updated_at"] != item["created_at"] and request["order_item_id"] not in updated_items:
            add(
                "biz_order_item", "UPDATE", item["updated_at"],
                key=request["order_item_id"], changes=item,
            )
            updated_items.add(request["order_item_id"])
    for row in all_rows["biz_refund_transaction"]:
        if row["updated_at"] != row["created_at"] or row["refund_txn_status"] != "INIT":
            add("biz_refund_transaction", "UPDATE", row["updated_at"], key=row["refund_txn_id"], changes={
                "refund_txn_status": row["refund_txn_status"], "succeeded_at": row["succeeded_at"], "updated_at": row["updated_at"],
            })

    for event in all_rows["biz_coupon_event"]:
        kind = event["event_type"]
        if kind == "ISSUE":
            continue
        changes = {"coupon_status": event["to_status"], "updated_at": event["occurred_at"]}
        if kind == "LOCK":
            changes.update(locked_order_id=event["order_id"], locked_at=event["occurred_at"])
        elif kind == "USE":
            changes.update(locked_order_id="", locked_at="", used_order_id=event["order_id"], used_at=event["occurred_at"])
        elif kind == "UNLOCK":
            changes.update(locked_order_id="", locked_at="", used_order_id="", used_at="")
        elif kind != "EXPIRE":
            raise ValueError(f"unsupported coupon event: {kind}")
        add("biz_coupon", "UPDATE", event["occurred_at"], key=event["coupon_id"], changes=changes)
    for event in all_rows["biz_product_change_event"]:
        after = json.loads(event["after_data"])
        if "sale_price_cents" not in after:
            raise ValueError("cannot apply SKU change without after sale_price_cents")
        add("biz_sku", "UPDATE", event["effective_at"], key=event["target_id"], changes={
            "sale_price_cents": str(after["sale_price_cents"]), "updated_at": event["effective_at"],
        })
    return sorted(actions, key=lambda item: (item["operation_time"], LOAD_RANK[item["table"]], item["stable_sequence"]))


def _apply_action(action: dict, state: dict[str, dict[str, dict[str, str]]], sequence: int) -> dict:
    table = action["table"]
    pk = PRIMARY_KEYS[table]
    if action["kind"] == "INSERT":
        row = dict(action["row"])
        key = row[pk]
        if key in state[table]:
            raise ValueError(f"duplicate replay INSERT: {table}.{key}")
    else:
        key = action["key"]
        if key not in state[table]:
            raise ValueError(f"replay UPDATE before INSERT: {table}.{key}")
        row = dict(state[table][key])
        row.update(action["changes"])
    state[table][key] = row
    business_column = BUSINESS_TIME[table]
    return {
        "sequence": sequence, "operation_time": dt(action["operation_time"]), "table": table,
        "operation_type": action["kind"], "primary_key": {pk: key},
        "business_date": row.get(business_column, "")[:10], "row": row,
    }


def _extract_summary(table: str, operations: list[dict], state: dict[str, dict[str, dict[str, str]]], snapshot_date: str) -> dict:
    if table == "biz_identity_mapping":
        rows = list(state[table].values())
        date_counts = {snapshot_date: len(rows)} if rows else {}
    else:
        by_key = {}
        pk = PRIMARY_KEYS[table]
        for operation in operations:
            if operation["table"] == table:
                by_key[operation["primary_key"][pk]] = operation["row"]
        rows = list(by_key.values())
        date_counts = dict(sorted(Counter(
            row[BUSINESS_TIME[table]][:10] for row in rows if row.get(BUSINESS_TIME[table])
        ).items()))
    return {
        "extract_row_count": len(rows),
        "affected_business_dates": sorted(date_counts),
        "business_date_row_counts": date_counts,
    }


def _assert_final_state(state: dict[str, dict[str, dict[str, str]]], all_rows: dict[str, list[dict[str, str]]]) -> None:
    for table in TABLE_ORDER:
        pk = PRIMARY_KEYS[table]
        expected = {row[pk]: row for row in all_rows[table]}
        if state[table] != expected:
            mismatched = sorted(
                key for key in set(state[table]) | set(expected)
                if state[table].get(key) != expected.get(key)
            )
            sample = ", ".join(mismatched[:3])
            raise ValueError(f"replay final state mismatch: {table} primary keys [{sample}]")


def _expected_tables(items: list[dict], count_key: str) -> dict[str, dict]:
    return {
        item["table_name"]: {
            "row_count": item[count_key],
            "affected_business_dates": item["affected_business_dates"],
            "business_date_row_counts": item["business_date_row_counts"],
        }
        for item in items
    }


def _publish_directory(work: Path, output: Path) -> None:
    for attempt in range(5):
        try:
            os.replace(work, output)
            return
        except PermissionError:
            if os.name != "nt" or attempt == 4:
                raise
            time.sleep(0.05 * (attempt + 1))


def build_replay(config: DatasetConfig, seed: int, generated_at: str, output: Path) -> dict:
    if output.exists():
        raise FileExistsError(f"output already exists; choose a new directory: {output}")
    history_start = datetime.combine(config.start.date(), datetime.min.time())
    cutover = history_start + timedelta(days=60)
    replay_end = history_start + timedelta(days=90)
    if config.history_days != 90 or config.end != replay_end - timedelta(milliseconds=1):
        raise ValueError("history_end must equal the final millisecond of day 90")
    datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    output.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f".{output.name}.incomplete-", dir=output.parent))
    try:
        final_dir = work / "_final"
        source_manifest = generate(config, seed, generated_at, final_dir)
        all_rows = {table: _read_csv(final_dir / f"{table}.csv") for table in TABLE_ORDER}
        actions = _build_actions(all_rows)
        if any(action["operation_time"] < history_start or action["operation_time"] >= replay_end for action in actions):
            raise ValueError("replay action outside the configured 90-day window")
        state = {table: {} for table in TABLE_ORDER}
        before_cutover = [action for action in actions if action["operation_time"] < cutover]
        after_cutover = [action for action in actions if action["operation_time"] >= cutover]
        for sequence, action in enumerate(before_cutover, start=1):
            _apply_action(action, state, sequence)

        bootstrap_dir = work / "bootstrap"
        bootstrap_dir.mkdir()
        table_entries = []
        bootstrap_counts = {}
        for table in TABLE_ORDER:
            rows = [state[table][key] for key in sorted(state[table], key=lambda value: int(value))]
            entry = _write_csv(bootstrap_dir / f"{table}.csv", table, rows)
            entry.update(table_name=table, extract_row_count=entry["row_count"])
            bootstrap_counts[table] = entry["row_count"]
            if table == "biz_identity_mapping":
                entry["affected_business_dates"] = [(cutover - timedelta(days=1)).date().isoformat()] if rows else []
                entry["business_date_row_counts"] = {
                    (cutover - timedelta(days=1)).date().isoformat(): len(rows)
                } if rows else {}
                entry["watermark"] = {"mode": "full_snapshot", "snapshot_date": (cutover - timedelta(days=1)).date().isoformat()}
            else:
                entry["watermark"] = {"mode": "upper_bound", "upper_exclusive": dt(cutover)}
            table_entries.append(entry)

        packages = []
        for day_index in range(30):
            window_start = cutover + timedelta(days=day_index)
            window_end = window_start + timedelta(days=1)
            package_dir = work / "daily" / f"day_{61 + day_index:02d}"
            package_dir.mkdir(parents=True)
            selected = [action for action in after_cutover if window_start <= action["operation_time"] < window_end]
            operations = [_apply_action(action, state, index) for index, action in enumerate(selected, start=1)]
            operations_path = package_dir / "operations.jsonl"
            with operations_path.open("w", encoding="utf-8", newline="\n") as handle:
                for operation in operations:
                    handle.write(canonical_json(operation) + "\n")
            expected_path = package_dir / "expected_result.json"
            _write_json(expected_path, {
                "window_end": dt(window_end), "table_row_counts": {table: len(state[table]) for table in TABLE_ORDER},
                "order_status_counts": dict(sorted(Counter(row["order_status"] for row in state["biz_order"].values()).items())),
            })
            counts = Counter(operation["table"] for operation in operations)
            table_items = []
            for table in TABLE_ORDER:
                summary = _extract_summary(table, operations, state, window_start.date().isoformat())
                table_items.append({
                    "table_name": table, "operation_count": counts[table], **summary,
                    "watermark": ({"mode": "full_snapshot", "snapshot_date": window_start.date().isoformat()}
                                  if table == "biz_identity_mapping"
                                  else {"mode": "half_open", "start": dt(window_start), "end": dt(window_end)}),
                })
            package_manifest = {
                "package_version": 1, "day_number": 61 + day_index,
                "batch_id": f"{config.raw['dataset_version']}-day-{61 + day_index:02d}",
                "window_start": dt(window_start), "window_end": dt(window_end),
                "operations": {"file": operations_path.name, "row_count": len(operations), "sha256": _sha256(operations_path)},
                "expected_result": {"file": expected_path.name, "sha256": _sha256(expected_path)}, "tables": table_items,
            }
            package_manifest_path = package_dir / "package_manifest.json"
            _write_json(package_manifest_path, package_manifest)
            packages.append({
                "day_number": 61 + day_index, "path": str(package_dir.relative_to(work)).replace(os.sep, "/"),
                "window_start": dt(window_start), "window_end": dt(window_end), "manifest_sha256": _sha256(package_manifest_path),
            })

        bootstrap_expected_path = bootstrap_dir / "expected_result.json"
        _write_json(bootstrap_expected_path, {"table_row_counts": bootstrap_counts})
        source_contract_dir = work / "source_contract"
        source_contract_dir.mkdir()
        source_manifest_path = source_contract_dir / "dataset_manifest.json"
        entity_manifest_path = source_contract_dir / source_manifest["entity_manifest"]["file"]
        shutil.copy2(final_dir / "dataset_manifest.json", source_manifest_path)
        shutil.copy2(final_dir / source_manifest["entity_manifest"]["file"], entity_manifest_path)
        manifest = {
            "replay_manifest_version": REPLAY_MANIFEST_VERSION, "dataset_version": config.raw["dataset_version"],
            "generator_version": source_manifest["generator_version"], "seed": seed, "timezone": "Asia/Shanghai",
            "generated_at": generated_at, "history_start": dt(history_start), "cutover_time": dt(cutover),
            "replay_end_exclusive": dt(replay_end),
            "source_bundle": {
                "dataset_manifest": {"path": "source_contract/dataset_manifest.json", "sha256": _sha256(source_manifest_path)},
                "entity_manifest": {"path": f"source_contract/{entity_manifest_path.name}", "sha256": _sha256(entity_manifest_path)},
            },
            "bootstrap": {"path": "bootstrap", "tables": table_entries, "expected_result": {"file": "expected_result.json", "sha256": _sha256(bootstrap_expected_path)}},
            "daily_packages": packages,
        }
        hash_input = {
            "bootstrap": [{"table_name": item["table_name"], "sha256": item["sha256"]} for item in table_entries],
            "daily": [{"day_number": item["day_number"], "manifest_sha256": item["manifest_sha256"]} for item in packages],
        }
        manifest["business_hash"] = hashlib.sha256(canonical_json(hash_input).encode("utf-8")).hexdigest()
        replay_manifest_path = work / "replay_manifest.json"
        _write_json(replay_manifest_path, manifest)
        replay_sha256 = _sha256(replay_manifest_path)
        _write_json(bootstrap_dir / "ods_batch_contract.json", {
            "batch_contract_version": 1, "dataset_version": manifest["dataset_version"], "mode": "bootstrap",
            "business_date": (cutover - timedelta(days=1)).date().isoformat(), "window_start": None, "window_end": None,
            "batch_id": f"{manifest['dataset_version']}-bootstrap-day-60", "extract_time": dt(cutover),
            "replay_manifest": {"path": "../replay_manifest.json", "sha256": replay_sha256},
            "expected_tables": _expected_tables(table_entries, "extract_row_count"),
        })
        for package_ref in packages:
            package_dir = work / package_ref["path"]
            package = json.loads((package_dir / "package_manifest.json").read_text(encoding="utf-8"))
            _write_json(package_dir / "ods_batch_contract.json", {
                "batch_contract_version": 1, "dataset_version": manifest["dataset_version"], "mode": "incremental",
                "business_date": package_ref["window_start"][:10], "window_start": package_ref["window_start"],
                "window_end": package_ref["window_end"], "batch_id": package["batch_id"], "extract_time": package_ref["window_end"],
                "replay_manifest": {"path": "../../replay_manifest.json", "sha256": replay_sha256},
                "expected_tables": _expected_tables(package["tables"], "extract_row_count"),
            })
        _assert_final_state(state, all_rows)
        shutil.rmtree(final_dir)
        _publish_directory(work, output)
        return manifest
    except Exception:
        shutil.rmtree(work, ignore_errors=True)
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--generated-at", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manifest = build_replay(load_config(args.config), args.seed, args.generated_at, args.output)
    print(canonical_json({"status": "generated", "output": str(args.output), "business_hash": manifest["business_hash"], "daily_packages": len(manifest["daily_packages"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
