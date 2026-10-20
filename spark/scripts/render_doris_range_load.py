#!/usr/bin/env python3
"""生成显式日期范围的 Hive ADS → Doris Spark Writer 脚本。"""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Any


BATCH_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}$")


def load_contract(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def validate_runtime(contract: dict[str, Any], start_date: str, end_date: str, batch_id: str) -> int:
    """验证闭区间、批次和固定 Source/Target，并返回期望业务日数。"""
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    if start > end:
        raise ValueError("start_date must not exceed end_date")
    if not BATCH_ID.fullmatch(batch_id):
        raise ValueError("unsafe batch_id")
    if contract.get("source") != "ecommerce_ads.ads_daily_business_overview":
        raise ValueError("unexpected serving source")
    if f"{contract.get('database')}.{contract.get('table')}" != "ecommerce_serving.ads_daily_business_overview":
        raise ValueError("unexpected serving target")
    return (end - start).days + 1


def render_script(contract: dict[str, Any], start_date: str, end_date: str, batch_id: str) -> str:
    expected_days = validate_runtime(contract, start_date, end_date, batch_id)
    projection = ", ".join(f"`{column[0]}`" for column in contract["columns"])
    compact_range = f"{start_date.replace('-', '')}_{end_date.replace('-', '')}"
    return f'''#!/usr/bin/env python3
"""由 render_doris_range_load.py 生成；密码仅从环境变量读取。"""
import os
from pyspark.sql import SparkSession

required = ("DORIS_FENODES", "DORIS_USER", "DORIS_PASSWORD")
missing = [name for name in required if not os.environ.get(name)]
if missing:
    raise SystemExit("missing Doris environment variables: " + ",".join(missing))

spark = SparkSession.builder.appName("m6-doris-range-{compact_range}-{batch_id}").enableHiveSupport().getOrCreate()
try:
    frame = spark.sql("""SELECT {projection}
FROM {contract['source']}
WHERE dt >= '{start_date}' AND dt <= '{end_date}'
  AND business_date >= DATE '{start_date}' AND business_date <= DATE '{end_date}'""")
    row_count = frame.count()
    distinct_days = frame.select("business_date").distinct().count()
    if row_count != {expected_days} or distinct_days != {expected_days}:
        raise RuntimeError(f"expected {expected_days} rows and dates, got rows={{row_count}}, dates={{distinct_days}}")
    (frame.write.format("doris")
      .option("doris.table.identifier", "{contract['database']}.{contract['table']}")
      .option("doris.fenodes", os.environ["DORIS_FENODES"])
      .option("user", os.environ["DORIS_USER"])
      .option("password", os.environ["DORIS_PASSWORD"])
      .option("doris.sink.label-prefix", "m6_{compact_range}_{batch_id}")
      .option("doris.sink.enable-2pc", "true")
      .mode("append")
      .save())
finally:
    spark.stop()
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    script = render_script(load_contract(args.contract), args.start_date, args.end_date, args.batch_id)
    if args.output:
        args.output.write_text(script, encoding="utf-8", newline="\n")
    else:
        print(script, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
