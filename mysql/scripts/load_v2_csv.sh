#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo=$(cd -- "$script_dir/../.." && pwd)
validator="$script_dir/validate_v2_csv_bundle.py"
template="$repo/mysql/sql/load_v2_csv.sql"
gate="$repo/mysql/sql/source_gate.sql"
bundle=''
dry_run=0
temp_dir=''

usage() {
  echo 'Usage: load_v2_csv.sh [--dry-run] --bundle <generated-bundle>'
}

die() { echo "ERROR: $*" >&2; exit 2; }

while (($#)); do
  case "$1" in
    --dry-run) dry_run=1; shift ;;
    --bundle) (($# >= 2)) || die '--bundle requires a value'; bundle=$2; shift 2 ;;
    --help|-h) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done
[[ -n $bundle ]] || die '--bundle is required'

if command -v python3 >/dev/null 2>&1 && python3 --version >/dev/null 2>&1; then python_bin=python3
elif command -v python >/dev/null 2>&1 && python --version >/dev/null 2>&1; then python_bin=python
else die 'Python 3 is required'
fi

if ((dry_run)); then
  "$python_bin" "$validator" --bundle "$bundle"
  exit 0
fi

command -v mysql >/dev/null 2>&1 || die 'mysql client is required'
: "${MYSQL_HOST:?MYSQL_HOST is required}"
: "${MYSQL_PORT:?MYSQL_PORT is required}"
: "${MYSQL_DATABASE:?MYSQL_DATABASE is required}"
: "${MYSQL_USER:?MYSQL_USER is required}"
: "${MYSQL_PASSWORD:?MYSQL_PASSWORD is required}"
[[ $MYSQL_DATABASE =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || die 'MYSQL_DATABASE must be a safe SQL identifier'
[[ $MYSQL_USER =~ ^[A-Za-z_][A-Za-z0-9_.-]*$ ]] || die 'MYSQL_USER contains unsupported characters'
[[ $MYSQL_PORT =~ ^[0-9]+$ ]] && ((MYSQL_PORT >= 1 && MYSQL_PORT <= 65535)) || die 'MYSQL_PORT must be between 1 and 65535'
[[ $MYSQL_HOST != *$'\n'* && $MYSQL_HOST != *$'\r'* ]] || die 'MYSQL_HOST must not contain a newline'
[[ $MYSQL_PASSWORD != *$'\n'* && $MYSQL_PASSWORD != *$'\r'* ]] || die 'MYSQL_PASSWORD must not contain a newline'

umask 077
temp_dir=$(mktemp -d "${TMPDIR:-/tmp}/v2-source-load.XXXXXX")
cleanup() { [[ -z $temp_dir ]] || rm -rf -- "$temp_dir"; }
trap cleanup EXIT INT TERM
defaults_file="$temp_dir/mysql.cnf"
session_sql="$temp_dir/load.sql"
plan_file="$temp_dir/plan.json"
escaped_password=${MYSQL_PASSWORD//\\/\\\\}
escaped_password=${escaped_password//\"/\\\"}
printf '[client]\nuser=%s\npassword="%s"\n' "$MYSQL_USER" "$escaped_password" > "$defaults_file"
chmod 600 "$defaults_file"

"$python_bin" "$validator" --bundle "$bundle" --output "$plan_file" \
  --render-load-sql "$session_sql" --load-template "$template" --source-gate "$gate"

mysql --defaults-extra-file="$defaults_file" --protocol=TCP --host="$MYSQL_HOST" \
  --port="$MYSQL_PORT" --database="$MYSQL_DATABASE" --local-infile=1 \
  --batch --skip-column-names --raw < "$session_sql"
echo 'V2 source load committed after Source Gate passed.'
