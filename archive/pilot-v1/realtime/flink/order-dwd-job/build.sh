#!/usr/bin/env bash
set -euo pipefail
FLINK_HOME="${FLINK_HOME:-/data/module/flink-1.20.5-cdc}"
ROOT="$(cd "$(dirname "$0")" && pwd)"
for pattern in "flink-doris-connector-1.20-26.1.1.jar" "flink-sql-connector-kafka-3.3.0-1.20.jar"; do
  test -f "$FLINK_HOME/lib/$pattern" || { echo "MISSING: $FLINK_HOME/lib/$pattern"; exit 1; }
done
command -v javac >/dev/null || { echo 'MISSING: javac'; exit 1; }
mkdir -p "$ROOT/build/classes"
javac --release 11 -encoding UTF-8 -cp "$FLINK_HOME/lib/*" -d "$ROOT/build/classes" "$ROOT/src/com/ecommerce/r1/OrderDwdJob.java"
jar --create --file "$ROOT/build/r1-order-dwd.jar" --main-class com.ecommerce.r1.OrderDwdJob -C "$ROOT/build/classes" .
echo "BUILT: $ROOT/build/r1-order-dwd.jar"
