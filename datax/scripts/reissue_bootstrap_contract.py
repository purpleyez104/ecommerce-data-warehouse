#!/usr/bin/env python3
"""Issue a new staging batch from an already verified Bootstrap snapshot contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import generate_job


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reissue(source_contract: Path, output_dir: Path, batch_id: str, extract_time: str) -> Path:
    """保留不可变 Snapshot/期望行数，只签发新的 staging 身份和抽取时间。"""
    if output_dir.exists():
        raise FileExistsError(f"output directory already exists: {output_dir}")
    payload = json.loads(source_contract.read_text(encoding="utf-8"))
    if payload.get("batch_contract_version") != 2 or payload.get("mode") != "bootstrap":
        raise ValueError("source must be a version 2 Bootstrap contract")
    if payload.get("batch_id") == batch_id:
        raise ValueError("new batch_id must differ from the source batch_id")
    if not generate_job.BATCH_ID_PATTERN.fullmatch(batch_id):
        raise ValueError(f"Invalid batch_id: {batch_id}")
    binding = payload.get("source_manifest", {})
    manifest_name = binding.get("path")
    if not isinstance(manifest_name, str) or Path(manifest_name).name != manifest_name:
        raise ValueError("source manifest must be a sibling file")
    manifest = source_contract.parent / manifest_name
    if not manifest.is_file() or _sha256(manifest) != binding.get("sha256"):
        raise ValueError("source snapshot manifest missing or SHA-256 mismatch")

    payload["batch_id"] = batch_id
    payload["extract_time"] = generate_job._parse_timestamp("extract_time", extract_time)
    output_dir.mkdir(parents=True)
    shutil.copyfile(manifest, output_dir / manifest.name)
    target = output_dir / "ods_batch_contract.json"
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-contract", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--extract-time", required=True)
    args = parser.parse_args()
    target = reissue(
        args.source_contract.resolve(), args.output_dir.resolve(), args.batch_id, args.extract_time
    )
    print(json.dumps({"status": "generated", "batch_contract": str(target)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
