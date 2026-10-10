"""Business Generator configuration loading and validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .contracts import TABLE_COLUMNS


@dataclass(frozen=True)
class DatasetConfig:
    raw: dict

    @property
    def counts(self) -> dict[str, int]:
        return self.raw["counts"]

    @property
    def start(self) -> datetime:
        return datetime.fromisoformat(self.raw["history_start"])

    @property
    def end(self) -> datetime:
        return datetime.fromisoformat(self.raw["history_end"])

    @property
    def history_days(self) -> int:
        return (self.end.date() - self.start.date()).days + 1


def load_config(path: Path) -> DatasetConfig:
    data = json.loads(path.read_text(encoding="utf-8"))
    required = {"dataset_version", "history_start", "history_end", "timezone", "counts", "promotion_dates"}
    missing = required - data.keys()
    if missing:
        raise ValueError(f"config missing keys: {sorted(missing)}")
    if data["timezone"] != "Asia/Shanghai":
        raise ValueError("timezone must be Asia/Shanghai")
    cfg = DatasetConfig(data)
    if cfg.start >= cfg.end:
        raise ValueError("history_start must be before history_end")
    for name in TABLE_COLUMNS:
        if name not in cfg.counts:
            raise ValueError(f"counts missing table: {name}")
        if not isinstance(cfg.counts[name], int) or cfg.counts[name] < 0:
            raise ValueError(f"invalid count for {name}")
    if cfg.counts["biz_order"] <= 0 or cfg.counts["biz_sku"] <= 0:
        raise ValueError("order and sku counts must be positive")
    return cfg
