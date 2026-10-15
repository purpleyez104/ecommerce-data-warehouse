#!/usr/bin/env python3
"""Plan and orchestrate a 21-table ODS stage/validate/publish-ready batch."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import generate_job


REPO_ROOT = Path(__file__).resolve().parents[2]
SQL_RENDERER = REPO_ROOT / "spark/scripts/render_ods_batch_sql.py"
REQUIRED_BATCH_KEYS = {
    "batch_contract_version", "dataset_version", "mode", "business_date", "window_start",
    "window_end", "batch_id", "extract_time", "replay_manifest", "expected_tables",
}


def _load_sql_renderer():
    spec = importlib.util.spec_from_file_location("render_ods_batch_sql", SQL_RENDERER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SQL = _load_sql_renderer()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _private_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            descriptor = -1
            handle.write(content)
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _load_batch(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) != REQUIRED_BATCH_KEYS:
        raise ValueError("invalid batch contract keys")
    if payload["batch_contract_version"] != 1:
        raise ValueError("unsupported batch_contract_version")
    if payload["mode"] not in {"bootstrap", "incremental"}:
        raise ValueError("mode must be bootstrap or incremental")
    if payload["mode"] == "bootstrap" and (payload["window_start"] is not None or payload["window_end"] is not None):
        raise ValueError("bootstrap batch must not define an incremental window")
    if payload["mode"] == "incremental" and (not payload["window_start"] or not payload["window_end"]):
        raise ValueError("incremental batch requires window_start and window_end")
    return payload


def _validate_output_dir(output_dir: Path, project_home: Path) -> Path:
    project_root = project_home.resolve()
    allowed_root = (project_root / "runtime" / "ods").resolve()
    requested = output_dir.resolve()
    try:
        relative = requested.relative_to(allowed_root)
    except ValueError as exc:
        raise ValueError("output_dir must be inside project_home/runtime/ods") from exc
    if not relative.parts:
        raise ValueError("output_dir must be a batch directory below project_home/runtime/ods")
    current = output_dir.absolute().parent
    while current != current.parent:
        if current.exists() and current.is_symlink():
            raise ValueError("output_dir must not traverse a symlink")
        if current.resolve() == project_root:
            break
        current = current.parent
    return requested


def _manifest_expected(batch: dict, batch_contract_path: Path) -> dict[str, dict]:
    binding = batch["replay_manifest"]
    if not isinstance(binding, dict) or set(binding) != {"path", "sha256"}:
        raise ValueError("invalid replay_manifest binding")
    manifest_path = Path(binding["path"])
    if not manifest_path.is_absolute():
        manifest_path = (batch_contract_path.parent / manifest_path).resolve()
    if not manifest_path.is_file() or _sha256(manifest_path) != binding["sha256"]:
        raise ValueError("replay manifest missing or SHA-256 mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("replay_manifest_version") != 1 or manifest.get("dataset_version") != batch["dataset_version"]:
        raise ValueError("replay manifest contract mismatch")
    if batch["mode"] == "bootstrap":
        expected = {
            item["table_name"]: {
                "row_count": item["row_count"],
                "affected_business_dates": item["affected_business_dates"],
                "business_date_row_counts": item["business_date_row_counts"],
            }
            for item in manifest["bootstrap"]["tables"]
        }
    else:
        matches = [
            item for item in manifest["daily_packages"]
            if item["window_start"] == batch["window_start"] and item["window_end"] == batch["window_end"]
        ]
        if len(matches) != 1:
            raise ValueError("incremental window does not match exactly one replay package")
        package_path = manifest_path.parent / matches[0]["path"] / "package_manifest.json"
        if not package_path.is_file() or _sha256(package_path) != matches[0]["manifest_sha256"]:
            raise ValueError("daily package manifest missing or SHA-256 mismatch")
        package = json.loads(package_path.read_text(encoding="utf-8"))
        expected = {
            item["table_name"]: {
                "row_count": item["extract_row_count"],
                "affected_business_dates": item["affected_business_dates"],
                "business_date_row_counts": item["business_date_row_counts"],
            }
            for item in package["tables"]
        }
    expected_business_date = (
        (datetime.fromisoformat(manifest["cutover_time"]) - timedelta(days=1)).date().isoformat()
        if batch["mode"] == "bootstrap"
        else batch["window_start"][:10]
    )
    if batch["business_date"] != expected_business_date:
        raise ValueError("batch business_date does not match the replay window")
    if batch["expected_tables"] != expected:
        raise ValueError("batch expected_tables do not match the replay manifest")
    return expected


class DryRunExecutor:
    """An injectable no-I/O executor used for local planning and tests."""

    authorizes_publish = False

    def stage(self, jobs: list[Path], plan: dict) -> None:
        return None

    def validate(self, validation_sql: Path, plan: dict) -> None:
        return None

    def prepare_publish(self, publish_sql: Path, plan: dict) -> None:
        return None


def run_batch(batch_contract_path: Path, output_dir: Path, project_home: Path, stage_root: str,
              executor=None, contract_path: Path = generate_job.DEFAULT_CONTRACT) -> dict:
    output_dir = _validate_output_dir(output_dir, project_home)
    if output_dir.exists():
        raise FileExistsError(f"batch output already exists: {output_dir}")
    output_dir.mkdir(parents=True)
    state = {"state": "planned", "state_history": ["planned"], "publish_allowed": False, "error": None}
    state_path = output_dir / "state.json"

    def save_state() -> None:
        content = json.dumps(state, ensure_ascii=False, indent=2) + "\n"
        if state_path.exists():
            state_path.write_text(content, encoding="utf-8", newline="\n")
            try:
                os.chmod(state_path, 0o600)
            except OSError:
                pass
        else:
            _private_write(state_path, content)

    save_state()
    try:
        batch = _load_batch(batch_contract_path)
        contract = generate_job.load_contract(contract_path)
        expected = _manifest_expected(batch, batch_contract_path)
        if set(expected) != set(contract["tables"]):
            raise ValueError("batch table set must exactly match the 21-table ODS contract")
        generate_job._parse_date(batch["business_date"])
        generate_job._parse_timestamp("extract_time", batch["extract_time"])
        env = {
            "MYSQL_JDBC_URL": "${MYSQL_JDBC_URL}",
            "MYSQL_USER": "${MYSQL_USER}",
            "MYSQL_PASSWORD": "${MYSQL_PASSWORD}",
            "HDFS_DEFAULT_FS": "${HDFS_DEFAULT_FS}",
            "ODS_STAGE_ROOT": stage_root,
            "PROJECT_HOME": str(project_home.resolve()),
        }
        jobs_dir = output_dir / "jobs"
        job_paths = []
        for table, policy in contract["tables"].items():
            window_start = batch["window_start"]
            window_end = batch["window_end"]
            if batch["mode"] == "incremental" and policy["load_strategy"] == "full_snapshot":
                window_start = window_end = None
            rendered = generate_job.render_job(
                env, contract, table, batch["mode"], batch["business_date"], batch["batch_id"],
                batch["extract_time"], window_start, window_end,
            )
            path = jobs_dir / f"{table}_{batch['batch_id']}.json"
            generate_job.write_private_job(path, rendered)
            job_paths.append(path)

        sql = SQL.render_batch_sql(contract, batch, stage_root)
        sql_dir = output_dir / "sql"
        validation_path = sql_dir / "validation.sql"
        publish_path = sql_dir / "publish.sql"
        partition_path = sql_dir / "partition_plan.json"
        _private_write(validation_path, sql["validation_sql"])
        _private_write(publish_path, sql["publish_sql"])
        _private_write(partition_path, json.dumps(sql["partition_plan"], ensure_ascii=False, indent=2) + "\n")
        plan = {
            "batch_id": batch["batch_id"], "dataset_version": batch["dataset_version"], "mode": batch["mode"],
            "business_date": batch["business_date"], "window_start": batch["window_start"], "window_end": batch["window_end"],
            "job_count": len(job_paths), "jobs": [str(path.relative_to(output_dir)).replace(os.sep, "/") for path in job_paths],
            "validation_sql": str(validation_path.relative_to(output_dir)).replace(os.sep, "/"),
            "publish_sql": str(publish_path.relative_to(output_dir)).replace(os.sep, "/"),
            "partition_plan": str(partition_path.relative_to(output_dir)).replace(os.sep, "/"),
            "affected_business_dates": sorted({date for item in expected.values() for date in item["affected_business_dates"]}),
            "external_runtime": "not_run",
        }
        _private_write(output_dir / "batch_plan.json", json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
        active_executor = executor or DryRunExecutor()
        active_executor.stage(job_paths, plan)
        state.update(state="staged")
        state["state_history"].append("staged")
        save_state()
        active_executor.validate(validation_path, plan)
        state.update(state="validated")
        state["state_history"].append("validated")
        save_state()
        active_executor.prepare_publish(publish_path, plan)
        state.update(
            state="publish_ready",
            publish_allowed=bool(getattr(active_executor, "authorizes_publish", False)),
        )
        state["state_history"].append("publish_ready")
        save_state()
        return {"state": state, "plan": plan}
    except Exception as exc:
        state.update(state="failed", publish_allowed=False, error=str(exc))
        state["state_history"].append("failed")
        save_state()
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-contract", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--project-home", type=Path, required=True)
    parser.add_argument("--stage-root", required=True)
    parser.add_argument("--contract", type=Path, default=generate_job.DEFAULT_CONTRACT)
    parser.add_argument("--dry-run", action="store_true", required=True)
    args = parser.parse_args(argv)
    try:
        result = run_batch(args.batch_contract, args.output_dir, args.project_home, args.stage_root, contract_path=args.contract)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"status": result["state"]["state"], "plan": str(args.output_dir / "batch_plan.json")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
