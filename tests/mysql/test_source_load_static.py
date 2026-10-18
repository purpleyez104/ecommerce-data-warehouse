from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GENERATOR_ROOT = ROOT / "mock" / "generator" / "business_generator"
sys.path.insert(0, str(GENERATOR_ROOT / "src"))

from business_generator.config import load_config
from business_generator.contracts import LOAD_TABLE_ORDER, TABLE_COLUMNS
from business_generator.generator import generate


VALIDATOR = ROOT / "mysql" / "scripts" / "validate_csv_bundle.py"
PARSER = ROOT / "mysql" / "scripts" / "parse_source_gate.py"
LOAD_SCRIPT = ROOT / "mysql" / "scripts" / "load_csv_bundle.sh"
GATE_SCRIPT = ROOT / "mysql" / "scripts" / "run_source_gate.sh"
GATE_SQL = ROOT / "mysql" / "sql" / "source_gate.sql"


class SourceLoadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.temp.name) / "bundle"
        generate(load_config(GENERATOR_ROOT / "config" / "smoke.json"), 20260928, "2026-09-28T10:00:00+08:00", cls.base)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def copy_bundle(self, name: str) -> Path:
        target = Path(self.temp.name) / name
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(self.base, target)
        return target

    def run_validator(self, bundle: Path):
        return subprocess.run([sys.executable, str(VALIDATOR), "--bundle", str(bundle)], text=True, capture_output=True)

    def rehash_csv(self, bundle: Path, table: str) -> None:
        csv_path = bundle / f"{table}.csv"
        manifest_path = bundle / "dataset_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        entry = next(item for item in manifest["tables"] if item["table_name"] == table)
        entry["csv_file_size_bytes"] = csv_path.stat().st_size
        entry["sha256"] = hashlib.sha256(csv_path.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8", newline="\n")

    def rehash_entity_manifest(self, bundle: Path) -> None:
        entity_path = bundle / "entity_manifest.json"
        manifest_path = bundle / "dataset_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["entity_manifest"]["sha256"] = hashlib.sha256(entity_path.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8", newline="\n")

    def test_complete_bundle_produces_fk_safe_plan(self):
        result = self.run_validator(self.base)
        self.assertEqual(result.returncode, 0, result.stderr)
        plan = json.loads(result.stdout)
        self.assertEqual(plan["load_table_order"], LOAD_TABLE_ORDER)
        self.assertEqual(len(plan["tables"]), 21)
        fk_edges = [
            ("biz_user", "biz_identity_mapping"), ("biz_visitor", "biz_identity_mapping"),
            ("biz_category", "biz_spu"), ("biz_spu", "biz_sku"),
            ("biz_user", "biz_cart"), ("biz_visitor", "biz_cart"),
            ("biz_cart", "biz_cart_item"), ("biz_sku", "biz_cart_item"),
            ("biz_cart", "biz_cart_merge_record"), ("biz_user", "biz_cart_merge_record"),
            ("biz_coupon_template", "biz_coupon"), ("biz_user", "biz_coupon"),
            ("biz_user", "biz_order"), ("biz_visitor", "biz_order"), ("biz_coupon", "biz_order"),
            ("biz_order", "biz_order_item"), ("biz_sku", "biz_order_item"),
            ("biz_spu", "biz_order_item"), ("biz_category", "biz_order_item"),
            ("biz_order", "biz_order_status_event"), ("biz_order", "biz_payment_attempt"),
            ("biz_payment_attempt", "biz_payment_event"), ("biz_order_item", "biz_refund_request"),
            ("biz_refund_request", "biz_refund_transaction"), ("biz_refund_request", "biz_refund_event"),
            ("biz_refund_transaction", "biz_refund_event"), ("biz_coupon", "biz_coupon_event"),
            ("biz_order", "biz_coupon_event"),
        ]
        for parent, child in fk_edges:
            self.assertLess(LOAD_TABLE_ORDER.index(parent), LOAD_TABLE_ORDER.index(child), (parent, child))

    def test_bundle_defects_fail_with_specific_object(self):
        cases = []
        missing = self.copy_bundle("missing")
        (missing / "biz_user.csv").unlink()
        cases.append((missing, "biz_user.csv"))

        extra = self.copy_bundle("extra")
        (extra / "biz_extra.csv").write_text("id\r\n", encoding="utf-8", newline="")
        cases.append((extra, "biz_extra.csv"))

        header = self.copy_bundle("header")
        path = header / "biz_user.csv"
        path.write_text(path.read_text(encoding="utf-8").replace("user_id", "bad_id", 1), encoding="utf-8", newline="")
        cases.append((header, "biz_user"))

        tampered = self.copy_bundle("tampered")
        with (tampered / "biz_user.csv").open("a", encoding="utf-8", newline="") as handle:
            handle.write("\r\n")
        cases.append((tampered, "biz_user"))

        duplicate_manifest = self.copy_bundle("duplicate-manifest")
        manifest_path = duplicate_manifest / "dataset_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["tables"][-1] = dict(manifest["tables"][0])
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8", newline="\n")
        cases.append((duplicate_manifest, "duplicate"))

        for bundle, expected in cases:
            with self.subTest(bundle=bundle.name):
                result = self.run_validator(bundle)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stderr)

    def test_out_of_range_reference_fails_after_rehash(self):
        bundle = self.copy_bundle("bad-reference")
        csv_path = bundle / "biz_order_item.csv"
        with csv_path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
            fields = list(rows[0])
        rows[0]["sku_id"] = "999999999"
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        self.rehash_csv(bundle, "biz_order_item")
        result = self.run_validator(bundle)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sku_id=999999999", result.stderr)

    def test_non_nullable_empty_value_fails_after_rehash(self):
        bundle = self.copy_bundle("empty-required")
        csv_path = bundle / "biz_user.csv"
        with csv_path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
            fields = list(rows[0])
        rows[0]["user_key"] = ""
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        self.rehash_csv(bundle, "biz_user")
        result = self.run_validator(bundle)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("empty non-nullable", result.stderr)
        self.assertIn("user_key", result.stderr)

    def test_missing_trailing_cell_fails_after_rehash(self):
        bundle = self.copy_bundle("missing-trailing-cell")
        csv_path = bundle / "biz_user.csv"
        with csv_path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.reader(handle))
        rows[1] = rows[1][:-1]
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            csv.writer(handle).writerows(rows)
        self.rehash_csv(bundle, "biz_user")
        result = self.run_validator(bundle)
        self.assertEqual(result.returncode, 2)
        self.assertIn("missing trailing field", result.stderr)

    def test_manifest_schema_and_required_statistics_are_strict(self):
        cases = []
        extra = self.copy_bundle("manifest-extra-field")
        extra_path = extra / "dataset_manifest.json"
        extra_manifest = json.loads(extra_path.read_text(encoding="utf-8"))
        extra_manifest["unexpected"] = True
        extra_path.write_text(json.dumps(extra_manifest), encoding="utf-8", newline="\n")
        cases.append((extra, "top-level field set"))

        missing_stat = self.copy_bundle("manifest-missing-stat")
        stat_path = missing_stat / "dataset_manifest.json"
        stat_manifest = json.loads(stat_path.read_text(encoding="utf-8"))
        del stat_manifest["business_statistics"]["paid_orders"]
        stat_path.write_text(json.dumps(stat_manifest), encoding="utf-8", newline="\n")
        cases.append((missing_stat, "business_statistics.paid_orders"))

        for bundle, expected in cases:
            with self.subTest(bundle=bundle.name):
                result = self.run_validator(bundle)
                self.assertEqual(result.returncode, 2)
                self.assertIn(expected, result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_identity_mapping_manifest_must_exactly_match_csv(self):
        bundle = self.copy_bundle("identity-mapping-mismatch")
        entity_path = bundle / "entity_manifest.json"
        entity = json.loads(entity_path.read_text(encoding="utf-8"))
        entity["entities"]["identity_mappings"].pop()
        entity_path.write_text(json.dumps(entity), encoding="utf-8", newline="\n")
        self.rehash_entity_manifest(bundle)
        result = self.run_validator(bundle)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("identity_mappings does not exactly match", result.stderr)

    def test_entity_attributes_must_match_business_csv(self):
        for name, field in (("users", "registered_at"), ("visitors", "first_seen_at"), ("skus", "available_from")):
            with self.subTest(entity=name):
                bundle = self.copy_bundle(f"entity-drift-{name}")
                entity_path = bundle / "entity_manifest.json"
                entity = json.loads(entity_path.read_text(encoding="utf-8"))
                entity["entities"][name][0][field] = "1999-01-01 00:00:00.000"
                entity_path.write_text(json.dumps(entity), encoding="utf-8", newline="\n")
                self.rehash_entity_manifest(bundle)
                result = self.run_validator(bundle)
                self.assertEqual(result.returncode, 2)
                self.assertIn(f"entities.{name} does not exactly match", result.stderr)

    def test_manifest_time_and_order_status_statistics_are_semantic(self):
        bad_days = self.copy_bundle("bad-history-days")
        manifest_path = bad_days / "dataset_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["history_days"] += 1
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8", newline="\n")

        bad_range = self.copy_bundle("bad-history-range")
        manifest_path = bad_range / "dataset_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        entity_path = bad_range / "entity_manifest.json"
        entity = json.loads(entity_path.read_text(encoding="utf-8"))
        manifest["history_start"] = "2026-01-01T00:00:00"
        entity["history_start"] = manifest["history_start"]
        entity_path.write_text(json.dumps(entity), encoding="utf-8", newline="\n")
        manifest["entity_manifest"]["sha256"] = hashlib.sha256(entity_path.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8", newline="\n")

        bad_stats = self.copy_bundle("bad-order-stats")
        manifest_path = bad_stats / "dataset_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["business_statistics"]["paid_orders"] += 1
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8", newline="\n")

        for bundle, expected in (
            (bad_days, "history_days mismatch"),
            (bad_range, "history_start must be <= history_end"),
            (bad_stats, "business_statistics.paid_orders"),
        ):
            with self.subTest(bundle=bundle.name):
                result = self.run_validator(bundle)
                self.assertEqual(result.returncode, 2)
                self.assertIn(expected, result.stderr)

    def make_fake_mysql(self, directory: Path) -> Path:
        fake = directory / "mysql"
        fake.write_text(
            "#!/usr/bin/env bash\n"
            "printf '%s\\n' \"$*\" > \"$FAKE_MYSQL_ARGS\"\n"
            "input=$(cat)\n"
            "printf '%s' \"$input\" > \"$FAKE_MYSQL_STDIN\"\n"
            "if [[ ${FAKE_MYSQL_MODE:-} == schema ]]; then\n"
            "  [[ $input == *'__source_load_schema_mismatch__'* && $input == *'LOAD DATA LOCAL INFILE'* ]] || exit 97\n"
            "  exit 8\n"
            "fi\n"
            "if [[ ${FAKE_MYSQL_MODE:-} == nonempty ]]; then\n"
            "  [[ $input == *'__source_load_target_not_empty__'* && $input == *'LOAD DATA LOCAL INFILE'* ]] || exit 98\n"
            "  exit 8\n"
            "fi\n"
            "if [[ -n ${FAKE_MYSQL_OUTPUT:-} ]]; then cat \"$FAKE_MYSQL_OUTPUT\"; fi\n"
            "exit \"${FAKE_MYSQL_EXIT:-0}\"\n",
            encoding="utf-8",
            newline="\n",
        )
        fake.chmod(0o755)
        return fake

    def mysql_env(self, fake_dir: Path) -> dict[str, str]:
        env = os.environ.copy()
        env.update({
            "PATH": str(fake_dir) + os.pathsep + env.get("PATH", ""),
            "MYSQL_HOST": "127.0.0.1",
            "MYSQL_PORT": "3306",
            "MYSQL_DATABASE": "ecommerce_oltp",
            "MYSQL_USER": "loader",
            "MYSQL_PASSWORD": "not-on-command-line",
            "FAKE_MYSQL_ARGS": str(fake_dir / "args.txt"),
            "FAKE_MYSQL_STDIN": str(fake_dir / "stdin.sql"),
        })
        return env

    def test_dry_run_never_invokes_mysql(self):
        with tempfile.TemporaryDirectory() as directory:
            fake_dir = Path(directory)
            self.make_fake_mysql(fake_dir)
            env = self.mysql_env(fake_dir)
            result = subprocess.run(["bash", str(LOAD_SCRIPT), "--dry-run", "--bundle", str(self.base)], env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((fake_dir / "args.txt").exists())

    def test_real_mode_is_one_session_protected_and_password_is_not_argv(self):
        with tempfile.TemporaryDirectory() as directory:
            fake_dir = Path(directory)
            self.make_fake_mysql(fake_dir)
            env = self.mysql_env(fake_dir)
            result = subprocess.run(["bash", str(LOAD_SCRIPT), "--bundle", str(self.base)], env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            args = (fake_dir / "args.txt").read_text(encoding="utf-8")
            sql = (fake_dir / "stdin.sql").read_text(encoding="utf-8")
            self.assertNotIn(env["MYSQL_PASSWORD"], args)
            self.assertNotIn("--password", args)
            self.assertEqual(sql.count("LOAD DATA LOCAL INFILE"), 21)
            self.assertEqual(sql.count("SET @source_load_warning_count = @@warning_count;"), 21)
            self.assertEqual(sql.count("__source_load_conversion_warning__"), 21)
            self.assertLess(sql.index("__source_load_schema_mismatch__"), sql.index("LOAD DATA LOCAL INFILE"))
            self.assertLess(sql.index("__source_load_target_not_empty__"), sql.index("LOAD DATA LOCAL INFILE"))
            self.assertLess(sql.index("SOURCE "), sql.index("COMMIT;"))

    def test_mysql_or_gate_failure_is_nonzero(self):
        with tempfile.TemporaryDirectory() as directory:
            fake_dir = Path(directory)
            self.make_fake_mysql(fake_dir)
            env = self.mysql_env(fake_dir)
            env["FAKE_MYSQL_EXIT"] = "9"
            load = subprocess.run(["bash", str(LOAD_SCRIPT), "--bundle", str(self.base)], env=env, text=True, capture_output=True)
            self.assertNotEqual(load.returncode, 0)
            gate = subprocess.run(["bash", str(GATE_SCRIPT), "--bundle", str(self.base)], env=env, text=True, capture_output=True)
            self.assertNotEqual(gate.returncode, 0)

    def test_unsafe_mysql_user_is_rejected_before_client_invocation(self):
        with tempfile.TemporaryDirectory() as directory:
            fake_dir = Path(directory)
            self.make_fake_mysql(fake_dir)
            env = self.mysql_env(fake_dir)
            env["MYSQL_USER"] = "loader\npassword=attacker-controlled"
            result = subprocess.run(["bash", str(LOAD_SCRIPT), "--bundle", str(self.base)], env=env, text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("MYSQL_USER", result.stderr)
            self.assertFalse((fake_dir / "args.txt").exists())

    def test_schema_mismatch_and_nonempty_target_fail_before_load(self):
        with tempfile.TemporaryDirectory() as directory:
            fake_dir = Path(directory)
            self.make_fake_mysql(fake_dir)
            for mode in ("schema", "nonempty"):
                env = self.mysql_env(fake_dir)
                env["FAKE_MYSQL_MODE"] = mode
                result = subprocess.run(["bash", str(LOAD_SCRIPT), "--bundle", str(self.base)], env=env, text=True, capture_output=True)
                self.assertEqual(result.returncode, 8, (mode, result.stderr))

    def test_source_gate_runner_parses_fake_client_protocol_end_to_end(self):
        import re
        rules = re.findall(r"^-- RULE: ([a-z0-9_.]+)$", GATE_SQL.read_text(encoding="utf-8"), re.MULTILINE)
        valid = "".join(f"{rule}\t0\n" for rule in rules)
        variants = [
            ("valid", valid, True),
            ("missing", "".join(f"{rule}\t0\n" for rule in rules[1:]), False),
            ("unknown", valid + "unknown.rule\t0\n", False),
            ("non-integer", valid.replace("\t0\n", "\tNaN\n", 1), False),
            ("nonzero", valid.replace("\t0\n", "\t1\n", 1), False),
        ]
        with tempfile.TemporaryDirectory() as directory:
            fake_dir = Path(directory)
            self.make_fake_mysql(fake_dir)
            for name, output, should_pass in variants:
                output_path = fake_dir / f"{name}.tsv"
                output_path.write_text(output, encoding="utf-8", newline="\n")
                env = self.mysql_env(fake_dir)
                env["FAKE_MYSQL_OUTPUT"] = str(output_path)
                result = subprocess.run(
                    ["bash", str(GATE_SCRIPT), "--bundle", str(self.base)],
                    env=env, text=True, capture_output=True,
                )
                self.assertEqual(result.returncode == 0, should_pass, (name, result.stderr))

    def test_source_gate_contains_state_and_chain_guards(self):
        sql = GATE_SQL.read_text(encoding="utf-8")
        for fragment in (
            "uc.user_id IS NULL",
            "o.order_status='CREATED' AND c.coupon_status='LOCKED'",
            "o.order_status='PAID' AND c.coupon_status='USED'",
            "o.order_status='CANCELED' AND c.coupon_status IN ('UNUSED','EXPIRED')",
            "o.user_id IS NOT NULL AND o.user_id<>c.user_id",
            "coupon.event_order_reference",
            "event.chain_continuity",
            "LAG(to_status)",
            "ROW_NUMBER() OVER (PARTITION BY e.payment_attempt_id ORDER BY e.occurred_at DESC,e.payment_event_id DESC)",
            "p.payment_status<>'INIT'",
            "TIMESTAMPADD(MINUTE,15,o.created_at)",
        ):
            self.assertIn(fragment, sql)
        self.assertNotIn("NOT (o.user_id <=> c.user_id)", sql)


class SourceGateProtocolTests(unittest.TestCase):
    def rules(self) -> list[str]:
        import re
        return re.findall(r"^-- RULE: ([a-z0-9_.]+)$", GATE_SQL.read_text(encoding="utf-8"), re.MULTILINE)

    def parse_output(self, text: str):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", delete=False) as handle:
            handle.write(text)
            path = Path(handle.name)
        try:
            return subprocess.run([sys.executable, str(PARSER), "--sql", str(GATE_SQL), "--output", str(path)], text=True, capture_output=True)
        finally:
            path.unlink()

    def test_only_complete_unique_zero_rule_set_passes(self):
        valid = "".join(f"{rule}\t0\n" for rule in self.rules())
        self.assertEqual(self.parse_output(valid).returncode, 0)
        mutations = [
            valid.replace("\t0\n", "\t1\n", 1),
            valid + "unknown.rule\t0\n",
            valid + f"{self.rules()[0]}\t0\n",
            valid.replace("\t0\n", "\tNaN\n", 1),
            "".join(f"{rule}\t0\n" for rule in self.rules()[1:]),
        ]
        for output in mutations:
            with self.subTest(output=output[-80:]):
                self.assertNotEqual(self.parse_output(output).returncode, 0)


if __name__ == "__main__":
    unittest.main()
