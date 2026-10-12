"""Standalone Behavior Generator for historical and continuous JSONL events."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import __version__
from .common import canonical_json, long_tail_weights, stable_rng, weighted_time
from .config import DatasetConfig, load_config
from .contracts import BEHAVIOR_TYPES
from .entity_manifest import EntityManifest, load_entity_manifest


SHANGHAI = timezone(timedelta(hours=8))


def _iso(value: datetime) -> str:
    return value.replace(tzinfo=SHANGHAI).isoformat(timespec="milliseconds")


def generate(config: DatasetConfig, seed: int, generated_at: str, output: Path, entity_manifest: EntityManifest, event_count: int | None = None,
             start: datetime | None = None, end: datetime | None = None) -> dict:
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    total = config.raw["behavior_events"] if event_count is None else event_count
    if total <= 0:
        raise ValueError("event_count must be positive")
    range_start, range_end = start or config.start, end or config.end
    if range_start >= range_end:
        raise ValueError("behavior start must be before end")
    rng = stable_rng(seed, "behavior")
    type_counts = Counter()
    daily = Counter()
    sku_counts = Counter()
    eligible_visitors = [visitor_id for visitor_id, first_seen in entity_manifest.visitor_first_seen_at.items() if first_seen <= range_end]
    if not eligible_visitors:
        raise ValueError("entity manifest has no visitor available in behavior range")
    sku_ids = entity_manifest.sku_ids
    sku_weights = long_tail_weights(len(sku_ids))
    event_weights = [30, 28, 18, 18, 6]
    visitor_event_counts = Counter(rng.choice(eligible_visitors) for _ in range(total))
    event_namespace = hashlib.sha256(
        f"{config.raw['dataset_version']}:{seed}:{range_start.isoformat()}:{range_end.isoformat()}".encode()
    ).hexdigest()[:12]
    output_index = 0
    session_total = 0
    mapped_total = 0
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        for visitor_id in sorted(visitor_event_counts):
            visitor_events = []
            event_start = max(range_start, entity_manifest.visitor_first_seen_at[visitor_id])
            mapping = entity_manifest.mappings.get(visitor_id)
            for _ in range(visitor_event_counts[visitor_id]):
                event_type = rng.choices(BEHAVIOR_TYPES, weights=event_weights, k=1)[0]
                event_time = weighted_time(rng, event_start, range_end, set(config.raw["promotion_dates"]))
                mapped = mapping is not None and event_time >= mapping.effective_from and (mapping.effective_to is None or event_time <= mapping.effective_to) and rng.random() < 0.75
                sku_id = None if event_type == "PAGE_VIEW" and rng.random() < 0.70 else rng.choices(sku_ids, weights=sku_weights, k=1)[0]
                visitor_events.append({
                    "event_type": event_type,
                    "event_time_value": event_time,
                    "ingest_time_value": min(range_end, event_time + timedelta(milliseconds=rng.randrange(50, 120_001))),
                    "visitor_id": visitor_id,
                    "user_id": mapping.user_id if mapped else None,
                    "sku_id": sku_id,
                    "page_id": f"PAGE-{rng.randint(1, 80):04d}",
                    "quantity": rng.randint(1, 3) if event_type in {"ADD_CART", "REMOVE_CART"} else None,
                    "identity_version": mapping.identity_version if mapped else None,
                })
            visitor_events.sort(key=lambda event: event["event_time_value"])
            session_index = 0
            previous_event_time = None
            for event in visitor_events:
                event_time = event.pop("event_time_value")
                ingest_time = event.pop("ingest_time_value")
                if previous_event_time is None or event_time - previous_event_time > timedelta(minutes=30):
                    session_index += 1
                    session_total += 1
                previous_event_time = event_time
                output_index += 1
                event["event_id"] = f"BEH-{event_namespace}-{output_index:012d}"
                event["event_time"] = _iso(event_time)
                event["ingest_time"] = _iso(ingest_time)
                event["session_id"] = f"SES-BEH-{visitor_id:010d}-{session_index:06d}"
                handle.write(canonical_json(event) + "\n")
                type_counts[event["event_type"]] += 1
                daily[event_time.date().isoformat()] += 1
                if event["user_id"] is not None:
                    mapped_total += 1
                if event["sku_id"]:
                    sku_counts[event["sku_id"]] += 1
    ranked = sorted(sku_counts.values(), reverse=True)
    interactions = sum(ranked) or 1
    manifest = {
        "dataset_version": config.raw["dataset_version"],
        "generator_version": __version__,
        "seed": seed,
        "generated_at": generated_at,
        "timezone": config.raw["timezone"],
        "event_count": total,
        "file_size_bytes": output.stat().st_size,
        "min_event_time": range_start.isoformat(),
        "max_event_time": range_end.isoformat(),
        "event_type_counts": dict(sorted(type_counts.items())),
        "mapped_event_count": mapped_total,
        "session_count": session_total,
        "min_daily_events": min(daily.values()),
        "max_daily_events": max(daily.values()),
        "peak_date": daily.most_common(1)[0][0],
        "top_5_percent_sku_share": round(sum(ranked[: max(1, math.ceil(len(sku_ids) * 0.05))]) / interactions, 6),
        "top_20_percent_sku_share": round(sum(ranked[: max(1, math.ceil(len(sku_ids) * 0.20))]) / interactions, 6),
        "source_entity_manifest": {"dataset_version": entity_manifest.dataset_version, "version": 1, "sha256": entity_manifest.sha256},
    }
    manifest_path = output.with_suffix(output.suffix + ".manifest.json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate V2 behavior events without impersonating MySQL CDC")
    sub = parser.add_subparsers(dest="mode", required=True)
    for mode in ("bootstrap", "continuous"):
        command = sub.add_parser(mode)
        command.add_argument("--config", type=Path, required=True)
        command.add_argument("--seed", type=int, required=True)
        command.add_argument("--generated-at", required=True)
        command.add_argument("--output", type=Path, required=True)
        command.add_argument("--entity-manifest", type=Path, required=True)
        if mode == "continuous":
            command.add_argument("--events", type=int, required=True)
            command.add_argument("--start", required=True)
            command.add_argument("--end", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    datetime.fromisoformat(args.generated_at.replace("Z", "+00:00"))
    cfg = load_config(args.config)
    entities = load_entity_manifest(args.entity_manifest, cfg)
    if args.mode == "bootstrap":
        manifest = generate(cfg, args.seed, args.generated_at, args.output, entities)
    else:
        manifest = generate(cfg, args.seed, args.generated_at, args.output, entities, args.events, datetime.fromisoformat(args.start), datetime.fromisoformat(args.end))
    print(canonical_json({"status": "generated", "mode": args.mode, "output": str(args.output), "events": manifest["event_count"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
