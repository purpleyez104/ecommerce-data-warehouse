"""构建并审计 60 天历史初始化 + 30 天增量的 Behavior Replay Bundle。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

from . import __version__
from .common import canonical_json
from .config import DatasetConfig, load_config
from .contracts import BEHAVIOR_TYPES
from .entity_manifest import EntityManifest, load_entity_manifest
from .generator import generate


REPLAY_MANIFEST_VERSION = 1
EVENT_FIELDS = {
    "event_id", "event_type", "event_time", "identity_version", "ingest_time",
    "page_id", "quantity", "session_id", "sku_id", "user_id", "visitor_id",
}
EVENT_ID_PATTERN = re.compile(r"^BEH-([0-9a-f]{12})-(\d{12})$")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _resolve_inside(root: Path, relative_path: str) -> Path:
    path = (root / relative_path).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"bundle path escapes root: {relative_path}")
    return path


def _validate_window(config: DatasetConfig, cutover_date: date) -> tuple[datetime, datetime]:
    expected_cutover = config.start.date() + timedelta(days=60)
    expected_end = config.start.date() + timedelta(days=90)
    if cutover_date != expected_cutover:
        raise ValueError(f"cutover must start day 61: expected={expected_cutover}, actual={cutover_date}")
    if config.end.date() + timedelta(days=1) != expected_end:
        raise ValueError("behavior replay config must cover exactly 90 calendar days")
    return datetime.combine(cutover_date, datetime.min.time()), datetime.combine(expected_end, datetime.min.time())


@dataclass
class PackageStats:
    row_count: int = 0
    min_event_time: str | None = None
    max_event_time: str | None = None
    event_type_counts: Counter = field(default_factory=Counter)

    def add(self, event: dict) -> None:
        event_time = event["event_time"]
        self.row_count += 1
        self.min_event_time = event_time if self.min_event_time is None else min(self.min_event_time, event_time)
        self.max_event_time = event_time if self.max_event_time is None else max(self.max_event_time, event_time)
        self.event_type_counts[event["event_type"]] += 1


def _sort_daily_file(path: Path) -> None:
    """日包规模远小于全量文件，可以按日排序而不把 90 天事件全部载入内存。"""
    rows = path.read_text(encoding="utf-8").splitlines()

    def event_order(line: str) -> tuple[str, str]:
        event = json.loads(line)
        return event["event_time"], event["event_id"]

    rows.sort(key=event_order)
    path.write_text("".join(f"{line}\n" for line in rows), encoding="utf-8", newline="\n")


def _package_manifest(
    bundle_root: Path,
    package_dir: Path,
    stats: PackageStats,
    *,
    day_start: int,
    day_end: int,
    window_start: datetime,
    window_end: datetime,
) -> dict:
    events_path = package_dir / "events.jsonl"
    payload = {
        "package_version": 1,
        "day_start": day_start,
        "day_end": day_end,
        "window_start": window_start.isoformat(timespec="milliseconds"),
        "window_end_exclusive": window_end.isoformat(timespec="milliseconds"),
        "events": {
            "file": "events.jsonl",
            "row_count": stats.row_count,
            "sha256": _sha256(events_path),
            "min_event_time": stats.min_event_time,
            "max_event_time": stats.max_event_time,
            "event_type_counts": dict(sorted(stats.event_type_counts.items())),
        },
    }
    manifest_path = package_dir / "package_manifest.json"
    _write_json(manifest_path, payload)
    return {
        "day_start": day_start,
        "day_end": day_end,
        "path": package_dir.relative_to(bundle_root).as_posix(),
        "window_start": payload["window_start"],
        "window_end_exclusive": payload["window_end_exclusive"],
        "event_count": stats.row_count,
        "events_sha256": payload["events"]["sha256"],
        "manifest_sha256": _sha256(manifest_path),
    }


def build_replay_bundle(
    config: DatasetConfig,
    seed: int,
    generated_at: str,
    output: Path,
    entity_manifest_path: Path,
    cutover_date: date,
) -> dict:
    """生成一次完整事件集，再切分为一个 Bootstrap 和 30 个按日排序的增量包。"""
    if output.exists():
        raise FileExistsError(f"output already exists; choose a new directory: {output}")
    cutover, replay_end = _validate_window(config, cutover_date)
    entities = load_entity_manifest(entity_manifest_path, config)
    output.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f".{output.name}.incomplete-", dir=output.parent))
    try:
        source_dir = work / "_source"
        source_dir.mkdir()
        source_path = source_dir / "events.jsonl"
        source_manifest = generate(config, seed, generated_at, source_path, entities)
        source_event_sha256 = _sha256(source_path)
        source_manifest_path = source_path.with_suffix(source_path.suffix + ".manifest.json")

        bootstrap_dir = work / "bootstrap"
        bootstrap_dir.mkdir()
        bootstrap_path = bootstrap_dir / "events.jsonl"
        daily_dirs = []
        daily_paths = []
        for offset in range(30):
            package_dir = work / "daily" / f"day_{61 + offset:02d}"
            package_dir.mkdir(parents=True)
            daily_dirs.append(package_dir)
            daily_paths.append(package_dir / "events.jsonl")

        bootstrap_stats = PackageStats()
        daily_stats = [PackageStats() for _ in range(30)]
        event_namespace = None
        handles = [bootstrap_path.open("w", encoding="utf-8", newline="\n")]
        handles.extend(path.open("w", encoding="utf-8", newline="\n") for path in daily_paths)
        try:
            with source_path.open(encoding="utf-8") as source:
                for line in source:
                    event = json.loads(line)
                    event_time = datetime.fromisoformat(event["event_time"]).replace(tzinfo=None)
                    match = EVENT_ID_PATTERN.fullmatch(event["event_id"])
                    if match is None:
                        raise ValueError(f"invalid generated event_id: {event['event_id']}")
                    event_namespace = event_namespace or match.group(1)
                    if match.group(1) != event_namespace:
                        raise ValueError("generated events use multiple event_id namespaces")
                    if event_time < cutover:
                        handles[0].write(line)
                        bootstrap_stats.add(event)
                        continue
                    day_offset = (event_time.date() - cutover.date()).days
                    if not 0 <= day_offset < 30 or event_time >= replay_end:
                        raise ValueError(f"event is outside replay window: {event['event_id']}")
                    handles[day_offset + 1].write(line)
                    daily_stats[day_offset].add(event)
        finally:
            for handle in handles:
                handle.close()

        for path in daily_paths:
            _sort_daily_file(path)

        bootstrap_ref = _package_manifest(
            work, bootstrap_dir, bootstrap_stats,
            day_start=1, day_end=60, window_start=config.start, window_end=cutover,
        )
        daily_refs = []
        for offset, (package_dir, stats) in enumerate(zip(daily_dirs, daily_stats)):
            window_start = cutover + timedelta(days=offset)
            daily_refs.append(_package_manifest(
                work, package_dir, stats,
                day_start=61 + offset, day_end=61 + offset,
                window_start=window_start, window_end=window_start + timedelta(days=1),
            ))

        content_items = [
            {"path": f"{bootstrap_ref['path']}/events.jsonl", "sha256": bootstrap_ref["events_sha256"]},
            *[
                {"path": f"{item['path']}/events.jsonl", "sha256": item["events_sha256"]}
                for item in daily_refs
            ],
        ]
        manifest = {
            "replay_manifest_version": REPLAY_MANIFEST_VERSION,
            "dataset_version": config.raw["dataset_version"],
            "generator_version": __version__,
            "seed": seed,
            "generated_at": generated_at,
            "timezone": config.raw["timezone"],
            "history_start": config.start.isoformat(timespec="milliseconds"),
            "cutover_time": cutover.isoformat(timespec="milliseconds"),
            "replay_end_exclusive": replay_end.isoformat(timespec="milliseconds"),
            "event_count": source_manifest["event_count"],
            "event_id_namespace": event_namespace,
            "source_generation": {
                "events_sha256": source_event_sha256,
                "manifest_sha256": _sha256(source_manifest_path),
                "entity_manifest": {
                    "dataset_version": entities.dataset_version,
                    "sha256": entities.sha256,
                },
            },
            "bootstrap": bootstrap_ref,
            "daily_packages": daily_refs,
            "content_sha256": hashlib.sha256(canonical_json(content_items).encode("utf-8")).hexdigest(),
        }
        _write_json(work / "replay_manifest.json", manifest)
        shutil.rmtree(source_dir)
        validate_replay_bundle(work, config, entity_manifest_path)
        os.replace(work, output)
        return manifest
    except Exception:
        shutil.rmtree(work, ignore_errors=True)
        raise


def validate_replay_bundle(bundle: Path, config: DatasetConfig, entity_manifest_path: Path) -> dict:
    """离线审计 Bundle 的 Manifest、Hash、窗口、Schema 与全局 Event ID 唯一性。"""
    bundle = bundle.resolve()
    manifest_path = bundle / "replay_manifest.json"
    if not manifest_path.is_file():
        raise ValueError("behavior replay manifest does not exist")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("replay_manifest_version") != REPLAY_MANIFEST_VERSION:
        raise ValueError("unsupported behavior replay manifest version")
    if manifest.get("dataset_version") != config.raw["dataset_version"]:
        raise ValueError("behavior replay dataset version does not match config")
    expected_cutover, expected_end = _validate_window(config, config.start.date() + timedelta(days=60))
    if manifest.get("history_start") != config.start.isoformat(timespec="milliseconds"):
        raise ValueError("behavior replay history start does not match config")
    if manifest.get("cutover_time") != expected_cutover.isoformat(timespec="milliseconds"):
        raise ValueError("behavior replay cutover does not match config")
    if manifest.get("replay_end_exclusive") != expected_end.isoformat(timespec="milliseconds"):
        raise ValueError("behavior replay end does not match config")
    entities = load_entity_manifest(entity_manifest_path, config)
    if manifest.get("source_generation", {}).get("entity_manifest") != {
        "dataset_version": entities.dataset_version,
        "sha256": entities.sha256,
    }:
        raise ValueError("behavior replay entity manifest binding does not match")
    packages = [manifest.get("bootstrap"), *manifest.get("daily_packages", [])]
    if packages[0] is None or len(packages) != 31:
        raise ValueError("behavior replay must contain one bootstrap and 30 daily packages")

    total = manifest.get("event_count")
    namespace = manifest.get("event_id_namespace")
    if not isinstance(total, int) or total <= 0 or not isinstance(namespace, str):
        raise ValueError("behavior replay has invalid event identity metadata")
    seen = bytearray(total + 1)
    seen_count = 0
    content_items = []
    for package_index, package_ref in enumerate(packages):
        expected_day = 1 if package_index == 0 else 60 + package_index
        expected_day_end = 60 if package_index == 0 else expected_day
        if package_ref.get("day_start") != expected_day or package_ref.get("day_end") != expected_day_end:
            raise ValueError("behavior replay package day sequence is invalid")
        package_dir = _resolve_inside(bundle, package_ref["path"])
        package_manifest_path = package_dir / "package_manifest.json"
        if _sha256(package_manifest_path) != package_ref["manifest_sha256"]:
            raise ValueError(f"behavior package manifest hash mismatch: {package_ref['path']}")
        package = json.loads(package_manifest_path.read_text(encoding="utf-8"))
        events_path = package_dir / package["events"]["file"]
        events_sha256 = _sha256(events_path)
        if events_sha256 != package["events"]["sha256"] or events_sha256 != package_ref["events_sha256"]:
            raise ValueError(f"behavior event file hash mismatch: {package_ref['path']}")
        content_items.append({"path": events_path.relative_to(bundle).as_posix(), "sha256": events_sha256})
        window_start = datetime.fromisoformat(package["window_start"])
        window_end = datetime.fromisoformat(package["window_end_exclusive"])
        row_count = 0
        previous_order = None
        type_counts = Counter()
        min_event_time = None
        max_event_time = None
        with events_path.open(encoding="utf-8") as handle:
            for line in handle:
                event = json.loads(line)
                if set(event) != EVENT_FIELDS:
                    raise ValueError(f"behavior event schema mismatch: {package_ref['path']}")
                event_time = datetime.fromisoformat(event["event_time"]).replace(tzinfo=None)
                ingest_time = datetime.fromisoformat(event["ingest_time"]).replace(tzinfo=None)
                if not window_start <= event_time < window_end or ingest_time < event_time:
                    raise ValueError(f"behavior event time is outside package window: {event['event_id']}")
                if event["event_type"] not in BEHAVIOR_TYPES:
                    raise ValueError(f"unsupported behavior event type: {event['event_type']}")
                visitor_id = event["visitor_id"]
                if visitor_id not in entities.visitor_first_seen_at or event_time < entities.visitor_first_seen_at[visitor_id]:
                    raise ValueError(f"behavior event references unavailable visitor: {event['event_id']}")
                sku_id = event["sku_id"]
                if sku_id is not None and (sku_id not in entities.sku_available_from or event_time < entities.sku_available_from[sku_id]):
                    raise ValueError(f"behavior event references unavailable SKU: {event['event_id']}")
                mapping = entities.mappings.get(visitor_id)
                if event["user_id"] is None:
                    if event["identity_version"] is not None:
                        raise ValueError(f"anonymous behavior event has identity version: {event['event_id']}")
                elif (
                    mapping is None
                    or event["user_id"] != mapping.user_id
                    or event["identity_version"] != mapping.identity_version
                    or event_time < mapping.effective_from
                    or (mapping.effective_to is not None and event_time > mapping.effective_to)
                ):
                    raise ValueError(f"behavior event identity mapping is invalid: {event['event_id']}")
                if not isinstance(event["session_id"], str) or not event["session_id"]:
                    raise ValueError(f"behavior event session_id is invalid: {event['event_id']}")
                match = EVENT_ID_PATTERN.fullmatch(event["event_id"])
                if match is None or match.group(1) != namespace:
                    raise ValueError(f"behavior event_id namespace mismatch: {event['event_id']}")
                sequence = int(match.group(2))
                if not 1 <= sequence <= total or seen[sequence]:
                    raise ValueError(f"duplicate or out-of-range behavior event_id: {event['event_id']}")
                seen[sequence] = 1
                seen_count += 1
                row_count += 1
                type_counts[event["event_type"]] += 1
                min_event_time = event["event_time"] if min_event_time is None else min(min_event_time, event["event_time"])
                max_event_time = event["event_time"] if max_event_time is None else max(max_event_time, event["event_time"])
                order = (event["event_time"], event["event_id"])
                if package_index > 0 and previous_order is not None and order < previous_order:
                    raise ValueError(f"daily behavior package is not ordered: {package_ref['path']}")
                previous_order = order
        if row_count != package["events"]["row_count"] or row_count != package_ref["event_count"]:
            raise ValueError(f"behavior package row count mismatch: {package_ref['path']}")
        if dict(sorted(type_counts.items())) != package["events"]["event_type_counts"]:
            raise ValueError(f"behavior package event type counts mismatch: {package_ref['path']}")
        if min_event_time != package["events"]["min_event_time"] or max_event_time != package["events"]["max_event_time"]:
            raise ValueError(f"behavior package event time bounds mismatch: {package_ref['path']}")
    if seen_count != total:
        raise ValueError(f"behavior replay event count mismatch: expected={total}, actual={seen_count}")
    content_sha256 = hashlib.sha256(canonical_json(content_items).encode("utf-8")).hexdigest()
    if content_sha256 != manifest.get("content_sha256"):
        raise ValueError("behavior replay content hash mismatch")
    return {
        "status": "valid",
        "event_count": seen_count,
        "daily_packages": 30,
        "content_sha256": content_sha256,
        "external_system_contacted": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build")
    build.add_argument("--config", type=Path, required=True)
    build.add_argument("--entity-manifest", type=Path, required=True)
    build.add_argument("--seed", type=int, required=True)
    build.add_argument("--generated-at", required=True)
    build.add_argument("--cutover-date", type=date.fromisoformat, required=True)
    build.add_argument("--output", type=Path, required=True)
    validate = subparsers.add_parser("validate")
    validate.add_argument("--config", type=Path, required=True)
    validate.add_argument("--entity-manifest", type=Path, required=True)
    validate.add_argument("--bundle", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config(args.config)
    if args.command == "build":
        datetime.fromisoformat(args.generated_at.replace("Z", "+00:00"))
        result = build_replay_bundle(
            config, args.seed, args.generated_at, args.output, args.entity_manifest, args.cutover_date,
        )
        response = {
            "status": "generated", "output": str(args.output),
            "events": result["event_count"], "daily_packages": len(result["daily_packages"]),
            "content_sha256": result["content_sha256"],
        }
    else:
        response = validate_replay_bundle(args.bundle, config, args.entity_manifest)
    print(canonical_json(response))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
