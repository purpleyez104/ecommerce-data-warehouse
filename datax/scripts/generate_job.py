#!/usr/bin/env python3
"""Render one private DataX job for a formal ODS batch."""

import argparse
import copy
from datetime import date, datetime
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import string


REPO_ROOT = Path(__file__).resolve().parents[2]
BASE = REPO_ROOT / "datax"
TEMPLATE = BASE / "templates/mysql_to_hdfs_ods.json.tpl"
DEFAULT_CONTRACT = BASE / "config/ods_tables.json"
SOURCE_DDL = REPO_ROOT / "mysql/ddl/001_ecommerce_oltp.sql"
SOURCE_CONTRACT = REPO_ROOT / "mock/generator/business_generator/src/business_generator/contracts.py"
REQUIRED_ENV = (
    "MYSQL_JDBC_URL",
    "MYSQL_USER",
    "MYSQL_PASSWORD",
    "HDFS_DEFAULT_FS",
    "ODS_STAGE_ROOT",
    "PROJECT_HOME",
)
VARIABLE_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
BATCH_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d{1,3})?$")
DDL_TABLE_PATTERN = re.compile(
    r"CREATE TABLE `(?P<table>[A-Za-z_][A-Za-z0-9_]*)` \(\n(?P<body>.*?)\n\) ENGINE=",
    re.DOTALL,
)
DDL_COLUMN_PATTERN = re.compile(
    r"^  `(?P<column>[A-Za-z_][A-Za-z0-9_]*)` (?P<type>BIGINT|INT|VARCHAR\(\d+\)|DATETIME\(\d+\)|JSON)(?:\s|$)"
)
TOP_LEVEL_KEYS = {"contract_version", "source_database", "column_contract", "tables"}
POLICY_KEYS = {
    "source_table",
    "target_table",
    "load_strategy",
    "primary_key",
    "watermark_column",
    "business_time",
    "partition",
    "extract",
    "quality_rules",
}
LOAD_STRATEGIES = {"mutable_incremental", "append_only", "full_snapshot"}
REQUIRED_QUALITY_RULES = {
    "primary_key_not_null",
    "primary_key_unique",
    "source_target_row_count",
}
COLUMN_CONTRACT = {
    "column_order": "TABLE_COLUMNS",
    "column_types": "mysql/ddl/001_ecommerce_oltp.sql",
}
PARTITION_CONTRACT = {"column": "dt", "source": "business_date"}
WATERMARK_EXTRACT = {"bootstrap": "full", "incremental": "half_open_watermark"}
SNAPSHOT_EXTRACT = {"bootstrap": "full", "incremental": "full_snapshot"}
AUDIT_COLUMNS = (
    ("business_date", "string"),
    ("extract_time", "string"),
    ("batch_id", "string"),
    ("source_table", "string"),
)


def _load_source_columns():
    spec = importlib.util.spec_from_file_location("business_generator_contracts", SOURCE_CONTRACT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.TABLE_COLUMNS


TABLE_COLUMNS = _load_source_columns()


def _expand_env(raw_env):
    env = dict(raw_env)
    for _ in range(len(env) + 1):
        changed = False
        for key, value in env.items():
            expanded = string.Template(value).safe_substitute(env)
            if expanded != value:
                env[key] = expanded
                changed = True
        if not changed:
            break
    unresolved = {name for value in env.values() for name in VARIABLE_PATTERN.findall(value)}
    if unresolved:
        raise ValueError("Unresolved DataX config variables: " + ", ".join(sorted(unresolved)))
    return env


def load_env(env_file=None):
    path = Path(env_file or os.environ.get("DATAX_ENV_FILE", BASE / "config/datax.env"))
    if not path.is_file():
        raise FileNotFoundError(
            f"DataX config not found: {path}. Copy config/datax.env.example to config/datax.env and fill private values."
        )
    raw_env = {}
    with path.open(encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                raise ValueError(f"Invalid DataX config line {line_number}: expected KEY=VALUE")
            key, value = line.split("=", 1)
            key = key.strip()
            if not key:
                raise ValueError(f"Invalid DataX config line {line_number}: empty key")
            if key in raw_env:
                raise ValueError(f"Duplicate DataX config key at line {line_number}: {key}")
            raw_env[key] = value.strip()
    env = _expand_env(raw_env)
    missing = [key for key in REQUIRED_ENV if not env.get(key)]
    if missing:
        raise ValueError("Missing required DataX config values: " + ", ".join(missing))
    _validate_hdfs_root(env["ODS_STAGE_ROOT"])
    job_output_dir(env)
    return env


def parse_ddl_mysql_types(ddl_path=SOURCE_DDL):
    ddl = Path(ddl_path).read_text(encoding="utf-8")
    result = {}
    for match in DDL_TABLE_PATTERN.finditer(ddl):
        columns = {}
        for line in match.group("body").splitlines():
            column_match = DDL_COLUMN_PATTERN.match(line)
            if column_match:
                columns[column_match.group("column")] = column_match.group("type")
        result[match.group("table")] = columns
    return result


def parse_ddl_types(ddl_path=SOURCE_DDL):
    return {
        table: {
            column: "long" if mysql_type in {"BIGINT", "INT"} else "string"
            for column, mysql_type in columns.items()
        }
        for table, columns in parse_ddl_mysql_types(ddl_path).items()
    }


def _require_exact_keys(value, expected, label):
    if not isinstance(value, dict) or set(value) != expected:
        missing = expected - set(value) if isinstance(value, dict) else expected
        extra = set(value) - expected if isinstance(value, dict) else set()
        detail = []
        if missing:
            detail.append("missing " + ", ".join(sorted(missing)))
        if extra:
            detail.append("unknown " + ", ".join(sorted(extra)))
        raise ValueError(f"{label}: invalid keys ({'; '.join(detail)})")


def _validate_policy(table, policy, source_columns, mysql_types):
    _require_exact_keys(policy, POLICY_KEYS, table)
    if policy["source_table"] != table:
        raise ValueError(f"{table}: source_table must match the contract table key")
    target = policy["target_table"]
    if not isinstance(target, str) or not IDENTIFIER_PATTERN.fullmatch(target) or not target.startswith("ods_"):
        raise ValueError(f"{table}: invalid target_table")
    strategy = policy["load_strategy"]
    if strategy not in LOAD_STRATEGIES:
        raise ValueError(f"{table}: invalid load_strategy")
    primary_key = policy["primary_key"]
    if (
        not isinstance(primary_key, list)
        or not primary_key
        or len(set(primary_key)) != len(primary_key)
        or not set(primary_key).issubset(source_columns)
    ):
        raise ValueError(f"{table}: invalid primary_key")
    watermark = policy["watermark_column"]
    business_time = policy["business_time"]
    if strategy == "full_snapshot":
        if watermark is not None or policy["extract"] != SNAPSHOT_EXTRACT:
            raise ValueError(f"{table}: full_snapshot must not define a watermark and must use snapshot extraction")
        if business_time != {"mode": "parameter"}:
            raise ValueError(f"{table}: full_snapshot business_time must use the business_date parameter")
    else:
        if watermark not in source_columns or policy["extract"] != WATERMARK_EXTRACT:
            raise ValueError(f"{table}: invalid watermark extraction policy")
        if not mysql_types.get(watermark, "").startswith("DATETIME"):
            raise ValueError(f"{table}: watermark_column must be DATETIME")
        if strategy == "mutable_incremental" and watermark != "updated_at":
            raise ValueError(f"{table}: mutable_incremental must use updated_at")
        if strategy == "append_only" and watermark not in {"recorded_at", "merged_at"}:
            raise ValueError(f"{table}: append_only must use a record-time watermark")
        if (
            not isinstance(business_time, dict)
            or set(business_time) != {"mode", "column"}
            or business_time.get("mode") != "column"
            or business_time.get("column") not in source_columns
        ):
            raise ValueError(f"{table}: invalid business_time")
        if not mysql_types.get(business_time["column"], "").startswith("DATETIME"):
            raise ValueError(f"{table}: business_time column must be DATETIME")
    if policy["partition"] != PARTITION_CONTRACT:
        raise ValueError(f"{table}: invalid partition contract")
    quality_rules = policy["quality_rules"]
    if (
        not isinstance(quality_rules, list)
        or not quality_rules
        or any(not isinstance(rule, str) or not rule for rule in quality_rules)
        or len(set(quality_rules)) != len(quality_rules)
        or set(quality_rules) != REQUIRED_QUALITY_RULES
    ):
        raise ValueError(f"{table}: invalid quality_rules")


def load_contract(contract_path=DEFAULT_CONTRACT, ddl_path=SOURCE_DDL):
    payload = json.loads(Path(contract_path).read_text(encoding="utf-8"))
    _require_exact_keys(payload, TOP_LEVEL_KEYS, "ODS contract")
    if not isinstance(payload["contract_version"], str) or not payload["contract_version"]:
        raise ValueError("ODS contract: invalid contract_version")
    if not IDENTIFIER_PATTERN.fullmatch(payload["source_database"]):
        raise ValueError("ODS contract: invalid source_database")
    if payload["column_contract"] != COLUMN_CONTRACT:
        raise ValueError("ODS contract: invalid column_contract")
    tables = payload["tables"]
    if not isinstance(tables, dict) or set(tables) != set(TABLE_COLUMNS):
        raise ValueError("ODS contract table set must exactly match TABLE_COLUMNS")
    mysql_types = parse_ddl_mysql_types(ddl_path)
    ddl_types = parse_ddl_types(ddl_path)
    result = copy.deepcopy(payload)
    targets = set()
    for table, source_columns in TABLE_COLUMNS.items():
        policy = result["tables"][table]
        _validate_policy(table, policy, source_columns, mysql_types.get(table, {}))
        if policy["target_table"] in targets:
            raise ValueError(f"{table}: duplicate target_table")
        targets.add(policy["target_table"])
        missing_types = set(source_columns) - set(ddl_types.get(table, {}))
        if missing_types:
            raise ValueError(f"{table}: DDL types missing for {', '.join(sorted(missing_types))}")
        policy["columns"] = [
            {"name": column, "type": ddl_types[table][column]} for column in source_columns
        ]
    return result


def _parse_date(value):
    try:
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise ValueError(f"Invalid business_date: {value}") from exc


def _parse_timestamp(name, value):
    if not isinstance(value, str) or not TIMESTAMP_PATTERN.fullmatch(value):
        raise ValueError(f"Invalid {name}: {value}; expected YYYY-MM-DD HH:MM:SS[.fff]")
    fmt = "%Y-%m-%d %H:%M:%S.%f" if "." in value else "%Y-%m-%d %H:%M:%S"
    try:
        parsed = datetime.strptime(value, fmt)
    except ValueError as exc:
        raise ValueError(f"Invalid {name}: {value}") from exc
    return parsed.isoformat(sep=" ", timespec="milliseconds" if "." in value else "seconds")


def _sql_literal(value):
    return "'" + value.replace("'", "''") + "'"


def _json_string(value):
    return json.dumps(str(value), ensure_ascii=False)[1:-1]


def _validate_hdfs_root(value):
    if not isinstance(value, str) or not re.fullmatch(r"/[A-Za-z0-9._/-]+", value):
        raise ValueError("ODS_STAGE_ROOT must be a scoped absolute HDFS path using safe path characters")
    path = PurePosixPath(value)
    if ".." in path.parts or path == PurePosixPath("/"):
        raise ValueError("ODS_STAGE_ROOT must be a scoped absolute HDFS path without '..'")
    return str(path).rstrip("/")


def build_where(policy, mode, window_start=None, window_end=None):
    if mode == "bootstrap":
        if window_start or window_end:
            raise ValueError("bootstrap mode must not receive an incremental window")
        return "1 = 1"
    if mode != "incremental":
        raise ValueError(f"Unknown extraction mode: {mode}")
    if policy["load_strategy"] == "full_snapshot":
        if window_start or window_end:
            raise ValueError("full_snapshot incremental mode must not receive a window")
        return "1 = 1"
    if not window_start or not window_end:
        raise ValueError("incremental mode requires window_start and window_end")
    start = _parse_timestamp("window_start", window_start)
    end = _parse_timestamp("window_end", window_end)
    if start >= end:
        raise ValueError("window_start must be earlier than window_end")
    watermark = policy["watermark_column"]
    return f"`{watermark}` >= {_sql_literal(start)} AND `{watermark}` < {_sql_literal(end)}"


def _business_date_expression(policy, business_date):
    business_time = policy["business_time"]
    if business_time["mode"] == "parameter":
        return _sql_literal(business_date)
    return f"DATE_FORMAT(`{business_time['column']}`, '%Y-%m-%d')"


def render_job(env, contract, table, mode, business_date, batch_id, extract_time,
               window_start=None, window_end=None):
    if not isinstance(table, str) or not IDENTIFIER_PATTERN.fullmatch(table) or table not in contract["tables"]:
        raise ValueError(f"Unknown ODS source table: {table}")
    if not isinstance(batch_id, str) or not BATCH_ID_PATTERN.fullmatch(batch_id):
        raise ValueError(f"Invalid batch_id: {batch_id}")
    business_date = _parse_date(business_date)
    extract_time = _parse_timestamp("extract_time", extract_time)
    policy = contract["tables"][table]
    where = build_where(policy, mode, window_start, window_end)
    source_select = [f"`{column['name']}`" for column in policy["columns"]]
    audit_select = [
        f"{_business_date_expression(policy, business_date)} AS `business_date`",
        f"{_sql_literal(extract_time)} AS `extract_time`",
        f"{_sql_literal(batch_id)} AS `batch_id`",
        f"{_sql_literal(policy['source_table'])} AS `source_table`",
    ]
    query = (
        "SELECT\n  "
        + ",\n  ".join(source_select + audit_select)
        + f"\nFROM `{policy['source_table']}`\nWHERE {where}"
    )
    stage_root = _validate_hdfs_root(env["ODS_STAGE_ROOT"])
    output_path = f"{stage_root}/{policy['target_table']}/batch_id={batch_id}"
    writer_columns = policy["columns"] + [
        {"name": name, "type": datax_type} for name, datax_type in AUDIT_COLUMNS
    ]
    values = {
        **env,
        "QUERY_SQL": query,
        "OUTPUT_PATH": output_path,
        "FILE_NAME": f"{table}_{batch_id}",
    }
    substitutions = {key: _json_string(value) for key, value in values.items()}
    substitutions["WRITER_COLUMNS"] = json.dumps(writer_columns, ensure_ascii=False, separators=(",", ":"))
    rendered = string.Template(TEMPLATE.read_text(encoding="utf-8")).substitute(substitutions)
    return json.dumps(json.loads(rendered), ensure_ascii=False, indent=2) + "\n"


def _is_relative_to(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def job_output_dir(env):
    project_home_value = env.get("PROJECT_HOME")
    if not project_home_value:
        raise ValueError("Missing required DataX config value: PROJECT_HOME")
    project_home = Path(project_home_value).expanduser()
    if not project_home.is_absolute():
        raise ValueError("PROJECT_HOME must be an absolute path")
    allowed_root = (project_home / "runtime/datax/jobs").resolve(strict=False)
    requested = Path(env.get("DATAX_JOB_DIR") or allowed_root).expanduser()
    if not requested.is_absolute():
        raise ValueError("DATAX_JOB_DIR must be an absolute path")
    resolved = requested.resolve(strict=False)
    if not _is_relative_to(resolved, allowed_root):
        raise ValueError("DATAX_JOB_DIR must stay within PROJECT_HOME/runtime/datax/jobs")
    return resolved


def write_private_job(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            descriptor = -1
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table", required=True)
    parser.add_argument("--mode", required=True, choices=("bootstrap", "incremental"))
    parser.add_argument("--business-date", required=True)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--extract-time", required=True)
    parser.add_argument("--window-start")
    parser.add_argument("--window-end")
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--env-file", type=Path)
    args = parser.parse_args(argv)
    env = load_env(args.env_file)
    result = render_job(
        env,
        load_contract(args.contract),
        args.table,
        args.mode,
        args.business_date,
        args.batch_id,
        args.extract_time,
        args.window_start,
        args.window_end,
    )
    outfile = job_output_dir(env) / f"{args.table}_{args.batch_id}.json"
    write_private_job(outfile, result)
    print(outfile)


if __name__ == "__main__":
    main()
