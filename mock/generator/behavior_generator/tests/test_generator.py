from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from behavior_generator.config import load_config
from behavior_generator.contracts import BEHAVIOR_TYPES
from behavior_generator.generator import generate


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "smoke.json"


class BehaviorGeneratorTests(unittest.TestCase):
    def test_bootstrap_is_deterministic_and_uses_metric_event_types(self):
        cfg = load_config(CONFIG)
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.jsonl"
            second = Path(directory) / "second.jsonl"
            manifest = generate(cfg, 7, "2026-09-28T10:00:00+08:00", first)
            generate(cfg, 7, "2026-09-28T10:00:00+08:00", second)
            self.assertEqual(hashlib.sha256(first.read_bytes()).digest(), hashlib.sha256(second.read_bytes()).digest())
            events = [json.loads(line) for line in first.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(events), cfg.raw["behavior_events"])
            self.assertEqual(len({event["event_id"] for event in events}), len(events))
            self.assertTrue({event["event_type"] for event in events}.issubset(set(BEHAVIOR_TYPES)))
            self.assertEqual(manifest["event_count"], len(events))


if __name__ == "__main__":
    unittest.main()
