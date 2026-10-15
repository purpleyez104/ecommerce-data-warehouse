from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path

from behavior_generator.config import load_config
from behavior_generator.replay import build_replay_bundle, validate_replay_bundle


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "replay_smoke.json"


def write_entity_manifest(path: Path, cfg) -> None:
    start = cfg.start.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    mappings = [
        {
            "visitor_id": visitor_id,
            "user_id": ((visitor_id - 1) % cfg.counts["biz_user"]) + 1,
            "session_id": f"SES-MAP-{visitor_id:010d}",
            "identity_version": 1,
            "effective_from": start,
            "effective_to": None,
        }
        for visitor_id in range(1, cfg.counts["biz_identity_mapping"] + 1)
    ]
    payload = {
        "entity_manifest_version": 1,
        "dataset_version": "business-replay-smoke",
        "source_generator_version": "test",
        "seed": 20260105,
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


class BehaviorReplayTests(unittest.TestCase):
    def test_builds_deterministic_60_plus_30_bundle_and_validates_it(self):
        cfg = load_config(CONFIG)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entity_path = root / "entity_manifest.json"
            write_entity_manifest(entity_path, cfg)
            first = root / "first"
            second = root / "second"

            first_manifest = build_replay_bundle(
                cfg, 20260105, "2026-10-15T10:00:00+08:00", first, entity_path, date(2025, 10, 31),
            )
            second_manifest = build_replay_bundle(
                cfg, 20260105, "2026-10-15T10:00:00+08:00", second, entity_path, date(2025, 10, 31),
            )
            result = validate_replay_bundle(first, cfg, entity_path)
            relative_result = validate_replay_bundle(Path(os.path.relpath(first, Path.cwd())), cfg, entity_path)

            self.assertEqual(first_manifest["content_sha256"], second_manifest["content_sha256"])
            self.assertEqual(first_manifest["event_count"], 900)
            self.assertEqual(first_manifest["bootstrap"]["day_start"], 1)
            self.assertEqual(first_manifest["bootstrap"]["day_end"], 60)
            self.assertEqual(len(first_manifest["daily_packages"]), 30)
            self.assertEqual(result["event_count"], 900)
            self.assertEqual(relative_result["content_sha256"], result["content_sha256"])
            self.assertFalse(result["external_system_contacted"])

    def test_validation_rejects_tampered_event_file(self):
        cfg = load_config(CONFIG)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entity_path = root / "entity_manifest.json"
            write_entity_manifest(entity_path, cfg)
            bundle = root / "bundle"
            build_replay_bundle(
                cfg, 20260105, "2026-10-15T10:00:00+08:00", bundle, entity_path, date(2025, 10, 31),
            )
            events_path = bundle / "daily" / "day_61" / "events.jsonl"
            events_path.write_text(events_path.read_text(encoding="utf-8") + "{}\n", encoding="utf-8", newline="\n")

            with self.assertRaisesRegex(ValueError, "event file hash mismatch"):
                validate_replay_bundle(bundle, cfg, entity_path)

    def test_build_rejects_non_day_61_cutover(self):
        cfg = load_config(CONFIG)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entity_path = root / "entity_manifest.json"
            write_entity_manifest(entity_path, cfg)

            with self.assertRaisesRegex(ValueError, "cutover must start day 61"):
                build_replay_bundle(
                    cfg, 20260105, "2026-10-15T10:00:00+08:00", root / "bundle",
                    entity_path, date(2025, 10, 30),
                )


if __name__ == "__main__":
    unittest.main()
