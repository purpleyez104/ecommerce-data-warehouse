#!/usr/bin/env python3
"""生成显式业务日的 Hive ADS → Doris Spark Writer 脚本。"""

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


def validate_runtime(contract: dict[str, Any], business_date: str, batch_id: str) -> None:
    """验证日期、批次及固定 Source/Target，避免运行时注入。"""
    date.fromisoformat(business_date)
    if not BATCH_ID.fullmatch(batch_id):
        raise ValueError("unsafe batch_id")
    if contract.get("source") != "ecommerce_ads.ads_daily_business_overview":
        raise ValueError("unexpected serving source")
    if f"{contract.get('database')}.{contract.get('table')}" != "ecommerce_serving.ads_daily_business_overview":
        raise ValueError("unexpected serving target")


def render_script(contract: dict[str, Any], business_date: str, batch_id: str) -> str:
    validate_runtime(contract, business_date, batch_id)
    columns = [column[0] for column in contract["columns"]]
    projection = ", ".join(f"`{column}`" for column in columns)
    return f'''#!/usr/bin/env python3
"""由 render_doris_load.py 生成；密码仅从环境变量读取。"""
import os
from pyspark.sql import SparkSession

required = ("DORIS_FENODES", "DORIS_USER", "DORIS_PASSWORD")
missing = [name for name in required if not os.environ.get(name)]
if missing:
    raise SystemExit("missing Doris environment variables: " + ",".join(missing))

spark = SparkSession.builder.appName("m6-doris-load-{business_date}-{batch_id}").enableHiveSupport().getOrCreate()
try:
    frame = spark.sql("""SELECT {projection}
FROM {contract['source']}
WHERE dt = '{business_date}' AND business_date = DATE '{business_date}'""")
    if frame.count() != 1:
        raise RuntimeError("expected exactly one ADS row for business_date")
    (frame.write.format("doris")
      .option("doris.table.identifier", "{contract['database']}.{contract['table']}")
      .option("doris.fenodes", os.environ["DORIS_FENODES"])
      .option("user", os.environ["DORIS_USER"])
      .option("password", os.environ["DORIS_PASSWORD"])
      .option("doris.sink.label-prefix", "m6_{business_date.replace('-', '')}_{batch_id}")
      .option("doris.sink.enable-2pc", "true")
      .mode("append")
      .save())
finally:
    spark.stop()
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--business-date", required=True)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    script = render_script(load_contract(args.contract), args.business_date, args.batch_id)
    if args.output:
        args.output.write_text(script, encoding="utf-8", newline="\n")
    else:
        print(script, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
