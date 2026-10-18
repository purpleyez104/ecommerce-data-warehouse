#!/usr/bin/env python3
"""Preflight one Behavior Replay package and render Spark ODS load/gate SQL."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPO_ROOT / "hive/ods/behavior_event_contract.json"
EVENT_ID = re.compile(r"^BEH-[0-9a-f]{12}-[0-9]{12}$")
IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
EXPECTED_FIELDS = {
    "event_id", "event_type", "event_time", "identity_version", "ingest_time",
    "page_id", "quantity", "session_id", "sku_id", "user_id", "visitor_id",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _package_ref(manifest: dict, package: str) -> dict:
    if package == "bootstrap":
        ref = manifest.get("bootstrap")
    else:
        match = re.fullmatch(r"day_(6[1-9]|[78][0-9]|90)", package)
        if match is None:
            raise ValueError("package must be bootstrap or day_61..day_90")
        day = int(match.group(1))
        ref = next((item for item in manifest.get("daily_packages", []) if item.get("day_start") == day), None)
    if not isinstance(ref, dict):
        raise ValueError(f"package is missing from replay manifest: {package}")
    return ref


def preflight_package(bundle: Path, package: str) -> dict:
    """Validate package manifest, file hash, exact schema and core event invariants."""
    replay_path = bundle / "replay_manifest.json"
    replay = json.loads(replay_path.read_text(encoding="utf-8"))
    if replay.get("timezone") != "Asia/Shanghai":
        raise ValueError("behavior replay timezone must be Asia/Shanghai")
    ref = _package_ref(replay, package)
    package_dir = bundle / ref["path"]
    manifest_path = package_dir / "package_manifest.json"
    events_path = package_dir / "events.jsonl"
    if _sha256(manifest_path) != ref.get("manifest_sha256"):
        raise ValueError("package manifest hash mismatch")
    package_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = package_manifest.get("events", {})
    if _sha256(events_path) != expected.get("sha256") or expected.get("sha256") != ref.get("events_sha256"):
        raise ValueError("event file hash mismatch")

    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    allowed = set(contract["event_types"])
    seen: set[str] = set()
    type_counts: Counter[str] = Counter()
    date_counts: Counter[str] = Counter()
    row_count = 0
    with events_path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            event = json.loads(line)
            if set(event) != EXPECTED_FIELDS:
                raise ValueError(f"behavior event schema mismatch at line {line_number}")
            event_id = event["event_id"]
            if not isinstance(event_id, str) or EVENT_ID.fullmatch(event_id) is None or event_id in seen:
                raise ValueError(f"invalid or duplicate event_id at line {line_number}")
            event_time = datetime.fromisoformat(event["event_time"])
            ingest_time = datetime.fromisoformat(event["ingest_time"])
            if ingest_time < event_time:
                raise ValueError(f"ingest_time precedes event_time at line {line_number}")
            event_type = event["event_type"]
            if event_type not in allowed:
                raise ValueError(f"unsupported event_type at line {line_number}")
            if not isinstance(event["visitor_id"], int) or not isinstance(event["session_id"], str) or not event["session_id"]:
                raise ValueError(f"invalid visitor/session at line {line_number}")
            quantity = event["quantity"]
            if (event_type in {"ADD_CART", "REMOVE_CART"}) != isinstance(quantity, int):
                raise ValueError(f"invalid quantity semantics at line {line_number}")
            seen.add(event_id)
            type_counts[event_type] += 1
            date_counts[event_time.date().isoformat()] += 1
            row_count += 1
    if row_count != expected.get("row_count") or row_count != ref.get("event_count"):
        raise ValueError("behavior package row count mismatch")
    if dict(sorted(type_counts.items())) != expected.get("event_type_counts"):
        raise ValueError("behavior package event type counts mismatch")
    return {
        "package": package,
        "relative_path": ref["path"],
        "row_count": row_count,
        "event_type_counts": dict(sorted(type_counts.items())),
        "business_date_row_counts": dict(sorted(date_counts.items())),
        "events_sha256": expected["sha256"],
    }


def preflight_bundle(bundle: Path) -> dict:
    """逐包校验完整 60/30 Bundle，并聚合最终 ODS 期望。"""
    packages = ["bootstrap", *[f"day_{day}" for day in range(61, 91)]]
    results = [preflight_package(bundle, package) for package in packages]
    date_counts: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()
    for result in results:
        date_counts.update(result["business_date_row_counts"])
        type_counts.update(result["event_type_counts"])
    total = sum(item["row_count"] for item in results)
    replay = json.loads((bundle / "replay_manifest.json").read_text(encoding="utf-8"))
    if total != replay.get("event_count"):
        raise ValueError("behavior bundle row count mismatch")
    return {
        "package": "all",
        "row_count": total,
        "event_type_counts": dict(sorted(type_counts.items())),
        "business_date_row_counts": dict(sorted(date_counts.items())),
        "content_sha256": replay["content_sha256"],
        "package_count": len(results),
    }


def _quoted(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def render_sql(preflight: dict, input_uri: str, database: str, batch_id: str) -> tuple[str, str]:
    """Render idempotent dynamic-partition publish SQL and an independent gate."""
    if not IDENTIFIER.fullmatch(database) or not re.fullmatch(r"[A-Za-z0-9._-]+", batch_id):
        raise ValueError("invalid database or batch_id")
    if not input_uri or "'" in input_uri:
        raise ValueError("invalid input URI")
    total = preflight["row_count"]
    recursive_option = ", recursiveFileLookup 'true', pathGlobFilter 'events.jsonl'" if preflight.get("package") == "all" else ""
    load_sql = "\n".join([
        "SET spark.sql.ansi.enabled=true;",
        "SET spark.sql.sources.partitionOverwriteMode=dynamic;",
        "CREATE OR REPLACE TEMPORARY VIEW `behavior_json_stage` USING json",
        f"OPTIONS (path {_quoted(input_uri)}{recursive_option});",
        f"SELECT assert_true(COUNT(*)={total}, 'behavior staging row count mismatch') FROM `behavior_json_stage`;",
        f"INSERT OVERWRITE TABLE `{database}`.`ods_behavior_event` PARTITION (`dt`)",
        "SELECT CAST(`event_id` AS STRING), CAST(`event_type` AS STRING), CAST(`event_time` AS TIMESTAMP),",
        "  CAST(`identity_version` AS BIGINT), CAST(`ingest_time` AS TIMESTAMP), CAST(`page_id` AS STRING),",
        "  CAST(`quantity` AS INT), CAST(`session_id` AS STRING), CAST(`sku_id` AS BIGINT),",
        "  CAST(`user_id` AS BIGINT), CAST(`visitor_id` AS BIGINT),",
        f"  {_quoted(batch_id)}, input_file_name(), current_timestamp(), date_format(to_timestamp(`event_time`), 'yyyy-MM-dd')",
        "FROM `behavior_json_stage`;",
        "",
    ])
    gate = [
        "SET spark.sql.ansi.enabled=true;",
        f"SELECT assert_true(COUNT(*)={total}, 'behavior batch row count mismatch') FROM `{database}`.`ods_behavior_event` WHERE `batch_id`={_quoted(batch_id)};",
        f"SELECT assert_true(COUNT(*)=0, 'behavior duplicate event_id') FROM (SELECT `event_id`, COUNT(*) c FROM `{database}`.`ods_behavior_event` GROUP BY `event_id` HAVING c>1) d;",
        f"SELECT assert_true(COUNT(*)=0, 'behavior invalid event') FROM `{database}`.`ods_behavior_event` WHERE `event_id` IS NULL OR `session_id` IS NULL OR `visitor_id` IS NULL OR `ingest_time` < `event_time` OR `event_type` NOT IN ('PAGE_VIEW','PRODUCT_EXPOSURE','PRODUCT_CLICK','ADD_CART','REMOVE_CART');",
    ]
    for business_date, count in preflight["business_date_row_counts"].items():
        gate.append(f"SELECT assert_true(COUNT(*)={count}, 'behavior {business_date} row count mismatch') FROM `{database}`.`ods_behavior_event` WHERE `batch_id`={_quoted(batch_id)} AND `dt`={_quoted(business_date)};")
    gate.extend(["SELECT 'BEHAVIOR_ODS_GATE_PASS';", ""])
    return load_sql, "\n".join(gate)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--package", required=True, help="bootstrap, day_61..day_90, or all")
    parser.add_argument("--input-uri", required=True)
    parser.add_argument("--database", default="ecommerce_ods")
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = preflight_bundle(args.bundle.resolve()) if args.package == "all" else preflight_package(args.bundle.resolve(), args.package)
    load_sql, gate_sql = render_sql(result, args.input_uri, args.database, args.batch_id)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    (args.output_dir / "load.sql").write_text(load_sql, encoding="utf-8", newline="\n")
    (args.output_dir / "gate.sql").write_text(gate_sql, encoding="utf-8", newline="\n")
    (args.output_dir / "preflight.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
