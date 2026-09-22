#!/usr/bin/env bash
# Linux-native T7 MySQL acceptance. Password is read only from a process environment variable.
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd -- "$script_dir/../.." && pwd)
ddl="$repo_root/mysql/ddl/001_ecommerce_oltp_candidate.sql"
seed="$repo_root/mysql/seed/001_ecommerce_oltp_fixed_seed.sql"
failures="$repo_root/mysql/seed/002_ecommerce_oltp_constraint_failure_cases.sql"
expected="$repo_root/mock/m2_fixed_seed_expected_results.json"
idempotency="$script_dir/invoke_fixed_seed_idempotency.sh"
server='' port='' user='' run_id='' confirm='' mysql_path=mysql python_path=python3 password_variable=M2_TEST_MYSQL_PASSWORD evidence_root="$repo_root/.local-notes/m2/t7"

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
while (($#)); do case "$1" in
  --server) server=${2:?}; shift 2 ;; --port) port=${2:?}; shift 2 ;; --user) user=${2:?}; shift 2 ;; --run-id) run_id=${2:?}; shift 2 ;;
  --confirm-isolated-databases) confirm=1; shift ;; --mysql-path) mysql_path=${2:?}; shift 2 ;; --python-path) python_path=${2:?}; shift 2 ;;
  --password-environment-variable) password_variable=${2:?}; shift 2 ;; --evidence-root) evidence_root=${2:?}; shift 2 ;;
  --validate-safety-only)
    self_test_database='ecommerce_oltp_t7_generated_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
    [[ run_42 =~ ^[a-z0-9_]{1,36}$ && ! Run_42 =~ ^[a-z0-9_]{1,36}$ && ${#self_test_database} -eq 64 ]] || die 'T7 safety self-test failed.'
    printf 'PASS: T7 acceptance harness safety self-test\n'; exit 0 ;;
  *) die "Unknown argument: $1" ;;
esac; done
[[ -n $confirm && -n $server && -n $port && -n $user && -n $run_id ]] || die 'Server, port, user, run-id, and --confirm-isolated-databases are required.'
[[ $port =~ ^[0-9]+$ ]] && ((port>=1 && port<=65535)) || die 'Port must be between 1 and 65535.'
[[ $run_id =~ ^[a-z0-9_]{1,36}$ ]] || die 'RunId must already be lowercase and contain only 1-36 letters, digits, or underscores.'
fixed_database="ecommerce_oltp_t7_fixed_$run_id"; generated_database="ecommerce_oltp_t7_generated_$run_id"
[[ ${#fixed_database} -le 64 && ${#generated_database} -le 64 ]] || die 'T7 database name exceeds MySQL identifier length.'
created_databases=()
for path in "$ddl" "$seed" "$failures" "$expected" "$idempotency"; do [[ -f $path ]] || die "Required T7 input is missing: $path"; done
command -v "$mysql_path" >/dev/null || die "MySQL client '$mysql_path' was not found."
command -v "$python_path" >/dev/null || die "Python executable '$python_path' was not found."
password=${!password_variable-}; [[ -n $password ]] || die "Process environment variable $password_variable is required."
if sed -E '/^[[:space:]]*--/d' "$ddl" "$seed" | grep -Eqi 'FOREIGN_KEY_CHECKS'; then die 'T7 refuses input that disables FOREIGN_KEY_CHECKS.'; fi
evidence_dir="$evidence_root/$run_id"; mkdir -p -- "$evidence_dir"; stages="$evidence_dir/stages.tsv"; : > "$stages"
started_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
mysql_client_version=$("$mysql_path" --version | tr '\n' ' ')
record() { printf '%s\t%s\n' "$1" "$2" >> "$stages"; }
mysql_query() {
  local db=$1 sql=$2
  local args=(--protocol=TCP --batch --skip-column-names --raw "--host=$server" "--port=$port" "--user=$user")
  [[ -n $db ]] && args+=("--database=$db")
  MYSQL_PWD=$password "$mysql_path" "${args[@]}" "--execute=$sql"
}
mysql_file() {
  local db=$1 path=$2
  local args=(--protocol=TCP --batch --skip-column-names --raw "--host=$server" "--port=$port" "--user=$user")
  [[ -n $db ]] && args+=("--database=$db")
  MYSQL_PWD=$password "$mysql_path" "${args[@]}" < "$path"
}
scalar() { local value; value=$(mysql_query "$1" "$2"); [[ $(printf '%s\n' "$value"|wc -l) -eq 1 ]] || die "Expected one scalar result for: $2"; printf '%s\n' "$value"; }
same() { [[ $1 == "$2" ]] || die "$3 (expected $2; got $1)"; }
register_created_database() {
  local database=$1
  [[ $database == "$fixed_database" || $database == "$generated_database" ]] || die "Refusing to register a database outside this T7 run: $database"
  created_databases+=("$database")
}
cleanup_created_databases() {
  local database
  for database in "${created_databases[@]}"; do
    [[ $database == "$fixed_database" || $database == "$generated_database" ]] || { printf 'ERROR: Refusing to clean an unregistered T7 database: %s\n' "$database" >&2; return 1; }
    if mysql_query '' "DROP DATABASE IF EXISTS \`$database\`;" >/dev/null; then
      record "cleanup_$database" dropped
    else
      printf 'ERROR: Failed to drop T7 database: %s\n' "$database" >&2
      return 1
    fi
  done
}
cleanup() { local code=$?; cleanup_created_databases || code=1; M2_T7_STAGES=$stages M2_T7_STATUS=$([[ $code -eq 0 ]] && printf passed || printf failed) M2_T7_RUN_ID=$run_id M2_T7_FIXED=$fixed_database M2_T7_GENERATED=$generated_database M2_T7_STARTED_AT=$started_at M2_T7_FINISHED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)" M2_T7_MYSQL_CLIENT_VERSION=$mysql_client_version M2_T7_DDL=$ddl M2_T7_SEED=$seed M2_T7_FAILURES=$failures M2_T7_EXPECTED=$expected "$python_path" - "$evidence_dir/summary.json" <<'PY'
import hashlib
import json,os,sys
items=[]
for line in open(os.environ['M2_T7_STAGES'],encoding='utf-8'):
 n,r=line.rstrip('\n').split('\t',1); items.append({'name':n,'exit_code':0,'result':r})
inputs={os.path.basename(path):hashlib.sha256(open(path,'rb').read()).hexdigest() for path in (os.environ['M2_T7_DDL'],os.environ['M2_T7_SEED'],os.environ['M2_T7_FAILURES'],os.environ['M2_T7_EXPECTED'])}
json.dump({'status':os.environ['M2_T7_STATUS'],'run_id':os.environ['M2_T7_RUN_ID'],'databases':[os.environ['M2_T7_FIXED'],os.environ['M2_T7_GENERATED']],'started_at':os.environ['M2_T7_STARTED_AT'],'finished_at':os.environ['M2_T7_FINISHED_AT'],'mysql_client_version':os.environ['M2_T7_MYSQL_CLIENT_VERSION'],'inputs':inputs,'stages':items},open(sys.argv[1],'w',encoding='utf-8'),ensure_ascii=False,indent=2)
PY
exit "$code"; }
trap cleanup EXIT

cd -- "$repo_root"
[[ $(grep -c '^CREATE TABLE `' "$ddl") -eq 19 ]] || die 'Expected 19 CREATE TABLE blocks.'
[[ $(grep -c '^START TRANSACTION;' "$failures") -eq 5 ]] || die 'Expected five isolated MySQL constraint failure blocks.'
M2_T7_EXPECTED=$expected M2_T7_SEED=$seed "$python_path" - <<'PY'
import hashlib,json,os
value=json.load(open(os.environ['M2_T7_EXPECTED'],encoding='utf-8'))
assert len(value['table_counts'])==19 and value['content_digest']['algorithm']=='SHA-256'
assert hashlib.sha256(open(os.environ['M2_T7_SEED'],'rb').read()).hexdigest()==value['content_digest']['sha256']
PY
"$python_path" -m unittest discover -s tests/m2 -p 'test_*.py'
record static_contracts 'Linux input integrity and Generator Python tests passed'
version=$(scalar '' 'SELECT VERSION();'); [[ $version =~ ^8[.]0[.]46 ]] || die "Expected MySQL 8.0.46; got $version"
for db in "$fixed_database" "$generated_database"; do same "$(scalar '' "SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name='$db';")" 0 "T7 database already exists: $db"; done; record mysql_preflight "$version"
for db in "$fixed_database" "$generated_database"; do mysql_query '' "CREATE DATABASE \`$db\` CHARACTER SET utf8mb4;" >/dev/null; register_created_database "$db"; record "create_$db" created; mysql_file "$db" "$ddl" >/dev/null; same "$(scalar "$db" 'SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_type="BASE TABLE";')" 19 'DDL table count'; record "ddl_$db" '19 tables created'; done
mysql_file "$fixed_database" "$seed" >/dev/null; record fixed_seed_first_load 'fixed seed loaded'
bash "$idempotency" --server "$server" --port "$port" --database "$fixed_database" --user "$user" --confirm-isolated-database --mysql-path "$mysql_path" --python-path "$python_path"; record fixed_seed_rerun 'same content produced no write'
drift="$evidence_dir/expected_drift.json"; M2_T7_EXPECTED=$expected M2_T7_DRIFT=$drift "$python_path" - <<'PY'
import json,os
v=json.load(open(os.environ['M2_T7_EXPECTED'],encoding='utf-8'));v['table_counts']['user_account']+=1
json.dump(v,open(os.environ['M2_T7_DRIFT'],'w',encoding='utf-8'),ensure_ascii=False)
PY
if bash "$idempotency" --server "$server" --port "$port" --database "$fixed_database" --user "$user" --confirm-isolated-database --mysql-path "$mysql_path" --python-path "$python_path" --expected-path "$drift"; then die 'Controlled expected-results drift unexpectedly passed.'; fi
bash "$idempotency" --server "$server" --port "$port" --database "$fixed_database" --user "$user" --confirm-isolated-database --mysql-path "$mysql_path" --python-path "$python_path"; record fixed_seed_drift_rejection 'drift rejected and baseline rechecked'
mapfile -t blocks < <(M2_T7_FAILURES=$failures M2_T7_OUT=$evidence_dir "$python_path" - <<'PY'
import os,re
for i,b in enumerate(re.findall(r'(?ms)START TRANSACTION;.*?ROLLBACK;',open(os.environ['M2_T7_FAILURES'],encoding='utf-8').read()),1):
 p=os.path.join(os.environ['M2_T7_OUT'],f'constraint_{i}.sql');open(p,'w',encoding='utf-8').write(b+'\n');print(p)
PY
)
[[ ${#blocks[@]} -eq 5 ]] || die 'Expected five extracted failure blocks.'
for block in "${blocks[@]}"; do if mysql_file "$fixed_database" "$block"; then die 'A MySQL constraint failure case unexpectedly succeeded.'; fi; done
bash "$idempotency" --server "$server" --port "$port" --database "$fixed_database" --user "$user" --confirm-isolated-database --mysql-path "$mysql_path" --python-path "$python_path"; record mysql_constraint_failures 'five failures rejected; fixed baseline unchanged'
one="$evidence_dir/generated_1.sql"; two="$evidence_dir/generated_2.sql"; for output in "$one" "$two"; do "$python_path" -m generator.generate_ecommerce_oltp --seed 42 --start-date 2025-01-29 --days 4 --scale 1 --output "$output"; done
same "$(sha256sum "$one"|awk '{print $1}')" "$(sha256sum "$two"|awk '{print $1}')" 'Generator checksum'; mysql_file "$generated_database" "$one" >/dev/null; same "$(scalar "$generated_database" 'SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_type="BASE TABLE";')" 19 'Generated DDL table count'; record generator_determinism_and_load "$(sha256sum "$one"|awk '{print $1}')"
same "$(scalar "$generated_database" "SELECT GROUP_CONCAT(DISTINCT business_date ORDER BY business_date SEPARATOR ',') FROM (SELECT DATE(registered_at) business_date FROM user_account UNION SELECT DATE(event_time) FROM page_view_event UNION SELECT DATE(ordered_at) FROM sales_order UNION SELECT DATE(paid_at) FROM payment_attempt WHERE payment_status='SUCCESS' UNION SELECT DATE(refunded_at) FROM refund_attempt WHERE refund_status='SUCCESS') x WHERE business_date BETWEEN '2025-01-29' AND '2025-02-01';")" '2025-01-29,2025-01-30,2025-01-31,2025-02-01' 'Generated business-date coverage'
same "$(scalar "$generated_database" 'SELECT COUNT(*) FROM sales_order so WHERE so.original_amount<>(SELECT COALESCE(SUM(oi.original_amount),0) FROM sales_order_item oi WHERE oi.order_pk=so.sales_order_pk);')" 0 'Order/item original amount conservation'
same "$(scalar "$generated_database" "SELECT COUNT(*) FROM payment_attempt pa JOIN sales_order so ON so.sales_order_pk=pa.order_pk WHERE pa.payment_status='SUCCESS' AND pa.payment_amount<>so.payable_amount;")" 0 'Payment/order conservation'
same "$(scalar "$generated_database" "SELECT COUNT(*) FROM (SELECT order_pk FROM payment_attempt WHERE payment_status='SUCCESS' GROUP BY order_pk HAVING COUNT(*)>1) x;")" 0 'One successful payment constraint'
same "$(scalar "$generated_database" "SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=DATABASE() AND ((table_name='payment_attempt' AND column_name='successful_order_pk') OR (table_name='refund_attempt' AND column_name='successful_return_order_pk')) AND extra LIKE '%VIRTUAL GENERATED%';")" 2 'VIRTUAL generated-column definitions'
old=$(scalar "$generated_database" "SELECT DATE_FORMAT(update_time,'%Y-%m-%d %H:%i:%s.%f') FROM brand WHERE brand_pk=1;"); mysql_query "$generated_database" "UPDATE brand SET is_deleted=1,deleted_at='2025-02-02 00:00:00.000',update_time='2025-02-02 00:00:00.000' WHERE brand_pk=1;" >/dev/null; same "$(scalar "$generated_database" "SELECT COUNT(*) FROM brand WHERE brand_pk=1 AND is_deleted=1 AND deleted_at IS NOT NULL AND update_time>'$old';")" 1 'Valid soft delete and update_time'
if mysql_query "$generated_database" 'UPDATE brand SET is_deleted=0 WHERE brand_pk=1;' >/dev/null; then die 'Invalid soft-delete combination unexpectedly succeeded.'; fi
same "$(scalar "$generated_database" 'SELECT COUNT(*) FROM brand WHERE brand_pk=1 AND is_deleted=1 AND deleted_at IS NOT NULL;')" 1 'Invalid soft-delete update must not alter the row'; same "$(scalar "$generated_database" 'SELECT COUNT(*) FROM brand;')" 2 'Soft delete must retain the business row'
old=$(scalar "$generated_database" "SELECT DATE_FORMAT(update_time,'%Y-%m-%d %H:%i:%s.%f') FROM brand WHERE brand_pk=1;"); mysql_query "$generated_database" "UPDATE brand SET update_time='2025-02-03 00:00:00.000' WHERE brand_pk=1;" >/dev/null; new=$(scalar "$generated_database" "SELECT DATE_FORMAT(update_time,'%Y-%m-%d %H:%i:%s.%f') FROM brand WHERE brand_pk=1;"); [[ $new != "$old" ]] || die 'Allowed update did not change update_time.'; same "$(scalar "$generated_database" "SELECT COUNT(*) FROM brand WHERE (update_time,brand_pk)>('2025-02-01 23:59:59.999',0);")" 1 'Incremental update_time boundary'
record generated_semantics 'business dates, conservation, generated columns, soft delete, and update_time boundary passed'
printf 'PASS: T7 MySQL acceptance completed; sanitized evidence at %s/summary.json\n' "$evidence_dir"
