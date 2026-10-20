#!/usr/bin/env python3
"""Render a Spark job that blocks on Hive ADS and Doris row-level differences."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any


def load_contract(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def render_script(contract: dict[str, Any], start_date: str, end_date: str) -> str:
    """按显式闭区间比较全部 Contract 字段；任一方向存在差异即失败。"""
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    if start > end:
        raise ValueError("start_date must not exceed end_date")
    if contract.get("source") != "ecommerce_ads.ads_daily_business_overview":
        raise ValueError("unexpected serving source")
    target = f"{contract.get('database')}.{contract.get('table')}"
    if target != "ecommerce_serving.ads_daily_business_overview":
        raise ValueError("unexpected serving target")
    columns = [column[0] for column in contract.get("columns", [])]
    if not columns or columns[0] != "business_date" or len(columns) != 22:
        raise ValueError("serving columns drift")
    projection = ", ".join(f"`{column}`" for column in columns)
    return f'''#!/usr/bin/env python3
"""Generated Doris reconciliation; credentials are read only from environment."""
import os
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

required = ("DORIS_FENODES", "DORIS_USER", "DORIS_PASSWORD")
missing = [name for name in required if not os.environ.get(name)]
if missing:
    raise SystemExit("missing Doris environment variables: " + ",".join(missing))

spark = SparkSession.builder.appName("m6-doris-reconciliation-{start_date}-{end_date}").enableHiveSupport().getOrCreate()
try:
    hive = spark.sql("""SELECT {projection} FROM {contract['source']}
WHERE dt >= '{start_date}' AND dt <= '{end_date}'
  AND business_date >= DATE '{start_date}' AND business_date <= DATE '{end_date}'""")
    doris = (spark.read.format("doris")
      .option("doris.table.identifier", "{target}")
      .option("doris.fenodes", os.environ["DORIS_FENODES"])
      .option("user", os.environ["DORIS_USER"])
      .option("password", os.environ["DORIS_PASSWORD"])
      .option("doris.read.field", "{projection}")
      .load()
      .where("business_date >= DATE '{start_date}' AND business_date <= DATE '{end_date}'")
      .select({', '.join(repr(column) for column in columns)}))
    # Hive timestamp 保留微秒，而 Serving Contract 的 Doris DATETIME 只保留秒。
    # 对账统一到目标物理类型可表达的精度，其他业务列仍逐值严格比较。
    hive = hive.withColumn("load_time", F.date_trunc("second", F.col("load_time")))
    doris = doris.withColumn("load_time", F.date_trunc("second", F.col("load_time")))
    if hive.count() != {(end - start).days + 1} or doris.count() != {(end - start).days + 1}:
        raise RuntimeError("serving date coverage mismatch")
    hive_only = hive.exceptAll(doris)
    doris_only = doris.exceptAll(hive)
    hive_only_count = hive_only.count()
    doris_only_count = doris_only.count()
    if hive_only_count or doris_only_count:
        # 只输出业务日期和差异数量，既能定位批次边界，又不泄露凭据或业务明细。
        hive_only_dates = [str(row["business_date"]) for row in hive_only.select("business_date").orderBy("business_date").limit(10).collect()]
        doris_only_dates = [str(row["business_date"]) for row in doris_only.select("business_date").orderBy("business_date").limit(10).collect()]
        joined = hive.alias("h").join(doris.alias("d"), "business_date", "full")
        mismatch_columns = joined.agg(*[
            F.sum(
                F.when(
                    ~F.col(f"h.{{column}}").eqNullSafe(F.col(f"d.{{column}}")), 1
                ).otherwise(0)
            ).alias(column)
            for column in {columns[1:]!r}
        ]).first().asDict()
        mismatch_columns = {{
            column: count for column, count in mismatch_columns.items() if count
        }}
        raise RuntimeError(
            f"Hive and Doris rows differ: hive_only={{hive_only_count}} "
            f"doris_only={{doris_only_count}} hive_dates={{hive_only_dates}} "
            f"doris_dates={{doris_only_dates}} mismatch_columns={{mismatch_columns}}"
        )
    print("SERVING_RECONCILIATION_PASS")
finally:
    spark.stop()
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    script = render_script(load_contract(args.contract), args.start_date, args.end_date)
    if args.output:
        args.output.write_text(script, encoding="utf-8", newline="\n")
    else:
        print(script, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
