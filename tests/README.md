# tests/：仅测试、验收、故障注入（与正式工程分离）

- `../mock/generator/*/tests/`：V2 Business / Behavior Generator 的 Targeted Unit Test；通过只证明本地代码契约，不证明 Source Gate 或目标环境 Runtime。
- `../archive/pilot-v1/ecommerce_generator_v1/tests/`：旧 Pilot Generator 测试，仅用于历史复核，不作为 V2 正式入口。
- `datax/`：DataX Job Generator 的环境变量展开、JSON 生成和缺失配置失败测试。
- 原 `mysql/sql/acceptance.sql` 已从当前工作区移除；新的权威批次业务验收 SQL 尚未确认。
- `scripts/read_runtime.sh`：读取 YARN/Flink/Kafka 状态。
- `scripts/check_snapshot_21.py`：读取最初 32 条 CDC 快照（仅初始基线适用）。
- `scripts/check_empty_table_probes.py`：两张原空表的 INSERT / DELETE 事件匹配。
- `scripts/check_order_batch_cdc.py`：按 run-id 核对创建事件及最终订单状态，不核对其他表。
- `../archive/pilot-v1/realtime/acceptance/check_dwd_order_consistency.sh`：只读比较冻结 100 单的 MySQL/Doris 汇总、订单主键、状态及三个金额字段；当前为 `implemented / not_run`。
- `../archive/pilot-v1/offline/reference/check_ods_order_quality.sh`：以 Spark SQL 只读核对 `hist-v1-001` 的订单数、状态、88 个分区、三项金额及审计/日期规则；当前为 `implemented / not_run`。
- `fault_injection/`：破坏性故障注入，**默认不执行**，需要隔离环境与人工批准。

## 使用示例

从**仓库根目录**运行：

```bash
bash tests/run_unit.sh
```

订单 CDC：先记录 Kafka 分区、起始 offset、实际消息数量，精准读取并通过管道交给 Python，**不要假定持续运行中的 Topic 永远是同一个 offset**：

```bash
kafka-console-consumer.sh --bootstrap-server hadoop201:9092 \
 --topic cdc_m2_21tables_acceptance --partition 0 --offset 235 \
 --max-messages 1535 --timeout-ms 15000 \
 | python3 tests/scripts/check_order_batch_cdc.py \
    --run-id hist-v1-001 --orders 100 --paid 69 --canceled 31 --messages 1535
```

以上 235/1535 仅为历史记录的精准回放示例，并非实时消费配置。快照脚本的32行基线也仅适用于2026-09-20的生成器写入之前，不要用它验收当前新增数据。

订单 DWD 逐行对账须在目标 ECS、确认仍使用冻结 100 单基线后执行：

```bash
bash archive/pilot-v1/realtime/acceptance/check_dwd_order_consistency.sh
```

只有退出码为 `0` 且输出 `ORDER_DWD_CONSISTENCY: PASS` 才表示脚本覆盖的主键、状态及金额字段一致；不代表订单 UPDATE、Checkpoint、恢复或端到端 Exactly-Once 已通过。

订单 ODS 固定基线检查须在目标 ECS、确认 Hive 表仍对应 `hist-v1-001` 后执行：

```bash
bash archive/pilot-v1/offline/reference/check_ods_order_quality.sh
```

只有退出码为 `0` 且输出 `ODS_ORDER_QUALITY: PASS` 才表示九列固定基线一致。该入口不负责 DataX 抽取、HDFS 分区移动或 Hive 分区注册；验收来源和限制见 `docs/acceptance/biz_order_ods_acceptance.md`。
