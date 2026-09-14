#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  collect-vm-environment-evidence.sh \
    --run-id <safe-id> \
    --output-dir <absolute-path> \
    [--max-clock-skew-seconds <non-negative-integer>]

Collects non-disruptive, allowlisted VM and installed-component evidence from
hadoop201, hadoop202, and hadoop203. The default clock-skew threshold is 5s.
This inventory does not perform component functional acceptance.
USAGE
}

run_id=''
output_dir=''
max_clock_skew_seconds=5

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
    --max-clock-skew-seconds)
      [[ $# -ge 2 ]] || { usage >&2; exit 2; }
      max_clock_skew_seconds=$2
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

resolved_output_dir=$(readlink -m -- "$output_dir")
case "$resolved_output_dir" in
  /data/logs/ecommerce-data-warehouse/m1/*) output_dir=$resolved_output_dir ;;
  *)
    printf '%s\n' 'output-dir must resolve below /data/logs/ecommerce-data-warehouse/m1/' >&2
    exit 2
    ;;
esac

[[ $max_clock_skew_seconds =~ ^[0-9]+$ ]] || {
  printf '%s\n' 'max-clock-skew-seconds must be a non-negative integer' >&2
  exit 2
}

if [[ -d $output_dir ]] && [[ -n $(find "$output_dir" -mindepth 1 -maxdepth 1 -print -quit) ]]; then
  printf 'output-dir already contains files: %s\n' "$output_dir" >&2
  exit 2
fi

[[ $(id -un) == yee ]] || {
  printf 'This script must run as yee; actual user: %s\n' "$(id -un)" >&2
  exit 3
}

[[ $(hostname -s) == hadoop201 ]] || {
  printf 'This script must run on hadoop201; actual host: %s\n' "$(hostname -s)" >&2
  exit 3
}

for command_name in ssh date hostname id mkdir find tee awk grep sed readlink; do
  command -v "$command_name" >/dev/null 2>&1 || {
    printf 'Required command is unavailable: %s\n' "$command_name" >&2
    exit 4
  }
done

umask 077
mkdir -p "$output_dir"
main_log="$output_dir/collect-vm-environment-evidence.log"
summary_file="$output_dir/summary.env"
exec > >(tee -a "$main_log") 2>&1

nodes=(hadoop201 hadoop202 hadoop203)
sections=(
  identity-system
  network-time
  storage
  limits-runtime
  process-ports
  component-inventory
  component-config-whitelist
)
components=(mysql hive kafka spark datax)
declare -A node_status
declare -A node_clock_skew
declare -A component_status
overall_status=FAIL

evidence_value() {
  local file=$1
  local key=$2
  local value
  [[ -r $file ]] || { printf '%s\n' 'UNKNOWN'; return 0; }
  value=$(awk -F= -v expected="$key" '$1 == expected {sub(/^[^=]*=/, ""); print; exit}' "$file")
  [[ -n $value ]] && printf '%s\n' "$value" || printf '%s\n' 'UNKNOWN'
}

write_summary() {
  local exit_code=$1
  local node component storage_file inventory_file hive_target
  local hive_known=0
  local hive_missing=0
  local hive_reference=''
  local hive_path_consistency=UNKNOWN

  {
    printf 'status=%s\n' "$overall_status"
    printf 'run_id=%s\n' "$run_id"
    printf 'orchestrator_node=hadoop201\n'
    printf 'started_by=yee\n'
    printf 'max_clock_skew_seconds=%s\n' "$max_clock_skew_seconds"
    printf 'exit_code=%s\n' "$exit_code"
    for node in "${nodes[@]}"; do
      printf 'node.%s.status=%s\n' "$node" "${node_status[$node]:-FAIL}"
      printf 'node.%s.clock_skew_seconds=%s\n' "$node" "${node_clock_skew[$node]:-UNKNOWN}"
      storage_file="$output_dir/$node/storage.txt"
      printf 'node.%s.data_directory=%s\n' "$node" \
        "$(evidence_value "$storage_file" 'data.directory')"
      printf 'node.%s.data_write_permission=%s\n' "$node" \
        "$(evidence_value "$storage_file" 'data.write_permission')"
      printf 'node.%s.module_root=%s\n' "$node" \
        "$(evidence_value "$storage_file" 'directory.module.path')"
      printf 'node.%s.log_root=%s\n' "$node" \
        "$(evidence_value "$storage_file" 'directory.logs.path')"
    done
    for component in "${components[@]}"; do
      printf 'component.%s.status=%s\n' "$component" "${component_status[$component]:-UNKNOWN}"
    done
    for node in "${nodes[@]}"; do
      inventory_file="$output_dir/$node/component-inventory.txt"
      hive_target=$(evidence_value "$inventory_file" 'stable.hive')
      if [[ $hive_target == UNKNOWN || $hive_target == NOT_FOUND ]]; then
        hive_missing=$((hive_missing + 1))
        continue
      fi
      if [[ -z $hive_reference ]]; then
        hive_reference=$hive_target
      elif [[ $hive_reference != "$hive_target" ]]; then
        hive_path_consistency=DRIFT
      fi
      hive_known=$((hive_known + 1))
    done
    if [[ $hive_path_consistency != DRIFT ]]; then
      if ((hive_known == ${#nodes[@]} && hive_missing == 0)); then
        hive_path_consistency=CONSISTENT
      elif ((hive_known > 0)); then
        hive_path_consistency=PARTIAL
      fi
    fi
    printf 'component.hive.stable_path_consistency=%s\n' "$hive_path_consistency"
    printf 'evidence_boundary=inventory_only_not_component_verification\n'
  } > "$summary_file"
}

on_exit() {
  local exit_code=$1
  set +e
  if ((exit_code != 0)); then
    overall_status=FAIL
  fi
  write_summary "$exit_code"
  exit "$exit_code"
}
trap 'on_exit $?' EXIT

remote_collect() {
  local section=$1
  local expected_node=$2
  local actual_node
  actual_node=$(hostname -s 2>/dev/null || printf UNKNOWN)

  [[ $actual_node == "$expected_node" ]] || {
    printf 'expected_node=%s\nactual_node=%s\n' "$expected_node" "$actual_node" >&2
    return 3
  }
  [[ $(id -un) == yee ]] || {
    printf 'expected_user=yee\nactual_user=%s\n' "$(id -un)" >&2
    return 3
  }

  command_path() {
    local candidate
    for candidate in "$@"; do
      if [[ $candidate == */* ]]; then
        if [[ -x $candidate ]]; then
          readlink -f "$candidate" 2>/dev/null || printf '%s\n' "$candidate"
          return 0
        fi
      elif command -v "$candidate" >/dev/null 2>&1; then
        command -v "$candidate"
        return 0
      fi
    done
    return 1
  }

  resolved_directory() {
    local candidate=$1
    if [[ -e $candidate || -L $candidate ]]; then
      readlink -f "$candidate" 2>/dev/null || printf '%s\n' "$candidate"
    else
      printf '%s\n' 'NOT_FOUND'
    fi
  }

  safe_version() {
    local component=$1
    local executable=$2
    local output=''
    case "$component" in
      mysql)
        output=$("$executable" --version 2>&1 || true)
        ;;
      hive)
        if command -v timeout >/dev/null 2>&1; then
          output=$(timeout 15 "$executable" --version 2>&1 || true)
        else
          output=$("$executable" --version 2>&1 || true)
        fi
        ;;
      kafka)
        if command -v timeout >/dev/null 2>&1; then
          output=$(timeout 15 "$executable" --version 2>&1 || true)
        else
          output=$("$executable" --version 2>&1 || true)
        fi
        ;;
      spark)
        if command -v timeout >/dev/null 2>&1; then
          output=$(timeout 15 "$executable" --version 2>&1 || true)
        else
          output=$("$executable" --version 2>&1 || true)
        fi
        ;;
    esac
    if [[ -n $output ]]; then
      printf '%s\n' "$output" | sed -n '1,12p'
    else
      printf '%s\n' 'UNKNOWN_no_version_output'
    fi
  }

  print_path_record() {
    local label=$1
    local path=$2
    if [[ -e $path || -L $path ]]; then
      printf '%s.path=%s\n' "$label" "$path"
      printf '%s.resolved=%s\n' "$label" "$(readlink -f "$path" 2>/dev/null || printf UNKNOWN)"
      if command -v stat >/dev/null 2>&1; then
        stat -c "$label.owner=%U:%G" "$path" 2>/dev/null || true
        stat -c "$label.mode=%a" "$path" 2>/dev/null || true
      fi
    else
      printf '%s=NOT_FOUND\n' "$label"
    fi
  }

  print_kv_whitelist() {
    local file=$1
    local allow_pattern=$2
    [[ -r $file ]] || return 0
    printf 'source=%s\n' "$file"
    awk -v allow="$allow_pattern" '
      /^[[:space:]]*[#;]/ { next }
      index($0, "=") == 0 { next }
      {
        key = substr($0, 1, index($0, "=") - 1)
        value = substr($0, index($0, "=") + 1)
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", key)
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
        sub(/^export[[:space:]]+/, "", key)
        lower = tolower(key)
        if (lower ~ /(password|passwd|secret|token|credential|private[._-]?key)/) next
        if (key ~ allow) {
          gsub(/:\/\/[^\/@[:space:]]+@/, "://REDACTED@", value)
          sub(/\?.*$/, "", value)
          printf "%s=%s\n", key, value
        }
      }
    ' "$file"
  }

  print_hive_xml_whitelist() {
    local file=$1
    [[ -r $file ]] || return 0
    printf 'source=%s\n' "$file"
    if ! command -v python3 >/dev/null 2>&1; then
      printf '%s\n' 'hive_xml_parse=UNKNOWN_python3_unavailable'
      return 0
    fi
    python3 - "$file" <<'PY'
import re
import sys
import xml.etree.ElementTree as ET

allowed = {
    "javax.jdo.option.ConnectionURL",
    "hive.metastore.uris",
    "hive.metastore.warehouse.dir",
    "hive.server2.thrift.bind.host",
    "hive.server2.thrift.port",
    "hive.server2.transport.mode",
    "hive.exec.scratchdir",
    "hive.exec.local.scratchdir",
    "hive.querylog.location",
}

try:
    root = ET.parse(sys.argv[1]).getroot()
except Exception as exc:
    print(f"hive_xml_parse=UNKNOWN_{type(exc).__name__}")
    raise SystemExit(0)

for prop in root.findall("property"):
    name = (prop.findtext("name") or "").strip()
    if name not in allowed:
        continue
    value = (prop.findtext("value") or "").strip()
    if name == "javax.jdo.option.ConnectionURL":
        value = re.sub(r"//[^/@\s]+@", "//REDACTED@", value)
        value = value.split("?", 1)[0]
    print(f"{name}={value}")
PY
  }

  case "$section" in
    identity-system)
      printf 'node=%s\nuser=%s\ncollected_at=%s\n' \
        "$actual_node" "$(id -un)" "$(date --iso-8601=seconds)"
      if command -v hostnamectl >/dev/null 2>&1; then hostnamectl 2>&1 || true; fi
      if [[ -r /etc/os-release ]]; then sed -n '1,40p' /etc/os-release; fi
      uname -a 2>&1 || true
      if command -v lscpu >/dev/null 2>&1; then lscpu 2>&1 || true; fi
      if command -v free >/dev/null 2>&1; then free -h 2>&1 || true; fi
      if command -v uptime >/dev/null 2>&1; then uptime 2>&1 || true; fi
      ;;
    network-time)
      printf 'node=%s\nepoch_seconds=%s\ncollected_at=%s\n' \
        "$actual_node" "$(date +%s)" "$(date --iso-8601=seconds)"
      if command -v timedatectl >/dev/null 2>&1; then timedatectl 2>&1 || true; fi
      if command -v ip >/dev/null 2>&1; then ip -brief address 2>&1 || true; ip route 2>&1 || true; fi
      for peer in hadoop201 hadoop202 hadoop203; do
        if command -v getent >/dev/null 2>&1; then
          printf 'resolve.%s=' "$peer"
          getent ahostsv4 "$peer" 2>/dev/null | awk 'NR == 1 {print $1} END {if (NR == 0) print "UNKNOWN"}'
        fi
        if command -v ping >/dev/null 2>&1; then
          if ping -c 1 -W 2 "$peer" >/dev/null 2>&1; then
            printf 'ping.%s=PASS\n' "$peer"
          else
            printf 'ping.%s=FAIL\n' "$peer"
          fi
        else
          printf 'ping.%s=UNKNOWN_command_unavailable\n' "$peer"
        fi
      done
      ;;
    storage)
      if command -v lsblk >/dev/null 2>&1; then
        lsblk -o NAME,TYPE,FSTYPE,SIZE,MOUNTPOINTS,UUID 2>&1 || true
      fi
      if command -v findmnt >/dev/null 2>&1; then findmnt 2>&1 || true; fi
      if command -v df >/dev/null 2>&1; then df -hT / /data 2>&1 || true; fi
      if command -v stat >/dev/null 2>&1; then
        stat -c 'path=%n owner=%U:%G mode=%a type=%F' /data 2>&1 || true
      fi
      [[ -d /data ]] && printf 'data.directory=FOUND\n' || printf 'data.directory=NOT_FOUND\n'
      [[ -w /data ]] && printf 'data.write_permission=YES\n' || printf 'data.write_permission=NO\n'
      for path in /data/software /data/module /data/hadoop /data/kafka /data/spark \
        /data/hive /data/mysql /data/datax /data/logs /data/tmp; do
        print_path_record "directory.${path#/data/}" "$path"
      done
      ;;
    limits-runtime)
      ulimit -a 2>&1 || true
      printf 'proc_loadavg='; sed -n '1p' /proc/loadavg 2>/dev/null || printf 'UNKNOWN\n'
      if [[ -r /proc/meminfo ]]; then
        grep -E '^(MemTotal|MemAvailable|SwapTotal|SwapFree):' /proc/meminfo || true
      fi
      for java_home in /usr/lib/jvm/java-8-openjdk-amd64 \
        /usr/lib/jvm/java-11-openjdk-amd64 \
        /usr/lib/jvm/java-17-openjdk-amd64; do
        printf 'java_home=%s\n' "$(resolved_directory "$java_home")"
        if [[ -x $java_home/bin/java ]]; then "$java_home/bin/java" -version 2>&1 || true; fi
      done
      if command -v java >/dev/null 2>&1; then
        printf 'default_java=%s\n' "$(readlink -f "$(command -v java)" 2>/dev/null || command -v java)"
        java -version 2>&1 || true
      else
        printf 'default_java=NOT_FOUND\n'
      fi
      ;;
    process-ports)
      if command -v jps >/dev/null 2>&1; then
        jps 2>&1 || true
        while read -r java_pid java_main _; do
          [[ $java_pid =~ ^[0-9]+$ ]] || continue
          printf 'java_process.pid=%s main=%s executable=%s\n' \
            "$java_pid" "${java_main:-UNKNOWN}" \
            "$(readlink -f "/proc/$java_pid/exe" 2>/dev/null || printf UNKNOWN)"
        done < <(jps -l 2>/dev/null || true)
      fi
      if command -v ps >/dev/null 2>&1; then
        ps -eo pid=,user=,comm= | grep -Ei \
          '(java|mysqld|mysql|hive|kafka|spark|datax|namenode|datanode|resourcemanager|nodemanager)' || true
      fi
      if command -v ss >/dev/null 2>&1; then
        ss -lntup 2>&1 || true
      else
        printf '%s\n' 'listening_ports=UNKNOWN_ss_unavailable'
      fi
      ;;
    component-inventory)
      mysql_bin=$(command_path mysqld /usr/sbin/mysqld /usr/bin/mysqld || true)
      hive_bin=$(command_path hive /data/module/hive/bin/hive || true)
      kafka_bin=$(command_path kafka-topics.sh /data/module/kafka/bin/kafka-topics.sh || true)
      spark_bin=$(command_path spark-submit /data/module/spark/bin/spark-submit || true)
      datax_bin=$(command_path datax.py || true)
      if [[ -z $datax_bin ]]; then
        for datax_candidate in \
          /data/module/datax/bin/datax.py \
          /data/module/datax-current/bin/datax.py; do
          if [[ -r $datax_candidate ]]; then
            datax_bin=$(readlink -f "$datax_candidate" 2>/dev/null || printf '%s\n' "$datax_candidate")
            break
          fi
        done
      fi

      for record in \
        "MYSQL_HOME:${MYSQL_HOME:-UNSET}" \
        "HIVE_HOME:${HIVE_HOME:-UNSET}" \
        "HADOOP_HOME:${HADOOP_HOME:-UNSET}" \
        "HADOOP_CONF_DIR:${HADOOP_CONF_DIR:-UNSET}" \
        "SPARK_HOME:${SPARK_HOME:-UNSET}" \
        "DATAX_HOME:${DATAX_HOME:-UNSET}"; do
        printf 'environment.%s\n' "$record"
      done

      printf 'stable.mysql=%s\n' "$(resolved_directory /data/module/mysql)"
      printf 'stable.hive=%s\n' "$(resolved_directory /data/module/hive)"
      printf 'stable.kafka=%s\n' "$(resolved_directory /data/module/kafka)"
      printf 'stable.spark=%s\n' "$(resolved_directory /data/module/spark)"
      printf 'stable.datax=%s\n' "$(resolved_directory /data/module/datax)"
      printf 'stable.datax_current=%s\n' "$(resolved_directory /data/module/datax-current)"
      if [[ -d /data/module ]]; then
        while IFS= read -r hive_candidate; do
          printf 'installed.hive=%s\n' "$hive_candidate"
        done < <(find /data/module -mindepth 1 -maxdepth 1 -type d \
          -name 'apache-hive-*' -print 2>/dev/null | sort)
      fi

      for pair in \
        "mysql:$mysql_bin" "hive:$hive_bin" "kafka:$kafka_bin" \
        "spark:$spark_bin" "datax:$datax_bin"; do
        component=${pair%%:*}
        executable=${pair#*:}
        if [[ -n $executable ]]; then
          printf 'component.%s=FOUND\n' "$component"
          printf 'component.%s.command=%s\n' "$component" "$executable"
          if [[ $component == datax ]]; then
            if command -v python3 >/dev/null 2>&1; then
              printf 'component.datax.python=%s\n' "$(command -v python3)"
              printf 'component.datax.python_version=%s\n' "$(python3 --version 2>&1 || printf UNKNOWN)"
            else
              printf '%s\n' 'component.datax.python=NOT_FOUND'
            fi
            printf 'component.datax.entry_sha256='
            if command -v sha256sum >/dev/null 2>&1; then
              sha256sum "$executable" 2>/dev/null | awk '{print $1}' || printf 'UNKNOWN\n'
            else
              printf 'UNKNOWN_sha256sum_unavailable\n'
            fi
            if command -v stat >/dev/null 2>&1; then
              stat -c 'component.datax.entry_mtime=%y' "$executable" 2>/dev/null || true
            fi
          else
            printf 'component.%s.version.begin\n' "$component"
            safe_version "$component" "$executable"
            printf 'component.%s.version.end\n' "$component"
          fi
        else
          printf 'component.%s=NOT_FOUND\n' "$component"
        fi
      done

      datax_home=$(resolved_directory /data/module/datax)
      if [[ $datax_home == NOT_FOUND ]]; then
        datax_home=$(resolved_directory /data/module/datax-current)
      fi
      if [[ $datax_home != NOT_FOUND ]]; then
        print_path_record 'datax_plugin.mysqlreader' "$datax_home/plugin/reader/mysqlreader"
        print_path_record 'datax_plugin.hdfswriter' "$datax_home/plugin/writer/hdfswriter"
        print_path_record 'datax_log.log' "$datax_home/log"
        print_path_record 'datax_log.log_perf' "$datax_home/log_perf"
      else
        printf '%s\n' 'datax_plugin.mysqlreader=NOT_FOUND'
        printf '%s\n' 'datax_plugin.hdfswriter=NOT_FOUND'
        printf '%s\n' 'datax_log.log=NOT_FOUND'
        printf '%s\n' 'datax_log.log_perf=NOT_FOUND'
      fi
      ;;
    component-config-whitelist)
      mysql_allow='^(bind-address|mysqlx-bind-address|port|datadir|socket|pid-file|log-error|server-id|log-bin|binlog_format|binlog_row_image|expire_logs_days|binlog_expire_logs_seconds|character-set-server|collation-server|default-time-zone)$'
      for file in \
        /etc/mysql/my.cnf \
        /etc/mysql/mysql.cnf \
        /etc/mysql/mysql.conf.d/mysqld.cnf \
        /data/module/mysql/my.cnf; do
        print_kv_whitelist "$file" "$mysql_allow"
      done

      hive_home=$(resolved_directory /data/module/hive)
      if [[ $hive_home != NOT_FOUND ]]; then
        print_hive_xml_whitelist "$hive_home/conf/hive-site.xml"
      else
        printf '%s\n' 'hive_config=NOT_FOUND'
      fi

      kafka_allow='^(process.roles|node.id|controller.quorum.voters|controller.listener.names|listeners|advertised.listeners|listener.security.protocol.map|inter.broker.listener.name|log.dirs|metadata.log.dir|num.partitions|default.replication.factor|min.insync.replicas|auto.create.topics.enable|delete.topic.enable)$'
      kafka_home=$(resolved_directory /data/module/kafka)
      if [[ $kafka_home != NOT_FOUND ]]; then
        for file in "$kafka_home/config/server.properties" "$kafka_home/config/kraft/server.properties"; do
          print_kv_whitelist "$file" "$kafka_allow"
        done
      else
        printf '%s\n' 'kafka_config=NOT_FOUND'
      fi
      for file in /data/kafka/meta.properties /data/kafka/metadata.properties; do
        print_kv_whitelist "$file" '^(cluster.id|node.id|version)$'
      done
      if [[ -d /data/kafka ]]; then
        while IFS= read -r file; do
          print_kv_whitelist "$file" '^(cluster.id|node.id|version)$'
        done < <(find /data/kafka -maxdepth 4 -type f -name meta.properties -print 2>/dev/null)
      fi

      spark_allow='^(spark.master|spark.submit.deployMode|spark.eventLog.enabled|spark.eventLog.dir|spark.history.fs.logDirectory|spark.sql.warehouse.dir|spark.sql.catalogImplementation|spark.yarn.queue|spark.local.dir)$'
      spark_home=$(resolved_directory /data/module/spark)
      if [[ $spark_home != NOT_FOUND ]]; then
        print_kv_whitelist "$spark_home/conf/spark-defaults.conf" "$spark_allow"
        print_kv_whitelist "$spark_home/conf/spark-env.sh" \
          '^(SPARK_HOME|SPARK_CONF_DIR|SPARK_LOG_DIR|SPARK_LOCAL_DIRS|HADOOP_CONF_DIR|YARN_CONF_DIR)$'
      else
        printf '%s\n' 'spark_config=NOT_FOUND'
      fi

      datax_home=$(resolved_directory /data/module/datax)
      if [[ $datax_home == NOT_FOUND ]]; then
        datax_home=$(resolved_directory /data/module/datax-current)
      fi
      printf 'datax.home=%s\n' "$datax_home"
      if [[ $datax_home != NOT_FOUND ]]; then
        printf 'datax.mysqlreader=%s\n' "$(resolved_directory "$datax_home/plugin/reader/mysqlreader")"
        printf 'datax.hdfswriter=%s\n' "$(resolved_directory "$datax_home/plugin/writer/hdfswriter")"
      else
        printf '%s\n' 'datax.mysqlreader=NOT_FOUND'
        printf '%s\n' 'datax.hdfswriter=NOT_FOUND'
      fi
      ;;
    *)
      printf 'Unknown remote section: %s\n' "$section" >&2
      return 2
      ;;
  esac
}

run_remote_section() {
  local node=$1
  local section=$2
  {
    declare -f remote_collect
    printf '%s\n' 'remote_collect "$1" "$2"'
  } | ssh -o BatchMode=yes -o ConnectTimeout=10 "$node" bash -s -- "$section" "$node"
}

printf 'run_id=%s\n' "$run_id"
printf 'started_at=%s\n' "$(date --iso-8601=seconds)"
printf 'output_dir=%s\n' "$output_dir"
printf 'evidence_boundary=%s\n' 'inventory only; no component functional acceptance'

collection_failed=0
collection_partial=0

for node in "${nodes[@]}"; do
  node_dir="$output_dir/$node"
  mkdir -p "$node_dir"
  node_status[$node]=COLLECTED

  if ! remote_epoch=$(ssh -o BatchMode=yes -o ConnectTimeout=10 "$node" date +%s 2>/dev/null); then
    printf 'Unable to collect clock or establish SSH to %s\n' "$node" >&2
    node_status[$node]=FAIL
    node_clock_skew[$node]=UNKNOWN
    collection_failed=1
    continue
  fi

  local_epoch=$(date +%s)
  if [[ $remote_epoch =~ ^[0-9]+$ ]]; then
    skew=$((local_epoch - remote_epoch))
    ((skew < 0)) && skew=$((-skew))
    node_clock_skew[$node]=$skew
    if ((skew > max_clock_skew_seconds)); then
      printf 'Clock skew exceeds threshold on %s: %ss > %ss\n' \
        "$node" "$skew" "$max_clock_skew_seconds" >&2
      node_status[$node]=FAIL
      collection_failed=1
    fi
  else
    node_clock_skew[$node]=UNKNOWN
    node_status[$node]=FAIL
    collection_failed=1
  fi

  for section in "${sections[@]}"; do
    evidence_file="$node_dir/$section.txt"
    if ! run_remote_section "$node" "$section" > "$evidence_file" 2>&1; then
      printf 'Section collection failed: node=%s section=%s file=%s\n' \
        "$node" "$section" "$evidence_file" >&2
      node_status[$node]=FAIL
      collection_failed=1
    fi
  done
done

for component in "${components[@]}"; do
  found_count=0
  not_found_count=0
  unknown_count=0
  for node in "${nodes[@]}"; do
    inventory_file="$output_dir/$node/component-inventory.txt"
    if [[ ! -r $inventory_file ]]; then
      unknown_count=$((unknown_count + 1))
    elif grep -Fxq "component.$component=FOUND" "$inventory_file"; then
      found_count=$((found_count + 1))
    elif grep -Fxq "component.$component=NOT_FOUND" "$inventory_file"; then
      not_found_count=$((not_found_count + 1))
    else
      unknown_count=$((unknown_count + 1))
    fi
  done

  if ((found_count > 0)); then
    component_status[$component]=FOUND
  elif ((not_found_count == ${#nodes[@]})); then
    component_status[$component]=NOT_FOUND
    collection_partial=1
  else
    component_status[$component]=UNKNOWN
    collection_partial=1
  fi
done

if ((collection_failed == 1)); then
  overall_status=FAIL
  printf '%s\n' 'VM environment evidence collection failed; review summary.env and node evidence.' >&2
  exit 5
elif ((collection_partial == 1)); then
  overall_status=PARTIAL
  printf '%s\n' 'VM evidence was collected; one or more component installations were not found or remain unknown.'
else
  overall_status=COLLECTED
  printf '%s\n' 'VM and installed-component evidence collection completed.'
fi

printf 'completed_at=%s\n' "$(date --iso-8601=seconds)"
