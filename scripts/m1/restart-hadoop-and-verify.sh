#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  restart-hadoop-and-verify.sh \
    --run-id <safe-id> \
    --output-dir <absolute-path> \
    --confirm-restart EXISTING_HADOOP_CLUSTER

Stops and restarts the existing HDFS, YARN, and JobHistoryServer services.
Run only after the non-disruptive Hadoop smoke test has passed and been reviewed.
USAGE
}

run_id=''
output_dir=''
confirmation=''

while (($# > 0)); do
  case "$1" in
    --run-id)
      [[ $# -ge 2 ]] || { usage >&2; exit 2; }
      run_id=$2
      shift 2
      ;;
    --output-dir)
      [[ $# -ge 2 ]] || { usage >&2; exit 2; }
      output_dir=$2
      shift 2
      ;;
    --confirm-restart)
      [[ $# -ge 2 ]] || { usage >&2; exit 2; }
      confirmation=$2
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

[[ $run_id =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$ ]] || {
  printf '%s\n' 'run-id must match [A-Za-z0-9][A-Za-z0-9._-]{0,79}' >&2
  exit 2
}

case "$output_dir" in
  /*) ;;
  *)
    printf '%s\n' 'output-dir must be an absolute path' >&2
    exit 2
    ;;
esac

[[ $output_dir != / && $output_dir != /data ]] || {
  printf '%s\n' 'output-dir is too broad' >&2
  exit 2
}

[[ $confirmation == EXISTING_HADOOP_CLUSTER ]] || {
  printf '%s\n' 'Confirmation mismatch; no service action was taken.' >&2
  exit 3
}

if [[ -d $output_dir ]] && [[ -n $(find "$output_dir" -mindepth 1 -maxdepth 1 -print -quit) ]]; then
  printf 'output-dir already contains files: %s\n' "$output_dir" >&2
  exit 2
fi

umask 077
mkdir -p "$output_dir"
main_log="$output_dir/restart-hadoop-and-verify.log"
summary_file="$output_dir/summary.env"
exec > >(tee -a "$main_log") 2>&1

hdfs_target="/tmp/ecommerce_data_warehouse/m1/$run_id"
hdfs_created=0
cluster_stopped=0
cluster_restored=0

attempt_recovery() {
  set +e
  start-dfs.sh
  start-yarn.sh
  mapred --daemon start historyserver
  set -e
}

on_exit() {
  local exit_code=$1
  set +e

  if ((cluster_stopped == 1 && cluster_restored == 0)); then
    printf '%s\n' 'Attempting best-effort Hadoop service recovery after failure.'
    attempt_recovery
  fi

  if ((hdfs_created == 1)); then
    hdfs dfs -rm -r "$hdfs_target" >/dev/null 2>&1
  fi

  if ((exit_code == 0)); then
    {
      printf 'status=PASS\n'
      printf 'run_id=%s\n' "$run_id"
      printf 'node=hadoop201\n'
    } > "$summary_file"
  else
    {
      printf 'status=FAIL\n'
      printf 'run_id=%s\n' "$run_id"
      printf 'node=%s\n' "$(hostname -s 2>/dev/null || printf unknown)"
      printf 'exit_code=%s\n' "$exit_code"
      printf 'log=%s\n' "$main_log"
    } > "$summary_file"
  fi

  exit "$exit_code"
}
trap 'on_exit $?' EXIT

[[ $(id -un) == yee ]] || {
  printf 'This script must run as yee; actual user: %s\n' "$(id -un)" >&2
  exit 4
}

[[ $(hostname -s) == hadoop201 ]] || {
  printf 'This script must run on hadoop201; actual host: %s\n' "$(hostname -s)" >&2
  exit 4
}

for command_name in hdfs yarn jps sha256sum awk grep tee start-dfs.sh stop-dfs.sh \
  start-yarn.sh stop-yarn.sh mapred seq sleep date hostname; do
  command -v "$command_name" >/dev/null 2>&1 || {
    printf 'Required command is unavailable: %s\n' "$command_name" >&2
    exit 5
  }
done

if hdfs dfs -test -e "$hdfs_target"; then
  printf 'Refusing to reuse existing HDFS target: %s\n' "$hdfs_target" >&2
  exit 6
fi

sentinel='existing-hadoop-restart-sentinel-v1'
sentinel_hash=$(printf '%s\n' "$sentinel" | sha256sum | awk '{print $1}')
hdfs dfs -mkdir -p "$hdfs_target"
hdfs_created=1
printf '%s\n' "$sentinel" | hdfs dfs -put - "$hdfs_target/sentinel.txt"

{
  printf 'captured_at=%s\n' "$(date --iso-8601=seconds)"
  jps -lv
  hdfs dfsadmin -report
  yarn node -list -all
} > "$output_dir/before-restart.txt" 2>&1

printf '%s\n' 'Stopping JobHistoryServer, YARN, and HDFS.'
cluster_stopped=1
mapred --daemon stop historyserver
stop-yarn.sh
stop-dfs.sh

printf '%s\n' 'Starting HDFS, YARN, and JobHistoryServer.'
start-dfs.sh
start-yarn.sh
mapred --daemon start historyserver

for attempt in $(seq 1 18); do
  hdfs_report=$(hdfs dfsadmin -report 2>&1 || true)
  yarn_nodes=$(yarn node -list -all 2>&1 || true)
  if grep -Eq 'Live datanodes \(2\)' <<< "$hdfs_report" && \
      grep -Eq 'Total Nodes:[[:space:]]*2' <<< "$yarn_nodes" && \
      [[ $(grep -Ec '[[:space:]]RUNNING([[:space:]]|$)' <<< "$yarn_nodes" || true) -eq 2 ]]; then
    cluster_restored=1
    break
  fi
  printf 'Waiting for cluster recovery: attempt %s/18\n' "$attempt"
  sleep 5
done

((cluster_restored == 1)) || {
  printf '%s\n' 'Hadoop topology did not recover within 90 seconds.' >&2
  exit 7
}

{
  printf 'captured_at=%s\n' "$(date --iso-8601=seconds)"
  jps -lv
  hdfs dfsadmin -report
  yarn node -list -all
} > "$output_dir/after-restart.txt" 2>&1

for expected_process in NameNode SecondaryNameNode ResourceManager JobHistoryServer; do
  grep -Eq "[[:space:]]$expected_process([[:space:]]|$)" "$output_dir/after-restart.txt" || {
    printf 'Expected process is missing on hadoop201: %s\n' "$expected_process" >&2
    exit 8
  }
done

actual_hash=$(hdfs dfs -cat "$hdfs_target/sentinel.txt" | sha256sum | awk '{print $1}')
[[ $sentinel_hash == "$actual_hash" ]] || {
  printf 'Restart sentinel SHA-256 mismatch: expected=%s actual=%s\n' \
    "$sentinel_hash" "$actual_hash" >&2
  exit 9
}

{
  printf 'expected_sha256=%s\n' "$sentinel_hash"
  printf 'actual_sha256=%s\n' "$actual_hash"
} > "$output_dir/restart-sentinel.env"

hdfs dfs -rm -r "$hdfs_target"
hdfs_created=0
hdfs dfs -test -e "$hdfs_target" && {
  printf 'HDFS restart target still exists after cleanup: %s\n' "$hdfs_target" >&2
  exit 10
}

printf 'completed_at=%s\n' "$(date --iso-8601=seconds)"
printf '%s\n' 'Hadoop controlled restart verification passed.'
