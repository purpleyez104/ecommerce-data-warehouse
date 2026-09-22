# tests/：仅测试、验收、故障注入（与正式工程分离）

- `unit/`：原生成器的 8 项 pytest，已从工程目录移入本目录。
- `mysql/sql/acceptance.sql`：仓库根目录下的原生只读批次业务验收 SQL，`<RUN_ID>` 为替换占位符。
- `scripts/check_batch_mysql.sh`：只读调用验收 SQL；`read_runtime.sh`：读取 YARN/Flink/Kafka 状态。
- `scripts/check_snapshot_21.py`：读取最初 32 条 CDC 快照（仅初始基线适用）。
- `scripts/check_empty_table_probes.py`：两张原空表的 INSERT / DELETE 事件匹配。
- `scripts/check_order_batch_cdc.py`：按 run-id 核对创建事件及最终订单状态，不核对其他表。
- `fault_injection/`：破坏性故障注入，**默认不执行**，需要隔离环境与人工批准。
- `evidence/`：来自已给出终端结果的静态验收摘要，不代表本包直接连库。

## 使用示例

从**仓库根目录**运行：

```bash
bash tests/run_unit.sh
```

核对批次（只读）：

```bash
bash tests/scripts/check_batch_mysql.sh hist-v1-001
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
