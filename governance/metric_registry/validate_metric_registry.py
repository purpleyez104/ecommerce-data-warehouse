#!/usr/bin/env python3
"""校验 Project 1 Metric Registry 的发布边界与定义绑定。"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


METRIC_ID = re.compile(r"^(TR|TF|PR|US|RF|MK)-\d{2}$")
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
VERIFIED_STATUS = re.compile(r"^状态：`VERIFIED`$", re.MULTILINE)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_json(path: Path) -> dict[str, Any]:
    """读取 JSON Object；数组或标量根节点不是有效 Contract。"""
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    _require(isinstance(value, dict), f"{path}: root must be an object")
    return value


def definition_row(document: str, row_key: str) -> str:
    """按稳定 Metric ID 找到唯一 Markdown 定义行并标准化空白。"""
    prefix = f"| {row_key} |"
    rows = [line.strip() for line in document.splitlines() if line.strip().startswith(prefix)]
    _require(len(rows) == 1, f"{row_key}: expected exactly one definition row, found {len(rows)}")
    return " ".join(rows[0].split())


def definition_hash(document: str, row_key: str) -> str:
    """计算 Registry 用于检测定义漂移的 SHA-256。"""
    return hashlib.sha256(definition_row(document, row_key).encode("utf-8")).hexdigest()


def validate_registry(
    registry: dict[str, Any],
    aggregate_contract: dict[str, Any],
    repo_root: Path,
) -> dict[str, int]:
    """校验唯一键、版本、定义哈希、物理输出和 Runtime 验收引用。"""
    _require(SEMVER.fullmatch(str(registry.get("registry_version", ""))) is not None,
             "registry_version must be semantic version")
    _require(registry.get("status") == "verified", "registry status must be verified")
    metrics = registry.get("metrics")
    _require(isinstance(metrics, list) and metrics, "metrics must be a non-empty array")
    registry_evidence = registry.get("acceptance_evidence")
    _require(isinstance(registry_evidence, list) and registry_evidence,
             "registry acceptance_evidence must be a non-empty array")

    models = aggregate_contract.get("models")
    _require(isinstance(models, dict), "aggregate contract models must be an object")
    seen: set[tuple[str, str]] = set()
    evidence_paths: set[str] = set()

    for metric in metrics:
        _require(isinstance(metric, dict), "metric entry must be an object")
        metric_id = metric.get("metric_id")
        version = metric.get("definition_version")
        _require(isinstance(metric_id, str) and METRIC_ID.fullmatch(metric_id) is not None,
                 f"invalid metric_id: {metric_id}")
        _require(isinstance(version, str) and SEMVER.fullmatch(version) is not None,
                 f"{metric_id}: definition_version is required and must be semantic version")
        key = (metric_id, version)
        _require(key not in seen, f"duplicate metric definition: {metric_id}@{version}")
        seen.add(key)
        _require(metric.get("publication_status", registry.get("status")) == "verified",
                 f"{metric_id}: only verified metrics may be published")

        ref = metric.get("definition_ref")
        _require(ref is None or isinstance(ref, dict), f"{metric_id}: definition_ref must be an object")
        ref_path = ref.get("path") if ref else registry.get("definition_source")
        row_key = ref.get("row_key") if ref else metric_id
        _require(ref_path == registry.get("definition_source"),
                 f"{metric_id}: definition_ref must use registry definition_source")
        _require(row_key == metric_id, f"{metric_id}: definition row_key must equal metric_id")
        source_path = repo_root / ref_path
        _require(source_path.is_file(), f"{metric_id}: missing definition source {ref_path}")
        expected_hash = definition_hash(source_path.read_text(encoding="utf-8"), metric_id)
        actual_hash = metric.get("definition_sha256")
        _require(isinstance(actual_hash, str) and SHA256.fullmatch(actual_hash) is not None,
                 f"{metric_id}: definition_sha256 must be lowercase SHA-256")
        _require(actual_hash == expected_hash, f"{metric_id}: definition hash mismatch")

        _require(isinstance(metric.get("time_semantics"), str) and metric["time_semantics"].strip(),
                 f"{metric_id}: time_semantics is required")

        output = metric.get("output")
        _require(isinstance(output, dict), f"{metric_id}: output is required")
        model_name = output.get("model")
        measure = output.get("measure")
        _require(model_name in models, f"{metric_id}: unknown output model {model_name}")
        model_measures = models[model_name].get("measures", [])
        _require(measure in model_measures, f"{metric_id}: unknown output measure {measure}")
        grain = metric.get("result_grain", models[model_name].get("business_key"))
        _require(isinstance(grain, list) and grain and all(isinstance(v, str) and v for v in grain),
                 f"{metric_id}: result_grain is required")
        lineage = metric.get("lineage", [*models[model_name].get("sources", []), model_name])
        _require(isinstance(lineage, list) and model_name in lineage,
                 f"{metric_id}: lineage must include output model")

        evidence = metric.get("acceptance_evidence", registry_evidence)
        _require(isinstance(evidence, list) and evidence,
                 f"{metric_id}: verified publication requires acceptance evidence")
        for relative_path in evidence:
            _require(isinstance(relative_path, str) and relative_path.startswith("docs/acceptance/"),
                     f"{metric_id}: evidence must be under docs/acceptance")
            evidence_path = repo_root / relative_path
            _require(evidence_path.is_file(), f"{metric_id}: missing evidence {relative_path}")
            _require(VERIFIED_STATUS.search(evidence_path.read_text(encoding="utf-8")) is not None,
                     f"{metric_id}: evidence is not VERIFIED: {relative_path}")
            evidence_paths.add(relative_path)

    return {"metrics": len(metrics), "evidence_files": len(evidence_paths)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--aggregate-contract", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    args = parser.parse_args()
    summary = validate_registry(
        load_json(args.registry),
        load_json(args.aggregate_contract),
        args.repo_root.resolve(),
    )
    print(json.dumps({"status": "valid", **summary}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
