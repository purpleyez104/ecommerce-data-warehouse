from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class DatasetConfig:
    raw: dict

    @property
    def counts(self) -> dict[str, int]:
        return self.raw["entity_counts"]

    @property
    def start(self) -> datetime:
        return datetime.fromisoformat(self.raw["history_start"])

    @property
    def end(self) -> datetime:
        return datetime.fromisoformat(self.raw["history_end"])


def load_config(path: Path) -> DatasetConfig:
    data = json.loads(path.read_text(encoding="utf-8"))
    required = {"dataset_version", "history_start", "history_end", "timezone", "promotion_dates", "entity_counts", "behavior_events"}
    missing = required - data.keys()
    if missing:
        raise ValueError(f"config missing keys: {sorted(missing)}")
    if data["timezone"] != "Asia/Shanghai":
        raise ValueError("timezone must be Asia/Shanghai")
    for name in ("biz_user", "biz_visitor", "biz_identity_mapping", "biz_sku"):
        if not isinstance(data["entity_counts"].get(name), int) or data["entity_counts"][name] <= 0:
            raise ValueError(f"invalid entity count: {name}")
    cfg = DatasetConfig(data)
    if cfg.start >= cfg.end or data["behavior_events"] <= 0:
        raise ValueError("invalid behavior time range or event count")
    return cfg
