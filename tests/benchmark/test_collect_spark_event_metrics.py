import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "collect_spark_event_metrics", ROOT / "spark/scripts/collect_spark_event_metrics.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

SUMMARY_SPEC = importlib.util.spec_from_file_location(
    "summarize_benchmark_metrics", ROOT / "spark/scripts/summarize_benchmark_metrics.py"
)
assert SUMMARY_SPEC and SUMMARY_SPEC.loader
SUMMARY_MODULE = importlib.util.module_from_spec(SUMMARY_SPEC)
SUMMARY_SPEC.loader.exec_module(SUMMARY_MODULE)


class SparkEventMetricsTests(unittest.TestCase):
    def test_collects_successful_task_metrics(self):
        events = [
            {"Event": "SparkListenerApplicationStart", "App Name": "m7-test", "App ID": "application_1_1", "Timestamp": 1000},
            {"Event": "SparkListenerTaskEnd", "Task End Reason": {"Reason": "Success"}, "Task Metrics": {
                "Executor Run Time": 30, "Executor CPU Time": 20,
                "Memory Bytes Spilled": 7, "Disk Bytes Spilled": 11,
                "Input Metrics": {"Bytes Read": 101, "Records Read": 5},
                "Shuffle Read Metrics": {"Remote Bytes Read": 13, "Local Bytes Read": 17, "Total Records Read": 3},
                "Shuffle Write Metrics": {"Shuffle Bytes Written": 19, "Shuffle Records Written": 4},
            }},
            {"Event": "SparkListenerStageCompleted"},
            {"Event": "SparkListenerJobEnd", "Job Result": {"Result": "JobSucceeded"}},
            {"Event": "SparkListenerApplicationEnd", "Timestamp": 1120},
        ]
        result = MODULE.collect_metrics(json.dumps(event) for event in events)
        self.assertEqual("application_1_1", result["application_id"])
        self.assertEqual(120, result["duration_ms"])
        self.assertEqual(30, result["shuffle_read_bytes"])
        self.assertEqual(19, result["shuffle_write_bytes"])
        self.assertEqual(101, result["input_bytes"])
        self.assertEqual(1, result["task_count"])

    def test_rejects_incomplete_log(self):
        with self.assertRaisesRegex(ValueError, "missing application boundaries"):
            MODULE.collect_metrics([json.dumps({"Event": "SparkListenerApplicationStart", "Timestamp": 1})])

    def test_summary_requires_three_successful_runs_per_variant(self):
        paths = []
        # Windows Sandbox 的系统 TEMP 可能不可写，统一复用项目内已忽略目录。
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime/tmp") as temp_dir:
            root = Path(temp_dir)
            for experiment, variants in SUMMARY_MODULE.VARIANTS.items():
                for variant in variants:
                    for run_index in (1, 2, 3):
                        record = {
                            "experiment": experiment,
                            "variant": variant,
                            "run_index": run_index,
                            "measured": True,
                            "application_id": f"application_{run_index}",
                            "failed_job_count": 0,
                            "failed_task_count": 0,
                        }
                        record.update({metric: run_index for metric in SUMMARY_MODULE.METRICS})
                        path = root / f"{experiment}-{variant}-{run_index}.metrics.json"
                        path.write_text(json.dumps(record), encoding="utf-8")
                        paths.append(path)
            summary = SUMMARY_MODULE.summarize(paths)
        self.assertEqual(3, summary["measured_runs_per_variant"])
        median_metrics = summary["experiments"]["partition_pruning"]["optimized"]["median"]
        self.assertEqual(2, median_metrics["duration_ms"])


if __name__ == "__main__":
    unittest.main()
