"""Business Generator deterministic helpers."""

from __future__ import annotations

import hashlib
import json
import math
import random
from datetime import datetime, timedelta


DT_FORMAT = "%Y-%m-%d %H:%M:%S.%f"


def dt(value: datetime | None) -> str:
    return "" if value is None else value.strftime(DT_FORMAT)[:-3]


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_rng(seed: int, namespace: str) -> random.Random:
    digest = hashlib.sha256(f"{seed}:{namespace}".encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def allocate(total: int, weights: list[float]) -> list[int]:
    raw = [total * weight / sum(weights) for weight in weights]
    result = [int(value) for value in raw]
    for index in sorted(range(len(raw)), key=lambda i: raw[i] - result[i], reverse=True)[: total - sum(result)]:
        result[index] += 1
    return result


def long_tail_weights(size: int) -> list[float]:
    """Allocate about 40%/30%/30% mass to top 5%/next 15%/remaining 80%."""
    top_5 = max(1, math.ceil(size * 0.05))
    top_20 = max(top_5 + 1, math.ceil(size * 0.20))
    return [
        0.40 / top_5 if rank < top_5 else
        0.30 / (top_20 - top_5) if rank < top_20 else
        0.30 / (size - top_20)
        for rank in range(size)
    ]


def weighted_time(rng: random.Random, start: datetime, end: datetime, promotions: set[str]) -> datetime:
    days = (end.date() - start.date()).days + 1
    day_weights = []
    for offset in range(days):
        day = start.date() + timedelta(days=offset)
        weight = 1.18 if day.weekday() >= 5 else 1.0
        if day.isoformat() in promotions:
            weight *= 3.0
        day_weights.append(weight * rng.uniform(0.85, 1.15))
    day_index = rng.choices(range(days), weights=day_weights, k=1)[0]
    hour_weights = [0.15, 0.12, 0.10, 0.09, 0.08, 0.10, 0.20, 0.35, 0.55, 0.70, 0.80, 0.95,
                    1.15, 1.05, 0.90, 0.85, 0.95, 1.15, 1.45, 1.75, 1.90, 1.65, 1.10, 0.55]
    hour = rng.choices(range(24), weights=hour_weights, k=1)[0]
    value = datetime.combine(start.date() + timedelta(days=day_index), datetime.min.time())
    value += timedelta(hours=hour, minutes=rng.randrange(60), seconds=rng.randrange(60), milliseconds=rng.randrange(1000))
    return min(max(value, start), end)
