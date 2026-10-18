#!/usr/bin/env bash
set -euo pipefail

# 按业务日交替推进 Source Replay 与 ODS；任一日未通过即停止，已提交日通过
# result/state 证据识别并跳过，避免从固定首日重复写入。
if [[ $# -ne 2 ]]; then
  echo "Usage: $0 <start-day> <end-day>" >&2
  exit 2
fi

start_day=$1
end_day=$2
for value in "$start_day" "$end_day"; do
  [[ $value =~ ^(6[1-9]|[78][0-9]|90)$ ]] || {
    echo "Day must be between 61 and 90: $value" >&2
    exit 2
  }
done
(( start_day <= end_day )) || {
  echo "start-day must not exceed end-day" >&2
  exit 2
}

required=(
  SOURCE_REPLAY_BUNDLE SOURCE_OUTPUT_ROOT ODS_PROJECT_HOME ODS_REMOTE_HOST
  ODS_TARGET_DATABASE ODS_STAGE_ROOT DATAX_ENV_FILE
)
for name in "${required[@]}"; do
  [[ -n ${!name:-} ]] || {
    echo "Missing required environment variable: $name" >&2
    exit 2
  }
done

script_root=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source_executor=${SOURCE_EXECUTOR:-"$script_root/../../mysql/scripts/execute_replay_daily_package.py"}
checkpoint_root=${RANGE_CHECKPOINT_ROOT:-"$SOURCE_OUTPUT_ROOT/ods-range-${start_day}-${end_day}"}
mkdir -p "$checkpoint_root"

for day in $(seq "$start_day" "$end_day"); do
  day_name=$(printf 'day_%02d' "$day")
  source_output="$SOURCE_OUTPUT_ROOT/source-${day_name}"
  source_result="$source_output/result.json"

  if [[ -f $source_result ]]; then
    python3 - "$source_result" "$day" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], encoding="utf-8"))
day = int(sys.argv[2])
if payload.get("status") != "executed" or payload.get("day_number") != day or payload.get("violation_count") != 0:
    raise SystemExit(f"invalid existing Source result for day {day}")
PY
  elif [[ -e $source_output ]]; then
    echo "Incomplete Source output exists: $source_output" >&2
    exit 1
  else
    python3 "$source_executor" \
      --replay-bundle "$SOURCE_REPLAY_BUNDLE" \
      --day "$day" \
      --output "$source_output" \
      --execute \
      --confirm-day "$day"
  fi

  contract="$ODS_PROJECT_HOME/replay-bundle/daily/$day_name/ods_batch_contract.json"
  ods_output="$ODS_PROJECT_HOME/runtime/ods/${day_name}-incremental"
  ssh -o BatchMode=yes "$ODS_REMOTE_HOST" bash -s -- \
    "$ODS_PROJECT_HOME" "$contract" "$ods_output" "$ODS_STAGE_ROOT" \
    "$ODS_TARGET_DATABASE" "$DATAX_ENV_FILE" <<'REMOTE'
set -euo pipefail
project_home=$1
contract=$2
output=$3
stage_root=$4
target_database=$5
env_file=$6
state_file="$output/state.json"

if [[ -f $state_file ]]; then
  python3 - "$state_file" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], encoding="utf-8"))
if payload.get("state") != "published" or payload.get("publish_allowed") is not True:
    raise SystemExit(f"existing ODS output is not published: {sys.argv[1]}")
PY
elif [[ -e $output ]]; then
  echo "Incomplete ODS output exists: $output" >&2
  exit 1
else
  cd "$project_home"
  python3 datax/scripts/run_ods_batch.py \
    --batch-contract "$contract" \
    --output-dir "$output" \
    --project-home "$project_home" \
    --stage-root "$stage_root" \
    --target-database "$target_database" \
    --execute \
    --env-file "$env_file" \
    --spark-sql /data/module/spark/bin/spark-sql
fi
REMOTE

  printf '%s\tverified\n' "$day" > "$checkpoint_root/$day_name.checkpoint"
done

printf '{"status":"verified","start_day":%s,"end_day":%s}\n' "$start_day" "$end_day" \
  > "$checkpoint_root/range-state.json"
