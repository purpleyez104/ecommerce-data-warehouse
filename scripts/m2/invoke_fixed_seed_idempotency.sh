#!/usr/bin/env bash
# T7 fixed Seed idempotency gate. This runner only writes when all 19 tables are empty.
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd -- "$script_dir/../.." && pwd)
server='' port='' database='' user='' confirm=''
mysql_path=mysql python_path=python3 password_variable=M2_TEST_MYSQL_PASSWORD
expected_path="$repo_root/mock/m2_fixed_seed_expected_results.json"
seed_path="$repo_root/mysql/seed/001_ecommerce_oltp_fixed_seed.sql"

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
while (($#)); do
  case "$1" in
    --server) server=${2:?}; shift 2 ;; --port) port=${2:?}; shift 2 ;;
    --database) database=${2:?}; shift 2 ;; --user) user=${2:?}; shift 2 ;;
    --confirm-isolated-database) confirm=1; shift ;;
    --mysql-path) mysql_path=${2:?}; shift 2 ;; --python-path) python_path=${2:?}; shift 2 ;;
    --password-environment-variable) password_variable=${2:?}; shift 2 ;;
    --expected-path) expected_path=${2:?}; shift 2 ;; --seed-path) seed_path=${2:?}; shift 2 ;;
    --validate-parser-only) "$python_path" - <<'PY'
def split_row(row):
    value=row.strip().rstrip(',;')[1:-1]; result=[]; field=[]; quoted=False; i=0
    while i < len(value):
        char=value[i]
        if char=="'":
            field.append(char)
            if quoted and i+1 < len(value) and value[i+1]=="'": field.append("'"); i+=1
            else: quoted=not quoted
        elif char==',' and not quoted: result.append(''.join(field)); field=[]
        else: field.append(char)
        i+=1
    if quoted: raise ValueError('unterminated quoted value')
    result.append(''.join(field)); return result
assert split_row("(1,'comma,value','escaped ''quote'''),")==['1',"'comma,value'","'escaped ''quote'''"]
print('PASS: idempotency runner seed row parser')
PY
      exit 0 ;;
    *) die "Unknown argument: $1" ;;
  esac
done
[[ -n $confirm && -n $server && -n $port && -n $database && -n $user ]] || die 'Server, port, database, user, and --confirm-isolated-database are required.'
[[ $database =~ ^ecommerce_oltp_t7_fixed_[a-z0-9_]{1,36}$ && ${#database} -le 64 ]] || die 'Database must be a lowercase, current-run ecommerce_oltp_t7_fixed_<run-id> identifier within the MySQL length limit.'
command -v "$mysql_path" >/dev/null || die "MySQL client '$mysql_path' was not found."
command -v "$python_path" >/dev/null || die "Python executable '$python_path' was not found."
password=${!password_variable-}; [[ -n $password ]] || die "Process environment variable $password_variable is required."
[[ -f $expected_path && -f $seed_path ]] || die 'Expected-results JSON or normal Seed SQL is missing.'

M2_T7_SERVER=$server M2_T7_PORT=$port M2_T7_DATABASE=$database M2_T7_USER=$user M2_T7_MYSQL=$mysql_path M2_T7_EXPECTED=$expected_path M2_T7_SEED=$seed_path MYSQL_PWD=$password "$python_path" - <<'PY'
import hashlib, json, os, re, subprocess
e=json.load(open(os.environ['M2_T7_EXPECTED'], encoding='utf-8'))
seed=open(os.environ['M2_T7_SEED'], encoding='utf-8').read()
if e['content_digest']['algorithm']!='SHA-256' or hashlib.sha256(seed.encode()).hexdigest()!=e['content_digest']['sha256']: raise SystemExit('Normal fixed Seed does not match the expected-results content digest.')
tables=list(e['table_counts'])
if len(tables)!=19: raise SystemExit('Expected-results JSON must define 19 tables.')
base=[os.environ['M2_T7_MYSQL'],'--protocol=TCP','--batch','--skip-column-names','--raw',f"--host={os.environ['M2_T7_SERVER']}",f"--port={os.environ['M2_T7_PORT']}",f"--user={os.environ['M2_T7_USER']}",f"--database={os.environ['M2_T7_DATABASE']}"]
def run(sql=None, data=None):
    cmd=base+([f'--execute={sql}'] if sql is not None else [])
    p=subprocess.run(cmd,input=data,text=True,capture_output=True,env=os.environ.copy())
    if p.returncode: raise SystemExit('MySQL query returned non-zero.')
    return p.stdout.splitlines()
counts={t:int(run(f'SELECT COUNT(*) FROM `{t}`;')[0]) for t in tables}
if all(v==0 for v in counts.values()): run(data=seed)
def split_row(row):
    value=row.strip().rstrip(',;').strip()
    if not value.startswith('(') or not value.endswith(')'): raise ValueError('Seed row must be enclosed in parentheses.')
    value=value[1:-1]; result=[]; field=[]; quoted=False; i=0
    while i < len(value):
        char=value[i]
        if char=="'":
            field.append(char)
            if quoted and i+1 < len(value) and value[i+1]=="'": field.append("'"); i+=1
            else: quoted=not quoted
        elif char==',' and not quoted: result.append(''.join(field)); field=[]
        else: field.append(char)
        i+=1
    if quoted: raise ValueError('Seed row contains an unterminated quoted value.')
    result.append(''.join(field)); return result
def normalize(value):
    value=value.strip()
    if value=='NULL': return '<NULL>'
    if value.startswith("'") and value.endswith("'"): value=value[1:-1].replace("''", "'")
    return value+'000' if re.fullmatch(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}', value) else value
def digest(rows): return hashlib.sha256('\n'.join(rows).encode()).hexdigest()
quoted_tables=','.join("'"+table+"'" for table in tables)
columns={}
for line in run("SELECT table_name,column_name,data_type,extra FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name IN ("+quoted_tables+") AND extra NOT LIKE '%GENERATED%' ORDER BY table_name,ordinal_position;"):
    table,column,data_type,_=line.split('\t',3); columns.setdefault(table,[]).append((column,data_type))
if set(columns)!=set(tables): raise SystemExit('Target database does not contain every fixed Seed table.')
for table in tables:
    match=re.search(r'^INSERT INTO `'+re.escape(table)+r'`.*?VALUES\r?\n(?P<rows>.*?);',seed,re.M|re.S)
    if not match: raise SystemExit(f'Missing INSERT block for {table}.')
    rows=[line for line in match.group('rows').splitlines() if re.match(r'^\s{2}\(',line)]
    if len(rows)!=int(e['table_counts'][table]): raise SystemExit(f'Seed/JSON row-count mismatch for {table}.')
    canonical=[]
    for row in rows:
        fields=split_row(row)
        if len(fields)!=len(columns[table]): raise SystemExit(f'Seed field count does not match non-generated columns for {table}.')
        canonical.append(chr(31).join(normalize(value) for value in fields))
    selected=[]
    for column,data_type in columns[table]:
        quoted='`'+column.replace('`','``')+'`'
        selected.append(f"CASE WHEN {quoted} IS NULL THEN '<NULL>' ELSE DATE_FORMAT({quoted}, '%Y-%m-%d %H:%i:%s.%f') END" if data_type in ('datetime','timestamp') else f"CASE WHEN {quoted} IS NULL THEN '<NULL>' ELSE CAST({quoted} AS CHAR) END")
    actual=run(f"SELECT CONCAT_WS(CHAR(31), {', '.join(selected)}) FROM `{table}` ORDER BY `{table}_pk`;")
    if len(actual)!=len(canonical) or digest(actual)!=digest(canonical): raise SystemExit(f'Existing content for {table} differs from the fixed Seed; no write was performed.')
print('PASS: isolated database matches the fixed Seed; no second write was performed.')
PY
