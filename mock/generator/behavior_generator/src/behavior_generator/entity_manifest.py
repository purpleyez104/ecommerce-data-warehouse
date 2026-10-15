"""Load and validate the Business Generator entity contract."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .config import DatasetConfig


DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"


@dataclass(frozen=True)
class IdentityMapping:
    user_id: int
    session_id: str
    identity_version: int
    effective_from: datetime
    effective_to: datetime | None


@dataclass(frozen=True)
class EntityManifest:
    dataset_version: str
    sha256: str
    user_registered_at: dict[int, datetime]
    visitor_first_seen_at: dict[int, datetime]
    mappings: dict[int, IdentityMapping]
    sku_ids: list[int]
    sku_available_from: dict[int, datetime]


def _datetime(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError(f"entity manifest invalid datetime: {field}")
    try:
        return datetime.strptime(value, DATETIME_FORMAT)
    except ValueError as exc:
        raise ValueError(f"entity manifest invalid datetime: {field}") from exc


def _unique_rows(rows: object, key: str, name: str) -> dict[int, dict]:
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"entity manifest missing entities: {name}")
    result = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get(key), int) or row[key] <= 0:
            raise ValueError(f"entity manifest invalid {name}.{key}")
        if row[key] in result:
            raise ValueError(f"entity manifest duplicate {name}.{key}: {row[key]}")
        result[row[key]] = row
    return result


def load_entity_manifest(path: Path, config: DatasetConfig) -> EntityManifest:
    if not path.is_file():
        raise ValueError(f"entity manifest does not exist: {path}")
    raw_bytes = path.read_bytes()
    try:
        data = json.loads(raw_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"entity manifest is not valid UTF-8 JSON: {path}") from exc
    required = {"entity_manifest_version", "dataset_version", "source_generator_version", "seed", "history_start", "history_end", "timezone", "entities"}
    if not isinstance(data, dict) or required - data.keys():
        raise ValueError("entity manifest missing required top-level fields")
    if data["entity_manifest_version"] != 1:
        raise ValueError(f"unsupported entity manifest version: {data['entity_manifest_version']}")
    if not isinstance(data["dataset_version"], str) or not data["dataset_version"] or not isinstance(data["source_generator_version"], str) or not data["source_generator_version"] or not isinstance(data["seed"], int):
        raise ValueError("entity manifest has invalid source identity")
    if data["timezone"] != config.raw["timezone"]:
        raise ValueError("entity manifest timezone does not match behavior config")
    if data["history_start"] != config.raw["history_start"] or data["history_end"] != config.raw["history_end"]:
        raise ValueError("entity manifest history range does not match behavior config")
    entities = data["entities"]
    if not isinstance(entities, dict):
        raise ValueError("entity manifest entities must be an object")
    users = _unique_rows(entities.get("users"), "user_id", "users")
    visitors = _unique_rows(entities.get("visitors"), "visitor_id", "visitors")
    mappings = _unique_rows(entities.get("identity_mappings"), "visitor_id", "identity_mappings")
    skus = _unique_rows(entities.get("skus"), "sku_id", "skus")
    expected_counts = {
        "users": config.counts["biz_user"],
        "visitors": config.counts["biz_visitor"],
        "identity_mappings": config.counts["biz_identity_mapping"],
        "skus": config.counts["biz_sku"],
    }
    actual_counts = {"users": len(users), "visitors": len(visitors), "identity_mappings": len(mappings), "skus": len(skus)}
    if actual_counts != expected_counts:
        raise ValueError(f"entity manifest counts do not match behavior config: expected={expected_counts}, actual={actual_counts}")
    user_registered_at = {key: _datetime(row.get("registered_at"), f"users[{key}].registered_at") for key, row in users.items()}
    visitor_first_seen_at = {key: _datetime(row.get("first_seen_at"), f"visitors[{key}].first_seen_at") for key, row in visitors.items()}
    for user_id, registered_at in user_registered_at.items():
        if not config.start <= registered_at <= config.end:
            raise ValueError(f"entity manifest user is outside history range: user_id={user_id}")
    for visitor_id, first_seen_at in visitor_first_seen_at.items():
        if not config.start <= first_seen_at <= config.end:
            raise ValueError(f"entity manifest visitor is outside history range: visitor_id={visitor_id}")
    sku_available_from = {}
    for sku_id, row in skus.items():
        available_from = _datetime(row.get("available_from"), f"skus[{sku_id}].available_from")
        if not config.start <= available_from <= config.end:
            raise ValueError(f"entity manifest sku is outside history range: sku_id={sku_id}")
        sku_available_from[sku_id] = available_from
    parsed_mappings = {}
    for visitor_id, row in mappings.items():
        user_id = row.get("user_id")
        if user_id not in users or visitor_id not in visitors:
            raise ValueError(f"entity manifest mapping references unknown entity: visitor_id={visitor_id}, user_id={user_id}")
        session_id = row.get("session_id")
        identity_version = row.get("identity_version")
        if not isinstance(session_id, str) or not session_id or not isinstance(identity_version, int) or identity_version <= 0:
            raise ValueError(f"entity manifest invalid identity mapping: visitor_id={visitor_id}")
        effective_from = _datetime(row.get("effective_from"), f"identity_mappings[{visitor_id}].effective_from")
        effective_to = None if row.get("effective_to") is None else _datetime(row.get("effective_to"), f"identity_mappings[{visitor_id}].effective_to")
        if effective_from < max(user_registered_at[user_id], visitor_first_seen_at[visitor_id]):
            raise ValueError(f"entity manifest mapping precedes source entity: visitor_id={visitor_id}")
        if effective_from > config.end:
            raise ValueError(f"entity manifest mapping is outside history range: visitor_id={visitor_id}")
        if effective_to is not None and effective_to < effective_from:
            raise ValueError(f"entity manifest mapping has reversed effective range: visitor_id={visitor_id}")
        parsed_mappings[visitor_id] = IdentityMapping(user_id, session_id, identity_version, effective_from, effective_to)
    return EntityManifest(
        dataset_version=data["dataset_version"],
        sha256=hashlib.sha256(raw_bytes).hexdigest(),
        user_registered_at=user_registered_at,
        visitor_first_seen_at=visitor_first_seen_at,
        mappings=parsed_mappings,
        sku_ids=sorted(skus),
        sku_available_from=sku_available_from,
    )
