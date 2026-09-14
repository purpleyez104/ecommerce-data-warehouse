#!/usr/bin/env bash
# Shared safety and evidence helpers for Milestone 1 component acceptance.
# This library deliberately contains no component-specific commands or cleanup.

set -euo pipefail

readonly EVIDENCE_SCHEMA_VERSION=1
readonly EVIDENCE_DEFAULT_OUTPUT_ROOT='/data/logs/ecommerce-data-warehouse/m1'

EVIDENCE_COMPONENT=''
EVIDENCE_RUN_ID=''
EVIDENCE_OUTPUT_ROOT=''
EVIDENCE_RUN_DIR=''
EVIDENCE_STARTED_AT_UTC=''
EVIDENCE_STEP_NUMBER=0
EVIDENCE_STATUS='PASS'
EVIDENCE_REQUIRED_FAILURES=0
EVIDENCE_FINALIZED=0
declare -a EVIDENCE_CLEANUP_HANDLERS=()
declare -a EVIDENCE_CLEANUP_TARGETS=()
declare -a EVIDENCE_CLEANUP_OWNERS=()
declare -A EVIDENCE_SUMMARY=()

evidence_error() {
  printf '%s\n' "$*" >&2
}

evidence_require_initialized() {
  [[ -n $EVIDENCE_RUN_DIR ]] || {
    evidence_error 'Evidence library is not initialized.'
    return 2
  }
}

evidence_is_safe_run_id() {
  local run_id=$1
  [[ $run_id =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]]
}

evidence_is_safe_component() {
  local component=$1
  [[ $component =~ ^[a-z][a-z0-9_]*$ ]]
}

evidence_is_safe_output_root() {
  local output_root=$1
  local resolved_root

  [[ $output_root == /* ]] || return 1
  [[ $output_root != *'..'* ]] || return 1
  resolved_root=$(readlink -m -- "$output_root") || return 1
  [[ $resolved_root != / && $resolved_root != /data ]] || return 1
  printf '%s\n' "$resolved_root"
}

evidence_init() {
  local component=$1
  local run_id=$2
  local output_root=${3:-$EVIDENCE_DEFAULT_OUTPUT_ROOT}
  local resolved_root run_dir

  evidence_is_safe_component "$component" || {
    evidence_error "Invalid component name: $component"
    return 2
  }
  evidence_is_safe_run_id "$run_id" || {
    evidence_error 'run-id must use lowercase letters, numbers, and single hyphens only.'
    return 2
  }
  [[ $run_id == "$component"-* ]] || {
    evidence_error "run-id must start with component prefix '$component-'."
    return 2
  }
  resolved_root=$(evidence_is_safe_output_root "$output_root") || {
    evidence_error 'output-root must be an absolute, non-broad path without parent traversal.'
    return 2
  }
  run_dir="$resolved_root/$run_id"
  [[ ! -e $run_dir ]] || {
    evidence_error "Evidence directory already exists: $run_dir"
    return 2
  }

  umask 077
  mkdir -p -- "$resolved_root"
  mkdir -- "$run_dir"
  mkdir -- "$run_dir/versions" "$run_dir/configuration" "$run_dir/runtime" \
    "$run_dir/functional" "$run_dir/recovery" "$run_dir/cleanup"

  EVIDENCE_COMPONENT=$component
  EVIDENCE_RUN_ID=$run_id
  EVIDENCE_OUTPUT_ROOT=$resolved_root
  EVIDENCE_RUN_DIR=$run_dir
  EVIDENCE_STARTED_AT_UTC=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
  EVIDENCE_SUMMARY[schema_version]=$EVIDENCE_SCHEMA_VERSION
  EVIDENCE_SUMMARY[component]=$component
  EVIDENCE_SUMMARY[run_id]=$run_id
  EVIDENCE_SUMMARY[started_at_utc]=$EVIDENCE_STARTED_AT_UTC
  EVIDENCE_SUMMARY[initiator_host]=$(hostname -f 2>/dev/null || hostname)
  EVIDENCE_SUMMARY[cleanup]=NOT_RUN
  EVIDENCE_SUMMARY[functional_check]=NOT_RUN
  EVIDENCE_SUMMARY[recovery_check]=NOT_RUN
  EVIDENCE_SUMMARY[failure_path_check]=NOT_RUN
}

evidence_redact_stream() {
  sed -E \
    -e 's/(^|[[:space:]])(-p)[^[:space:]]+/\1\2[REDACTED]/g' \
    -e 's/(^|[[:space:]])(--password=)[^[:space:]]+/\1\2[REDACTED]/Ig' \
    -e 's/(^|[[:space:]])(MYSQL_PWD=)[^[:space:]]+/\1\2[REDACTED]/g' \
    -e 's/((password|passwd|secret|token|credential|private[ _-]?key|jdbc[ _-]?password)[[:space:]]*[:=][[:space:]]*)[^[:space:]"'"'"'&,;]+/\1[REDACTED]/Ig' \
    -e 's/(Authorization:[[:space:]]*(Basic|Bearer)[[:space:]]+)[^[:space:]]+/\1[REDACTED]/Ig'
}

evidence_redact_file() {
  local source_file=$1
  local destination_file=$2
  evidence_require_initialized || return $?
  [[ -r $source_file ]] || {
    evidence_error "Cannot redact unreadable file: $source_file"
    return 2
  }
  evidence_redact_stream < "$source_file" > "$destination_file"
}

evidence_log() {
  local level=$1
  shift
  evidence_require_initialized || return $?
  printf '%s step=%03d level=%s %s\n' \
    "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$EVIDENCE_STEP_NUMBER" "$level" "$*" \
    | evidence_redact_stream >> "$EVIDENCE_RUN_DIR/commands.log"
}

evidence_run() {
  local description=$1
  local relative_log=$2
  local command_exit redact_exit
  local -a pipeline_status
  shift 2

  evidence_require_initialized || return $?
  [[ $relative_log != /* && $relative_log != *'..'* ]] || {
    evidence_error "Unsafe relative log path: $relative_log"
    return 2
  }
  [[ $# -gt 0 ]] || {
    evidence_error 'evidence_run requires a command argument vector.'
    return 2
  }

  EVIDENCE_STEP_NUMBER=$((EVIDENCE_STEP_NUMBER + 1))
  evidence_log INFO "begin description=$description log=$relative_log"
  mkdir -p -- "$(dirname "$EVIDENCE_RUN_DIR/$relative_log")"
  set +e
  "$@" 2>&1 | evidence_redact_stream > "$EVIDENCE_RUN_DIR/$relative_log"
  pipeline_status=("${PIPESTATUS[@]}")
  set -e
  command_exit=${pipeline_status[0]}
  redact_exit=${pipeline_status[1]}
  if ((redact_exit != 0)); then
    evidence_error "Evidence redaction failed for log: $relative_log"
    return "$redact_exit"
  fi
  evidence_log INFO "end description=$description exit_code=$command_exit log=$relative_log"
  printf '%s step=%03d exit_code=%s description=%s log=%s\n' \
    "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$EVIDENCE_STEP_NUMBER" "$command_exit" "$description" "$relative_log" \
    >> "$EVIDENCE_RUN_DIR/commands.log"
  return "$command_exit"
}

evidence_assert() {
  local assertion_name=$1
  local result=$2
  local detail=$3

  evidence_require_initialized || return $?
  [[ $result == PASS || $result == FAIL || $result == PARTIAL || $result == NOT_RUN || $result == NOT_APPLICABLE ]] || {
    evidence_error "Invalid assertion result: $result"
    return 2
  }
  printf '%s assertion=%s result=%s detail=%s\n' \
    "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$assertion_name" "$result" "$detail" \
    | evidence_redact_stream >> "$EVIDENCE_RUN_DIR/assertions.log"
  if [[ $result == FAIL ]]; then
    EVIDENCE_REQUIRED_FAILURES=$((EVIDENCE_REQUIRED_FAILURES + 1))
    EVIDENCE_STATUS='FAIL'
  elif [[ $result == PARTIAL && $EVIDENCE_STATUS == PASS ]]; then
    EVIDENCE_STATUS='PARTIAL'
  fi
}

evidence_assert_equals() {
  local assertion_name=$1
  local expected=$2
  local actual=$3
  evidence_require_initialized || return $?
  if [[ $expected == "$actual" ]]; then
    evidence_assert "$assertion_name" PASS "expected=$expected actual=$actual"
    return 0
  fi
  evidence_assert "$assertion_name" FAIL "expected=$expected actual=$actual"
  return 1
}

evidence_assert_matches() {
  local assertion_name=$1
  local expression=$2
  local actual=$3
  evidence_require_initialized || return $?
  if [[ $actual =~ $expression ]]; then
    evidence_assert "$assertion_name" PASS "expression=$expression actual=$actual"
    return 0
  fi
  evidence_assert "$assertion_name" FAIL "expression=$expression actual=$actual"
  return 1
}

evidence_sha256() {
  local file=$1
  evidence_require_initialized || return $?
  [[ -f $file ]] || {
    evidence_error "SHA-256 input is not a regular file: $file"
    return 2
  }
  sha256sum -- "$file" | awk '{print $1}'
}

evidence_summary_set() {
  local key=$1
  local value=$2
  evidence_require_initialized || return $?
  [[ $key =~ ^[a-z][a-z0-9_]*$ ]] || {
    evidence_error "Invalid summary key: $key"
    return 2
  }
  [[ ! $key =~ (password|passwd|secret|token|credential|private_key) ]] || {
    evidence_error "Sensitive summary key is forbidden: $key"
    return 2
  }
  EVIDENCE_SUMMARY[$key]=$value
}

evidence_mark_partial() {
  local reason=$1
  evidence_require_initialized || return $?
  if [[ $EVIDENCE_STATUS != FAIL ]]; then
    EVIDENCE_STATUS='PARTIAL'
  fi
  evidence_log INFO "partial reason=$reason"
}

evidence_register_cleanup() {
  local handler=$1
  local target=$2
  local owner=${3:-$(id -un)}

  evidence_require_initialized || return $?
  [[ $owner == "$(id -un)" ]] || {
    evidence_error "Cleanup owner must match invoking user: $owner"
    return 2
  }
  [[ $handler =~ ^[a-z][a-z0-9_]*$ ]] && declare -F "$handler" >/dev/null || {
    evidence_error "Cleanup handler is not a declared safe function: $handler"
    return 2
  }
  [[ -n $target && $target != / && $target != /data && $target != "$EVIDENCE_OUTPUT_ROOT" && $target != *'..'* ]] || {
    evidence_error "Unsafe cleanup target: $target"
    return 2
  }
  [[ $target == *"m1_accept_${EVIDENCE_RUN_ID}"* ]] || {
    evidence_error "Cleanup target lacks current temporary prefix: $target"
    return 2
  }
  EVIDENCE_CLEANUP_HANDLERS+=("$handler")
  EVIDENCE_CLEANUP_TARGETS+=("$target")
  EVIDENCE_CLEANUP_OWNERS+=("$owner")
}

evidence_cleanup_registration_is_safe() {
  local handler=$1
  local target=$2
  local owner=$3
  [[ $owner == "$(id -un)" ]] || return 1
  [[ $target != / && $target != /data && $target != "$EVIDENCE_OUTPUT_ROOT" && $target != *'..'* ]] || return 1
  [[ $target == *"m1_accept_${EVIDENCE_RUN_ID}"* ]] || return 1
  [[ $handler =~ ^[a-z][a-z0-9_]*$ ]] || return 1
  declare -F "$handler" >/dev/null
}

evidence_cleanup() {
  local index handler target owner cleanup_failed=0
  evidence_require_initialized || return $?

  for index in "${!EVIDENCE_CLEANUP_TARGETS[@]}"; do
    handler=${EVIDENCE_CLEANUP_HANDLERS[$index]}
    target=${EVIDENCE_CLEANUP_TARGETS[$index]}
    owner=${EVIDENCE_CLEANUP_OWNERS[$index]}
    if ! evidence_cleanup_registration_is_safe "$handler" "$target" "$owner"; then
      evidence_error "Cleanup guard rejected target: $target"
      cleanup_failed=1
      continue
    fi
    if "$handler" "$target"; then
      evidence_log INFO "cleanup=PASS target=$target"
    else
      evidence_error "Cleanup handler failed for target: $target"
      cleanup_failed=1
    fi
  done

  if ((cleanup_failed == 1)); then
    EVIDENCE_SUMMARY[cleanup]=FAIL
    EVIDENCE_STATUS='FAIL'
    return 1
  fi
  EVIDENCE_SUMMARY[cleanup]=PASS
}

evidence_finalize() {
  local exit_code=${1:-0}
  local key
  evidence_require_initialized || return $?
  ((EVIDENCE_FINALIZED == 0)) || return 0
  EVIDENCE_FINALIZED=1

  if ! evidence_cleanup; then
    exit_code=1
  fi
  if ((exit_code != 0 || EVIDENCE_REQUIRED_FAILURES > 0)); then
    EVIDENCE_STATUS='FAIL'
  fi
  if [[ $EVIDENCE_STATUS == PASS ]]; then
    if [[ ${EVIDENCE_SUMMARY[functional_check]:-NOT_RUN} != PASS || \
        ${EVIDENCE_SUMMARY[failure_path_check]:-NOT_RUN} != PASS ]]; then
      EVIDENCE_STATUS='FAIL'
    elif [[ ${EVIDENCE_SUMMARY[recovery_check]:-NOT_RUN} == NOT_RUN ]]; then
      EVIDENCE_STATUS='PARTIAL'
    elif [[ ${EVIDENCE_SUMMARY[recovery_check]} != PASS && \
        ${EVIDENCE_SUMMARY[recovery_check]} != NOT_APPLICABLE ]]; then
      EVIDENCE_STATUS='FAIL'
    fi
  fi
  EVIDENCE_SUMMARY[status]=$EVIDENCE_STATUS
  EVIDENCE_SUMMARY[finished_at_utc]=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
  EVIDENCE_SUMMARY[exit_code]=$exit_code
  {
    for key in schema_version component run_id status started_at_utc finished_at_utc initiator_host \
      functional_check recovery_check failure_path_check cleanup exit_code; do
      printf '%s=%s\n' "$key" "${EVIDENCE_SUMMARY[$key]:-NOT_RUN}"
    done
    for key in "${!EVIDENCE_SUMMARY[@]}"; do
      case "$key" in
        schema_version|component|run_id|status|started_at_utc|finished_at_utc|initiator_host|functional_check|recovery_check|failure_path_check|cleanup|exit_code) ;;
        *) printf '%s=%s\n' "$key" "${EVIDENCE_SUMMARY[$key]}" ;;
      esac
    done | sort
  } | evidence_redact_stream > "$EVIDENCE_RUN_DIR/summary.env"
  [[ $EVIDENCE_STATUS != FAIL ]]
}

evidence_install_exit_trap() {
  trap 'exit_code=$?; evidence_finalize "$exit_code" || exit_code=1; exit "$exit_code"' EXIT
}
