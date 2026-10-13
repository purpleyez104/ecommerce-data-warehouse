# V2 离实时一体化数仓整体实施计划 v1.7

> 仓库状态：`candidate / DESIGNED / not_run`。本文件保留 2026-09-28 的阶段设计输入，不替代 `docs/plan.md` 的当前 Milestone、进入条件和阻断项；未实际执行的步骤不得写成当前进度。

## 0. 计划定位

本计划作为 V2 后续会话与项目开发的统一阶段导航。

总体原则：

```text
一个正式业务源
一套业务模型
一套业务规则
一套 Metrics Contract

逻辑模型统一设计
链路独立实现
数据源分批接入

Business Offline
Business Realtime
Behavior Pipeline

最终统一对账
```

旧 100 单 Pilot 继续定位：

```text
PILOT / ACCEPTANCE / HISTORY
```

不再作为 V2 正式开发入口。

---

# 1. 文档职责

## V2-DATA-SPEC v2.4

负责：

```text
业务模型
数据规模
Generator
业务规则
时间规则
SCD2
```

## metrics V2.1

负责：

```text
指标定义
公式
粒度
时间口径
去重
修订
指标状态
实现优先级
```

## 本实施计划

负责：

```text
Phase
Step
依赖关系
Gate
并行开发关系
```

## Warehouse Model / Data Dictionary

负责：

```text
ODS / DWD / DIM / DWS / ADS 表设计

完整字段

字段来源

字段血缘

数据类型

主键和粒度
```

## DDL / SQL

负责：

```text
实际物理建表
实际数据加工
```


## DolphinScheduler / Orchestration

负责：

```text
批处理任务调度

DAG 依赖编排

business_date 参数传递

失败重试

运行状态

Runtime Gate 串联

告警

工作流运行证据
```

边界：

```text
DolphinScheduler
= Control / Orchestration Plane

DataX / Spark SQL / Hive SQL / Doris SQL / Python / Shell
= 实际批处理执行单元

Flink
= 实时长期运行计算引擎
```

DolphinScheduler 不改变 Source Contract、Warehouse Model 或 Metrics Contract。

阶段完成必须依据：

```text
真实执行
+
Gate Result
+
Evidence
```

---

# 2. 整体阶段

```text
Phase A
公共业务、数据与模型基线

Phase B
Business Offline Pipeline

Phase C
Business Realtime Pipeline

Phase D
Continuous Business Increment

Phase E
Behavior Pipeline

Phase F
Reconciliation

Phase G
Benchmark / Final Evidence
```

总体关系：

```text
                         Phase A
               Unified Business & Model
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
       Phase B          Phase C          Phase E
       Business         Business         Behavior
       Offline          Realtime         Pipeline
          │                │                │
          └─────────┬──────┘                │
                    ▼                       │
                 Phase D                    │
            Continuous Business             │
                    │                       │
          ┌─────────┴─────────┐             │
          ▼                   ▼             │
     Offline T+1      Realtime Increment    │
          │                   │             │
          └─────────┬─────────┴─────────────┘
                    ▼
                 Phase F
              Reconciliation
                    │
                    ▼
                 Phase G
                 Benchmark
```

---


## 2.1 Data Plane 与 Control Plane

V2 同时区分：

```text
Data Plane
---------
Business Offline:
ecommerce_oltp
→ DataX
→ ODS
→ Spark
→ DWD / DIM
→ DWS
→ ADS
→ Doris

Business Realtime:
ecommerce_oltp
→ Binlog
→ Flink CDC
→ Kafka
→ Flink
→ Doris
```

以及：

```text
Control / Orchestration Plane
-----------------------------
DolphinScheduler

→ 调度批处理任务
→ 组织依赖
→ 传递 business_date
→ 执行 Runtime Gate
→ 失败重试与告警
→ 触发离实时对账
```

DolphinScheduler 不是数据流中的存储或计算层。

建设原则：

```text
先保证 DataX / SQL / Spark / 校验脚本
可以脱离 DolphinScheduler 独立执行并验收

        ↓

再接入 DolphinScheduler

        ↓

正式 T+1 阶段由 DolphinScheduler
作为批处理顶层运行入口
```

Bootstrap Historical Full Load 属于一次性建仓过程，
不要求为了调度展示而强制包装成完整周期 DAG。


# 3. Phase A｜公共业务、数据与模型基线

## A01. 正式 OLTP DDL 核验

正式源：

```text
ecommerce_oltp
```

确认：

```text
7 个业务域
21 张业务表
```

核验：

```text
字段
类型
PK / UK / FK

金额字段
状态字段

业务发生时间
created_at
updated_at
recorded_at
```

---

## A02. Source Contract

为 21 张源表冻结：

```text
业务含义

字段定义

CSV 顺序

NULL 规则

时间格式

主键

外键

业务时间字段

增量发现字段
```

并区分：

```text
Current State Table

Event Table

Master Data Table
```

---

## A02.1 Metric Required Fields Review

Source Contract 冻结前，必须根据 `metrics V2.1` 反向检查指标所需源字段是否存在。

至少确认：

### Order

```text
order_id

created_at

status

gross_amount_cents

discount_amount_cents

payable_amount_cents

user / identity relation

coupon relation
```

### Order Item

```text
order_item_id

order_id

sku_id

quantity

transaction_unit_price_cents

gross_amount_cents

allocated_discount_cents

payable_amount_cents
```

### Payment

```text
payment_attempt_id

order_id

status

amount_cents

唯一资金业务标识

success_time
```

### Refund

```text
refund_request_id

order_id

order_item_id

refund_status

refund_amount_cents

refund_quantity
    # 允许 NULL

success_time
```

### Coupon

```text
coupon_id

order_id

coupon_status

coupon_event_id

event_type

occurred_at / business event time
```

### Identity

```text
visitor_id

user_id

identity_version

effective_from

effective_to
```

如果某个指标无法由冻结 Source Contract 推导：

```text
不能直接进入建模
```

必须先解决字段来源。

---

# 4. A03｜Metrics Contract Freeze

正式 Metrics Contract：

```text
metrics V2.1
```

指标体系一次性认领完整业务范围，不等于全部指标同时开发。

开发顺序：

```text
P0
核心交易 + 离实时对账

P1
Behavior / 营销 / 用户扩展

P2
待细化或增强分析
```

P0 至少包括：

```text
全部下单金额
GMV

创建订单数
有效订单数

成功支付金额
成功支付订单数

成功退款金额
退款件数

商品销量
商品销售金额

资金净流入
订单累计净支付

同批订单支付转化率
```

离线与实时只能实现同一 Metrics Contract。

---

# 5. A04｜Unified Warehouse Logical Model

Phase A 一次性完成：

```text
Business
+
Behavior
```

逻辑模型设计。

这里是：

```text
统一设计
```

不是：

```text
所有数据立即接入
```

---

## A04.1 ODS Logical Model

设计：

```text
Business ODS

Behavior ODS
```

---

## A04.2 DWD Logical Model

Business：

```text
Order Fact

Order Item Fact

Payment Fact

Refund Fact
```

Behavior：

```text
User Behavior Fact
```

每张事实必须冻结：

```text
grain

business key

event/business time

dimension relation

Canonical Fact Source
```

---

## A04.3 DIM

正式：

```text
dim_user

dim_product_zip
```

唯一 SCD2：

```text
dim_product_zip
```

历史交易按照：

```text
fact_time
```

匹配：

```text
[start_time, end_time)
```

获得：

```text
product_sk
```

不得直接关联当前商品属性完成历史分析。

---

## A04.4 DWS

统一设计：

```text
Trade Subject

User Subject

Product Subject

Behavior Subject
```

例如：

```text
交易日汇总

用户日订单汇总

商品日销售汇总

用户行为日汇总
```

---

## A04.5 ADS

根据 `metrics V2.1` 设计最终指标服务。

P0 Business 指标优先。

Behavior 等 P1 指标模型可以先设计、后接数据。

---

## A04.6 指标结果元数据原则

不要求所有 DWS / ADS 表机械加入相同版本字段。

根据指标性质设计：

```text
stat_date
或
cohort_date
```

修订敏感指标增加：

```text
as_of_time
```

需要重算审计时：

```text
calculation_version
或
batch_id
```

身份敏感指标：

```text
identity_version
```

具体字段进入：

```text
Warehouse Model
/
Data Dictionary
```

而不是写死在 Metrics Contract 中。

---

# 6. A05｜Business Generator

一个正式：

```text
Business Generator
```

内部可拆：

```text
user

product

cart

order

payment

refund

coupon
```

Bootstrap：

```text
Python
→ 21 CSV
→ LOAD DATA
→ ecommerce_oltp
```

Continuous：

```text
Business Transactions
→ INSERT / UPDATE
→ ecommerce_oltp
```

---

# 7. A06｜Bootstrap Historical Dataset

范围：

```text
2025-12-01 00:00:00
~
2026-02-28 23:59:59
```

目标：

```text
100,000 orders

≈285,000 order_items

≈1M OLTP rows
```

本项目不为新 Generator 建设独立 Smoke 数据档位。服务器现有 Generator 先直接按上述正式数据规模核验；不符合时按最小范围修改后重新生成。

同时产生：

```text
支付失败/重试

退款

优惠券状态

购物车合并

身份变化

商品变化

用户长尾

商品长尾

时间高低峰
```

输出：

```text
21 CSV
+
dataset_manifest.json
```

---

# 8. A07｜LOAD DATA

执行：

```text
21 CSV
→ LOAD DATA
→ ecommerce_oltp
```

记录：

```text
rows

bytes

duration

rows/s

MB/s
```

---

# 9. A08｜Source Gate

检查：

```text
21 tables exist

PK duplicate = 0

critical FK orphan = 0

order amount mismatch = 0

invalid order item count = 0

multiple success payment = 0

payment timeout violation = 0

refund overflow = 0

invalid coupon relation = 0

invalid time range = 0
```

通过：

```text
SOURCE_GATE = PASS
```

---


## A09. Orchestration Baseline

Phase A 只冻结公共调度约定，不在这里建设完整离线 DAG。

正式批处理编排器：

```text
DolphinScheduler
```

冻结：

```text
workflow naming

task naming

business_date parameter

retry principle

failure policy

alert principle

evidence fields
```

其中：

```text
business_date
= 本次调度 / 增量抽取窗口对应的业务日
```

例如：

```text
2026-03-07 运行 T+1
business_date = 2026-03-06
```

但：

```text
business_date
≠
所有数据最终 Hive dt
```

真正受影响的 ODS / DWD / DIM / DWS / ADS 分区仍根据：

```text
actual business time
+
affected business dates
```

确定。

A09 不阻塞 B01～B09 的离线任务开发；
但正式 T+1 Workflow Integration 前必须完成。


# 10. Phase B｜Business Offline

正式链路：

```text
ecommerce_oltp
→ DataX
→ Business ODS
→ Spark SQL
→ Business DWD
→ DIM
→ Business DWS
→ Business ADS
→ Doris
```

Behavior 不在 Phase B 实现。


Phase B 的 B01～B09 首先建设并验证离线任务本身。

要求：

```text
DataX Job

Spark SQL / Hive SQL

Doris Load

质量校验脚本
```

均能够脱离 DolphinScheduler 独立执行。

不采用：

```text
每完成一个数据层
→ 先到 DolphinScheduler 配置
→ 再继续开发下一层
```

避免把数据逻辑问题与调度配置问题混在一起。

---

## B01. Business ODS Physical Design

根据 A04 建立：

```text
21 Business ODS
```

统一：

```text
ORC
+
Snappy
+
dt
```

---

## B02. Historical Full Load

```text
ecommerce_oltp
→ DataX
→ Stage
→ Validate
→ Publish
→ ODS
```

---

## B03. ODS Gate

```text
source_rows = ods_rows

duplicate = 0

missing = 0

extra = 0

invalid_partition = 0
```

通过：

```text
ODS_GATE = PASS
```

---

## B04. Business DWD

落地：

```text
Order Fact

Order Item Fact

Payment Fact

Refund Fact

必要业务明细
```

严格执行：

```text
Canonical Fact Source
```

避免当前状态与事件历史重复统计。

---

## B05. DIM

建设：

```text
dim_user

dim_product_zip
```

商品历史版本来自：

```text
biz_sku

biz_spu

biz_category

biz_product_change_event
```

---

## B06. Model Gate

检查：

```text
Order ↔ OrderItem

Order ↔ Payment

OrderItem ↔ Refund

Order ↔ Coupon

Fact ↔ Dimension
```

SCD2：

```text
multi_version_sku_count > 0

invalid_range_count = 0

overlap_version_count = 0

multiple_current_count = 0
```

通过：

```text
MODEL_GATE = PASS
```

---

## B07. Business DWS

优先实现 Metrics P0 所需公共汇总：

```text
Trade

User Order

Product Sales
```

---

## B08. Business ADS

优先实现：

```text
TR P0

PR P0

RF P0

US 引用类核心指标
```

随后按优先级扩展 P1。

---

## B09. Offline Doris

```text
Business ADS
→ Doris
```

历史 Business Offline 闭环完成。

---


## B10. Offline Workflow Integration

B01～B09 独立执行和 Gate 验证稳定后，
再将已经验证的批处理任务接入 DolphinScheduler。

目标不是重新实现数据逻辑，而是把已有任务组织为可运行 DAG。

第一阶段接入：

```text
DataX

ODS Validate / Publish

ODS_GATE

DWD / DIM

MODEL_GATE

DWS

ADS

Doris Publish
```

接入后仍必须保留原始脚本 / SQL 的独立执行能力。

Bootstrap 历史全量允许保留为一次性独立执行流程；
正式周期调度重点是 Continuous 阶段的 T+1 Daily Workflow。

B10 完成标志：

```text
OFFLINE_WORKFLOW_READY = PASS
```


# 11. Phase C｜Business Realtime

正式：

```text
ecommerce_oltp
→ Binlog
→ Flink CDC
→ Kafka
→ Flink
→ Realtime DWD / DIM
→ DWS / ADS
→ Doris
```

Pilot 资产保留但与 Formal V2 隔离。


Realtime Application 属于长期运行流任务。

```text
Flink CDC

Domain Flink Applications
```

不采用：

```text
DolphinScheduler
→ 每几分钟启动一次 Flink
→ 处理一批数据后退出
```

DolphinScheduler 可用于：

```text
部署 / 启动入口

定期健康检查

工程验收任务

必要的恢复辅助
```

但 Event Time、Watermark、Window、Checkpoint、State 与持续消费仍由 Flink 管理。

---

## C01. Formal CDC Contract

核验：

```text
21 tables

PK

business key

status

money

business time

updated_at

recorded_at
```

---

## C02. Kafka Contract

冻结：

```text
Topic Namespace

Partition Count

Message Key

Partition Strategy

Retention

Replication Factor

min.insync.replicas

CDC Envelope
```

---

## C03. Event Version

正式设计：

```text
event_version
```

用于同一业务主键的新旧版本判断。

不得把 Pilot 的单分区 `kafka_offset` 直接扩展成多分区全局版本。

---

## C04. Initial Snapshot

```text
Formal Flink CDC
→ Initial Snapshot
→ Formal Kafka Raw CDC
```

Bootstrap 源保持稳定。

---

## C05. CDC Gate

检查：

```text
21 tables captured

snapshot rows correct

PK correct

source.db correct

source.table correct

partition/key correct

event_version correct

no pilot contamination
```

通过：

```text
CDC_GATE = PASS
```

---

## C06. Realtime Framework

抽取：

```text
Kafka Source

CDC Parser

Router

Metadata

Event Version

Checkpoint

Doris Sink

Error Handling

Recovery
```

---

## C07. Domain DWD / DIM

原则：

```text
Model by fact grain

Application by business domain
```

21 张表必须全部有明确归属。

---

## C08. Realtime Model Gate

验证：

```text
Order ↔ OrderItem

Order ↔ Payment

Order ↔ Refund

Order ↔ Coupon

Product

Identity

Fact ↔ Dimension
```

以及：

```text
payment retry

refund retry

coupon change

product change

identity revision

no double counting
```

通过：

```text
REALTIME_MODEL_GATE = PASS
```

---

## C09. Realtime DWS / ADS

第一阶段实现 Metrics P0 中可离实时直接对账的指标：

```text
全部下单金额

GMV

paid_order_count

sales_quantity

refund_amount

net_payment
```

后续按 Metrics Priority 扩展。

---

## C10. Realtime Doris

设计目标：

```text
End-to-End <= 5 min
```

这是目标，不是实测结论。

最终结果使用：

```text
Benchmark P95
```

---

## C11. Recovery Gate

统一验证：

```text
Checkpoint

Restart

State Restore

Kafka Resume

Doris No Duplicate

No Data Loss
```

通过：

```text
RECOVERY_GATE = PASS
```

---

# 12. Phase D｜Continuous Business

启动条件：

```text
SOURCE_GATE = PASS

ODS_GATE = PASS

CDC_GATE = PASS
```

然后：

```text
2026-03-01
→ Continuous
```

所有 Business 变化只写：

```text
ecommerce_oltp
```

---

## D01. Continuous Source Gate

检查：

```text
ID continuity

legal business relations

UPDATE works

Binlog captured

DataX detectable

SCD2 change generated
```

---

# 13. Business Offline T+1

进入 Continuous 后，正式每日批处理运行入口为：

```text
DolphinScheduler
→ v2_business_offline_daily
```

前提：

```text
B10 OFFLINE_WORKFLOW_READY = PASS

D01 Continuous 已启动
```

调度参数：

```text
business_date
```

例如：

```text
2026-03-07 执行
business_date = 2026-03-06
```

该参数用于确定本次增量抽取窗口。

Current State Table：

```text
主要根据 updated_at
发现 business_date 对应窗口内发生变化的数据
```

Event Table：

```text
主要根据 recorded_at
或 Source Contract 冻结字段
发现 business_date 对应窗口内新增记录
```

但：

```text
business_date
≠
Hive dt
```

一次 T+1 任务可能发现：

```text
新订单

历史订单取消

跨日退款

迟到事件

商品属性变化
```

因此正式 Workflow 必须：

```text
start
  ↓
resolve_business_date
  ↓
DataX Incremental
  ↓
Stage
  ↓
Validate
  ↓
identify affected business dates
  ↓
ODS Publish / Partition Rebuild
  ↓
ODS_GATE
  ↓
DWD Build ─────┐
               ├─→ DIM Build
               │
               └────→ MODEL_GATE
                         ↓
                        DWS
                         ↓
                        ADS
                         ↓
                    Doris Publish
                         ↓
                       end
```

当 Phase F 已启用后，在 `Doris Publish` 后继续挂接：

```text
Business Reconciliation
        ↓
RECONCILIATION_GATE
```

正式运行职责：

```text
DolphinScheduler
→ 时间调度
→ DAG 依赖
→ 参数传递
→ 失败重试
→ Runtime Gate
→ 告警
→ 运行证据

DataX / Spark / SQL / Python
→ 实际抽取、计算和校验
```

业务分区始终根据：

```text
actual business time
+
affected business dates
```

确定。

---

## T+1 Gate

覆盖：

```text
new order

old order update

late event

historical order refund

product change
```

---

# 14. Business Realtime Increment

Continuous 后验证：

```text
order create
→ payment fail
→ retry success
→ partial refund
```

完整经过：

```text
MySQL
→ Binlog
→ CDC
→ Kafka
→ Flink
→ Doris
```

通过：

```text
REALTIME_BUSINESS_GATE = PASS
```

---

# 15. Phase E｜Behavior Pipeline

Behavior 是独立数据链。

不属于：

```text
Business Offline

Business Realtime
```

但逻辑模型已经在 Phase A 统一设计。

---

## E01. Behavior Contract

Canonical Event Type：

```text
PAGE_VIEW

PRODUCT_EXPOSURE

PRODUCT_CLICK

ADD_CART

REMOVE_CART
```

正式字段：

```text
event_id

event_type

event_time

session_id

visitor_id

user_id

sku_id

spu_id

category_id

page

source

channel

device

platform

event_attributes
```

流式链路附加：

```text
ingest_time
```

语义：

```text
event_time
→ 指标统计 / Event Time / Window

ingest_time
→ 延迟 / 迟到监控
```

---

## E02. Behavior Generator

必须复用：

```text
user

visitor

identity mapping

sku

spu

category
```

不得创建第二套 ID 空间。

---

## E03. Historical Behavior

```text
2025-12-01
~
2026-02-28
```

目标：

```text
3M～5M events
```

链路：

```text
Historical Behavior Files
→ Behavior ODS
→ Spark
→ Behavior DWD
→ Behavior DWS / ADS
```

上述批处理任务先独立验证，稳定后可接入：

```text
DolphinScheduler
→ v2_behavior_historical
```

用于历史行为批处理的统一编排和 Gate 串联。

---

## E04. Continuous Behavior

```text
Behavior Generator
→ Kafka
→ Flink
→ Behavior DWD
→ Behavior DWS / ADS
→ Doris
```

Behavior 不进入 MySQL 21 表。

Continuous Behavior 的 Kafka / Flink 链路属于长期运行实时任务，
不由 DolphinScheduler 按固定分钟周期反复启动。

---

## E05. Behavior Metrics

实现：

```text
TF-01 ～ TF-08

US-03

行为相关漏斗
```

使用 `metrics V2.1`。

---

## Behavior Gate

检查：

```text
event_id unique

event_type valid

event_time valid

identity valid

product relation valid

dedup works

PV / UV correct

funnel computable

offline/realtime same contract
```

通过：

```text
BEHAVIOR_GATE = PASS
```

---

# 16. Phase F｜Reconciliation

## Business

比较：

```text
Offline ADS / Doris

vs

Realtime Doris
```

P0 至少覆盖：

```text
GMV

paid_order_count

sales_quantity

refund_amount

net_payment
```

记录：

```text
offline_value

realtime_value

difference

difference_ratio

as_of_time
```

正式运行时，Phase F 作为 DolphinScheduler Daily Workflow 的下游验收节点：

```text
DolphinScheduler
→ Reconciliation SQL / Python
→ 读取 Offline 结果
→ 读取 Realtime 结果
→ 统一 as_of_time / business window
→ 计算 difference / difference_ratio
→ 输出 Reconciliation Result
→ RECONCILIATION_GATE
```

DolphinScheduler 只负责触发、依赖、状态与失败处理；
实际指标读取和差异计算由 SQL / Python 完成。

建议额外记录：

```text
business_date
workflow_instance_id
check_time
status
```

---

## Behavior

比较：

```text
PV

UV

Exposure

Click

Add Cart

Funnel
```

---

## Reconciliation Gate

```text
differences explainable

closed business window converges

core metrics consistent
```

---

# 17. Phase G｜Benchmark

链路稳定且正式数据规模通过业务验收以后执行。性能实验使用独立数据档位：约 900,000 笔订单和 9,000,000 条行为事件；沿用相同 Contract，但使用独立 `dataset_version` 与输出目录。

记录：

```text
Dataset Scale

LOAD DATA

DataX FULL

DataX INCREMENTAL

ORC + Snappy

Spark

Kafka

Flink

Doris

Reconciliation

DolphinScheduler Workflow Evidence
```

批处理正式运行额外记录：

```text
workflow_name
workflow_instance_id
business_date
scheduled_time
start_time
end_time
duration
task_success_count
task_failure_count
retry_count
final_status
```

这些属于运行证据，不要求单独对 DolphinScheduler 做吞吐压测。

性能数字只能使用真实实测。

---

# 18. 阶段表

| 编号      | 阶段                              | 依赖            | 输出                            |
| ------- | ------------------------------- | ------------- | ----------------------------- |
| A01     | OLTP DDL Review                 | 无             | DDL Baseline                  |
| A02     | Source Contract                 | A01           | Source Contract               |
| A02.1   | Metric Required Fields Review   | A02 + Metrics | Field Coverage                |
| A03     | Metrics Contract Freeze         | A02           | Metrics V2.1                  |
| A04     | Unified Warehouse Logical Model | A02.1/A03     | Logical Model                 |
| A05     | Business Generator              | A02           | Generator                     |
| A06     | Bootstrap Dataset               | A05           | 21 CSV + Manifest             |
| A07     | LOAD DATA                       | A06           | ecommerce_oltp                |
| A08     | Source Gate                     | A07           | `SOURCE_GATE=PASS`            |
| A09     | Orchestration Baseline          | A08           | Orchestration Convention      |
| B01     | Business ODS Physical Design    | A04/A08       | ODS Schema                    |
| B02     | Historical Full Load            | B01           | ODS                           |
| B03     | ODS Gate                        | B02           | `ODS_GATE=PASS`               |
| B04     | Business DWD                    | B03/A04       | DWD                           |
| B05     | DIM                             | B03/A04       | DIM                           |
| B06     | Model Gate                      | B04/B05       | `MODEL_GATE=PASS`             |
| B07     | Business DWS                    | B06           | DWS                           |
| B08     | Business ADS                    | B07/A03       | ADS                           |
| B09     | Offline Doris                   | B08           | Serving                       |
| B10     | Offline Workflow Integration    | B09/A09       | `OFFLINE_WORKFLOW_READY=PASS` |
| C01     | Formal CDC Contract             | A08           | CDC Contract                  |
| C02     | Kafka Contract                  | C01           | Kafka Contract                |
| C03     | Event Version                   | C02           | Version Contract              |
| C04     | Initial Snapshot                | C01-C03       | Snapshot                      |
| C05     | CDC Gate                        | C04           | `CDC_GATE=PASS`               |
| C06     | Realtime Framework              | C05           | Framework                     |
| C07     | Domain DWD/DIM                  | C06/A04       | Realtime Model                |
| C08     | Realtime Model Gate             | C07           | `REALTIME_MODEL_GATE=PASS`    |
| C09     | Realtime DWS/ADS                | C08/A03       | Metrics                       |
| C10     | Realtime Doris                  | C09           | Serving                       |
| C11     | Recovery Gate                   | C07-C10       | `RECOVERY_GATE=PASS`          |
| D01     | Business Continuous             | B03/C05       | Continuous OLTP               |
| B11     | T+1 Daily Workflow              | D01/B10       | Incremental Offline           |
| C12     | Realtime Increment              | D01/C10       | `REALTIME_BUSINESS_GATE=PASS` |
| E01     | Behavior Contract               | A04           | Contract                      |
| E02     | Behavior Generator              | E01/A08       | Generator                     |
| E03     | Historical Behavior             | E02           | Historical Events             |
| E04     | Offline Behavior                | E03/A04       | Offline Behavior              |
| E05     | Behavior Kafka Contract         | E01           | Kafka Contract                |
| E06     | Continuous Behavior             | E02/E05       | Kafka Events                  |
| E07     | Realtime Behavior               | E06/A04       | Realtime Behavior             |
| E08     | Behavior Gate                   | E04/E07       | `BEHAVIOR_GATE=PASS`          |
| F01     | Business Reconciliation         | B11/C12       | Reconciliation                |
| F02     | Behavior Reconciliation         | E08           | Reconciliation                |
| G01-G04 | Benchmark / Evidence            | F             | Final Evidence                |

---


# 19. Gate 运行分类

Gate 分为两类。

## Runtime Batch Gate

适合进入 DolphinScheduler Daily / Batch Workflow：

```text
ODS_GATE

MODEL_GATE

T+1 Gate

Behavior Offline Gate

RECONCILIATION_GATE
```

例如：

```text
ODS_GATE FAIL
→ Workflow STOP
→ 不执行下游 DWD
→ Alert
```

## Engineering Acceptance Gate

主要用于阶段性工程验收，不要求每天完整执行：

```text
SOURCE_GATE

CDC_GATE

REALTIME_MODEL_GATE

RECOVERY_GATE

REALTIME_BUSINESS_GATE
```

这些 Gate 可以通过脚本被 DolphinScheduler 调用，
但不能因为存在调度器就机械地全部加入每日 DAG。

---

# 20. 阶段关闭规则

阶段不能因为：

```text
代码生成
SQL 写完
文件存在
```

就标记完成。

必须：

```text
Implementation
+
Execution
+
Gate
+
Evidence
```

阶段完成后更新：

```text
Current Status

File Fact Ledger

Actual File Path

Execution Result

Open Issues

Next Handoff
```

---

# 21. 当前开发入口

当前正式顺序：

```text
A01
核验 ecommerce_oltp 21 表 DDL
        ↓
A02
Source Contract
        ↓
A02.1
Metric Required Fields Review
        ↓
A03
Metrics V2.1 Freeze
        ↓
A04
Unified Warehouse Logical Model
        ↓
A05
Business Generator
        ↓
A06
21 CSV + Manifest
        ↓
A07
LOAD DATA
        ↓
A08
SOURCE_GATE = PASS
```

同时冻结：

```text
A09
DolphinScheduler Orchestration Baseline
```

A09 只定义调度规范，不要求在进入 B01 前先搭完整 DAG。

随后：

```text
Phase B Business Offline

Phase C Business Realtime

Phase E Behavior
```

按照各自依赖并行推进。

---

# 22. 执行原则

```text
1. 业务和数据规则以 V2-DATA-SPEC v2.4 为准。

2. 指标定义以 metrics V2.1 为准。

3. Phase 和依赖关系以本计划为准。

4. Source Contract 必须先通过 Metric Required Fields Review。

5. Metrics 定义完整认领，实施按 P0 / P1 / P2 分阶段完成。

6. Phase A 统一设计 Business + Behavior Logical Model。

7. Phase B 只实施 Business Offline。

8. Phase C 只实施 Business Realtime。

9. Phase E 独立实施 Behavior Offline + Realtime。

10. Behavior Event Type 统一使用：
    PAGE_VIEW
    PRODUCT_EXPOSURE
    PRODUCT_CLICK
    ADD_CART
    REMOVE_CART。

11. 商品历史分析统一通过 dim_product_zip。

12. as_of_time / calculation_version / identity_version 按指标性质使用，
    不机械加入所有表。

13. Business 数据只写 ecommerce_oltp。

14. Behavior 不写 MySQL 21 表。

15. Continuous 只有 ODS_GATE 和 CDC_GATE 均通过后启动。

16. 不重新启用 100 单 Pilot 作为正式 V2 入口。

17. 不逐表重复完整 Pilot，使用集中 Gate。

18. Benchmark 数字只采用真实工程实测。

19. Gate PASS 后更新状态、File Fact Ledger 与 Handoff。

20. DataX / Spark / SQL / 校验脚本必须先具备独立执行能力，
    再接入 DolphinScheduler。

21. Bootstrap Historical Full Load 不强制为了展示调度系统而重做周期 DAG。

22. Continuous T+1、历史 Behavior 批处理和 Reconciliation
    作为 DolphinScheduler 的主要正式编排对象。

23. DolphinScheduler 中的 business_date 表示调度 / 抽取窗口，
    不等同于 Hive dt；受影响分区仍按实际业务时间识别。

24. Flink CDC 与实时 Domain Application 为长期运行流任务；
    DolphinScheduler 不承担 Event Time、Watermark、Window、
    Checkpoint 或逐事件处理职责。
```

本版本作为 V2 后续统一建模、Business Offline、Business Realtime、Behavior、离实时对账和 Benchmark 的实施导航。
