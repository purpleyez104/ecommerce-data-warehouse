#!/usr/bin/env bash
set -euo pipefail

repo=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

if command -v python3 >/dev/null 2>&1 && python3 --version >/dev/null 2>&1; then
  python_bin=python3
elif command -v python >/dev/null 2>&1 && python --version >/dev/null 2>&1; then
  python_bin=python
else
  echo "ERROR: Python 3 is required" >&2
  exit 2
fi

cd "$repo"

PYTHONPATH="$repo/mock/generator/business_generator/src${PYTHONPATH:+:$PYTHONPATH}" \
  "$python_bin" -m unittest discover \
  -s mock/generator/business_generator/tests -p 'test_*.py' -v

PYTHONPATH="$repo/mock/generator/business_generator/src${PYTHONPATH:+:$PYTHONPATH}" \
  "$python_bin" -m py_compile \
  mock/generator/business_generator/src/business_generator/replay.py \
  mysql/scripts/plan_replay_bootstrap.py \
  mysql/scripts/replay_daily_package.py \
  mysql/scripts/execute_replay_daily_package.py \
  datax/scripts/run_ods_batch.py \
  datax/scripts/generate_ods_target_expectations.py \
  hive/ods/generate_behavior_ods_ddl.py \
  hive/model/generate_aggregate_ddl.py \
  hive/model/generate_model_ddl.py \
  hive/model/validate_model_contract.py \
  governance/metric_registry/validate_metric_registry.py \
  quality/generate_quality_result_ddl.py \
  reconciliation/generate_reconciliation_result_ddl.py \
  spark/scripts/render_ods_batch_sql.py \
  spark/scripts/render_behavior_ods_sql.py \
  spark/scripts/render_dim_snapshot_sql.py \
  spark/scripts/render_product_scd2_sql.py \
  spark/scripts/render_dwd_sql.py \
  spark/scripts/render_model_gate_sql.py \
  spark/scripts/render_aggregate_sql.py \
  spark/scripts/render_aggregate_gate_sql.py \
  spark/scripts/render_quality_result_sql.py \
  spark/scripts/render_cross_layer_reconciliation_sql.py

PYTHONPATH="$repo/mock/generator/behavior_generator/src${PYTHONPATH:+:$PYTHONPATH}" \
  "$python_bin" -m unittest discover \
  -s mock/generator/behavior_generator/tests -p 'test_*.py' -v

PYTHONPATH="$repo/mock/generator/behavior_generator/src${PYTHONPATH:+:$PYTHONPATH}" \
  "$python_bin" -m py_compile \
  mock/generator/behavior_generator/src/behavior_generator/replay.py

"$python_bin" -m unittest discover -s tests/datax -p 'test_*.py' -v

"$python_bin" -m unittest discover -s tests/model -p 'test_*.py' -v

"$python_bin" -m unittest discover -s tests/governance -p 'test_*.py' -v

"$python_bin" -m unittest discover -s tests/quality -p 'test_*.py' -v

"$python_bin" -m unittest discover -s tests/reconciliation -p 'test_*.py' -v

PYTHONPATH="$repo/mock/generator/business_generator/src${PYTHONPATH:+:$PYTHONPATH}" \
  "$python_bin" -m unittest discover -s tests/mysql -p 'test_*.py' -v
