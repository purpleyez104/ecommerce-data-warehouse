# M7 Spark 性能实验验收

验收日期：2026-10-21
状态：`VERIFIED`

## 1. 验收范围

本验收使用隔离 Hive Database `ecommerce_benchmark` 和 HDFS Root
`/warehouse/ecommerce/benchmark/m7-spark-20261020-r1`，只读复用已验收的
`ecommerce_dwd` / `ecommerce_dim`，不修改正式数仓表。固定 Contract 位于
`spark/benchmark/benchmark_contract.json`。

固定输入为：

| 对象 | 行数 |
| --- | ---: |
| `benchmark_order` | 900,000 |
| `benchmark_order_item` | 2,565,000 |
| `benchmark_behavior_event` | 9,000,000 |
| `benchmark_product` | 4,000 |

时间范围为 `2025-12-01..2026-02-28`，分区裁剪目标日为 `2026-02-14`。
数据使用 ORC + Snappy，HDFS 物理数据约 135 MB；当前集群副本占用约 271 MB。

## 2. 执行与证据

Setup SQL 由 `spark/scripts/render_benchmark_sql.py` 确定性生成。首次执行因源
`order_id` 为 `INT`，复制键表达式在提升为 `BIGINT` 前发生 Arithmetic Overflow；
修复为显式 `CAST(... AS BIGINT)` 后，从空隔离库重新执行并输出
`M7_BENCHMARK_SETUP_PASS`。Setup 内置四表行数和三张事实表业务键唯一性断言。

六个 Smoke Application 均成功，三组 Baseline / Optimized 的 `M7_RESULT` 分别
完全一致。Physical Plan 证明：

- 分区优化方案出现 `PartitionFilters: dt = 2026-02-14`，Baseline 不包含分区过滤。
- Join 两个方案分别出现 `SortMergeJoin` 与 `BroadcastHashJoin + BroadcastExchange`。
- 两阶段聚合比普通聚合多一层局部/全局 `HashAggregate`。

`spark/scripts/run_benchmark.sh` 将 Smoke 作为 Warm-up，随后为每个变体运行三次
Measured Application，共 18 次。每次均保存 SQL、日志、Application ID、结果指纹、
Spark Event Log 与 Metrics JSON；`spark/scripts/summarize_benchmark_metrics.py` 校验
每个变体恰有 `run_index=1,2,3`，且 `failed_job_count=0`、
`failed_task_count=0`。最终输出：

```text
M7_MEASURED_PASS runs=18
M7_BENCHMARK_SUMMARY_PASS variants=6 measured_runs=18
```

原始运行证据保存在服务器：

```text
/data/projects/ecommerce-data-warehouse-m6/runtime/benchmark/m7-spark-20261020-r1/
```

同一证据已同步到本地 Git Ignore 目录：

```text
runtime/benchmark/m7-spark-20261020-r1/
```

## 3. 三次测量中位数

| 实验 | Baseline | 对比方案 | Duration | Input bytes | Shuffle read/write | Stage | Task |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 分区裁剪 | 无效时间表达式过滤 | 正确 `dt` 过滤 | 35,672 → 32,979 ms | 9,274,966 → 3,311,644 | 574 → 160 bytes | 3 → 2 | 99 → 3 |
| Join | Sort Merge Join | Broadcast Hash Join | 42,587 → 43,333 ms | 8,575,048 → 8,575,048 | 6,114,668 → 12,186 bytes | 6 → 5 | 119 → 111 |
| 倾斜聚合 | 普通聚合 | 两阶段加盐聚合 | 38,456 → 39,625 ms | 63,128,186 → 63,128,186 | 409,103 → 6,316,203 bytes | 4 → 5 | 107 → 115 |

补充资源指标：Broadcast Join 的 Executor Run Time 中位数由 24,568 ms 降至
20,345 ms，Executor CPU Time 由 16.25s 降至 12.00s；两种 Join 均无 Spill。

## 4. 验收结论

- 分区裁剪在本次固定输入上有效：扫描字节、Stage、Task 和端到端中位耗时均下降；
  中位耗时约降低 7.6%。
- Broadcast Join 将 Shuffle 从约 6.11 MB 降至约 12 KB，并降低 Executor Time / CPU，
  但端到端中位耗时约增加 1.8%；因此只能陈述资源效率改善，不能陈述作业耗时提升。
- 当前 `COUNT/SUM` 场景中，Spark 的 `HashAggregate` 已执行 map-side partial
  aggregation；额外加盐增加分组和 Shuffle，两阶段方案没有收益。该结果作为负实验
  和适用边界保留，不通过修改数据或反复调参制造正向结论。

M7 Acceptance 已满足：固定版本、输入、SQL、Physical Plan、扫描量、Shuffle、
Stage、Task、Job/Application Duration、多次执行结果及适用限制均有真实证据。

## 5. 可复现与回滚

在已完成隔离 Setup 与 Smoke 的目标环境执行：

```bash
bash spark/scripts/run_benchmark.sh
python3 spark/scripts/summarize_benchmark_metrics.py \
  --metrics-dir runtime/benchmark/m7-spark-20261020-r1/measured \
  --output runtime/benchmark/m7-spark-20261020-r1/measured/summary.json
```

Runner 任一 Spark 失败、结果指纹漂移或 Event Log 缺失都会返回非零状态。隔离资产
需要回收时，仅允许删除 `ecommerce_benchmark` 和上述版本化 HDFS Root；正式
`ecommerce_dwd` / `ecommerce_dim` 保持只读。任何实际清理仍需单独授权。

## 6. 自动化验证

2026-10-21 本地统一入口 `tests/run_unit.sh` 通过 155/155，其中 M7 Benchmark 9 项；
该自动化结果证明 Contract、Renderer、Collector、Runner 与 Summary 的静态/单元范围，
真实性能结论仍以本验收记录的 YARN Applications 和 Spark Event Log 为准。
