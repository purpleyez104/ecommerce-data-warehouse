#!/usr/bin/env python3

import argparse
import json
import os
import re
import string
from pathlib import Path


BASE = Path(__file__).resolve().parent.parent
TEMPLATE = BASE / "templates/mysql_to_hdfs_ods.json.tpl"

REQUIRED_ENV = (
    "MYSQL_JDBC_URL",
    "MYSQL_USER",
    "MYSQL_PASSWORD",
    "HDFS_DEFAULT_FS",
)
VARIABLE_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
TABLE_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


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

    unresolved = {
        variable
        for value in env.values()
        for variable in VARIABLE_PATTERN.findall(value)
    }
    if unresolved:
        names = ", ".join(sorted(unresolved))
        raise ValueError(f"Unresolved DataX config variables: {names}")

    return env


def load_env(env_file=None):
    path = Path(
        env_file
        or os.environ.get("DATAX_ENV_FILE", BASE / "config/datax.env")
    )

    if not path.is_file():
        raise FileNotFoundError(
            f"DataX config not found: {path}. "
            "Copy config/datax.env.example to config/datax.env and fill private values."
        )

    raw_env = {}
    with path.open(encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                raise ValueError(
                    f"Invalid DataX config line {line_number}: expected KEY=VALUE"
                )
            key, value = line.split("=", 1)
            key = key.strip()
            if not key:
                raise ValueError(
                    f"Invalid DataX config line {line_number}: empty key"
                )
            raw_env[key] = value.strip()

    env = _expand_env(raw_env)
    missing = [key for key in REQUIRED_ENV if not env.get(key)]
    if missing:
        raise ValueError(
            "Missing required DataX config values: " + ", ".join(missing)
        )
    if not env.get("DATAX_JOB_DIR") and not env.get("PROJECT_HOME"):
        raise ValueError(
            "Missing required DataX config value: DATAX_JOB_DIR or PROJECT_HOME"
        )

    return env


def _json_string(value):
    return json.dumps(str(value), ensure_ascii=False)[1:-1]


def render_job(env, table, where, output_path):
    if not TABLE_PATTERN.fullmatch(table):
        raise ValueError(f"Invalid table name: {table}")
    if not where.strip():
        raise ValueError("WHERE expression must not be empty")

    query = f"SELECT *\nFROM {table}\nWHERE {where.strip()}"
    values = {
        **env,
        "QUERY_SQL": query,
        "OUTPUT_PATH": output_path,
        "FILE_NAME": table,
    }
    escaped_values = {
        key: _json_string(value)
        for key, value in values.items()
    }

    template = TEMPLATE.read_text(encoding="utf-8")
    rendered = string.Template(template).substitute(escaped_values)
    payload = json.loads(rendered)
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def job_output_dir(env):
    configured = env.get("DATAX_JOB_DIR")
    if configured:
        return Path(configured)
    return Path(env["PROJECT_HOME"]) / "runtime/datax/jobs"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", required=True)
    parser.add_argument("--where", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    env = load_env()
    result = render_job(env, args.table, args.where, args.output)

    output_dir = job_output_dir(env)
    output_dir.mkdir(parents=True, exist_ok=True)
    outfile = output_dir / f"{args.table}.json"
    outfile.write_text(result, encoding="utf-8", newline="\n")
    print(outfile)


if __name__ == "__main__":
    main()
