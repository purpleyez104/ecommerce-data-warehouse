#!/usr/bin/env python3
"""Build a formal ODS Bootstrap contract from a verified Business bundle."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

import generate_job


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def _business_date_column(policy: dict) -> str | None:
    business_time = policy["business_time"]
    return None if business_time["mode"] == "parameter" else business_time["column"]


def build_contract(bundle: Path, output_dir: Path, batch_id: str, extract_time: str) -> dict:
    """Validate the immutable bundle and emit a snapshot manifest plus batch contract."""
    manifest_path = bundle / "dataset_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("dataset_manifest_version") != 1:
        raise ValueError("unsupported dataset manifest version")
    contract = generate_job.load_contract()
    manifest_tables = {item["table_name"]: item for item in manifest.get("tables", [])}
    if set(manifest_tables) != set(contract["tables"]):
        raise ValueError("dataset manifest table set does not match ODS contract")

    history_end = datetime.fromisoformat(manifest["history_end"])
    business_date = history_end.date().isoformat()
    tables = []
    for table, policy in contract["tables"].items():
        item = manifest_tables[table]
        csv_path = bundle / item["file"]
        if not csv_path.is_file() or csv_path.stat().st_size != item["csv_file_size_bytes"] or _sha256(csv_path) != item["sha256"]:
            raise ValueError(f"bundle file binding mismatch: {table}")
        date_column = _business_date_column(policy)
        counts: Counter[str] = Counter()
        rows = 0
        with csv_path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != generate_job.TABLE_COLUMNS[table]:
                raise ValueError(f"CSV column contract mismatch: {table}")
            for row in reader:
                rows += 1
                date_value = business_date if date_column is None else row[date_column][:10]
                try:
                    datetime.strptime(date_value, "%Y-%m-%d")
                except ValueError as exc:
                    raise ValueError(f"invalid business date in {table}: {date_value}") from exc
                counts[date_value] += 1
        if rows != item["row_count"]:
            raise ValueError(f"dataset row count mismatch: {table}")
        tables.append({
            "table_name": table,
            "row_count": rows,
            "affected_business_dates": sorted(counts),
            "business_date_row_counts": dict(sorted(counts.items())),
        })

    snapshot_manifest = {
        "snapshot_manifest_version": 1,
        "dataset_version": manifest["dataset_version"],
        "dataset_manifest": {"path": str(manifest_path.resolve()), "sha256": _sha256(manifest_path)},
        "history_start": manifest["history_start"],
        "history_end": manifest["history_end"],
        "tables": tables,
    }
    snapshot_path = output_dir / "snapshot_manifest.json"
    _write_json(snapshot_path, snapshot_manifest)
    expected = {
        item["table_name"]: {
            "row_count": item["row_count"],
            "affected_business_dates": item["affected_business_dates"],
            "business_date_row_counts": item["business_date_row_counts"],
        }
        for item in tables
    }
    batch = {
        "batch_contract_version": 2,
        "dataset_version": manifest["dataset_version"],
        "mode": "bootstrap",
        "business_date": business_date,
        "window_start": None,
        "window_end": None,
        "batch_id": batch_id,
        "extract_time": generate_job._parse_timestamp("extract_time", extract_time),
        "source_manifest": {"type": "dataset_snapshot", "path": "snapshot_manifest.json", "sha256": _sha256(snapshot_path)},
        "expected_tables": expected,
    }
    batch_path = output_dir / "ods_batch_contract.json"
    _write_json(batch_path, batch)
    return {"snapshot_manifest": snapshot_path, "batch_contract": batch_path, "table_count": len(tables)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--extract-time", required=True)
    args = parser.parse_args(argv)
    if args.output_dir.exists():
        raise FileExistsError(f"output directory already exists: {args.output_dir}")
    args.output_dir.mkdir(parents=True)
    result = build_contract(args.bundle.resolve(), args.output_dir.resolve(), args.batch_id, args.extract_time)
    print(json.dumps({"status": "generated", **{key: str(value) for key, value in result.items()}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
