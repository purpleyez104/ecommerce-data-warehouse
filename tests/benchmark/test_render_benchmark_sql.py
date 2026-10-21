import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "render_benchmark_sql", ROOT / "spark/scripts/render_benchmark_sql.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class BenchmarkSqlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(
            (ROOT / "spark/benchmark/benchmark_contract.json").read_text(encoding="utf-8")
        )

    def test_setup_is_isolated_and_builds_fixed_scale(self):
        sql = MODULE.render_setup_sql(self.contract)
        self.assertIn("CREATE DATABASE IF NOT EXISTS ecommerce_benchmark", sql)
        self.assertEqual(4, sql.count("CREATE EXTERNAL TABLE IF NOT EXISTS"))
        self.assertIn("sequence(0, 8)", sql)
        self.assertIn("sequence(0, 2)", sql)
        self.assertIn("CAST(o.order_id AS BIGINT)", sql)
        self.assertIn("CAST(r.replica_id AS BIGINT) * 1000000000", sql)
        self.assertIn("benchmark_order.row_count", sql)
        self.assertIn("M7_BENCHMARK_SETUP_PASS", sql)
        self.assertNotIn("INSERT OVERWRITE TABLE ecommerce_dwd", sql)
        self.assertNotIn("INSERT OVERWRITE TABLE ecommerce_dim", sql)

    def test_partition_variants_differ_only_by_pruning_entry(self):
        baseline = MODULE.render_query_sql(self.contract, "partition_pruning", "baseline")
        optimized = MODULE.render_query_sql(self.contract, "partition_pruning", "optimized")
        self.assertIn("CAST(event_time AS DATE)", baseline)
        self.assertNotIn("dt='2026-02-14'", baseline)
        self.assertIn("dt='2026-02-14'", optimized)
        for marker in ("row_count", "quantity_sum", "result_hash"):
            self.assertIn(marker, baseline)
            self.assertIn(marker, optimized)

    def test_join_variants_force_sort_merge_and_broadcast(self):
        baseline = MODULE.render_query_sql(self.contract, "join_strategy", "sort_merge")
        optimized = MODULE.render_query_sql(self.contract, "join_strategy", "broadcast")
        self.assertIn("MERGE(i, p)", baseline)
        self.assertIn("BROADCAST(p)", optimized)
        self.assertIn("spark.sql.autoBroadcastJoinThreshold=-1", baseline)
        self.assertIn("spark.sql.autoBroadcastJoinThreshold=-1", optimized)

    def test_skew_variants_preserve_final_measures(self):
        baseline = MODULE.render_query_sql(self.contract, "skew_aggregation", "single_stage")
        optimized = MODULE.render_query_sql(self.contract, "skew_aggregation", "two_stage")
        self.assertIn("pmod(xxhash64(benchmark_event_id), 100)<40", baseline)
        self.assertIn("WITH salted AS", optimized)
        self.assertIn("pmod(xxhash64(benchmark_event_id), 16)", optimized)
        for marker in ("event_count", "quantity_sum", "result_hash", "M7_RESULT"):
            self.assertIn(marker, baseline)
            self.assertIn(marker, optimized)

    def test_contract_rejects_formal_database_or_scale_drift(self):
        database_drift = copy.deepcopy(self.contract)
        database_drift["database"] = "ecommerce_dwd"
        with self.assertRaisesRegex(ValueError, "must remain isolated"):
            MODULE.validate_contract(database_drift)
        scale_drift = copy.deepcopy(self.contract)
        scale_drift["tables"]["benchmark_order"]["expected_rows"] = 900001
        with self.assertRaisesRegex(ValueError, "source or scale drift"):
            MODULE.validate_contract(scale_drift)

    def test_measured_runner_preserves_fixed_repetitions_and_event_metrics(self):
        runner = (ROOT / "spark/scripts/run_benchmark.sh").read_text(encoding="utf-8")
        self.assertIn("for run_index in 1 2 3", runner)
        self.assertIn("M7_MEASURED_PASS runs=18", runner)
        self.assertIn('dfs -cat "${history_root}/${application_id}"', runner)
        self.assertIn("--measured", runner)
        self.assertIn("smoke variants are not equivalent", runner)


if __name__ == "__main__":
    unittest.main()
