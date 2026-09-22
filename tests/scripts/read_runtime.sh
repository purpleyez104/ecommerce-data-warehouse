#!/usr/bin/env bash
# 只读环境核对。参数: <application-id> <job-id> <jm-host:port> [topic]
set -euo pipefail
if [[ $# -lt 3 || $# -gt 4 ]];then echo 'usage: bash read_runtime.sh <application-id> <job-id> <jm-host:port> [topic]' >&2;exit 2;fi
APP=$1;JOB=$2;JM=$3;TOPIC=${4:-cdc_m2_21tables_acceptance}
[[ $APP =~ ^application_[0-9]+_[0-9]+$ && $JOB =~ ^[0-9a-f]{32}$ && $JM =~ ^[A-Za-z0-9.-]+:[0-9]+$ && $TOPIC =~ ^[A-Za-z0-9._-]+$ ]] || { echo 'invalid arguments' >&2;exit 2; }
echo '=== YARN ==='
yarn application -status "$APP" | grep -E 'State :|Final-State :|AM Host :|Diagnostics :' || true
echo '=== Flink Job ==='
curl -fsS "http://$JM/jobs/overview" | python3 -c 'import sys,json; [(print(j["jid"],j["state"],j["tasks"])) for j in json.load(sys.stdin).get("jobs",[])]'
echo '=== Checkpoints ==='
curl -fsS "http://$JM/jobs/$JOB/checkpoints" | python3 -c 'import sys,json;d=json.load(sys.stdin);print("counts:",d.get("counts"));print("last:",(d.get("latest",{}).get("completed") or {}).get("id"))'
echo '=== Kafka offsets ==='
kafka-get-offsets.sh --bootstrap-server hadoop201:9092 --topic "$TOPIC" --time -1
