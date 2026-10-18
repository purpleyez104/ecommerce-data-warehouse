from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GENERATOR_SRC = ROOT / "mock" / "generator" / "business_generator" / "src"
sys.path.insert(0, str(GENERATOR_SRC))

from business_generator.common import canonical_json
from business_generator.contracts import TABLE_COLUMNS, TABLE_ORDER


SCRIPT = ROOT / "mysql" / "scripts" / "replay_daily_package.py"
ZERO_HASH = "0" * 64


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def row(table: str, key: str) -> dict[str, str]:
    result = {column: f"{table}-{column}" for column in TABLE_COLUMNS[table]}
    result[TABLE_COLUMNS[table][0]] = key
    if "created_at" in result:
        result["created_at"] = "2026-03-02 00:00:00.000"
    if "updated_at" in result:
        result["updated_at"] = "2026-03-02 00:00:00.000"
    if table == "biz_user":
        result["registered_at"] = "2026-03-02 00:00:00.000"
    if table == "biz_visitor":
        result["first_seen_at"] = "2026-03-02 00:00:00.000"
        result["last_seen_at"] = "2026-03-02 00:00:00.000"
    return result


class ReplayDailyPackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name) / "base"
        self.make_bundle(self.base)

    def tearDown(self):
        self.temp.cleanup()

    def make_bundle(self, root: Path) -> None:
        package_dir = root / "daily" / "day_61"
        package_dir.mkdir(parents=True)
        operations = [
            {
                "sequence": 1,
                "operation_time": "2026-03-02 00:00:00.000",
                "table": "biz_user",
                "operation_type": "INSERT",
                "primary_key": {"user_id": "101"},
                "business_date": "2026-03-02",
                "row": row("biz_user", "101"),
            },
            {
                "sequence": 2,
                "operation_time": "2026-03-02 00:00:00.000",
                "table": "biz_visitor",
                "operation_type": "INSERT",
                "primary_key": {"visitor_id": "201"},
                "business_date": "2026-03-02",
                "row": row("biz_visitor", "201"),
            },
            {
                "sequence": 3,
                "operation_time": "2026-03-02 01:00:00.000",
                "table": "biz_user",
                "operation_type": "UPDATE",
                "primary_key": {"user_id": "101"},
                "business_date": "2026-03-02",
                "row": {**row("biz_user", "101"), "user_name": "测试用户", "updated_at": "2026-03-02 01:00:00.000"},
            },
        ]
        operations_path = package_dir / "operations.jsonl"
        operations_path.write_text("".join(canonical_json(item) + "\n" for item in operations), encoding="utf-8", newline="\n")
        expected_path = package_dir / "expected_result.json"
        write_json(expected_path, {
            "window_end": "2026-03-03 00:00:00.000",
            "table_row_counts": {table: 0 for table in TABLE_ORDER},
            "order_status_counts": {"CREATED": 0, "PAID": 0, "CANCELED": 0},
        })
        counts = {table: 0 for table in TABLE_ORDER}
        for operation in operations:
            counts[operation["table"]] += 1
        tables = [
            {
                "table_name": table,
                "operation_count": counts[table],
                "extract_row_count": 0,
                "affected_business_dates": [],
                "business_date_row_counts": {},
                "watermark": {"mode": "half_open"},
            }
            for table in TABLE_ORDER
        ]
        package = {
            "package_version": 1,
            "day_number": 61,
            "batch_id": "test-v1-day-61",
            "window_start": "2026-03-02 00:00:00.000",
            "window_end": "2026-03-03 00:00:00.000",
            "operations": {"file": "operations.jsonl", "row_count": len(operations), "sha256": sha256(operations_path)},
            "expected_result": {"file": "expected_result.json", "sha256": sha256(expected_path)},
            "tables": tables,
        }
        package_path = package_dir / "package_manifest.json"
        write_json(package_path, package)
        bootstrap = [{"table_name": table, "sha256": ZERO_HASH} for table in TABLE_ORDER]
        refs = []
        for day in range(61, 91):
            refs.append({
                "day_number": day,
                "path": f"daily/day_{day}",
                "window_start": "2026-03-02 00:00:00.000" if day == 61 else f"2026-03-{day - 59:02d} 00:00:00.000",
                "window_end": "2026-03-03 00:00:00.000" if day == 61 else f"2026-03-{day - 58:02d} 00:00:00.000",
                "manifest_sha256": sha256(package_path) if day == 61 else ZERO_HASH,
            })
        hash_input = {
            "bootstrap": bootstrap,
            "daily": [{"day_number": item["day_number"], "manifest_sha256": item["manifest_sha256"]} for item in refs],
        }
        manifest = {
            "replay_manifest_version": 1,
            "dataset_version": "test-v1",
            "bootstrap": {"tables": bootstrap},
            "daily_packages": refs,
            "business_hash": hashlib.sha256(canonical_json(hash_input).encode("utf-8")).hexdigest(),
        }
        manifest_path = root / "replay_manifest.json"
        write_json(manifest_path, manifest)
        write_json(package_dir / "ods_batch_contract.json", {
            "batch_contract_version": 1,
            "dataset_version": "test-v1",
            "mode": "incremental",
            "business_date": "2026-03-02",
            "window_start": package["window_start"],
            "window_end": package["window_end"],
            "batch_id": package["batch_id"],
            "extract_time": package["window_end"],
            "replay_manifest": {"path": "../../replay_manifest.json", "sha256": sha256(manifest_path)},
            "expected_tables": {},
        })

    def copy_bundle(self, name: str) -> Path:
        target = Path(self.temp.name) / name
        shutil.copytree(self.base, target)
        return target

    def run_script(self, bundle: Path, output: Path, *extra: str):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--replay-bundle", str(bundle), "--day", "61", "--output", str(output), *extra],
            text=True,
            capture_output=True,
        )

    def rebind_package(self, bundle: Path) -> None:
        package_path = bundle / "daily" / "day_61" / "package_manifest.json"
        manifest_path = bundle / "replay_manifest.json"
        contract_path = bundle / "daily" / "day_61" / "ods_batch_contract.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["daily_packages"][0]["manifest_sha256"] = sha256(package_path)
        hash_input = {
            "bootstrap": [{"table_name": item["table_name"], "sha256": item["sha256"]} for item in manifest["bootstrap"]["tables"]],
            "daily": [{"day_number": item["day_number"], "manifest_sha256": item["manifest_sha256"]} for item in manifest["daily_packages"]],
        }
        manifest["business_hash"] = hashlib.sha256(canonical_json(hash_input).encode("utf-8")).hexdigest()
        write_json(manifest_path, manifest)
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        contract["replay_manifest"]["sha256"] = sha256(manifest_path)
        write_json(contract_path, contract)

    def rebind_operations(self, bundle: Path) -> None:
        package_dir = bundle / "daily" / "day_61"
        package_path = package_dir / "package_manifest.json"
        package = json.loads(package_path.read_text(encoding="utf-8"))
        package["operations"]["sha256"] = sha256(package_dir / "operations.jsonl")
        write_json(package_path, package)
        self.rebind_package(bundle)

    def test_dry_run_writes_transactional_secret_free_plan(self):
        output = Path(self.temp.name) / "plan"
        result = self.run_script(self.base, output, "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        plan = json.loads((output / "plan.json").read_text(encoding="utf-8"))
        sql = (output / "replay.sql").read_text(encoding="utf-8")
        self.assertTrue(plan["dry_run"])
        self.assertFalse(plan["execution_authorized"])
        self.assertFalse(plan["database_contacted"])
        self.assertEqual(plan["operation_count"], 3)
        self.assertIn("START TRANSACTION;", sql)
        self.assertIn("COMMIT;", sql)
        self.assertIn("INSERT INTO `replay_batch_ledger`", sql)
        self.assertLess(sql.index("INSERT INTO `replay_batch_ledger`"), sql.index("INSERT INTO `biz_"))
        self.assertLess(sql.index("source_gate_results"), sql.index("COMMIT;"))
        self.assertIn("SET @expected_biz_user = 0;", sql)
        self.assertIn("SET @expected_paid_orders = 0;", sql)
        self.assertEqual(sql.count("INSERT INTO `biz_"), 2)
        self.assertEqual(sql.count("UPDATE `biz_user`"), 1)
        self.assertIn("e6b58be8af95e794a8", sql)
        for forbidden in ("MYSQL_PASSWORD", "--password", "127.0.0.1"):
            self.assertNotIn(forbidden, sql)
            self.assertNotIn(forbidden, json.dumps(plan))

    def test_dry_run_lock_and_existing_output_fail_nonzero(self):
        output = Path(self.temp.name) / "plan"
        missing_lock = self.run_script(self.base, output)
        self.assertEqual(missing_lock.returncode, 2)
        self.assertIn("--dry-run is required", missing_lock.stderr)
        output.mkdir()
        existing = self.run_script(self.base, output, "--dry-run")
        self.assertEqual(existing.returncode, 2)
        self.assertIn("output already exists", existing.stderr)

    def test_hash_schema_primary_key_and_order_defects_fail(self):
        cases = []

        hash_bundle = self.copy_bundle("bad-hash")
        with (hash_bundle / "daily" / "day_61" / "operations.jsonl").open("a", encoding="utf-8") as handle:
            handle.write("{}\n")
        cases.append((hash_bundle, "SHA-256 mismatch"))

        schema_bundle = self.copy_bundle("bad-schema")
        operations_path = schema_bundle / "daily" / "day_61" / "operations.jsonl"
        operations = [json.loads(line) for line in operations_path.read_text(encoding="utf-8").splitlines()]
        operations[0]["row"].pop("user_name")
        operations_path.write_text("".join(canonical_json(item) + "\n" for item in operations), encoding="utf-8", newline="\n")
        self.rebind_operations(schema_bundle)
        cases.append((schema_bundle, "row fields"))

        key_bundle = self.copy_bundle("bad-key")
        operations_path = key_bundle / "daily" / "day_61" / "operations.jsonl"
        operations = [json.loads(line) for line in operations_path.read_text(encoding="utf-8").splitlines()]
        operations[0]["primary_key"]["user_id"] = "999"
        operations_path.write_text("".join(canonical_json(item) + "\n" for item in operations), encoding="utf-8", newline="\n")
        self.rebind_operations(key_bundle)
        cases.append((key_bundle, "row primary key mismatch"))

        order_bundle = self.copy_bundle("bad-order")
        operations_path = order_bundle / "daily" / "day_61" / "operations.jsonl"
        operations = [json.loads(line) for line in operations_path.read_text(encoding="utf-8").splitlines()]
        operations[0], operations[1] = operations[1], operations[0]
        for index, operation in enumerate(operations, start=1):
            operation["sequence"] = index
        operations_path.write_text("".join(canonical_json(item) + "\n" for item in operations), encoding="utf-8", newline="\n")
        self.rebind_operations(order_bundle)
        cases.append((order_bundle, "FK-safe table order"))

        for bundle, expected in cases:
            with self.subTest(bundle=bundle.name):
                result = self.run_script(bundle, Path(self.temp.name) / f"out-{bundle.name}", "--dry-run")
                self.assertEqual(result.returncode, 2)
                self.assertIn(expected, result.stderr)
                self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
