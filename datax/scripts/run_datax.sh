#!/usr/bin/env bash

set -euo pipefail

BASE_DIR=$(cd "$(dirname "$0")/.." && pwd)
ENV_FILE=${DATAX_ENV_FILE:-${BASE_DIR}/config/datax.env}

if [ ! -f "${ENV_FILE}" ]; then
  echo "ERROR: DataX config not found: ${ENV_FILE}" >&2
  echo "Copy ${BASE_DIR}/config/datax.env.example to ${BASE_DIR}/config/datax.env and fill private values." >&2
  exit 2
fi

source "${ENV_FILE}"

if [ $# -ne 1 ]; then
  echo "Usage: $0 <job.json>" >&2
  exit 1
fi

JOB_FILE=$1
if [ ! -f "${JOB_FILE}" ]; then
  echo "ERROR: job not found: ${JOB_FILE}" >&2
  exit 1
fi

mkdir -p "${DATAX_LOG_DIR}"
LOG_FILE=${DATAX_LOG_DIR}/$(basename "${JOB_FILE}").log

echo "================================="
echo "DataX Execute"
echo "JOB=${JOB_FILE}"
echo "LOG=${LOG_FILE}"
echo "================================="

if python3 "${DATAX_HOME}/bin/datax.py" "${JOB_FILE}" >"${LOG_FILE}" 2>&1; then
  echo "DataX SUCCESS"
else
  rc=$?
  echo "DataX FAILED" >&2
  exit "${rc}"
fi
