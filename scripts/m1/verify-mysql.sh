#!/usr/bin/env bash
# MySQL 8.0.46 component acceptance. This script never changes permanent MySQL configuration.
set -euo pipefail

readonly MYSQL_EXPECTED_VERSION='8.0.46'
readonly MYSQL_EXPECTED_SERVER_ID='201'
readonly MYSQL_EXPECTED_BIND_ADDRESS='0.0.0.0'
readonly MYSQL_AUTH_FAILURE_PASSWORD='m1-cas-02-intentionally-invalid-password'

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
script_path=$(readlink -f -- "${BASH_SOURCE[0]}")
common_library_path=$(readlink -f -- "$script_dir/lib/evidence-common.sh")
source "$common_library_path"

run_id=''
secret_file=''
output_root="$EVIDENCE_DEFAULT_OUTPUT_ROOT"
confirm_restart=''
mysql_user=''
mysql_password=''
mysql_host='hadoop201'
mysql_port='3306'
temporary_database=''

usage() {
  cat <<'USAGE'
Usage: verify-mysql.sh --run-id <mysql-run-id> --secret-file <absolute-path>
                       [--output-root <absolute-path>]
                       [--confirm-restart EXISTING_MYSQL_INSTANCE]

The secret file must be mode 0600 or stricter, owned by the current user, and
contain MYSQL_USER and MYSQL_PASSWORD as key=value lines. It is never copied
or logged.
USAGE
}

die_usage() {
  evidence_error "$1"
  usage >&2
  exit 2
}

parse_args() {
  while (($#)); do
    case "$1" in
      --run-id) run_id=$2; shift 2 ;;
      --secret-file) secret_file=$2; shift 2 ;;
      --output-root) output_root=$2; shift 2 ;;
      --confirm-restart) confirm_restart=$2; shift 2 ;;
      --help|-h) usage; exit 0 ;;
      *) die_usage "Unknown argument: $1" ;;
    esac
  done
  [[ -n $run_id && -n $secret_file ]] || die_usage '--run-id and --secret-file are required.'
  [[ $run_id == mysql-* ]] || die_usage 'run-id must start with mysql-.'
}

require_commands() {
  local command
  for command in awk date find grep hostname mysql mysqlbinlog readlink sed sha256sum sort ssh ss stat sudo systemctl; do
    command -v "$command" >/dev/null || {
      evidence_error "Required command is unavailable: $command"
      return 127
    }
  done
}

validate_secret_file() {
  local candidate=$1 owner mode_decimal
  [[ $candidate == /* && $candidate != *'..'* ]] || {
    evidence_error 'Secret file must use an absolute path without parent traversal.'
    return 2
  }
  [[ -f $candidate && ! -L $candidate ]] || {
    evidence_error 'Secret file must be a regular, non-symlink file.'
    return 3
  }
  owner=$(stat -c '%U' -- "$candidate") || return 3
  [[ $owner == "$(id -un)" ]] || {
    evidence_error 'Secret file owner must be the current user.'
    return 3
  }
  mode_decimal=$((8#$(stat -c '%a' -- "$candidate"))) || return 3
  ((mode_decimal <= 8#600)) || {
    evidence_error 'Secret file mode must be 0600 or stricter.'
    return 3
  }
}

load_secret() {
  local line key value
  validate_secret_file "$secret_file" || return $?
  while IFS= read -r line || [[ -n $line ]]; do
    [[ -z $line || $line == \#* ]] && continue
    key=$(printf '%s' "$line" | sed 's/=.*//')
    value=$(printf '%s' "$line" | sed 's/^[^=]*=//')
    case "$key" in
      MYSQL_USER) mysql_user=$value ;;
      MYSQL_PASSWORD) mysql_password=$value ;;
      MYSQL_HOST) mysql_host=$value ;;
      MYSQL_PORT) mysql_port=$value ;;
      *) evidence_error "Unsupported Secret key: $key"; return 2 ;;
    esac
  done < "$secret_file"
  [[ -n $mysql_user && -n $mysql_password ]] || {
    evidence_error 'Secret file requires MYSQL_USER and MYSQL_PASSWORD.'
    return 2
  }
  [[ $mysql_port =~ ^[0-9]+$ ]] && ((mysql_port >= 1 && mysql_port <= 65535)) || {
    evidence_error 'MYSQL_PORT must be between 1 and 65535.'
    return 2
  }
}

mysql_exec() {
  MYSQL_PWD=$mysql_password mysql --protocol=TCP --host="$mysql_host" --port="$mysql_port" \
    --user="$mysql_user" --batch --skip-column-names --raw -e "$1"
}

mysql_file_exec() {
  MYSQL_PWD=$mysql_password mysql --protocol=TCP --host="$mysql_host" --port="$mysql_port" \
    --user="$mysql_user" --batch --raw < "$1"
}

mysqlbinlog_remote() {
  local binlog_file=$1 start_position=$2 stop_position=$3 destination=$4
  MYSQL_PWD=$mysql_password mysqlbinlog --read-from-remote-server --protocol=TCP \
    --host="$mysql_host" --port="$mysql_port" --user="$mysql_user" \
    --base64-output=DECODE-ROWS --verbose --start-position="$start_position" \
    --stop-position="$stop_position" "$binlog_file" > "$destination"
}

assert_server_version() {
  local actual_version=$1
  [[ $actual_version =~ ^8[.]0[.]46([.-].*)?$ ]] || {
    evidence_error "Expected MySQL Server 8.0.46 with optional Ubuntu package suffix; got: $actual_version"
    return 5
  }
}

remote_secret_validate() {
  local node=$1
  ssh -o BatchMode=yes -o ConnectTimeout=10 "$node" bash -s -- "$secret_file" "$(id -un)" <<'REMOTE'
set -euo pipefail
secret_path=$1
expected_owner=$2
[[ $secret_path == /* && $secret_path != *'..'* ]]
[[ -f $secret_path && ! -L $secret_path ]]
[[ $(stat -c '%U' -- "$secret_path") == "$expected_owner" ]]
mode=$((8#$(stat -c '%a' -- "$secret_path")))
((mode <= 8#600))
REMOTE
}

remote_tcp_check() {
  local node=$1
  ssh -o BatchMode=yes -o ConnectTimeout=10 "$node" bash -s -- "$mysql_host" "$mysql_port" <<'REMOTE'
set -euo pipefail
host=$1
port=$2
timeout 10 bash -c "</dev/tcp/$host/$port"
REMOTE
}

remote_mysql_auth() {
  local node=$1
  ssh -o BatchMode=yes -o ConnectTimeout=10 "$node" bash -s -- "$secret_file" "$(id -un)" "$mysql_host" "$mysql_port" <<'REMOTE'
set -euo pipefail
secret_path=$1
expected_owner=$2
host=$3
port=$4
[[ -f $secret_path && ! -L $secret_path ]]
[[ $(stat -c '%U' -- "$secret_path") == "$expected_owner" ]]
mode=$((8#$(stat -c '%a' -- "$secret_path")))
((mode <= 8#600))
set -a
. "$secret_path"
set +a
MYSQL_PWD="$MYSQL_PASSWORD" mysql --protocol=TCP --host="$host" --port="$port" \
  --user="$MYSQL_USER" --batch --skip-column-names -e 'SELECT @@version, @@server_id'
REMOTE
}

config_file_sha256() {
  local config_file=$1 hash
  if [[ -r $config_file ]]; then
    hash=$(sha256sum -- "$config_file")
  else
    hash=$(sudo -n sha256sum -- "$config_file") || {
      evidence_error "Cannot hash unreadable MySQL configuration file with non-interactive sudo: $config_file"
      return 3
    }
  fi
  hash=$(printf '%s\n' "$hash" | awk '{print $1}')
  [[ $hash =~ ^[a-f0-9]{64}$ ]] || {
    evidence_error "Invalid SHA-256 output for MySQL configuration file: $config_file"
    return 5
  }
  printf '%s\n' "$hash"
}

collect_config_metadata() {
  local path canonical owner mode hash found=0
  {
    printf 'canonical_path\towner\tmode\tsha256\n'
    for path in /etc/my.cnf /etc/mysql/my.cnf; do
      [[ -f $path && ! -L $path ]] || continue
      canonical=$(readlink -f -- "$path")
      owner=$(stat -c '%U' -- "$canonical")
      mode=$(stat -c '%a' -- "$canonical")
      hash=$(config_file_sha256 "$canonical") || return $?
      printf '%s\t%s\t%s\t%s\n' "$canonical" "$owner" "$mode" "$hash"
      found=1
    done
    if [[ -d /etc/mysql ]]; then
      while IFS= read -r path; do
        [[ -L $path ]] && continue
        canonical=$(readlink -f -- "$path")
        owner=$(stat -c '%U' -- "$canonical")
        mode=$(stat -c '%a' -- "$canonical")
        hash=$(config_file_sha256 "$canonical") || return $?
        printf '%s\t%s\t%s\t%s\n' "$canonical" "$owner" "$mode" "$hash"
        found=1
      done < <(find /etc/mysql -xdev -type f -name '*.cnf' -print | sort)
    fi
  } > "$EVIDENCE_RUN_DIR/configuration/mysql-config-files.tsv"
  ((found == 1)) || {
    evidence_error 'No regular MySQL configuration files were found for metadata capture.'
    return 5
  }
}

collect_configuration() {
  local variable_list
  variable_list="'server_id','port','bind_address','log_bin','binlog_format','binlog_row_image'"
  evidence_run 'capture MySQL systemd unit metadata' 'configuration/systemd-mysql.properties' \
    systemctl show mysql --property=ExecStart --property=FragmentPath --property=DropInPaths
  evidence_run 'capture MySQL default configuration search paths' 'configuration/mysql-default-search-paths.txt' \
    mysql --help
  collect_config_metadata
  mysql_exec "SHOW VARIABLES WHERE Variable_name IN ($variable_list)" \
    > "$EVIDENCE_RUN_DIR/configuration/mysql-variables.tsv"
  mysql_exec "SELECT VARIABLE_NAME, VARIABLE_SOURCE, COALESCE(VARIABLE_PATH, '') FROM performance_schema.variables_info WHERE VARIABLE_NAME IN ($variable_list) ORDER BY VARIABLE_NAME" \
    > "$EVIDENCE_RUN_DIR/configuration/mysql-variables-info.tsv"
}

assert_mysql_variable() {
  local variable=$1 expected=$2 actual
  actual=$(awk -F $'\t' -v name="$variable" '$1 == name {print $2; exit}' \
    "$EVIDENCE_RUN_DIR/configuration/mysql-variables.tsv")
  [[ $actual == "$expected" ]] || {
    evidence_assert "mysql_$variable" FAIL "expected=$expected actual=$actual"
    return 5
  }
  evidence_assert "mysql_$variable" PASS "expected=$expected actual=$actual"
}

assert_listener() {
  local listener
  listener=$(ss -ltnH | awk -v port="$mysql_port" '$4 ~ (":" port "$") {print $4; exit}')
  [[ -n $listener ]] || {
    evidence_assert mysql_listener FAIL "port=$mysql_port listener=missing"
    return 5
  }
  evidence_assert mysql_listener PASS "port=$mysql_port listener=$listener"
}

read_master_status() {
  mysql_exec 'SHOW MASTER STATUS' | awk -F $'\t' 'NR == 1 {print $1 "\t" $2}'
}

create_and_mutate_temporary_objects() {
  local master_status start_file start_position
  mysql_exec "CREATE DATABASE \`$temporary_database\`"
  mysql_exec "CREATE TABLE \`$temporary_database\`.binlog_probe (id INT PRIMARY KEY, payload VARCHAR(32) NOT NULL)"
  master_status=$(read_master_status)
  start_file=$(printf '%s' "$master_status" | awk -F $'\t' '{print $1}')
  start_position=$(printf '%s' "$master_status" | awk -F $'\t' '{print $2}')
  [[ -n $start_file && $start_position =~ ^[0-9]+$ ]] || {
    evidence_error 'Unable to capture the bounded binlog start file and position.'
    return 5
  }
  printf 'file=%s\nposition=%s\n' "$start_file" "$start_position" > "$EVIDENCE_RUN_DIR/functional/binlog-start.env"
  mysql_exec "INSERT INTO \`$temporary_database\`.binlog_probe (id, payload) VALUES (1, 'inserted')"
  mysql_exec "UPDATE \`$temporary_database\`.binlog_probe SET payload = 'updated' WHERE id = 1"
  mysql_exec "DELETE FROM \`$temporary_database\`.binlog_probe WHERE id = 1"
  mysql_exec "SELECT COUNT(*) FROM \`$temporary_database\`.binlog_probe" | grep -qx '0'
  printf '%s\t%s\n' "$start_file" "$start_position" > "$EVIDENCE_RUN_DIR/functional/binlog-bounds.tsv"
}

assert_scoped_row_event() {
  local event_name=$1
  awk -v database="$temporary_database" -v event_name="$event_name" '
    /Table_map:/ { target = sprintf("%c%s%c.%cbinlog_probe%c", 96, database, 96, 96, 96); in_target = index($0, target) > 0 }
    index($0, event_name) > 0 && in_target { found = 1 }
    END { exit found ? 0 : 1 }
  ' "$EVIDENCE_RUN_DIR/functional/binlog-row-events.txt" || {
    evidence_error "Missing scoped $event_name event for $temporary_database.binlog_probe."
    return 5
  }
}

capture_and_assert_binlog() {
  local bounds start_file start_position end_file end_position
  bounds=$(cat "$EVIDENCE_RUN_DIR/functional/binlog-bounds.tsv")
  start_file=$(printf '%s' "$bounds" | awk -F $'\t' '{print $1}')
  start_position=$(printf '%s' "$bounds" | awk -F $'\t' '{print $2}')
  bounds=$(read_master_status)
  end_file=$(printf '%s' "$bounds" | awk -F $'\t' '{print $1}')
  end_position=$(printf '%s' "$bounds" | awk -F $'\t' '{print $2}')
  [[ $start_file == "$end_file" ]] || {
    evidence_error "Binlog rotated during bounded capture: start=$start_file end=$end_file"
    return 5
  }
  [[ $end_position =~ ^[0-9]+$ ]] && ((end_position > start_position)) || {
    evidence_error 'Binlog did not advance after temporary I/U/D.'
    return 5
  }
  printf 'file=%s\nstart_position=%s\nstop_position=%s\n' "$end_file" "$start_position" "$end_position" \
    > "$EVIDENCE_RUN_DIR/functional/binlog-stop.env"
  mysqlbinlog_remote "$end_file" "$start_position" "$end_position" "$EVIDENCE_RUN_DIR/functional/binlog-row-events.txt"
  assert_scoped_row_event 'Write_rows'
  assert_scoped_row_event 'Update_rows'
  assert_scoped_row_event 'Delete_rows'
  grep -F "### INSERT INTO \`$temporary_database\`.\`binlog_probe\`" "$EVIDENCE_RUN_DIR/functional/binlog-row-events.txt" >/dev/null
  grep -F "### UPDATE \`$temporary_database\`.\`binlog_probe\`" "$EVIDENCE_RUN_DIR/functional/binlog-row-events.txt" >/dev/null
  grep -F "### DELETE FROM \`$temporary_database\`.\`binlog_probe\`" "$EVIDENCE_RUN_DIR/functional/binlog-row-events.txt" >/dev/null
}

verify_authentication_failure() {
  local failure_exit
  if evidence_run 'expected MySQL authentication failure' 'functional/mysql-auth-failure.txt' \
    env MYSQL_PWD="$MYSQL_AUTH_FAILURE_PASSWORD" mysql --protocol=TCP --host="$mysql_host" --port="$mysql_port" \
      --user="$mysql_user" --batch --skip-column-names -e 'SELECT 1'; then
    evidence_error 'Authentication failure test unexpectedly succeeded.'
    return 5
  else
    failure_exit=$?
  fi
  ((failure_exit != 0)) || {
    evidence_error 'Authentication failure test was not executed.'
    return 5
  }
  grep -Eiq 'Access denied|ERROR 1045' "$EVIDENCE_RUN_DIR/functional/mysql-auth-failure.txt" || {
    evidence_error 'Authentication failure output did not match the expected MySQL error.'
    return 5
  }
  evidence_summary_set failure_path_check PASS
}

cleanup_database() {
  local database=$1 remaining
  [[ $database == "m1_accept_$run_id" ]] || {
    evidence_error "Cleanup rejected non-current temporary database: $database"
    return 2
  }
  mysql_exec "DROP DATABASE IF EXISTS \`$database\`" || return $?
  remaining=$(mysql_exec "SELECT COUNT(*) FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = '$database'") || return $?
  [[ $remaining == 0 ]] || {
    evidence_error "Cleanup did not remove temporary database: $database"
    return 1
  }
}

restart_mysql() {
  sudo -n systemctl restart mysql
}

run_recovery() {
  local attempt
  if [[ -z $confirm_restart ]]; then
    evidence_mark_partial 'restart not authorized; pass --confirm-restart EXISTING_MYSQL_INSTANCE to run recovery'
    evidence_summary_set recovery_check NOT_APPLICABLE
    return 0
  fi
  [[ $confirm_restart == EXISTING_MYSQL_INSTANCE ]] || {
    evidence_error 'Restart confirmation token is invalid.'
    return 3
  }
  command -v sudo >/dev/null || return 127
  sudo -n true || {
    evidence_error 'Non-interactive sudo is required for the authorized restart.'
    return 3
  }
  restart_mysql
  for attempt in $(seq 1 30); do
    if systemctl is-active --quiet mysql && mysql_exec 'SELECT 1' | grep -qx '1'; then
      mysql_exec "SELECT COUNT(*) FROM \`$temporary_database\`.recovery_sentinel" | grep -qx '1'
      evidence_summary_set recovery_check PASS
      return 0
    fi
    sleep 2
  done
  evidence_error 'MySQL did not become healthy after the authorized restart.'
  return 5
}

append_manifest_hash() {
  local key=$1 input=$2
  [[ -f $input ]] || return 0
  printf '%s=%s\n' "$key" "$(evidence_sha256 "$input")"
}

write_integrity_manifest() {
  local manifest="$EVIDENCE_RUN_DIR/integrity/evidence-manifest.env"
  mkdir -p -- "$EVIDENCE_RUN_DIR/integrity"
  {
    printf 'manifest_schema_version=1\ncomponent=mysql\nrun_id=%s\n' "$run_id"
    append_manifest_hash verify_mysql_sha256 "$script_path"
    append_manifest_hash evidence_common_sha256 "$common_library_path"
    append_manifest_hash systemd_mysql_sha256 "$EVIDENCE_RUN_DIR/configuration/systemd-mysql.properties"
    append_manifest_hash config_file_metadata_sha256 "$EVIDENCE_RUN_DIR/configuration/mysql-config-files.tsv"
    append_manifest_hash mysql_variables_sha256 "$EVIDENCE_RUN_DIR/configuration/mysql-variables.tsv"
    append_manifest_hash mysql_variable_sources_sha256 "$EVIDENCE_RUN_DIR/configuration/mysql-variables-info.tsv"
  } > "$manifest"
}

install_mysql_exit_trap() {
  trap 'exit_code=$?; if ! write_integrity_manifest; then evidence_error "Evidence manifest generation failed."; exit_code=1; fi; evidence_finalize "$exit_code" || exit_code=1; exit "$exit_code"' EXIT
}

main() {
  local actual_version node
  parse_args "$@"
  require_commands
  validate_secret_file "$secret_file"
  evidence_init mysql "$run_id" "$output_root"
  install_mysql_exit_trap
  load_secret
  temporary_database="m1_accept_$run_id"
  evidence_register_cleanup cleanup_database "$temporary_database"

  evidence_run 'capture MySQL service state' 'runtime/mysql-service-status.txt' \
    systemctl status mysql --no-pager -l
  evidence_run 'capture MySQL listening sockets' 'runtime/mysql-listeners.txt' ss -ltnp
  actual_version=$(mysql_exec 'SELECT @@version')
  printf '%s\n' "$actual_version" > "$EVIDENCE_RUN_DIR/versions/mysql-server-version.txt"
  assert_server_version "$actual_version"
  evidence_assert mysql_server_version PASS "expected=$MYSQL_EXPECTED_VERSION actual=$actual_version"
  collect_configuration
  assert_listener
  assert_mysql_variable server_id "$MYSQL_EXPECTED_SERVER_ID"
  assert_mysql_variable port "$mysql_port"
  assert_mysql_variable bind_address "$MYSQL_EXPECTED_BIND_ADDRESS"
  assert_mysql_variable log_bin ON
  assert_mysql_variable binlog_format ROW
  assert_mysql_variable binlog_row_image FULL

  for node in hadoop201 hadoop202 hadoop203; do
    evidence_run "validate Secret file safety on $node" "runtime/$node-secret-safety.txt" remote_secret_validate "$node"
  done
  for node in hadoop201 hadoop202 hadoop203; do
    evidence_run "check MySQL TCP from $node" "runtime/$node-tcp.txt" remote_tcp_check "$node"
    evidence_run "authenticate to MySQL from $node" "runtime/$node-mysql-auth.txt" remote_mysql_auth "$node"
  done

  create_and_mutate_temporary_objects
  capture_and_assert_binlog
  mysql_exec "CREATE TABLE \`$temporary_database\`.recovery_sentinel (id INT PRIMARY KEY)"
  mysql_exec "INSERT INTO \`$temporary_database\`.recovery_sentinel (id) VALUES (1)"
  verify_authentication_failure
  evidence_summary_set functional_check PASS
  run_recovery
}

if [[ ${MYSQL_VERIFY_TEST_LIB_ONLY:-0} != 1 ]]; then
  main "$@"
fi
