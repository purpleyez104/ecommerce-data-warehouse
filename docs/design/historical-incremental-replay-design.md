# 历史初始化、双链路回放与拉链维度设计

状态：本地 Business/Behavior Replay 输入 `implemented / verified`；数据库、ODS、Kafka、CDC Runtime `not_run`

更新时间：2026-10-13

本文定义正式 90 天数据如何用于历史初始化、后续增量回放、离线与实时链路接续，以及 DIM SCD Type 2 拉链维度构建。它落实 `DR-037`，但不证明 Incremental Business Generator、批量 ODS、Formal CDC、DIM/DWD、Doris 接管或离实时对账已经实现或运行。

业务规则以[业务基线](../business/business-baseline.md)为准，源表字段以[物理模型](../source/physical-model.md)为准，离线和实时的阶段门禁以[阶段计划](../plan.md)为准。本文不授权清理或重新装载现有数据库，也不改变 2026-10-12 正式 90 天 bundle、1,328,502 行 MySQL 装载和 Shared Source Gate 的既有证据边界。

## 1. 目标与时间边界

正式数据仍覆盖连续 90 个业务日，但链路验收按同一确定性数据集拆分为：

```text
[history_start, cutover_time)       前 60 天：历史初始化窗口
[cutover_time, replay_end_exclusive) 后 30 天：逐日双链路回放窗口
```

`cutover_time` 固定为第 61 个业务日的 `00:00:00 Asia/Shanghai`，`replay_end_exclusive` 为第 91 个业务日零点。所有窗口统一使用左闭右开语义。任务不得使用执行机器当前日期推导时间范围。

90 天是完整观察窗口，不等于把 90 天最终状态一次性作为初始化输入。现有正式 bundle 和 Source Gate 继续证明规模、Schema、引用、状态与金额 Contract；新的时间推进式验收还必须提供：

- `bootstrap`：截至 `cutover_time` 的源表正确当前状态、前 60 天事实、事件和维度变化历史。
- `daily/day_61`～`daily/day_90`：每天的新增、更新、失效/删除、状态事件、维度变化和预期对账结果。
- 确定性的 Seed、`history_start`、`cutover_time`、`replay_end_exclusive`、Manifest SHA-256 与 `batch_id`。
- 可按业务动作顺序写入 MySQL 的增量操作；交易 CDC 不得通过直接写 Kafka 伪造。

如果初始化记录已经带有切换点之后才形成的最终状态，就构成未来数据泄漏，不能用于证明增量回放正确。

## 2. 总体数据流

```text
前 60 天 bootstrap
  ├─ MySQL 截至 T 的业务状态与历史
  │    ├─ DataX → HDFS batch staging → Hive ODS → Spark DIM/DWD → DWS → ADS
  │    │                                              └→ Doris 离线历史基线
  │    └─ Flink CDC Initial Snapshot → Kafka Snapshot Gate → 实时源状态基线
  └─ Historical Behavior Bundle → HDFS/Hive 行为历史基线（Bundle 已验证；装载入口待实现）

后 30 天 daily package
  ├─ Business Operations → MySQL Transaction → Binlog → Flink CDC → Kafka
  │                                                   → Flink → Doris 实时结果
  ├─ Behavior Events ────────────────────────────────→ Kafka → Flink/归档
  └─ 日终 DataX 增量 → HDFS batch staging → Hive ODS → Spark 重算
                                                     → Doris 离线结果
```

DataX 与 CDC 共享 MySQL 业务源和切换点，但职责不同：DataX 形成可重跑、可回补和可对账的离线结果；CDC/Flink 提供切换点后的低延迟结果。Kafka Raw CDC 只承担传输和有界重放，不是长期数仓存储。

历史 Behavior 与交易数据共享 90 天时间轴和 Entity Manifest，但不经过 MySQL/DataX。Behavior 使用一次 90 天生成结果切分为前 60 天 Bootstrap 与后 30 天 Daily Package，以保留跨日 Session；本地 Bundle 已完成。前 60 天批量归档入口、后 30 天 Kafka Topic、Schema、Partition 和保留期仍须在对应阶段实现并验收。

## 3. 切换点建立

切换点按以下顺序建立：

1. 在隔离环境只装载前 60 天业务操作，并将可变表推进到 `cutover_time` 前的正确状态。
2. 暂停 Incremental Business Generator，不允许切换期间继续写源。
3. 记录数据集版本、Manifest SHA-256、切换时间、各表行数、增量水位和 MySQL Binlog Offset。
4. 执行 DataX 历史初始化并完成 ODS 初始化 Gate。
5. 执行 Formal CDC Initial Snapshot，并以 Kafka Snapshot Gate 冻结表级和主键级基线。
6. 两条初始化链路均通过后，才从 `daily/day_61` 开始恢复 MySQL 事务写入和 Behavior Kafka 写入。

DataX 初始化和 CDC Snapshot 必须对应同一源端一致性点。具体锁、事务隔离和 Binlog Offset 获取方式在实现前固化；未证明一致性时保持 `not_run`，不能用两个独立完成时间相近的任务代替一致性证明。

## 4. 离线链路

### 4.1 前 60 天初始化

初始化抽取范围按数据类型确定：

| 类型 | 初始化输入 | ODS/DIM/DWD 归属 |
| --- | --- | --- |
| 当前状态维度源 | `cutover_time` 时刻完整快照 | ODS 使用快照日期；DIM 决定 Type 1 或 SCD2 |
| 事务事实 | 业务发生时间 `< cutover_time` 的全部历史记录 | 按事实自身业务日期写入 `dt` |
| 不可变事件 | 事件发生时间 `< cutover_time` 的全部事件 | 按事件发生日期写入 `dt` |
| 维度变化历史 | 生效时间 `< cutover_time` 的全部版本或每日快照 | 用于构建截至切换点的 SCD2 时间线 |

DataX 输出先进入批次隔离路径，完成文件、Schema、主键、行数、状态和金额检查后，才能原子发布并注册 Hive 分区。前 60 天事实必须按照记录自身业务日期分散到对应 `dt`，不能全部写入初始化执行日。

### 4.2 后 30 天日批增量

可变源表按可靠的 `source_updated_at` 半开窗口抽取；Append-only 表按 `recorded_at` 或 `merged_at` 记录水位抽取；小型且没有可靠更新时间的维度源使用每日全量快照。当前 21 表 Contract 中，`biz_identity_mapping` 因 `recorded_at` 不随撤销或 `effective_to` 补写可靠变化而明确采用每日全量快照。抽取窗口和业务分区不能混用：

```text
source_updated_at / recorded_at / merged_at → 决定增量批次抽取什么
snapshot_date                              → 决定全量快照批次与快照分区
business_time / effective_at               → 决定事实归属哪个 dt 或维度版本
load_time                                  → 只负责运行审计
```

例如第 61 天取消一张第 20 天创建的订单：增量批次是 `day_61`，订单当前状态事实仍归属 `dt=day_20`，取消事件归属 `dt=day_61`。发布任务必须识别并原子重建受影响的历史业务分区，而不是把旧订单移动到第 61 天。

### 4.3 重跑与回补

所有批任务显式接收：

```text
business_date
window_start
window_end
batch_id
dataset_version
```

重跑流程固定为：独立 staging → 校验 → 计算受影响分区 → 原子发布 → 下游重算 → 对账。相同业务窗口重复执行必须得到相同业务结果；新的 `batch_id`、`extract_time` 和 `load_time` 只形成新的运行审计，不得制造重复业务记录。

## 5. 实时链路

### 5.1 Initial Snapshot

Formal CDC 在切换点对 MySQL 当前状态执行 Initial Snapshot，并从一致的 Binlog Offset 接续增量。Snapshot Envelope 必须与后续 `INSERT/UPDATE/DELETE` 区分：Snapshot 用于初始化源状态和实时维度状态，不得把前 60 天全部存量订单统计成第 61 天新增交易。

前 60 天历史指标由离线结果提供。需要跨切换点累计的实时指标，应读取已验收的离线基线或采用另行验证的状态初始化方案；不得把历史数据伪装为实时业务事件。

### 5.2 后 30 天回放

每天的业务操作包只通过 MySQL Transaction 修改当前状态并写入不可变事件，由 ROW/FULL Binlog 产生真实 CDC：

```text
daily/day_N
→ MySQL Transaction
→ Binlog
→ Flink CDC
→ Kafka Raw CDC
→ Domain Flink Application
→ Doris 实时明细或指标
```

Behavior 事件由独立行为源写 Kafka，保留稳定 `event_id`、`event_time`、`ingest_time`、身份、Session 和商品引用；它不能通过 MySQL CDC 伪造。具体 Topic、Key、Partition、Watermark、迟到、去重、状态 TTL、Doris Key 模型和一致性目标仍由 Milestone 8 契约冻结。

## 6. 离实时接管与对账

切换点后，实时结果只负责尚未完成离线结算的开放业务日；离线日批通过 Gate 后逐日接管：

```text
第61天白天：第1～60天离线结果 + 第61天实时结果
第62天日批完成：第1～61天离线结果 + 第62天实时结果
...
第90天日批完成：第1～90天离线结果
```

服务层必须通过明确的结算边界或版本选择避免把同一业务日的离线值和实时值无条件相加。每日最低对账包括源端、CDC/Kafka、ODS、DIM/DWD 与 Doris 的行数/主键，以及订单、支付、退款金额和状态；差异无法解释时，离线结果不得接管该业务日。

## 7. 时间与审计 Contract

ODS、DIM/DWD 和运行审计至少保留或可追溯：

| 字段 | 责任 |
| --- | --- |
| `business_time` | 事实或事件真正发生时间，决定业务归属 |
| `effective_at` | 维度属性或状态版本生效时间 |
| `source_updated_at` | 可变源记录的增量抽取水位 |
| `extract_time` | DataX 读取源数据的时间 |
| `load_time` | 数据进入正式层的时间 |
| `business_date` / `dt` | 事实/事件业务日期或维度快照日期 |
| `batch_id` | 初始化、日批或回补运行标识 |
| `source_system` / `source_table` | 数据来源 |
| `operation_type` | `SNAPSHOT/INSERT/UPDATE/DELETE` 或等价操作 |
| `source_offset` | CDC Binlog Offset 或等价可重放位置 |

事实与事件按业务发生日期分区；维度全量快照按快照日期分区；抽取和装载时间只用于审计。源表没有可靠水位时，不得用数仓生成的 `load_time` 冒充源端变化时间。

## 8. SCD Type 2 拉链维度

### 8.1 适用范围

只有需要按历史属性还原事实的维度使用 SCD2。商品价格、类目归属、品牌和上下架状态是当前明确的候选；只关心当前值的稳定属性采用 Type 1。身份映射继续使用自身有效区间表达，不为追求形式重复建设第二套拉链。

Milestone 4 已在 `hive/model/model_contract.json` 冻结精确映射：`dim_product_zip` 跟踪价格、类目、品牌和上下架状态并使用 SCD2；`dim_identity_mapping` 沿用源有效区间；其他首批当前值维度使用 Type 1。修改前 6 张 DIM 与 8 张 DWD、2 张 DWS 与 1 张 ADS 已完成 Runtime Gate；M5-02 后当前申请粒度 `dwd_refund` 与下游 Aggregate 修正版也已完成受控迁移、Gate 和幂等重跑。

### 8.2 输入前提

完整 90 天拉链需要完整的维度变化历史。输入优先级为：

```text
带业务 effective_at 的变更事件
> 带可靠 source_updated_at 的变更记录
> 每日全量快照差异
```

如果只有第 60 天最终快照，只能从 `cutover_time` 开始记录版本，不能虚构前 60 天变化。当前 `biz_product_change_event` 是商品历史的候选来源，但其字段覆盖和版本连续性仍须在 DIM 实现前校验。

### 8.3 表结构与区间

拉链维度至少包含：

```text
surrogate_key
business_key
tracked_attributes
attribute_hash
effective_from
effective_to
is_current
source_updated_at
load_time
batch_id
```

有效区间使用 `[effective_from, effective_to)`；当前版本使用约定的开放结束时间和 `is_current=true`。`attribute_hash` 只包含被跟踪的业务属性，不包含 `batch_id`、`extract_time`、`load_time` 等审计字段。

### 8.4 前 60 天初始化

对每个业务键按 `effective_at` 排序并去重，当前版本的 `effective_to` 取下一版本的 `effective_from`，最后一个版本保持开放。初始化结果必须能够让切换点前的历史事实按业务时间命中且只命中一个维度版本。

### 8.5 后 30 天增量维护

对于当天变化的业务键：

- 业务键不存在：插入首个版本。
- 当前版本的 `attribute_hash` 相同：不生成新版本。
- `attribute_hash` 不同：关闭旧版本，并以业务生效时间插入新版本。

小规模维度优先重新生成受影响业务键的完整时间线；如果 Hive Merge 增加不必要复杂度，可以每日原子覆盖整张小型 DIM 拉链表。不得仅为了展示技术而引入额外存储格式或事务表依赖。

### 8.6 迟到变化与重跑

迟到维度变化按 `effective_at` 插回历史时间线。任务读取受影响业务键的全部历史版本，合并迟到变化，重新排序并生成完整有效区间，再原子替换该业务键或小型维度表。`load_time` 记录何时收到修正，但不能改变业务生效时间。

### 8.7 质量规则

- 每个业务键最多一个 `is_current=true`。
- `effective_from < effective_to`。
- 同一业务键的版本区间不重叠。
- 连续相同 `attribute_hash` 不产生重复版本。
- 相同业务键和 `effective_from` 唯一。
- 历史事实按业务时间只能命中一个维度版本。
- 切换点当前版本与源表快照一致。
- 迟到修正与同批次重跑后结果确定且无重复。

## 9. 验收边界

该设计只有在以下证据全部形成后才能从 `DESIGNED / not_run` 提升：

1. 固定 Seed 能重复生成相同 bootstrap、30 个 daily package、Manifest 和预期结果。
2. 初始化源状态不存在 `cutover_time` 之后的未来数据泄漏。
3. DataX 初始化把前 60 天事实发布到正确业务日期分区。
4. 连续 30 个增量窗口无水位缺口、无不可解释重复，并能重算历史分区。
5. Formal CDC Snapshot 与记录的 Binlog Offset 接续，无 Snapshot/增量重复统计。
6. INSERT/UPDATE/DELETE、迟到、重复、空日、失败恢复和回放通过。
7. SCD2 初始化、日增量、迟到修正和事实历史关联通过质量规则。
8. 离线逐日接管实时开放日，源端、离线和实时结果差异可解释。
9. 失败返回非零并阻断下游，重跑不会破坏已验收结果。

现有正式 90 天最终 bundle、Source Gate、Pilot ODS 与 Pilot CDC 证据均不能单独替代上述时间推进式验收。

## 10. 实施边界与回滚

Business Generator 已输出并本地审计 Seed `20260105`、Dataset `v2.3-replay-formal-20260105-r2` 的正式 Bootstrap、30 个 Daily Package、Manifest 和预期结果；正式规模重生成的 146 个文件逐文件 SHA-256 一致。Behavior 已基于同一时间轴和 Business r2 Entity Manifest 输出 Dataset `v2.3-behavior-replay-formal-20260105-r1`，共 3,000,000 条事件、一个 Day 1～60 Bootstrap 和 30 个 Daily Package，独立审计通过。下一步需单独授权后装载隔离 Source，再接续 DataX 受影响分区发布；Kafka Topic/Checkpoint Contract 冻结后另行授权 Behavior/CDC Runtime。任何数据库重置、重新装载、Topic 创建、CDC 启动、Doris 清理或正式回放都需要对应授权和可回滚方案。

若时间推进式实现失败，保留现有 90 天正式 bundle、正式 MySQL 与 Source Gate 证据不变；隔离失败的 replay 数据库、Topic、Checkpoint、HDFS staging 和 Doris 目标，保存失败证据后修正 Contract。不得通过直接修改既有正式数据、复用 Pilot Offset/Checkpoint 或降低 Gate 规则来绕过失败。
