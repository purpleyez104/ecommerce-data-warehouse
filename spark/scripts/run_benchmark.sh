#!/usr/bin/env bash
set -euo pipefail

# 在已完成 Setup 与 Smoke Gate 后执行固定的 3 次测量，并直接解析 Spark Event Log。
repo=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
dataset_version=m7-spark-20261020-r1
contract="${repo}/spark/benchmark/benchmark_contract.json"
renderer="${repo}/spark/scripts/render_benchmark_sql.py"
collector="${repo}/spark/scripts/collect_spark_event_metrics.py"
spark_sql=${SPARK_SQL_BIN:-/data/module/spark/bin/spark-sql}
hdfs_bin=${HDFS_BIN:-/data/module/hadoop/bin/hdfs}
history_root=${SPARK_HISTORY_ROOT:-/spark/history}
smoke_root="${repo}/runtime/benchmark/${dataset_version}/smoke"
run_root="${repo}/runtime/benchmark/${dataset_version}/measured"
manifest="${run_root}/manifest.tsv"

variants=(
  "partition_pruning baseline"
  "partition_pruning optimized"
  "join_strategy sort_merge"
  "join_strategy broadcast"
  "skew_aggregation single_stage"
  "skew_aggregation two_stage"
)

mkdir -p "${run_root}"
printf 'run_index\texperiment\tvariant\tapplication_id\tresult\tmetrics_file\n' >"${manifest}"

declare -A expected_results
for specification in "${variants[@]}"; do
  read -r experiment variant <<<"${specification}"
  smoke_log="${smoke_root}/${experiment}__${variant}.log"
  if [[ ! -f "${smoke_log}" ]]; then
    echo "M7_MEASURED_FAIL missing smoke log: ${smoke_log}" >&2
    exit 20
  fi
  result=$(grep '^M7_RESULT' "${smoke_log}" | tail -n 1 || true)
  if [[ -z "${result}" ]]; then
    echo "M7_MEASURED_FAIL missing smoke result: ${smoke_log}" >&2
    exit 21
  fi
  if [[ -n "${expected_results[${experiment}]:-}" && "${expected_results[${experiment}]}" != "${result}" ]]; then
    echo "M7_MEASURED_FAIL smoke variants are not equivalent: ${experiment}" >&2
    exit 22
  fi
  expected_results[${experiment}]="${result}"
done

for run_index in 1 2 3; do
  for specification in "${variants[@]}"; do
    read -r experiment variant <<<"${specification}"
    stem="run-${run_index}__${experiment}__${variant}"
    sql_file="${run_root}/${stem}.sql"
    log_file="${run_root}/${stem}.log"
    event_file="${run_root}/${stem}.eventlog.json"
    metrics_file="${run_root}/${stem}.metrics.json"

    python3 "${renderer}" \
      --contract "${contract}" \
      --mode query \
      --experiment "${experiment}" \
      --variant "${variant}" \
      --output "${sql_file}"

    if ! "${spark_sql}" --master yarn --name "m7-${stem}" \
        -f "${sql_file}" >"${log_file}" 2>&1; then
      echo "M7_MEASURED_FAIL Spark SQL failed: ${stem}" >&2
      tail -n 120 "${log_file}" >&2
      exit 23
    fi

    application_id=$(grep -oE 'application_[0-9]+_[0-9]+' "${log_file}" | head -n 1 || true)
    result=$(grep '^M7_RESULT' "${log_file}" | tail -n 1 || true)
    if [[ -z "${application_id}" || "${result}" != "${expected_results[${experiment}]}" ]]; then
      echo "M7_MEASURED_FAIL evidence or result mismatch: ${stem}" >&2
      exit 24
    fi

    "${hdfs_bin}" dfs -cat "${history_root}/${application_id}" >"${event_file}"
    python3 "${collector}" \
      --event-log "${event_file}" \
      --experiment "${experiment}" \
      --variant "${variant}" \
      --run-index "${run_index}" \
      --measured \
      --output "${metrics_file}"

    printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
      "${run_index}" "${experiment}" "${variant}" "${application_id}" \
      "${result}" "${metrics_file}" >>"${manifest}"
  done
done

echo "M7_MEASURED_PASS runs=18 manifest=${manifest}"
