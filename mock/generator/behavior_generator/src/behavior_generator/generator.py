"""Standalone Behavior Generator for historical and continuous JSONL events."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import __version__
from .common import canonical_json, long_tail_weights, stable_rng, weighted_time
from .config import DatasetConfig, load_config
from .contracts import BEHAVIOR_TYPES


SHANGHAI = timezone(timedelta(hours=8))


def _iso(value: datetime) -> str:
    return value.replace(tzinfo=SHANGHAI).isoformat(timespec="milliseconds")


def generate(config: DatasetConfig, seed: int, generated_at: str, output: Path, event_count: int | None = None,
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
    sku_total = config.counts["biz_sku"]
    sku_weights = long_tail_weights(sku_total)
    event_weights = [30, 28, 18, 18, 6]
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        for index in range(1, total + 1):
            event_type = rng.choices(BEHAVIOR_TYPES, weights=event_weights, k=1)[0]
            event_time = weighted_time(rng, range_start, range_end, set(config.raw["promotion_dates"]))
            visitor_id = rng.randint(1, config.counts["biz_visitor"])
            mapped = visitor_id <= config.counts["biz_identity_mapping"] and rng.random() < 0.75
            sku_id = None if event_type == "PAGE_VIEW" and rng.random() < 0.70 else rng.choices(range(1, sku_total + 1), weights=sku_weights, k=1)[0]
            quantity = rng.randint(1, 3) if event_type in {"ADD_CART", "REMOVE_CART"} else None
            event = {
                "event_id": f"BEH-{seed}-{index:012d}",
                "event_type": event_type,
                "event_time": _iso(event_time),
                "ingest_time": _iso(event_time + timedelta(milliseconds=rng.randrange(50, 120_001))),
                "visitor_id": visitor_id,
                "user_id": ((visitor_id - 1) % config.counts["biz_user"]) + 1 if mapped else None,
                "session_id": f"SES-{visitor_id:010d}-{index // 20:010d}",
                "sku_id": sku_id,
                "page_id": f"PAGE-{rng.randint(1, 80):04d}",
                "quantity": quantity,
                "identity_version": 1 if mapped else None,
            }
            handle.write(canonical_json(event) + "\n")
            type_counts[event_type] += 1
            daily[event_time.date().isoformat()] += 1
            if sku_id:
                sku_counts[sku_id] += 1
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
        "min_daily_events": min(daily.values()),
        "max_daily_events": max(daily.values()),
        "peak_date": daily.most_common(1)[0][0],
        "top_5_percent_sku_share": round(sum(ranked[: max(1, math.ceil(sku_total * 0.05))]) / interactions, 6),
        "top_20_percent_sku_share": round(sum(ranked[: max(1, math.ceil(sku_total * 0.20))]) / interactions, 6),
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
        if mode == "continuous":
            command.add_argument("--events", type=int, required=True)
            command.add_argument("--start", required=True)
            command.add_argument("--end", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    datetime.fromisoformat(args.generated_at.replace("Z", "+00:00"))
    cfg = load_config(args.config)
    if args.mode == "bootstrap":
        manifest = generate(cfg, args.seed, args.generated_at, args.output)
    else:
        manifest = generate(cfg, args.seed, args.generated_at, args.output, args.events, datetime.fromisoformat(args.start), datetime.fromisoformat(args.end))
    print(canonical_json({"status": "generated", "mode": args.mode, "output": str(args.output), "events": manifest["event_count"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
