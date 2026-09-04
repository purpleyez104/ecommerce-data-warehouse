#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  collect-hadoop-evidence.sh --run-id <safe-id> --output-dir <absolute-path>

Runs the non-disruptive Hadoop Milestone 1 smoke test from hadoop201 as yee.
USAGE
}

run_id=''
output_dir=''

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

if [[ -d $output_dir ]] && [[ -n $(find "$output_dir" -mindepth 1 -maxdepth 1 -print -quit) ]]; then
  printf 'output-dir already contains files: %s\n' "$output_dir" >&2
  exit 2
fi

umask 077
mkdir -p "$output_dir"
main_log="$output_dir/collect-hadoop-evidence.log"
summary_file="$output_dir/summary.env"
exec > >(tee -a "$main_log") 2>&1

hdfs_target="/tmp/ecommerce_data_warehouse/m1/$run_id"
local_tmp=''
hdfs_created=0

on_exit() {
  local exit_code=$1
  set +e

  if ((hdfs_created == 1)); then
    hdfs dfs -rm -r "$hdfs_target" >/dev/null 2>&1
  fi

  if [[ -n $local_tmp && -d $local_tmp ]]; then
    rm -rf -- "$local_tmp"
  fi

  if ((exit_code == 0)); then
    {
      printf 'status=PASS\n'
      printf 'run_id=%s\n' "$run_id"
      printf 'node=hadoop201\n'
      printf 'hdfs_target=%s\n' "$hdfs_target"
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
  exit 3
}

[[ $(hostname -s) == hadoop201 ]] || {
  printf 'This script must run on hadoop201; actual host: %s\n' "$(hostname -s)" >&2
  exit 3
}

for command_name in ssh java jps hadoop hdfs yarn sha256sum diff find awk grep sort tee \
  cp mktemp date hostname timedatectl readlink seq sleep; do
  command -v "$command_name" >/dev/null 2>&1 || {
    printf 'Required command is unavailable: %s\n' "$command_name" >&2
    exit 4
  }
done

: "${HADOOP_HOME:?HADOOP_HOME must be available to the non-interactive shell}"
examples_jar=$(find "$HADOOP_HOME/share/hadoop/mapreduce" -maxdepth 1 -type f \
  -name 'hadoop-mapreduce-examples-*.jar' -print -quit)
[[ -n $examples_jar ]] || {
  printf 'MapReduce examples jar was not found under %s\n' "$HADOOP_HOME/share/hadoop/mapreduce" >&2
  exit 4
}

printf 'run_id=%s\n' "$run_id"
printf 'started_at=%s\n' "$(date --iso-8601=seconds)"
printf 'host=%s\n' "$(hostname -f)"
printf 'user=%s\n' "$(id -un)"

{
  hostnamectl
  timedatectl
  java -version
  hadoop version
  jps -lv
} > "$output_dir/hadoop201-system.txt" 2>&1

for node in hadoop201 hadoop202 hadoop203; do
  node_log="$output_dir/$node-remote.txt"
  ssh -o BatchMode=yes -o ConnectTimeout=10 "$node" bash -s -- "$node" > "$node_log" 2>&1 <<'REMOTE'
set -euo pipefail
expected_node=$1
[[ $(hostname -s) == "$expected_node" ]]
printf 'host=%s\n' "$(hostname -s)"
printf 'user=%s\n' "$(id -un)"
printf 'time=%s\n' "$(date --iso-8601=seconds)"
java -version
jps -lv
for pid in $(jps | awk 'NR > 0 {print $1}'); do
  if [[ -e /proc/$pid/exe ]]; then
    printf 'pid=%s java=%s\n' "$pid" "$(readlink -f /proc/$pid/exe)"
  fi
done
REMOTE
done

hdfs dfsadmin -report > "$output_dir/hdfs-report.txt" 2>&1
yarn node -list -all > "$output_dir/yarn-nodes.txt" 2>&1

grep -Eq 'Live datanodes \(2\)' "$output_dir/hdfs-report.txt" || {
  printf '%s\n' 'Expected exactly 2 live DataNodes' >&2
  exit 5
}

grep -Eq 'Total Nodes:[[:space:]]*2' "$output_dir/yarn-nodes.txt" || {
  printf '%s\n' 'Expected exactly 2 YARN nodes' >&2
  exit 5
}

running_nodes=$(grep -Ec '[[:space:]]RUNNING([[:space:]]|$)' "$output_dir/yarn-nodes.txt" || true)
[[ $running_nodes -eq 2 ]] || {
  printf 'Expected 2 RUNNING NodeManagers; actual: %s\n' "$running_nodes" >&2
  exit 5
}

if hdfs dfs -test -e "$hdfs_target"; then
  printf 'Refusing to reuse existing HDFS target: %s\n' "$hdfs_target" >&2
  exit 6
fi

local_tmp=$(mktemp -d)
input_file="$local_tmp/input.txt"
expected_file="$local_tmp/expected.txt"
actual_file="$local_tmp/actual.txt"

printf 'alpha beta beta\ngamma alpha\n' > "$input_file"
printf 'alpha\t2\nbeta\t2\ngamma\t1\n' > "$expected_file"
local_hash=$(sha256sum "$input_file" | awk '{print $1}')

hdfs dfs -mkdir -p "$hdfs_target/input"
hdfs_created=1
hdfs dfs -put "$input_file" "$hdfs_target/input/input.txt"
hdfs_hash=$(hdfs dfs -cat "$hdfs_target/input/input.txt" | sha256sum | awk '{print $1}')

[[ $local_hash == "$hdfs_hash" ]] || {
  printf 'HDFS SHA-256 mismatch: local=%s hdfs=%s\n' "$local_hash" "$hdfs_hash" >&2
  exit 7
}

printf 'local_sha256=%s\n' "$local_hash" > "$output_dir/hdfs-checksum.env"
printf 'hdfs_sha256=%s\n' "$hdfs_hash" >> "$output_dir/hdfs-checksum.env"

mapreduce_log="$output_dir/mapreduce-wordcount.log"
set +e
hadoop jar "$examples_jar" wordcount \
  "$hdfs_target/input" "$hdfs_target/wordcount-output" 2>&1 | tee "$mapreduce_log"
mapreduce_exit=${PIPESTATUS[0]}
set -e

[[ $mapreduce_exit -eq 0 ]] || {
  printf 'MapReduce wordcount failed with exit code %s\n' "$mapreduce_exit" >&2
  exit "$mapreduce_exit"
}

hdfs dfs -cat "$hdfs_target/wordcount-output/part-*" | sort > "$actual_file"
diff -u "$expected_file" "$actual_file" | tee "$output_dir/wordcount-diff.txt"
cp "$actual_file" "$output_dir/wordcount-result.txt"

application_id=$(grep -Eo 'application_[0-9]+_[0-9]+' "$mapreduce_log" | tail -n 1)
[[ -n $application_id ]] || {
  printf '%s\n' 'YARN application ID was not found in MapReduce output' >&2
  exit 8
}

printf 'application_id=%s\n' "$application_id" > "$output_dir/yarn-application.env"
yarn application -status "$application_id" > "$output_dir/yarn-application-status.txt" 2>&1

set +e
yarn_logs_exit=1
for attempt in $(seq 1 6); do
  yarn logs -applicationId "$application_id" > "$output_dir/yarn-$application_id.log" 2>&1
  yarn_logs_exit=$?
  [[ $yarn_logs_exit -eq 0 ]] && break
  printf 'Waiting for aggregated YARN logs: attempt %s/6\n' "$attempt"
  sleep 5
done
set -e
[[ $yarn_logs_exit -eq 0 ]] || {
  printf 'Unable to collect aggregated YARN logs after retries; exit code: %s\n' \
    "$yarn_logs_exit" >&2
  exit 9
}

hdfs dfs -rm -r "$hdfs_target"
hdfs_created=0
hdfs dfs -test -e "$hdfs_target" && {
  printf 'HDFS smoke target still exists after cleanup: %s\n' "$hdfs_target" >&2
  exit 10
}

printf 'completed_at=%s\n' "$(date --iso-8601=seconds)"
printf '%s\n' 'Hadoop non-disruptive evidence collection passed.'
