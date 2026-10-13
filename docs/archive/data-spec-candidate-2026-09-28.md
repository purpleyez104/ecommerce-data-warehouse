# V2-DATA-SPEC｜离实时共用数据规格 v2.4

## 0. 文档状态

```text
Spec Name    : V2-DATA-SPEC
Spec Version : v2.4
Status       : CANDIDATE / DESIGNED / NOT_RUNTIME_VERIFIED

Business TZ     : Asia/Shanghai
Formal Source DB: ecommerce_oltp
```

> 仓库状态说明：本文件保留 2026-09-28 的 V2 设计输入。文内“冻结”表示该设计稿的目标约束，不代表已替代 `docs/spec.md`、`docs/plan.md` 或已完成 Runtime 验收；与正式文档冲突的内容保持 `DECISION_REQUIRED`。

本规范统一约束：

```text
V2 大规模业务数据
历史初始化
持续业务增量
离线链路
实时链路
用户行为数据
商品拉链维度
数据质量
Benchmark
简历量化证据
```

---

# 1. V2 总体原则

正式业务数据只有一个事实源：

```text
ecommerce_oltp
```

离线和实时不是两套业务数据，而是对同一个业务源采用不同采集方式：

```text
                    ecommerce_oltp
                          │
             ┌────────────┴────────────┐
             │                         │
           DataX                    Binlog
             │                         │
             ▼                         ▼
        Offline ODS                Flink CDC
             │                         │
         Spark SQL                    Kafka
             │                         │
   DWD → DIM → DWS → ADS             Flink
             │                         │
             └────────────┬────────────┘
                          ▼
                        Doris
                          │
                离实时结果对账
```

原则：

```text
一个业务源
一套业务模型
一套业务规则
一套指标口径
两种处理时效
最终结果收敛一致
```

---

# 2. Generator 数量

项目只定义两个逻辑 Generator：

```text
1. Business Generator
2. Behavior Generator
```

不是：

```text
21 张表 = 21 个 Generator
```

也不是：

```text
Historical Generator
+
Realtime Generator
```

---

# 3. Business Generator

Business Generator 负责：

```text
ecommerce_oltp
21 张业务表
```

内部可以按照业务域拆模块：

```text
user
product
cart
order
payment
refund
coupon
```

但仍属于同一个 Generator。

Business Generator 有两个运行阶段：

```text
Bootstrap Historical Initialization
Continuous Business Increment
```

二者共享：

```text
同一套业务规则
同一套 ID 体系
同一套用户与商品
同一套状态机
同一个 ecommerce_oltp
```

---

# 4. Bootstrap Historical Initialization

第一阶段：

```text
Bootstrap
```

用于一次性初始化历史业务数据。

历史范围：

```text
history_start = 2025-12-01 00:00:00
history_end   = 2026-02-28 23:59:59

history_days = 90
timezone     = Asia/Shanghai
```

正式生成方式：

```text
Business Generator
        ↓
21 CSV
        ↓
LOAD DATA
        ↓
ecommerce_oltp
```

采用该方式的原因：

```text
历史数据量较大
一次批量初始化
CSV 可以独立检查
LOAD DATA 装载效率高
生成逻辑与数据库装载解耦
```

禁止将百万级历史初始化重新实现为 Python 逐行 INSERT。

---

# 5. Continuous Business Increment

Bootstrap 完成以后：

```text
ecommerce_oltp
```

继续保留并持续发生业务变化。

从：

```text
2026-03-01 00:00:00
```

开始进入：

```text
Continuous Business Increment
```

同一个 Business Generator 继续模拟：

```text
新用户注册
新 Visitor
商品新增
商品修改
购物车操作
新订单
支付
支付失败
支付重试
订单取消
退款
优惠券发放与使用
身份映射变化
```

通过真实业务事务：

```text
INSERT
UPDATE
```

修改 `ecommerce_oltp`。

---

# 6. Bootstrap 和 Continuous 的关系

二者不是两套数据。

正确关系：

```text
2025-12-01
      │
      │ Bootstrap 90 天历史
      ▼
2026-02-28
      │
      ▼
ecommerce_oltp 当前完整状态
      │
      │ Continuous
      ▼
2026-03-01 → future
```

例如 Bootstrap 完成以后已经存在：

```text
40,000 users
4,000 SKU
100,000 orders
```

Continuous 不重新生成另一套 ID 空间，而是在已有业务世界中继续产生数据：

```text
已有用户继续消费
已有商品继续销售
新增用户继续注册
新订单继续产生
旧订单可能退款
已有商品继续发生属性变化
```

---

# 7. 离实时同源

Continuous 阶段发生一次业务变化后，只写入一次：

```text
ecommerce_oltp
```

然后由两条链路分别处理。

实时链路：

```text
ecommerce_oltp
→ MySQL Binlog
→ Flink CDC
→ Kafka
→ Flink
→ Doris
```

离线链路：

```text
ecommerce_oltp
→ DataX T+1 Incremental
→ ODS
→ Spark SQL
→ DWD
→ DIM
→ DWS
→ ADS
→ Doris
```

因此同一笔业务数据：

```text
实时链路先处理
离线链路 T+1 再处理
最终进行结果对账
```

---

# 8. 离线增量抽取规则

Bootstrap 初始化阶段：

```text
FULL LOAD
```

Continuous 阶段：

```text
INCREMENTAL LOAD
```

增量抽取的目的，是回答：

```text
“本次 DataX 任务应该同步哪些新增或发生变化的数据？”
```

## 8.1 当前状态表

会发生 UPDATE 的当前状态表，主要根据：

```text
updated_at
```

判断记录是否发生过变化。

例如：

```text
biz_user
biz_visitor
biz_sku
biz_cart
biz_cart_item
biz_order
biz_order_item
biz_payment_attempt
biz_refund_request
biz_refund_transaction
biz_coupon
```

例如某订单：

```text
created_at = 2026-03-05 10:00:00
updated_at = 2026-03-06 15:00:00
```

3 月 7 日执行 3 月 6 日的 T+1 任务时，由于：

```text
updated_at = 2026-03-06
```

该订单需要重新同步。

---

## 8.2 事件表

以追加新事件为主的表，主要根据：

```text
recorded_at
```

或该表明确的事件入库时间，判断是否出现新的记录。

例如：

```text
biz_product_change_event
biz_order_status_event
biz_payment_event
biz_refund_event
biz_coupon_event
```

`recorded_at` 表示：

```text
该事件什么时候被正式记录到业务系统中
```

它主要用于防止迟到事件被离线任务漏掉。

---

# 9. 增量抽取时间与业务分区时间

离线增量同步时必须区分两个概念。

## 9.1 增量抽取时间

增量抽取时间用于判断：

```text
“本次 DataX 应该抓哪些数据？”
```

规则：

```text
当前状态表
→ 主要使用 updated_at

事件表
→ 主要使用 recorded_at
```

例如：

```text
订单创建时间：2026-03-05
订单更新时间：2026-03-06
```

3 月 7 日运行 T+1 任务时：

```text
因为订单在 3 月 6 日发生过变化
所以 DataX 会重新抽取该订单
```

这里使用 `updated_at` 的目的只是：

```text
发现增量变化
```

---

## 9.2 业务分区时间

数据被 DataX 抽取以后，还需要确定：

```text
“这条数据业务上属于哪一天？”
```

该时间用于确定 Hive 中的：

```text
dt
```

分区。

不同业务对象根据自己的业务时间确定分区。

例如订单：

```text
订单业务日期
→ 根据 created_at 或明确的 business_date
```

事件：

```text
事件业务日期
→ 根据事件实际发生时间
```

---

## 9.3 示例：订单更新

假设订单：

```text
order_id   = 10001
created_at = 2026-03-05 10:00:00
updated_at = 2026-03-06 15:00:00
```

3 月 7 日执行离线任务。

DataX 根据：

```text
updated_at = 2026-03-06
```

判断：

```text
这条订单昨天发生了变化
需要重新抽取
```

但是该订单本身是：

```text
2026-03-05 创建的订单
```

因此业务上仍然属于：

```text
dt=2026-03-05
```

而不是：

```text
dt=2026-03-06
```

可以理解为：

```text
updated_at
→ 决定“这次要不要重新抓这条订单”

created_at / business_date
→ 决定“这条订单属于哪个业务日期”
```

其中这里的两个字段是不同用途，不表示数学运算。

---

## 9.4 示例：迟到支付事件

例如：

```text
支付实际发生时间：
2026-03-05 23:59:58

事件记录时间：
2026-03-06 00:00:02
```

事件表中可以表现为：

```text
occurred_at = 2026-03-05 23:59:58
recorded_at = 2026-03-06 00:00:02
```

离线任务根据：

```text
recorded_at
```

发现这条新增事件。

但该支付事件的业务日期仍然是：

```text
2026-03-05
```

所以应写入：

```text
dt=2026-03-05
```

可以简单记为：

```text
增量抽取字段
→ 决定“抓什么”

业务时间字段
→ 决定“放到哪个 dt 分区”
```

两者可能相同，也可能不同。

---

# 10. 每日离线增量流程

正式每日增量流程：

```text
DataX 抓取昨日新增或变化数据
        ↓
Stage
        ↓
Validate
        ↓
识别受影响业务日期
        ↓
更新对应 ODS 分区
        ↓
Spark 重算受影响 DWD 与 DIM
        ↓
重算相关 DWS 与 ADS
        ↓
与实时结果对账
```

Pilot 阶段已经验证的：

```text
Stage
→ Validate
→ Publish
```

继续保留。

后续将其抽象为可复用的批量离线处理框架，而不是针对每张表重复做 Pilot。

---


# 10.1 Runtime Orchestration Boundary

V2 正式批处理运行采用 DolphinScheduler 进行调度与 DAG 编排。

该约束属于：

```text
Control / Orchestration Plane
```

而不是新的数据处理层。

因此引入 DolphinScheduler 不改变：

```text
Formal Source DB

Source Contract

DataX FULL / INCREMENTAL 规则

业务时间与增量发现时间的区别

Hive dt 分区规则

DWD / DIM / DWS / ADS 模型

Metrics Contract

Behavior Event Time

Flink 流处理语义
```

批处理任务必须先可以独立执行和验证，再接入 DolphinScheduler。

Bootstrap Historical Full Load 属于一次性初始化过程，
不要求为了调度展示而强制包装成周期工作流。

Continuous 阶段正式 T+1 任务使用调度参数：

```text
business_date
```

例如：

```text
2026-03-07 执行
business_date = 2026-03-06
```

这里的 `business_date` 表示：

```text
本次增量抽取 / 调度窗口
```

不表示：

```text
所有数据必须写入 dt=business_date
```

实际 Hive `dt` 继续按照数据自己的业务时间确定；
若昨日发生的更新影响更早业务日期，必须识别并回刷对应历史分区。

正式 T+1 控制关系：

```text
DolphinScheduler
        ↓
DataX Incremental
        ↓
Stage / Validate
        ↓
Affected Business Dates
        ↓
ODS Publish
        ↓
Spark DWD / DIM
        ↓
DWS / ADS
        ↓
Doris
        ↓
Reconciliation
```

DolphinScheduler 只负责：

```text
时间调度
任务依赖
参数传递
失败重试
运行状态
Gate 串联
告警
运行证据
```

真正的数据抽取、计算和校验仍由 DataX、Spark SQL、SQL、Shell、Python 等任务完成。

实时业务链路和 Continuous Behavior 链路中的 Flink Application 属于长期运行流任务。

不采用：

```text
DolphinScheduler
→ 每几分钟重新启动 Flink
→ 处理一批后退出
```

Flink 的：

```text
Event Time
Watermark
Window
Checkpoint
State
持续 Kafka Consumption
```

仍由 Flink 自身管理。

Historical Behavior 批处理任务可以在独立验证后接入 DolphinScheduler；
Continuous Behavior 的 Kafka → Flink 链路仍按长期流任务运行。

---

# 11. 正式业务模型

正式源模型：

```text
7 个业务域
21 张业务表
```

## 用户与身份域

```text
biz_user
biz_visitor
biz_identity_mapping
```

## 商品域

```text
biz_category
biz_spu
biz_sku
biz_product_change_event
```

## 购物车域

```text
biz_cart
biz_cart_item
biz_cart_merge_record
```

## 订单域

```text
biz_order
biz_order_item
biz_order_status_event
```

## 支付域

```text
biz_payment_attempt
biz_payment_event
```

## 退款域

```text
biz_refund_request
biz_refund_transaction
biz_refund_event
```

## 优惠券域

```text
biz_coupon_template
biz_coupon
biz_coupon_event
```

---

# 12. 全局数据规范

```text
Storage Engine : InnoDB
Charset        : utf8mb4

Business ID    : BIGINT
Amount         : BIGINT cents
Quantity       : INT
Time           : DATETIME(3)
Timezone       : Asia/Shanghai
Status         : VARCHAR(32)
```

业务金额只使用整数分。

---

# 13. 正式数据规模

核心规模：

```text
90 days
100,000 orders
≈285,000 order_items
≈1M-level OLTP rows
```

目标规模：

| 表                        |           目标规模 |
| ------------------------ | -------------: |
| biz_user                 |         40,000 |
| biz_visitor              |         80,000 |
| biz_identity_mapping     |        ≈24,000 |
| biz_category             |             60 |
| biz_spu                  |          1,200 |
| biz_sku                  |          4,000 |
| biz_product_change_event |         ≈2,000 |
| biz_cart                 |        ≈50,000 |
| biz_cart_item            |       ≈110,000 |
| biz_cart_merge_record    |         ≈8,000 |
| biz_order                |        100,000 |
| biz_order_item           |       ≈285,000 |
| biz_order_status_event   |       ≈199,000 |
| biz_payment_attempt      |        ≈95,300 |
| biz_payment_event        |       ≈95,000+ |
| biz_refund_request       |          9,000 |
| biz_refund_transaction   |         ≈9,540 |
| biz_refund_event         | ≈25,000～30,000 |
| biz_coupon_template      |             30 |
| biz_coupon               |         60,000 |
| biz_coupon_event         |     ≈130,000 级 |

事件表允许根据业务状态流转自然浮动。`biz_product_change_event` 采用约 25% SKU 发生变化、每个变化 SKU 1～3 个版本的约束；4,000 SKU 下约 2,000 行与该约束相容，旧稿的约 12,000 行目标已移除。

---

# 14. 行为数据

行为数据不进入 MySQL 21 张业务表。

Behavior Generator 负责生成正式 Canonical Event Type：

```text
PAGE_VIEW
PRODUCT_EXPOSURE
PRODUCT_CLICK
ADD_CART
REMOVE_CART
```

禁止在正式 V2 Contract 中继续混用语义不完整的：

```text
VIEW
EXPOSURE
CLICK
```

历史行为规模：

```text
3M～5M events
```

正式数据规模不再附带独立的约 100 单 Smoke 数据档位。历史 Pilot 数据继续保留，但不作为新 Generator 的生成目标。

## 14.1 性能实验规模

正式数据规模通过业务验收后，使用同一 Contract 生成独立性能实验数据：

```text
orders          ≈ 900,000
behavior_events = 9,000,000
```

性能实验数据必须使用独立 `dataset_version` 和输出目录，并保持相同的 90 天时间范围、业务状态机、金额守恒、实体关系和 Behavior Event Contract。该档位只用于性能实验，不替代正式数据规模的 Source Gate。

Behavior Generator 同样存在两个运行阶段：

```text
Bootstrap Behavior
→ 历史行为文件
→ Offline ODS

Continuous Behavior
→ Kafka
→ Flink
```

两个阶段共享：

```text
user_id
visitor_id
session_id
sku_id
event_type
event_time
行为概率
```

---

# 15. 时间分布

数据禁止机械均匀生成。

必须体现：

```text
工作日和周末差异
日内高低峰
自然随机波动
少量促销峰值日
```

促销峰值日数据量可约为普通日：

```text
2～4 倍
```

最终实际比例由 `dataset_manifest.json` 记录。

日内至少体现：

```text
凌晨低谷
午间增长
晚间高峰
```

---

# 16. 商品长尾

4,000 SKU 采用明显的长尾销售分布。

目标范围：

```text
Top 5% SKU
约占 35%～45% 销量

Top 20% SKU
约占 65%～75% 销量

剩余 80% SKU
约占 25%～35% 销量
```

用于形成真实：

```text
TopN
Spark Shuffle
数据倾斜
Flink KeyBy 热点
Doris TopN
```

场景。

---

# 17. 用户活跃度

用户数据需要包含：

```text
高频购买用户
中活跃用户
低频用户
未购买注册用户
匿名 Visitor
匿名转登录用户
复购用户
```

不得让所有用户拥有近似相同的订单数量。

---

# 18. 订单规模与状态

```text
biz_order = 100,000
```

状态目标：

```text
PAID       70,000   70%
CANCELED   29,000   29%
CREATED     1,000    1%
```

`CREATED` 订单主要集中在 Bootstrap 截止时间附近。

不得大量存在数月未处理的历史 CREATED 订单。

---

# 19. 订单明细

一笔订单包含：

```text
1～5 个不同 SKU
```

分布：

```text
1 SKU   15%
2 SKU   25%
3 SKU   30%
4 SKU   20%
5 SKU   10%
```

平均：

```text
2.85 items/order
```

预计：

```text
≈285,000 order_items
```

必须满足：

```text
UNIQUE(order_id, sku_id)
```

---

# 20. 金额约束

明细：

```text
gross_amount_cents
=
quantity × unit_price_cents
```

```text
payable_amount_cents
=
gross_amount_cents
-
allocated_discount_cents
```

订单：

```text
order gross
=
SUM(item gross)

order discount
=
SUM(item discount)

order payable
=
SUM(item payable)
```

优惠金额采用整数分确定性分摊，并保证总额守恒。

---

# 21. 支付规则

同一订单最多存在：

```text
1 个有效 SUCCESS 支付
```

PAID 订单：

```text
85% 首次支付成功

15% 首次失败
→ 第二次支付成功
```

CANCELED 订单：

```text
55% 无支付尝试
40% 一次 FAILED
5% 两次 FAILED
```

CREATED 订单：

```text
70% 无支付尝试
30% INIT
```

预计：

```text
biz_payment_attempt ≈95,300
```

---

# 22. 支付窗口

支付截止时间：

```text
payment_deadline_at
=
order.created_at + 15 minutes
```

SUCCESS 支付必须发生在有效支付窗口内。

支付成功后的订单不得再进入取消状态。

---

# 23. 退款

约：

```text
8,000 个 PAID 订单
```

发生退款。

退款申请：

```text
refund_request = 9,000
```

状态分布：

```text
SUCCESS      80%
FAILED       15%
PROCESSING    3%
REQUESTED     2%
```

约 10% 的成功退款经历：

```text
FAILED
→ retry
→ SUCCESS
```

金额必须满足：

```text
refunded_cents
+
refund_reserved_cents
<=
order_item.payable_amount_cents
```

---

# 24. 优惠券

```text
coupon_template = 30
coupon          = 60,000
```

约：

```text
30,000 orders
```

涉及优惠券。

主要状态：

```text
UNUSED
LOCKED
USED
EXPIRED
```

主要状态流转：

```text
支付成功
LOCKED → USED

订单取消
LOCKED → UNUSED
或
LOCKED → EXPIRED

发生退款
优惠券不返还
```

---

# 25. 购物车

目标规模：

```text
biz_cart              ≈50,000
biz_cart_item         ≈110,000
biz_cart_merge_record ≈8,000
```

覆盖：

```text
游客购物车
用户购物车
登录后购物车合并
相同 SKU 合并
quantity 最大 99
数量截断案例
```

---

# 26. 事件表原则

事件表包括：

```text
biz_product_change_event
biz_order_status_event
biz_payment_event
biz_refund_event
biz_coupon_event
```

事件表负责：

```text
保存业务状态变化历史
```

但：

```text
事件表不等于第二份可独立累加的业务事实
```

后续 DWD 必须明确规范事实来源，避免当前状态表与事件表被重复统计。

---

# 27. SCD Type 2 范围

V2 只正式实现一个拉链维度：

```text
dim_product_zip
```

不同时建设：

```text
dim_user_zip
```

用户维度使用普通：

```text
dim_user
```

保存当前有效用户属性。

这样能够完整展示 SCD Type 2，同时避免增加不必要复杂度。

---

# 28. 为什么选择商品维度

商品天然存在：

```text
价格变化
上下架变化
品牌变化
类目变化
```

源端已经存在：

```text
biz_product_change_event
```

用于记录这些历史变化。

因此商品维度作为 V2 唯一正式拉链维度。

---

# 29. dim_product_zip

建议包含：

```text
product_sk
sku_id

spu_id
category_id

brand_code
brand_name

sku_name
sale_price_cents
sku_status

start_time
end_time
is_current
```

其中：

```text
product_sk
```

为数仓代理键。

```text
sku_id
```

为业务自然键。

---

# 30. 商品变化数据

4,000 SKU 中建议约：

```text
20%～30%
```

在 Bootstrap 90 天历史期间发生至少一次属性变化。

主要变化类型：

```text
PRICE
STATUS
CATEGORY
BRAND
```

变化频率：

```text
大部分变化 1 次
少部分变化 2～3 次
```

不为了拉链表人为制造大量无意义版本。

---

# 31. Bootstrap 中必须存在商品历史变化

例如：

```text
2025-12-10
SKU-A price = 9900

2026-01-08
SKU-A price = 10900

2026-02-17
SKU-A price = 11900
```

Bootstrap 截止时：

```text
biz_sku
```

保存最终当前价格：

```text
11900
```

同时：

```text
biz_product_change_event
```

保存商品历史变化。

这样在 DIM 初始化时可以真正构建多版本：

```text
dim_product_zip
```

---

# 32. 拉链时间边界

采用左闭右开时间区间：

```text
[start_time, end_time)
```

例如：

```text
sku_id   price   start        end
1001      9900   2025-12-10   2026-01-08
1001     10900   2026-01-08   2026-02-17
1001     11900   2026-02-17   9999-12-31
```

当前版本：

```text
is_current = 1
```

历史版本：

```text
is_current = 0
```

---

# 33. Bootstrap 拉链初始化

Bootstrap 初始化商品拉链维度时：

```text
商品当前状态
+
商品历史变更事件
        ↓
按照 effective_at 排序
        ↓
恢复商品属性历史版本
        ↓
dim_product_zip
```

不建设复杂的通用 SCD 框架。

只需要保证：

```text
同一 sku_id 的历史版本连续
版本之间不存在时间重叠
每个 sku_id 只有一个 current 版本
```

---

# 34. Continuous 拉链维护

Continuous 阶段商品发生变化时：

```text
UPDATE biz_sku
+
INSERT biz_product_change_event
```

例如：

```text
2026-03-05
price:
11900 → 12900
```

实时 CDC 可以立即捕获源端变化。

T+1 离线任务：

```text
抽取新增 product_change_event
        ↓
关闭 dim_product_zip 旧版本
        ↓
插入新的当前版本
```

完成 SCD Type 2 增量维护。

---

# 35. 商品事实关联历史版本

事实表不能始终关联商品当前版本。

历史交易根据交易发生时间匹配商品拉链：

```text
dim_product_zip.start_time
<=
order_time
```

并且：

```text
order_time
<
dim_product_zip.end_time
```

从而找到交易发生时有效的：

```text
product_sk
```

保证历史订单分析使用当时有效的商品属性。

---

# 36. 用户维度

V2 用户维度固定为：

```text
dim_user
```

不建设：

```text
dim_user_zip
```

当前保留：

```text
用户业务键
必要用户属性
当前用户状态
```

`biz_identity_mapping` 自身的：

```text
identity_version
effective_from
effective_to
```

继续用于身份映射历史，但不再包装成第二套 SCD Type 2 展示对象。

---

# 37. Business Generator 输出

Bootstrap 输出：

```text
21 CSV
+
dataset_manifest.json
```

CSV：

```text
biz_user.csv
biz_visitor.csv
biz_identity_mapping.csv

biz_category.csv
biz_spu.csv
biz_sku.csv
biz_product_change_event.csv

biz_cart.csv
biz_cart_item.csv
biz_cart_merge_record.csv

biz_order.csv
biz_order_item.csv
biz_order_status_event.csv

biz_payment_attempt.csv
biz_payment_event.csv

biz_refund_request.csv
biz_refund_transaction.csv
biz_refund_event.csv

biz_coupon_template.csv
biz_coupon.csv
biz_coupon_event.csv
```

---

# 38. Generator Seed

Generator 必须支持：

```text
--seed
```

Seed 由执行参数传入。

不得继续使用旧 Pilot Generator 中的硬编码固定 Seed。

---

# 39. Dataset Manifest

第一版 Generator 就必须生成：

```text
dataset_manifest.json
```

至少记录：

```text
dataset_version
generator_version
seed

history_start
history_end
history_days
timezone

generated_at
```

并记录每张业务表：

```text
table_name
row_count
csv_file_size_bytes
```

---

# 40. Manifest 业务统计

至少记录：

```text
paid_orders
canceled_orders
created_orders

payment_success
payment_failed
payment_init
retry_payment_orders

refund_success
refund_failed

coupon_used
coupon_locked
coupon_expired

product_change_events
changed_sku_count
multi_change_sku_count
```

---

# 41. Manifest 流量统计

记录：

```text
min_daily_orders
max_daily_orders
avg_daily_orders

peak_date
peak_date_orders

peak_hour
peak_hour_orders
```

---

# 42. Manifest 分布统计

商品：

```text
distinct_sku
top_5_percent_sku_share
top_20_percent_sku_share
```

用户：

```text
registered_users
visitors
mapped_visitors
active_order_users
repeat_buyers
avg_orders_per_user
```

---

# 43. LOAD DATA 留证

每张表正式装载时记录：

```text
table_name

csv_rows
mysql_rows

csv_bytes

load_start_time
load_end_time
load_elapsed_seconds

rows_per_second
MB_per_second
```

---

# 44. Source Gate

21 张 CSV 全部进入 MySQL 后执行一次集中 Source Gate。

检查：

```text
table_count = 21

PK duplicate = 0
critical FK orphan = 0

invalid time = 0

order amount mismatch = 0
invalid order item count = 0

multiple success payment = 0
payment timeout violation = 0

refund overflow = 0

invalid coupon relation = 0
```

不再执行每张表独立 Pilot。

---

# 45. ODS Gate

全部一期业务表进入 ODS 后统一检查：

```text
MySQL 行数与 ODS 行数

duplicate
missing
extra
invalid partition
```

同时验证：

```text
增量数据是否完整捕获
业务数据是否进入正确 dt 分区
```

---

# 46. Model Gate

DWD 与 DIM 完成后统一检查：

```text
Order ↔ Order Item

Order ↔ Payment

Order Item ↔ Refund

Order ↔ Coupon

Fact ↔ Dimension
```

商品拉链额外检查：

```text
product_zip_rows
distinct_sku

multi_version_sku_count

invalid_range_count = 0
overlap_version_count = 0
multiple_current_count = 0
```

---

# 47. 离线 Benchmark

正式链路完成后再进行性能测试。

记录：

```text
DataX rows/s
DataX MB/s

CSV size
ORC + Snappy size
compression ratio

Spark duration
Shuffle Read
Shuffle Write
Task Count
Spill
```

选择 1～2 个核心 Spark Job 做优化前后对比。

不预设性能提升比例。

---

# 48. 实时 Benchmark

实时链路稳定后测试：

```text
Kafka throughput
Kafka lag

Flink input records/s
Flink output records/s

Checkpoint duration
Checkpoint size
Backpressure

End-to-End P95 latency

Doris load throughput
Doris query P95
```

不提前编写性能数字。

---

# 49. 实时延迟定义

统一定义：

```text
End-to-End Latency
=
Doris 可查询时间
-
源业务提交时间
```

至少记录：

```text
Average
P50
P95
```

有条件再记录：

```text
P99
```

简历优先使用：

```text
P95
```

---

# 50. 离实时一致性

同一业务日期最终比较：

```text
Offline ADS
与
Realtime Doris
```

至少覆盖：

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
```

目标：

```text
最终收敛一致
```

---

# 51. 简历量化目标

项目完成后至少能够真实证明：

```text
21 张 OLTP 业务表

90 天历史数据

10 万级订单

约 28.5 万订单明细

百万级交易业务记录

300～500 万用户行为事件

商品 SCD Type 2 历史维度
```

后续通过实测再补充：

```text
DataX 吞吐

ORC + Snappy 压缩率

Spark 核心 ETL 优化前后耗时

Shuffle 降幅

Kafka 与 Flink 稳定吞吐

实时 P95 延迟

Doris 查询 P95

离实时一致性
```

---

# 52. 当前开发顺序

数据规格只给出依赖顺序，具体 Phase / Step 以整体实施计划为准。

```text
01
确认 ecommerce_oltp
21 张正式表实际 DDL

02
冻结 21 CSV Field Contract

03
根据 Metrics Contract
完成 Metric Required Fields Review

04
统一设计 Business + Behavior
ODS / DWD / DIM / DWS / ADS Logical Model

05
设计并实现 Business Generator

06
生成：
21 CSV
+
dataset_manifest.json

07
LOAD DATA
→ ecommerce_oltp

08
Source Gate

09
Business Offline：
ODS Physical Design
→ Historical Full Load
→ ODS Gate

10
Business Realtime：
Formal CDC Initial Snapshot
→ CDC Gate

09 与 10 在 Source Gate 后可并行推进。

11
继续建设：
Business DWD / DIM / DWS / ADS / Doris
以及 Realtime Domain Model / Serving

12
冻结 DolphinScheduler Orchestration Baseline：
business_date
workflow / task naming
retry / failure / alert principle

批处理任务先独立验证，
再进行 Workflow Integration。

13
满足：
ODS_GATE = PASS
+
CDC_GATE = PASS

后启动：
Continuous Business Increment

14
正式 T+1：
DolphinScheduler
→ DataX Incremental
→ affected business dates
→ ODS
→ DWD / DIM
→ DWS / ADS
→ Doris

15
Realtime：
长期运行 Flink CDC / Kafka / Flink
持续消费同一 ecommerce_oltp 的变化

16
Behavior Generator：
Bootstrap
+
Continuous

Historical Behavior 批处理可接入 DolphinScheduler；
Continuous Behavior 使用长期 Kafka / Flink 链路。

17
离实时对账：
DolphinScheduler 触发 Reconciliation SQL / Script
→ RECONCILIATION_GATE

18
专项 Benchmark

19
提取最终简历量化数据
```

Continuous 不允许在 Offline Historical ODS 与 Realtime Initial Snapshot 的基线尚未稳定时提前启动。

---

# 53. 当前明确停止的方案

不再继续：

```text
旧 100 单 Generator

旧固定 Seed

围绕 100 单继续逐表开发

每张表分别执行：
ODS → DWD → 验收
然后再做下一张

历史百万级数据逐行 INSERT

离线业务数据单独生成一套

实时业务数据再生成另一套

同时建设 dim_user_zip 和 dim_product_zip
```

---

# 54. 当前唯一正式基线

```text
SOURCE
------
ecommerce_oltp


BUSINESS GENERATOR
------------------
1 个

Bootstrap:
Python
→ 21 CSV
→ LOAD DATA
→ ecommerce_oltp

Continuous:
Business Transactions
→ INSERT / UPDATE
→ ecommerce_oltp


BEHAVIOR GENERATOR
------------------
1 个

Bootstrap:
历史行为数据
→ Offline ODS

Continuous:
行为事件
→ Kafka


HISTORY
-------
2025-12-01
~
2026-02-28

90 days


CONTINUOUS
----------
2026-03-01
→ future


SCALE
-----
100,000 orders
≈285,000 order_items
≈1M OLTP rows
3M～5M behavior events


SCD2
----
唯一正式拉链维度：
dim_product_zip

普通用户维度：
dim_user


OFFLINE
-------
ecommerce_oltp
→ DataX
→ ODS
→ Spark
→ DWD
→ DIM
→ DWS
→ ADS
→ Doris


REALTIME
--------
ecommerce_oltp
→ Binlog
→ Flink CDC
→ Kafka
→ Flink
→ Doris


INCREMENTAL EXTRACTION
----------------------
当前状态表：
主要根据 updated_at 判断是否发生变化

事件表：
主要根据 recorded_at 判断是否新增事件


WAREHOUSE PARTITION
-------------------
按照业务实际发生日期确定 dt

订单：
订单业务日期

支付、退款、状态事件：
事件实际发生日期


ORCHESTRATION
-------------
DolphinScheduler
= 批处理 Control / Orchestration Plane

正式周期编排重点：
Continuous T+1
Historical Behavior Batch
Reconciliation

business_date
= 调度 / 增量抽取窗口
≠ Hive dt

DataX / Spark / SQL / Python
= 实际批处理执行任务

Flink CDC / Realtime Flink Applications
= 长期运行流任务


FINAL
-----
离实时业务同源

实时先处理业务变化

离线 T+1 再同步同一业务源

增量抽取字段决定“抓什么”

业务时间字段决定“放哪个 dt 分区”

最终统一指标口径并完成离实时对账

Benchmark 数值全部来源于真实工程测试
```

本版本作为后续 V2 数据生成、离线链路、实时链路、商品拉链维度、数据质量和 Benchmark 的统一数据设计基线。
