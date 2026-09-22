> **整理说明（2026-09-20）**：该 README 原为生成器首次交付时编写，其中“尚未在 hadoop201 运行”的旧状态说明已过时。后续用户提供的终端结果确认：`smoke-v1-001` 10 单／34 明细、`hist-v1-001` 100 单／319 明细实际写入成功；100 单订单 CDC 创建 100/100、最终状态 69 PAID／31 CANCELED；4 项业务一致性异常为 0。该结果基于用户提供的终端输出，并非本地打包环境重连集群验证。所有历史局限（如离实时 Exactly-Once 未证明）仍然保留。原测试已移至 `tests/unit/`（仓库根目录），验收 SQL 已移至 `mysql/sql/acceptance.sql`（仓库根目录）。

# Python 电商业务数据生成器 V1

**当前交付：可运行源码 + 离线测试通过；尚未连接用户的 hadoop201 执行真实 MySQL 写入。** 只用于既有 `ecommerce_oltp_m2_acceptance` 验收库；不执行建表、不改 21 表 DDL、不使用旧种子 SQL、不关闭外键。

## 1. 工程范围

- 基于项目已确认的 21 张 `biz_*` 物理模型编写。`src/ecommerce_generator/schema_contract.json` 是从项目 M2-03 新版物理设计文件提取的字段**预检查契约**；不是要重新部署的 DDL。连接实际数据库时核对 21 张表及所需字段；实际数据约束还由 MySQL 和事务校验把关。
- 首批约 100 单；1～5 条不同 SKU，金额统一使用人民币**分**（整数），订单头与明细优惠按整数分配守恒，支付截止时间精确为创建后 15 分钟。
- 支付成功 / 支付失败重试 / 订单取消 / 订单券锁定核销解锁 / 成功与失败退款；当前状态与专用历史事件在**同一条 MySQL 事务**内提交。退款预留和累计已退、成功退款数量同步更新。重复支付回调使用相同稳定 callback ID 查验原事件，不再次生成支付成功事件。
- 隔离的新用户、访客、SPU、SKU、商品变更历史、购物车及登录合并、身份映射；不会复用或修改数据库当前已有的正式测试记录。只对本次创建的记录做更新。
- `--mode history`：默认回放 90 天跨度的 100 笔历史订单（历史末端留出合理处理时延）。`--mode live`：单笔事务逐笔写库；`--count 0` 时持续写入直到 Ctrl+C，速率由 `--interval-seconds` 控制。它们都写 **MySQL**，通过已经运行的 Flink CDC 读取真实 Binlog，生成器不向 Raw CDC Topic 发送数据。
- 独立 `ecommerce-behavior` 生成页面／商品／购物车三组行为事件：先落本地 JSONL；仅 `--publish` 时写入用户配置的三组行为 Topic，**不伪装 CDC**。

## 2. 安装（hadoop201，Python ≥3.10）

本目录位于项目仓库的 `mock/generator/ecommerce_generator_v1/`；目录移动不改变生成器的业务或运行契约。

```bash
cd /data/projects/ecommerce-data-warehouse/mock/generator/ecommerce_generator_v1
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test,behavior]'
cd ../../..
bash tests/run_unit.sh
cd mock/generator/ecommerce_generator_v1
```

没有安装第三方依赖时，可以设置 `PYTHONPATH=src` 运行纯 Python 的 Dry Run；实际 MySQL 写入需要 PyMySQL。不要将真实密码写入仓库、命令参数或上传给助手。

## 3. 首先运行 Dry Run（不会连接或写入数据库）

为保证严格复现，固定 `run-id`、随机种子和时间锚点；运行号只允许字母、数字、下划线和横线，不超过 16 位。Dry Run 只打印操作数量和业务场景，不暴露业务明细或口令。

```bash
python -m ecommerce_generator \
  --mode history --count 100 --history-days 90 \
  --run-id hist-v1-001 --seed 20260920 \
  --anchor 2026-09-20T14:00:00
```

不传 `--anchor` 时采用运行时的 Asia/Shanghai 本地日期时间；历史模式拒绝未来的锚点。测试样本会强制至少各覆盖一次取消、重试、退款成功、退款失败、用券和普通支付，剩余由 `--paid-rate`、`--retry-rate`、`--refund-rate`、`--coupon-rate` 控制。小样本的强制路径会影响实际样本比例，不宣称精准满足输入概率。

## 4. 真实 MySQL 写入：先预检，后显式执行

在私有 Shell 中提供连接参数。**不要将含密码的 `.env` 加入 Git，不能在消息中贴出密码**。例如：

```bash
export MYSQL_HOST=hadoop201
export MYSQL_PORT=3306
export MYSQL_DATABASE=ecommerce_oltp_m2_acceptance
export MYSQL_USER=ecommerce_user
# 在私有终端安全地设置 MYSQL_PASSWORD；不要通过聊天、仓库或 shell 历史明文保存
read -rsp 'MySQL password: ' MYSQL_PASSWORD; echo
export MYSQL_PASSWORD
```

预检（21 表所需字段、当前库、运行批次是否重复、会话时区、外键开关；不写库）：

```bash
python -m ecommerce_generator --mode history --count 100 \
  --run-id hist-v1-001 --seed 20260920 --preflight-only
```

预检通过后，写入约 100 笔订单。**`--apply` 是显式写入许可**：

```bash
python -m ecommerce_generator --mode history --count 100 \
  --run-id hist-v1-001 --seed 20260920 \
  --anchor 2026-09-20T14:00:00 --apply
```

部署时间晚于示例时间时，该锚点可替换为实际验收日；注意生成器禁止历史锚点晚于当前中国时间。批次标识被写入业务键并映射到隔离的 BIGINT ID 段；发现相同批次已有数据时拒绝重放。每笔订单独立事务，一笔失败立即回滚并终止，**此前已成功提交的订单不会自动回滚**；不能简单换标识重放来假装无重复。先排查失败和清理策略，不自动 DELETE 或 TRUNCATE。

大体量写入建议先在独立验收数据库测试；程序固定仅接受 `ecommerce_oltp_m2_acceptance`，不直接写生产业务库。`ecommerce_user` 需要对该验收库拥有对应的 SELECT/INSERT/UPDATE/DELETE 权限；账户授权策略由使用者管理。

## 5. 持续增量

在历史批次完成、原 21 表 CDC 作业处于 RUNNING 后，换一个**新运行号**持续产生真实业务 Binlog：

```bash
python -m ecommerce_generator --mode live --run-id live-v1-001 \
  --seed 20260921 --count 0 --interval-seconds 5 --apply
```

不想无限执行则指定 `--count 10`。`Ctrl+C` 停止后已提交的订单保留，当前未完成事务回滚；如需重启，不重用老运行号。历史和实时都是写 MySQL，同一个已运行 CDC 作业接续消费 Binlog；首次快照与历史 DataX 的重叠去重不是本程序能单独证明的，见 `docs/limitations.md`。

## 6. 行为数据：独立流，不是 CDC

```bash
python -m ecommerce_generator.behavior \
  --run-id hist-v1-001 --seed 20260920 --count 1000 \
  --anchor 2026-09-20T14:00:00 --history-days 90 \
  --output /tmp/m2_behavior_hist_v1_001.jsonl
```

执行 `--publish` 前由使用者创建并设置三个**不同的行为 Topic**：

```bash
export KAFKA_BOOTSTRAP_SERVERS='hadoop201:9092,hadoop202:9092,hadoop203:9092'
export M2_PAGE_TOPIC='behavior_page_m2_v1'
export M2_PRODUCT_TOPIC='behavior_product_m2_v1'
export M2_CART_TOPIC='behavior_cart_m2_v1'
# 在上面生成 JSONL 的同一命令里添加 --publish，并使用一个未存在的新输出路径
```

这些 Topic 名仅供示例，**不是最终冻结的 Topic 方案**。行为生成器不访问 MySQL，因此 `--run-id`、种子和锚点必须与已成功执行的 OLTP 批次一致，才能保持 ID 语义；不会自动检查你是否真的运行过 OLTP 批次。JSONL 是本地归档，不是 HDFS 90 天行为归档正式方案。发送成功只代表 Kafka Producer 收到 ACK，不等于跨 MySQL 与 Kafka 的原子事务。

## 7. 验收建议（在集群执行）

先验证 Pytest，再做 `--preflight-only`，再做 10 单验收批次，核对 `biz_order`、`biz_order_item`、`biz_payment_attempt`、`biz_refund_*` 和事件表的关联与金额，最后检查 `cdc_m2_21tables_acceptance` Topic 是否收到这**一批**新业务键的真实 Debezium 事件；确认后执行 100 单和 live。Kafka 验收应按业务键+表+事件版本过滤，不能仅比较总 Offset。`mysql/sql/acceptance.sql`（仓库根目录）提供无需暴露业务字段的 SQL 核验模板。

## 8. 当前真实验收状态

- 本地：静态编译、Dry Run、单元测试（见本次交付的测试输出）可执行。
- 远程：**尚未直接连接 hadoop201，因此没有实际执行 --apply、没有证明本生成器 SQL 在用户 MySQL 上通过、没有证明生成数据经 CDC 进入 Kafka。** 以前通过的是手工三表和 21 表小规模 CDC 验收，不得冒充生成器验收。
- 设计边界和待补项目见 `docs/limitations.md`。
