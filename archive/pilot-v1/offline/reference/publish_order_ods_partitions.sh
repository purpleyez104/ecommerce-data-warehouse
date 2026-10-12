#!/usr/bin/env bash

set -euo pipefail

readonly EXPECTED_PARTITION_COUNT=87
readonly PILOT_PARTITION='2026-09-17'

usage() {
  cat >&2 <<'EOF'
Usage:
  publish_order_ods_partitions.sh <source_root> <target_root> <partition_manifest>

The manifest must contain exactly 87 unique yyyy-MM-dd values, one per line.
This script reconstructs the remaining hist-v1-001 HDFS partition moves only.
It does not register Hive partitions.
EOF
}

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

if [[ $# -ne 3 ]]; then
  usage
  exit 2
fi

source_root=${1%/}
target_root=${2%/}
manifest_file=$3

for required_command in hdfs date; do
  command -v "${required_command}" >/dev/null 2>&1 \
    || fail "required command not found: ${required_command}"
done

for path_name in source_root target_root; do
  path_value=${!path_name}
  [[ "${path_value}" == /* ]] || fail "${path_name} must be an absolute HDFS path"
  [[ "${path_value}" != "/" ]] || fail "${path_name} must not be the HDFS root"
  [[ "${path_value}" != *$'\n'* && "${path_value}" != *$'\r'* ]] \
    || fail "${path_name} contains a newline"
done

[[ "${source_root}" != "${target_root}" ]] \
  || fail "source_root and target_root must differ"
[[ -f "${manifest_file}" ]] || fail "partition manifest not found: ${manifest_file}"

mapfile -t manifest_lines < "${manifest_file}"
[[ ${#manifest_lines[@]} -eq ${EXPECTED_PARTITION_COUNT} ]] \
  || fail "partition manifest must contain exactly ${EXPECTED_PARTITION_COUNT} lines"

declare -A seen_partitions=()
declare -a partitions=()

for raw_partition in "${manifest_lines[@]}"; do
  partition=${raw_partition%$'\r'}
  [[ "${partition}" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] \
    || fail "invalid partition value: ${partition}"

  normalized_partition=$(date -d "${partition}" +%F 2>/dev/null) \
    || fail "invalid calendar date: ${partition}"
  [[ "${normalized_partition}" == "${partition}" ]] \
    || fail "non-canonical partition date: ${partition}"
  [[ "${partition}" != "${PILOT_PARTITION}" ]] \
    || fail "pilot partition must not be republished: ${partition}"
  [[ -z "${seen_partitions[${partition}]+x}" ]] \
    || fail "duplicate partition date: ${partition}"

  seen_partitions[${partition}]=1
  partitions+=("${partition}")
done

hdfs dfs -test -d "${source_root}" \
  || fail "source root does not exist: ${source_root}"
hdfs dfs -test -d "${target_root}" \
  || fail "target root does not exist: ${target_root}"

# Complete every destructive precondition before the first move.
for partition in "${partitions[@]}"; do
  source_partition="${source_root}/dt=${partition}"
  target_partition="${target_root}/dt=${partition}"

  hdfs dfs -test -d "${source_partition}" \
    || fail "source partition does not exist: ${source_partition}"
  if hdfs dfs -test -e "${target_partition}"; then
    fail "target partition already exists: ${target_partition}"
  fi
done

echo "PRECHECK PASS: ${EXPECTED_PARTITION_COUNT} partitions are safe to move"

for partition in "${partitions[@]}"; do
  source_partition="${source_root}/dt=${partition}"
  target_partition="${target_root}/dt=${partition}"

  hdfs dfs -mv "${source_partition}" "${target_partition}"
  if hdfs dfs -test -e "${source_partition}"; then
    fail "source still exists after move: ${source_partition}"
  fi
  hdfs dfs -test -d "${target_partition}" \
    || fail "target missing after move: ${target_partition}"
done

echo "PUBLISH PASS: moved ${EXPECTED_PARTITION_COUNT} hist-v1-001 partitions"
echo "NEXT: register and verify Hive partitions with the separately reviewed command"
