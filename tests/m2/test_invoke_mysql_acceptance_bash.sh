#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
acceptance="$repo_root/scripts/m2/invoke_mysql_acceptance.sh"
idempotency="$repo_root/scripts/m2/invoke_fixed_seed_idempotency.sh"
temporary_root=$(mktemp -d)
trap 'rm -rf -- "$temporary_root"' EXIT

require() { grep -Eq -- "$2" "$1" || { printf 'Missing required pattern: %s\n' "$2" >&2; exit 1; }; }
forbidden() { ! grep -Eq -- "$2" "$1" || { printf 'Forbidden pattern: %s\n' "$2" >&2; exit 1; }; }

bash -n "$acceptance"
bash -n "$idempotency"
bash "$acceptance" --validate-safety-only
bash "$idempotency" --validate-parser-only
if bash "$acceptance" --server parse-only --port 1 --user parse-only --run-id parse_only >/dev/null 2>&1; then
  printf 'Missing explicit isolation confirmation unexpectedly passed.\n' >&2
  exit 1
fi
if bash "$acceptance" --server parse-only --port 1 --user parse-only --run-id bad-run-id --confirm-isolated-databases >/dev/null 2>&1; then
  printf 'Unsafe RunId unexpectedly passed before client access.\n' >&2
  exit 1
fi
if M2_TEST_MYSQL_PASSWORD=test bash "$idempotency" --server parse-only --port 1 --database ecommerce_oltp --user parse-only --confirm-isolated-database --mysql-path false >/dev/null 2>&1; then
  printf 'Non-T7 fixed database unexpectedly passed idempotency preflight.\n' >&2
  exit 1
fi
if M2_TEST_MYSQL_PASSWORD=test bash "$idempotency" --server parse-only --port 1 --database "ecommerce_oltp_t7_fixed_$(printf 'a%.0s' {1..37})" --user parse-only --confirm-isolated-database --mysql-path false >/dev/null 2>&1; then
  printf 'Overlength T7 fixed database unexpectedly passed idempotency preflight.\n' >&2
  exit 1
fi

fake_mysql="$temporary_root/mysql"
cat > "$fake_mysql" <<'FAKE'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "$M2_T7_FAKE_LOG"
case " $* " in
  *' --version '*) printf 'mysql fake client\n' ;;
  *'SELECT VERSION();'*) printf '8.0.46-test\n' ;;
  *' information_schema.schemata '*)
    [[ ${M2_T7_FAKE_MODE:?} == existing ]] && printf '1\n' || printf '0\n' ;;
  *' information_schema.tables '*) printf '19\n' ;;
  *' CREATE DATABASE '*) exit 0 ;;
  *'DROP DATABASE'*)
    [[ ${M2_T7_FAKE_MODE:?} == drop_fails ]] && exit 1
    exit 0 ;;
  *' --database=ecommerce_oltp_t7_fixed_'*)
    input=$(cat)
    [[ ${M2_T7_FAKE_MODE:?} == one_created_then_fail || ${M2_T7_FAKE_MODE:?} == drop_fails ]] && exit 1
    [[ ${M2_T7_FAKE_MODE:?} == both_created_then_fail && $input == *'INSERT INTO'* ]] && exit 1
    exit 0 ;;
  *' --database=ecommerce_oltp_t7_generated_'*) cat >/dev/null ;;
  *) exit 0 ;;
esac
FAKE
chmod +x "$fake_mysql"

existing_log="$temporary_root/existing.log"
if M2_TEST_MYSQL_PASSWORD=test M2_T7_FAKE_LOG="$existing_log" M2_T7_FAKE_MODE=existing \
  bash "$acceptance" --server fake --port 3306 --user fake --run-id cleanup_existing --confirm-isolated-databases \
  --mysql-path "$fake_mysql" --evidence-root "$temporary_root/evidence-existing" >/dev/null 2>&1; then
  printf 'Existing target database unexpectedly passed.\n' >&2
  exit 1
fi
if grep -q 'DROP DATABASE' "$existing_log"; then
  printf 'Existing target database path attempted DROP DATABASE.\n' >&2
  exit 1
fi

one_created_log="$temporary_root/one-created.log"
if M2_TEST_MYSQL_PASSWORD=test M2_T7_FAKE_LOG="$one_created_log" M2_T7_FAKE_MODE=one_created_then_fail \
  bash "$acceptance" --server fake --port 3306 --user fake --run-id cleanup_one_created --confirm-isolated-databases \
  --mysql-path "$fake_mysql" --evidence-root "$temporary_root/evidence-one-created" >/dev/null 2>&1; then
  printf 'Single-created-database failure unexpectedly passed.\n' >&2
  exit 1
fi
grep -q 'DROP DATABASE IF EXISTS `ecommerce_oltp_t7_fixed_cleanup_one_created`' "$one_created_log"
if grep -q 'DROP DATABASE IF EXISTS `ecommerce_oltp_t7_generated_cleanup_one_created`' "$one_created_log"; then
  printf 'Uncreated generated database was incorrectly cleaned.\n' >&2
  exit 1
fi

both_created_log="$temporary_root/both-created.log"
if M2_TEST_MYSQL_PASSWORD=test M2_T7_FAKE_LOG="$both_created_log" M2_T7_FAKE_MODE=both_created_then_fail \
  bash "$acceptance" --server fake --port 3306 --user fake --run-id cleanup_both_created --confirm-isolated-databases \
  --mysql-path "$fake_mysql" --evidence-root "$temporary_root/evidence-both-created" >/dev/null 2>&1; then
  printf 'Two-created-database controlled failure unexpectedly passed.\n' >&2
  exit 1
fi
grep -q 'DROP DATABASE IF EXISTS `ecommerce_oltp_t7_fixed_cleanup_both_created`' "$both_created_log"
grep -q 'DROP DATABASE IF EXISTS `ecommerce_oltp_t7_generated_cleanup_both_created`' "$both_created_log"

drop_failure_log="$temporary_root/drop-failure.log"
drop_failure_summary="$temporary_root/evidence-drop-failure/cleanup_drop_failure/summary.json"
if M2_TEST_MYSQL_PASSWORD=test M2_T7_FAKE_LOG="$drop_failure_log" M2_T7_FAKE_MODE=drop_fails \
  bash "$acceptance" --server fake --port 3306 --user fake --run-id cleanup_drop_failure --confirm-isolated-databases \
  --mysql-path "$fake_mysql" --evidence-root "$temporary_root/evidence-drop-failure" >/dev/null 2>&1; then
  printf 'Controlled DROP DATABASE failure unexpectedly passed.\n' >&2
  exit 1
fi
grep -q 'DROP DATABASE IF EXISTS `ecommerce_oltp_t7_fixed_cleanup_drop_failure`' "$drop_failure_log"
M2_T7_SUMMARY="$drop_failure_summary" python3 - <<'PY'
import json, os
summary = json.load(open(os.environ['M2_T7_SUMMARY'], encoding='utf-8'))
assert summary['status'] == 'failed'
assert not any(stage['name'] == 'cleanup_ecommerce_oltp_t7_fixed_cleanup_drop_failure' and stage['result'] == 'dropped' for stage in summary['stages'])
PY
require "$acceptance" 'M2_TEST_MYSQL_PASSWORD'
require "$acceptance" 'DROP DATABASE IF EXISTS'
require "$acceptance" 'created_databases=\(\)'
require "$acceptance" 'register_created_database "\$db"'
require "$acceptance" 'for database in "\$\{created_databases\[@\]\}"'
require "$acceptance" 'FOREIGN_KEY_CHECKS'
require "$acceptance" 'Generated business-date coverage'
require "$acceptance" 'Valid soft delete and update_time'
forbidden "$acceptance" '--password(=|[[:space:]])'
forbidden "$acceptance" 'DELETE[[:space:]]+FROM'
require "$idempotency" 'Existing content for'
require "$idempotency" 'ecommerce_oltp_t7_fixed_'
printf 'PASS: T7 Bash acceptance harness local safety and parse regression\n'
