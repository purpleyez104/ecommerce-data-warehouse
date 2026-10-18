#!/usr/bin/env python3
"""Plan and orchestrate a 21-table ODS stage/validate/publish-ready batch."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import generate_job


REPO_ROOT = Path(__file__).resolve().parents[2]
SQL_RENDERER = REPO_ROOT / "spark/scripts/render_ods_batch_sql.py"
REQUIRED_REPLAY_BATCH_KEYS = {
    "batch_contract_version", "dataset_version", "mode", "business_date", "window_start",
    "window_end", "batch_id", "extract_time", "replay_manifest", "expected_tables",
}
REQUIRED_SNAPSHOT_BATCH_KEYS = (REQUIRED_REPLAY_BATCH_KEYS - {"replay_manifest"}) | {"source_manifest"}
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


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
    if not isinstance(payload, dict) or frozenset(payload) not in {
        frozenset(REQUIRED_REPLAY_BATCH_KEYS), frozenset(REQUIRED_SNAPSHOT_BATCH_KEYS)
    }:
        raise ValueError("invalid batch contract keys")
    if payload["batch_contract_version"] not in {1, 2}:
        raise ValueError("unsupported batch_contract_version")
    if payload["batch_contract_version"] == 1 and "replay_manifest" not in payload:
        raise ValueError("version 1 batch requires replay_manifest")
    if payload["batch_contract_version"] == 2 and "source_manifest" not in payload:
        raise ValueError("version 2 batch requires source_manifest")
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
    if batch["batch_contract_version"] == 2:
        if batch["mode"] != "bootstrap":
            raise ValueError("snapshot manifest only supports bootstrap mode")
        binding = batch["source_manifest"]
        if not isinstance(binding, dict) or set(binding) != {"type", "path", "sha256"} or binding["type"] != "dataset_snapshot":
            raise ValueError("invalid source_manifest binding")
        manifest_path = Path(binding["path"])
        if not manifest_path.is_absolute():
            manifest_path = (batch_contract_path.parent / manifest_path).resolve()
        if not manifest_path.is_file() or _sha256(manifest_path) != binding["sha256"]:
            raise ValueError("snapshot manifest missing or SHA-256 mismatch")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("snapshot_manifest_version") != 1 or manifest.get("dataset_version") != batch["dataset_version"]:
            raise ValueError("snapshot manifest contract mismatch")
        expected = {
            item["table_name"]: {
                "row_count": item["row_count"],
                "affected_business_dates": item["affected_business_dates"],
                "business_date_row_counts": item["business_date_row_counts"],
            }
            for item in manifest["tables"]
        }
        if batch["business_date"] != manifest["history_end"][:10]:
            raise ValueError("batch business_date does not match snapshot history_end")
        if batch["expected_tables"] != expected:
            raise ValueError("batch expected_tables do not match the snapshot manifest")
        return expected

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
    publishes = False

    def stage(self, jobs: list[Path], plan: dict) -> None:
        return None

    def validate(self, validation_sql: Path, plan: dict) -> None:
        return None

    def prepare_publish(self, publish_sql: Path, plan: dict) -> None:
        return None


class SparkRuntimeExecutor:
    """Execute Spark validation and publish without requiring Source credentials."""

    authorizes_publish = True
    publishes = True

    def __init__(self, spark_sql: Path, output_dir: Path):
        self.spark_sql = spark_sql
        self.output_dir = output_dir
        self.logs_dir = output_dir / "logs"
        if not self.spark_sql.is_file():
            raise FileNotFoundError(f"spark-sql not found: {self.spark_sql}")

    def _run(self, command: list[str], log_name: str) -> None:
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self.logs_dir, 0o700)
        except OSError:
            pass
        log_path = self.logs_dir / log_name
        descriptor = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as log:
            completed = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, text=True, check=False)
        if completed.returncode != 0:
            raise RuntimeError(f"command failed with exit {completed.returncode}; log={log_path}")

    def stage(self, jobs: list[Path], plan: dict) -> None:
        raise RuntimeError("Spark-only executor cannot create DataX staging")

    def validate(self, validation_sql: Path, plan: dict) -> None:
        self._run([str(self.spark_sql), "-f", str(validation_sql)], "validation.log")

    def prepare_publish(self, publish_sql: Path, plan: dict) -> None:
        self._run([str(self.spark_sql), "-f", str(publish_sql)], "publish.log")


class RuntimeExecutor(SparkRuntimeExecutor):
    """Execute DataX, Spark validation and publish with private runtime config."""

    def __init__(self, env_file: Path, spark_sql: Path, output_dir: Path):
        self.env = generate_job.load_env(env_file)
        super().__init__(spark_sql, output_dir)
        datax_home = self.env.get("DATAX_HOME")
        if not datax_home:
            raise ValueError("DataX runtime config must define DATAX_HOME")
        self.datax = Path(datax_home) / "bin/datax.py"
        self.hdfs = Path(self.env.get("HDFS_BIN", "/data/module/hadoop/bin/hdfs"))
        if not self.datax.is_file():
            raise FileNotFoundError(f"DataX entrypoint not found: {self.datax}")
        if not self.hdfs.is_file():
            raise FileNotFoundError(f"hdfs command not found: {self.hdfs}")

    def stage(self, jobs: list[Path], plan: dict) -> None:
        substitutions = {
            "${MYSQL_JDBC_URL}": self.env["MYSQL_JDBC_URL"],
            "${MYSQL_USER}": self.env["MYSQL_USER"],
            "${MYSQL_PASSWORD}": self.env["MYSQL_PASSWORD"],
            "${HDFS_DEFAULT_FS}": self.env["HDFS_DEFAULT_FS"],
        }
        for job in jobs:
            content = job.read_text(encoding="utf-8")
            for placeholder, value in substitutions.items():
                content = content.replace(placeholder, value)
            if "${" in content:
                raise ValueError(f"unresolved runtime placeholder: {job}")
            payload = json.loads(content)
            output_path = payload["job"]["content"][0]["writer"]["parameter"]["path"]
            stage_root = generate_job._validate_hdfs_root(self.env["ODS_STAGE_ROOT"]).rstrip("/")
            if not output_path.startswith(stage_root + "/"):
                raise ValueError(f"DataX output path escapes ODS_STAGE_ROOT: {output_path}")
            # DataX 202309 HDFS Writer requires the isolated batch path to exist.
            self._run([str(self.hdfs), "dfs", "-mkdir", "-p", output_path], f"{job.stem}.mkdir.log")
            # Secret-bearing DataX jobs exist only for the duration of one subprocess.
            descriptor, raw_path = tempfile.mkstemp(prefix="ods-datax-", suffix=".json", dir=self.output_dir)
            runtime_job = Path(raw_path)
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(content)
                os.chmod(runtime_job, 0o600)
                self._run([sys.executable, str(self.datax), str(runtime_job)], f"{job.stem}.log")
            finally:
                runtime_job.unlink(missing_ok=True)


def _validate_resume_source(resume_from: Path, project_home: Path, plan: dict, partition_plan: list[dict]) -> Path:
    """Bind reused staging to the same batch, target and exact partition plan."""
    source = _validate_output_dir(resume_from, project_home)
    if not source.is_dir():
        raise ValueError("resume_from must be an existing ODS batch directory")
    state_path = source / "state.json"
    plan_path = source / "batch_plan.json"
    partitions_path = source / "sql/partition_plan.json"
    if not all(path.is_file() for path in (state_path, plan_path, partitions_path)):
        raise ValueError("resume_from is missing state or plan evidence")
    prior_state = json.loads(state_path.read_text(encoding="utf-8"))
    if "staged" not in prior_state.get("state_history", []):
        raise ValueError("resume_from never completed staging")
    prior_plan = json.loads(plan_path.read_text(encoding="utf-8"))
    binding_keys = (
        "batch_id", "dataset_version", "mode", "business_date", "window_start",
        "window_end", "job_count", "affected_business_dates", "target_database",
    )
    if any(prior_plan.get(key) != plan.get(key) for key in binding_keys):
        raise ValueError("resume_from batch plan does not match the requested batch")
    prior_partitions = json.loads(partitions_path.read_text(encoding="utf-8"))
    if prior_partitions != partition_plan:
        raise ValueError("resume_from partition plan does not match the requested batch")
    return source


def run_batch(batch_contract_path: Path, output_dir: Path, project_home: Path, stage_root: str,
              executor=None, contract_path: Path = generate_job.DEFAULT_CONTRACT,
              target_database: str = "ecommerce_ods", resume_from: Path | None = None) -> dict:
    output_dir = _validate_output_dir(output_dir, project_home)
    if output_dir.exists():
        raise FileExistsError(f"batch output already exists: {output_dir}")
    output_dir.mkdir(parents=True)
    try:
        os.chmod(output_dir, 0o700)
    except OSError:
        pass
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
        job_manifest = {
            "job_manifest_version": 1,
            "batch_id": batch["batch_id"],
            "dataset_version": batch["dataset_version"],
            "source_database": contract["source_database"],
            "target_database": target_database,
            "files": [
                {"file": path.name, "sha256": _sha256(path)} for path in job_paths
            ],
        }
        _private_write(jobs_dir / "job_manifest.json", json.dumps(job_manifest, ensure_ascii=False, indent=2) + "\n")

        if not IDENTIFIER_PATTERN.fullmatch(target_database):
            raise ValueError("invalid target_database")
        sql = SQL.render_batch_sql(contract, batch, stage_root, target_database)
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
            "target_database": target_database,
            "resume_from": None,
        }
        if resume_from is not None:
            resume_source = _validate_resume_source(resume_from, project_home, plan, sql["partition_plan"])
            plan["resume_from"] = str(resume_source)
        _private_write(output_dir / "batch_plan.json", json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
        active_executor = executor or DryRunExecutor()
        if resume_from is None:
            active_executor.stage(job_paths, plan)
            state.update(state="staged")
            state["state_history"].append("staged")
        else:
            state.update(state="staged_reused")
            state["state_history"].append("staged_reused")
        save_state()
        active_executor.validate(validation_path, plan)
        state.update(state="validated")
        state["state_history"].append("validated")
        save_state()
        active_executor.prepare_publish(publish_path, plan)
        final_state = "published" if getattr(active_executor, "publishes", False) else "publish_ready"
        state.update(
            state=final_state,
            publish_allowed=bool(getattr(active_executor, "authorizes_publish", False)),
        )
        state["state_history"].append(final_state)
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
    parser.add_argument("--target-database", default="ecommerce_ods")
    parser.add_argument("--resume-from", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--spark-sql", type=Path, default=Path("/data/module/spark/bin/spark-sql"))
    args = parser.parse_args(argv)
    try:
        executor = None
        if args.execute:
            if args.resume_from is not None:
                executor = SparkRuntimeExecutor(args.spark_sql, args.output_dir)
            elif args.env_file is None:
                raise ValueError("--execute requires --env-file")
            else:
                executor = RuntimeExecutor(args.env_file, args.spark_sql, args.output_dir)
        result = run_batch(
            args.batch_contract, args.output_dir, args.project_home, args.stage_root,
            executor=executor, contract_path=args.contract, target_database=args.target_database,
            resume_from=args.resume_from,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"status": result["state"]["state"], "plan": str(args.output_dir / "batch_plan.json")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
