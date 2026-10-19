#!/usr/bin/env python3
"""将 Aggregate Gate 结果持久化，并在写入后阻断失败运行。"""

from __future__ import annotations

import argparse
import importlib.util
import re
from pathlib import Path


SAFE_VALUE = re.compile(r"^[A-Za-z0-9._-]+$")
ASSERTION = re.compile(r"^SELECT assert_true\(\((.+)\), '([^']+)'\);$")


def _load_aggregate_gate_module():
    """从同目录加载唯一的 Aggregate Gate 实现，避免复制规则 SQL。"""
    path = Path(__file__).with_name("render_aggregate_gate_sql.py")
    spec = importlib.util.spec_from_file_location("aggregate_gate_for_quality", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load aggregate gate renderer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def aggregate_rules() -> list[tuple[str, str]]:
    """解析 Gate 的布尔查询与 Rule ID；最终 PASS 哨兵不是业务规则。"""
    rules: list[tuple[str, str]] = []
    for line in _load_aggregate_gate_module().render_sql().splitlines():
        match = ASSERTION.fullmatch(line)
        if match and match.group(2) != "AGGREGATE_GATE_PASS":
            rules.append((match.group(2), match.group(1)))
    if len(rules) != 40:
        raise ValueError(f"expected 40 aggregate quality rules, found {len(rules)}")
    return rules


def _literal(value: str, name: str) -> str:
    if not SAFE_VALUE.fullmatch(value):
        raise ValueError(f"unsafe {name}: {value}")
    return f"'{value}'"


def render_sql(run_id: str, batch_id: str) -> str:
    """按 run_id 幂等覆盖结果；先落盘，再断言 FAIL 数为零。"""
    run_literal = _literal(run_id, "run_id")
    batch_literal = _literal(batch_id, "batch_id")
    selects = []
    for rule_id, query in aggregate_rules():
        target_object, rule_type = rule_id.split(".", 1)
        # 每条规则返回布尔实际值，便于统一保存结构且不重写现有 Gate 逻辑。
        selects.append(f"""SELECT
  '{rule_id}' AS rule_id,
  '{target_object}' AS target_object,
  CAST(NULL AS DATE) AS business_date,
  '{rule_type}' AS rule_type,
  'true' AS expected_value,
  CAST(rule_passed AS STRING) AS actual_value,
  CASE WHEN rule_passed THEN 'PASS' ELSE 'FAIL' END AS status,
  {batch_literal} AS batch_id,
  current_timestamp() AS executed_at
FROM ({query}) quality_rule(rule_passed)""")
    union_sql = "\nUNION ALL\n".join(selects)
    return f"""SET spark.sql.ansi.enabled=true;
SET spark.sql.sources.partitionOverwriteMode=dynamic;

INSERT OVERWRITE TABLE ecommerce_quality.data_quality_result PARTITION (run_id={run_literal})
{union_sql};

SELECT assert_true(
  (SELECT COUNT(*)=40 FROM ecommerce_quality.data_quality_result WHERE run_id={run_literal}),
  'data_quality_result.rule_count'
);
SELECT assert_true(
  (SELECT COUNT(*)=0 FROM ecommerce_quality.data_quality_result WHERE run_id={run_literal} AND status='FAIL'),
  'data_quality_result.no_failures'
);
SELECT 'QUALITY_RESULT_GATE_PASS';
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    sql = render_sql(args.run_id, args.batch_id)
    if args.output:
        args.output.write_text(sql, encoding="utf-8", newline="\n")
    else:
        print(sql, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
