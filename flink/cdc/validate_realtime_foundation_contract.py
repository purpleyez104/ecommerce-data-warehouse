#!/usr/bin/env python3
"""严格验证 Formal Realtime Foundation Contract 的冻结字段。"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")
TOPIC = re.compile(r"^[a-z0-9._-]+$")
EXPECTED_TABLE_KEYS = {
    "biz_user": "user_id",
    "biz_visitor": "visitor_id",
    "biz_identity_mapping": "mapping_id",
    "biz_category": "category_id",
    "biz_spu": "spu_id",
    "biz_sku": "sku_id",
    "biz_product_change_event": "change_id",
    "biz_cart": "cart_id",
    "biz_cart_item": "cart_item_id",
    "biz_cart_merge_record": "merge_id",
    "biz_coupon_template": "template_id",
    "biz_coupon": "coupon_id",
    "biz_order": "order_id",
    "biz_order_item": "order_item_id",
    "biz_order_status_event": "order_event_id",
    "biz_payment_attempt": "payment_attempt_id",
    "biz_payment_event": "payment_event_id",
    "biz_refund_request": "refund_request_id",
    "biz_refund_transaction": "refund_txn_id",
    "biz_refund_event": "refund_event_id",
    "biz_coupon_event": "coupon_event_id",
}
EXPECTED_ENVELOPE_FIELDS = [
    "contract_version", "event_id", "event_version", "event_time", "ingest_time",
    "op", "key", "before", "after", "source", "transaction",
]
EXPECTED_DOMAINS = ["identity", "product", "cart", "trade", "payment", "refund", "marketing"]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _exact_keys(value: Any, expected: set[str], path: str) -> None:
    """拒绝缺失字段和未评审扩展，避免高返工 Contract 静默漂移。"""
    _require(isinstance(value, dict), f"{path} must be an object")
    actual = set(value)
    _require(actual == expected, f"{path} keys mismatch: missing={sorted(expected - actual)}, extra={sorted(actual - expected)}")


def load_json(path: Path) -> dict[str, Any]:
    """读取 UTF-8 JSON，并要求根节点为 Object。"""
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    _require(isinstance(value, dict), f"{path}: root must be an object")
    return value


def validate_contract(contract: dict[str, Any]) -> dict[str, int | str]:
    """验证 Topic、Key、Envelope、版本顺序和 Flink State 隔离边界。"""
    _exact_keys(contract, {"contract_version", "status", "namespace", "topic_defaults", "raw_cdc", "behavior", "standard", "envelope", "flink_state"}, "root")
    _require(contract["contract_version"] == "2026-10-21", "contract_version must be 2026-10-21")
    _require(contract["namespace"] == "ecommerce.realtime.v1", "namespace must be ecommerce.realtime.v1")

    status = contract["status"]
    _exact_keys(status, {"implementation", "static_verification", "runtime_verification"}, "status")
    _require(status == {"implementation": "implemented", "static_verification": "static_verified", "runtime_verification": "not_run"}, "status must preserve the static-only evidence boundary")

    defaults = contract["topic_defaults"]
    _exact_keys(defaults, {"partitions", "replication_factor", "min_insync_replicas", "cleanup_policy", "compression_type", "retention_ms"}, "topic_defaults")
    _require(defaults == {"partitions": 3, "replication_factor": 3, "min_insync_replicas": 2, "cleanup_policy": "delete", "compression_type": "producer", "retention_ms": 604800000}, "topic_defaults differ from the frozen durability contract")

    raw = contract["raw_cdc"]
    _exact_keys(raw, {"topic_pattern", "key_strategy", "topics"}, "raw_cdc")
    _require(raw["topic_pattern"] == "ecommerce.realtime.v1.cdc.<table>", "raw_cdc.topic_pattern mismatch")
    _require(raw["key_strategy"] == "table_primary_key", "raw_cdc.key_strategy must be table_primary_key")
    topics = raw["topics"]
    _require(isinstance(topics, dict), "raw_cdc.topics must be an object")
    _require(set(topics) == set(EXPECTED_TABLE_KEYS), "raw_cdc.topics must contain exactly the 21 formal source tables")
    seen_topics: set[str] = set()
    for table, primary_key in EXPECTED_TABLE_KEYS.items():
        _require(bool(IDENTIFIER.fullmatch(table)), f"invalid source table: {table}")
        item = topics[table]
        _exact_keys(item, {"topic", "primary_key"}, f"raw_cdc.topics.{table}")
        expected_topic = f"ecommerce.realtime.v1.cdc.{table}"
        _require(item["topic"] == expected_topic and bool(TOPIC.fullmatch(item["topic"])), f"{table}: topic mismatch")
        _require(item["topic"] not in seen_topics, f"duplicate topic: {item['topic']}")
        seen_topics.add(item["topic"])
        _require(item["primary_key"] == [primary_key], f"{table}: primary_key must be [{primary_key}]")

    behavior = contract["behavior"]
    _exact_keys(behavior, {"topic", "key_fields"}, "behavior")
    _require(behavior == {"topic": "ecommerce.realtime.v1.behavior.raw", "key_fields": ["session_id"]}, "behavior topic/key contract mismatch")

    standard = contract["standard"]
    _exact_keys(standard, {"topic_pattern", "key_strategy", "domains"}, "standard")
    _require(standard["topic_pattern"] == "ecommerce.realtime.v1.standard.<domain>", "standard.topic_pattern mismatch")
    _require(standard["key_strategy"] == "domain_aggregate_key", "standard topics must repartition by domain aggregate key")
    _require(standard["domains"] == EXPECTED_DOMAINS, "standard.domains mismatch")

    envelope = contract["envelope"]
    _exact_keys(envelope, {"serialization", "compatibility", "required_fields", "allowed_ops", "event_version"}, "envelope")
    _require(envelope["serialization"] == "json_utf8", "envelope.serialization mismatch")
    _require(envelope["compatibility"] == "backward", "envelope.compatibility mismatch")
    _require(envelope["required_fields"] == EXPECTED_ENVELOPE_FIELDS, "envelope.required_fields mismatch")
    _require(envelope["allowed_ops"] == ["r", "c", "u", "d"], "envelope.allowed_ops mismatch")
    version = envelope["event_version"]
    _exact_keys(version, {"strategy", "forbidden_strategies", "common_fields", "phase_order", "snapshot", "binlog"}, "envelope.event_version")
    _require(version["strategy"] == "source_epoch_phase_position", "event_version.strategy mismatch")
    _require(version["forbidden_strategies"] == ["kafka_offset"], "kafka_offset must remain explicitly forbidden")
    _require(version["common_fields"] == ["source_epoch", "phase"], "event_version.common_fields mismatch")
    _require(version["phase_order"] == ["snapshot", "binlog"], "event_version.phase_order mismatch")
    _require(version["snapshot"] == {"phase": "snapshot", "position_fields": ["snapshot_run_id", "table", "pk_hash"]}, "snapshot event_version mismatch")
    _require(version["binlog"] == {"phase": "binlog", "position_fields": ["file_index", "pos", "row"]}, "binlog event_version mismatch")

    state = contract["flink_state"]
    _exact_keys(state, {"checkpoint_root", "savepoint_root", "pilot_state_reuse"}, "flink_state")
    _require(state["checkpoint_root"] == "hdfs:///warehouse/ecommerce/realtime/v1/checkpoints/<application>", "checkpoint_root mismatch")
    _require(state["savepoint_root"] == "hdfs:///warehouse/ecommerce/realtime/v1/savepoints/<application>", "savepoint_root mismatch")
    _require(state["pilot_state_reuse"] is False, "Pilot state reuse must be false")

    return {"status": "static_verified", "runtime": "not_run", "raw_cdc_topics": len(topics), "standard_domains": len(EXPECTED_DOMAINS)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    args = parser.parse_args()
    summary = validate_contract(load_json(args.contract))
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
