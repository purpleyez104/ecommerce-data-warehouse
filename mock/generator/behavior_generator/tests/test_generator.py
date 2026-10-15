from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from behavior_generator.config import load_config
from behavior_generator.contracts import BEHAVIOR_TYPES
from behavior_generator.entity_manifest import load_entity_manifest
from behavior_generator.generator import generate


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "smoke.json"


def write_entity_manifest(path: Path, cfg, version: int = 1) -> None:
    start = cfg.start.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    mappings = []
    for visitor_id in range(1, cfg.counts["biz_identity_mapping"] + 1):
        mappings.append({
            "visitor_id": visitor_id,
            "user_id": ((visitor_id - 1) % cfg.counts["biz_user"]) + 1,
            "session_id": f"SES-MAP-{visitor_id:010d}",
            "identity_version": 1,
            "effective_from": start,
            "effective_to": None,
        })
    payload = {
        "entity_manifest_version": version,
        "dataset_version": "business-test-v1",
        "source_generator_version": "test",
        "seed": 7,
        "history_start": cfg.raw["history_start"],
        "history_end": cfg.raw["history_end"],
        "timezone": cfg.raw["timezone"],
        "entities": {
            "users": [{"user_id": value, "registered_at": start} for value in range(1, cfg.counts["biz_user"] + 1)],
            "visitors": [{"visitor_id": value, "first_seen_at": start} for value in range(1, cfg.counts["biz_visitor"] + 1)],
            "identity_mappings": mappings,
            "skus": [{"sku_id": value, "available_from": start} for value in range(1, cfg.counts["biz_sku"] + 1)],
        },
    }
    path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


class BehaviorGeneratorTests(unittest.TestCase):
    def test_bootstrap_is_deterministic_and_uses_metric_event_types(self):
        cfg = load_config(CONFIG)
        with tempfile.TemporaryDirectory() as directory:
            entity_path = Path(directory) / "entity_manifest.json"
            write_entity_manifest(entity_path, cfg)
            entity_manifest = load_entity_manifest(entity_path, cfg)
            first = Path(directory) / "first.jsonl"
            second = Path(directory) / "second.jsonl"
            manifest = generate(cfg, 7, "2026-09-28T10:00:00+08:00", first, entity_manifest)
            generate(cfg, 7, "2026-09-28T10:00:00+08:00", second, entity_manifest)
            self.assertEqual(hashlib.sha256(first.read_bytes()).digest(), hashlib.sha256(second.read_bytes()).digest())
            events = [json.loads(line) for line in first.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(events), cfg.raw["behavior_events"])
            self.assertEqual(len({event["event_id"] for event in events}), len(events))
            self.assertTrue({event["event_type"] for event in events}.issubset(set(BEHAVIOR_TYPES)))
            history_end = cfg.end.replace(tzinfo=datetime.fromisoformat(events[0]["event_time"]).tzinfo)
            visitor_events = {}
            for event in events:
                event_time = datetime.fromisoformat(event["event_time"])
                ingest_time = datetime.fromisoformat(event["ingest_time"])
                self.assertLessEqual(event_time, ingest_time)
                self.assertLessEqual(ingest_time, history_end)
                self.assertIn(event["visitor_id"], entity_manifest.visitor_first_seen_at)
                if event["sku_id"] is not None:
                    self.assertIn(event["sku_id"], entity_manifest.sku_ids)
                if event["user_id"] is not None:
                    mapping = entity_manifest.mappings[event["visitor_id"]]
                    self.assertEqual(event["user_id"], mapping.user_id)
                    self.assertEqual(event["identity_version"], mapping.identity_version)
                visitor_events.setdefault(event["visitor_id"], []).append(event)
            for visitor_id, rows in visitor_events.items():
                previous = None
                previous_session = None
                for event in rows:
                    current = datetime.fromisoformat(event["event_time"])
                    if previous is not None:
                        if current - previous > timedelta(minutes=30):
                            self.assertNotEqual(event["session_id"], previous_session)
                        else:
                            self.assertEqual(event["session_id"], previous_session)
                    previous = current
                    previous_session = event["session_id"]
            self.assertEqual(manifest["event_count"], len(events))
            self.assertEqual(manifest["session_count"], len({event["session_id"] for event in events}))
            self.assertEqual(manifest["source_entity_manifest"]["dataset_version"], "business-test-v1")

    def test_entity_manifest_rejects_unsupported_version(self):
        cfg = load_config(CONFIG)
        with tempfile.TemporaryDirectory() as directory:
            entity_path = Path(directory) / "entity_manifest.json"
            write_entity_manifest(entity_path, cfg, version=2)
            with self.assertRaisesRegex(ValueError, "unsupported entity manifest version"):
                load_entity_manifest(entity_path, cfg)

    def test_events_do_not_reference_sku_before_available_time(self):
        cfg = load_config(CONFIG)
        with tempfile.TemporaryDirectory() as directory:
            entity_path = Path(directory) / "entity_manifest.json"
            write_entity_manifest(entity_path, cfg)
            payload = json.loads(entity_path.read_text(encoding="utf-8"))
            available_from = (cfg.start + timedelta(days=4)).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            for sku in payload["entities"]["skus"]:
                sku["available_from"] = available_from
            entity_path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
            entity_manifest = load_entity_manifest(entity_path, cfg)
            output = Path(directory) / "events.jsonl"

            generate(cfg, 7, "2026-09-28T10:00:00+08:00", output, entity_manifest)

            for line in output.read_text(encoding="utf-8").splitlines():
                event = json.loads(line)
                if event["sku_id"] is not None:
                    self.assertGreaterEqual(datetime.fromisoformat(event["event_time"]).replace(tzinfo=None), cfg.start + timedelta(days=4))


if __name__ == "__main__":
    unittest.main()
