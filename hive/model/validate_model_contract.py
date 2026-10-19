#!/usr/bin/env python3
"""在生成 SQL 前验证冻结的 DIM/DWD Model Contract。"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")
ALLOWED_HISTORY = {"type_1", "scd2", "source_effective_interval"}
ALLOWED_FACT_KINDS = {"transaction", "accumulating_snapshot"}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_json(path: Path) -> dict[str, Any]:
    """读取 JSON Object，拒绝数组或标量根节点。"""
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    _require(isinstance(value, dict), f"{path}: root must be an object")
    return value


def validate_contract(contract: dict[str, Any], ods_contract: dict[str, Any]) -> dict[str, int]:
    """校验模型粒度、业务键、源表、历史策略与 Model Gate。"""
    models = contract.get("models")
    _require(isinstance(models, dict) and models, "models must be a non-empty object")

    ods_tables = ods_contract.get("tables")
    _require(isinstance(ods_tables, dict), "ODS contract tables must be an object")
    allowed_sources = {item["target_table"] for item in ods_tables.values()}
    allowed_sources.add("ods_behavior_event")

    layers = {"dim": 0, "dwd": 0}
    scd2_count = 0
    for model_name, model in models.items():
        _require(bool(IDENTIFIER.fullmatch(model_name)), f"invalid model name: {model_name}")
        _require(isinstance(model, dict), f"{model_name}: definition must be an object")
        layer = model.get("layer")
        _require(layer in layers, f"{model_name}: layer must be dim or dwd")
        _require(model_name.startswith(f"{layer}_"), f"{model_name}: prefix must match layer")
        layers[layer] += 1

        _require(isinstance(model.get("grain"), str) and model["grain"].strip(), f"{model_name}: grain is required")
        keys = model.get("business_key")
        _require(isinstance(keys, list) and keys, f"{model_name}: business_key is required")
        _require(all(isinstance(key, str) and IDENTIFIER.fullmatch(key) for key in keys), f"{model_name}: invalid business_key")

        sources = model.get("sources")
        _require(isinstance(sources, list) and sources, f"{model_name}: sources are required")
        unknown_sources = sorted(set(sources) - allowed_sources)
        _require(not unknown_sources, f"{model_name}: unknown ODS sources {unknown_sources}")
        _require(bool(model.get("partition_source")), f"{model_name}: partition_source is required")

        if layer == "dim":
            strategy = model.get("history_strategy")
            _require(strategy in ALLOWED_HISTORY, f"{model_name}: invalid history_strategy")
            if strategy in {"scd2", "source_effective_interval"}:
                _require(bool(model.get("effective_from")), f"{model_name}: effective_from is required")
                _require(bool(model.get("effective_to")), f"{model_name}: effective_to is required")
            if strategy == "scd2":
                scd2_count += 1
                for field in ("surrogate_key", "current_flag", "tracked_attributes"):
                    _require(bool(model.get(field)), f"{model_name}: {field} is required")
        else:
            _require(model.get("fact_kind") in ALLOWED_FACT_KINDS, f"{model_name}: invalid fact_kind")
            _require(bool(model.get("event_time")), f"{model_name}: event_time is required")

    gate = contract.get("model_gate")
    _require(isinstance(gate, dict), "model_gate must be an object")
    for group in ("common", "scd2", "facts", "amounts", "behavior"):
        rules = gate.get(group)
        _require(isinstance(rules, list) and rules, f"model_gate.{group} must be non-empty")
        _require(len(rules) == len(set(rules)), f"model_gate.{group} contains duplicates")

    _require(scd2_count == 1, "contract must define exactly one SCD2 model")
    _require("dwd_behavior_event" in models, "dwd_behavior_event is required")
    return {"models": len(models), "dim": layers["dim"], "dwd": layers["dwd"], "scd2": scd2_count}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--ods-contract", type=Path, required=True)
    args = parser.parse_args()
    summary = validate_contract(load_json(args.contract), load_json(args.ods_contract))
    print(json.dumps({"status": "valid", **summary}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
