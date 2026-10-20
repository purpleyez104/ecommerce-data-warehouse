# DolphinScheduler 调度入口

Milestone 1 已在目标三节点集群验证 DolphinScheduler 3.4.2 + MySQL JDBC Registry。根据 `DR-049`，项目不安装或维护 ZooKeeper；Kafka 继续使用 KRaft。

## 运行拓扑

- `hadoop201`：Master、API、Alert，以及 MySQL Metadata / JDBC Registry。
- `hadoop202`、`hadoop203`：各一个 Worker。
- API Health：`http://127.0.0.1:12345/dolphinscheduler/actuator/health`，远程访问使用 SSH 隧道，不开放公网端口。

组件原生入口为：

```bash
/data/module/apache-dolphinscheduler-3.4.2-bin/bin/dolphinscheduler-daemon.sh \
  start|stop|status master-server|worker-server|api-server|alert-server
```

启动顺序为 `Master → Worker → API → Alert`，停止顺序相反。账号和密码只允许从运行环境或受控 Secret 注入，不得写入仓库、命令输出或验收文档。

## 已验证边界

固定项目 `m1_jdbc_registry_acceptance` 包含：

- `m1_jdbc_success`：Shell 退出 `0`，最终状态必须为 `SUCCESS`。
- `m1_jdbc_expected_failure`：Shell 退出 `17`，最终状态必须为 `FAILURE`。

首次运行和全角色受控重启后复跑均已通过。该结果只证明 M1 调度组件能力，不证明 M6 正式 T+1 DAG、补数、重试、质量阻断或 Doris 对账已经由 DolphinScheduler 编排。

## M6 正式 DAG Contract

`workflow_contract.json` 固定完整 T+1 链路七个 Task 的顺序、运行参数和重试边界；该 DAG 已发布并产生自动重试、失败阻断和历史补数失败证据，但尚未取得完整成功终态。

```bash
python3 scheduler/dolphinscheduler/render_workflow_payload.py \
  --contract scheduler/dolphinscheduler/workflow_contract.json \
  --output runtime/dolphinscheduler/ecommerce_offline_t1.json
```

## M6 Aggregate Backfill Contract

当 ODS、DIM、DWD 已存在且 Model Gate 可通过时，使用 `backfill_workflow_contract.json` 从最低失效层回补。该 Workflow 固定为：

```text
model_ready_check
→ dws_ads_build
→ quality_gate
→ doris_load
→ serving_reconciliation
```

它不包含 DataX、ODS Ready 或 DIM/DWD Build，避免把 Type 1 当前态维度错误地按历史日重复写入。`business_date` 表示回补目标日，`model_as_of_date` 表示 Cohort 模型观察窗口终点，两者必须显式区分。

当前 Workflow Code 为 `187427451612864`。Instance `17` 已通过 Model Ready、DWS/ADS 和 40-rule Quality Gate；Doris Load 在一次自动重试后仍于 `frame.count()` 发生 `java.io.EOFException`，最终 Reconciliation 未运行。没有新的 YARN Task Result、HDFS Block 或序列化边界证据前，不重复触发相同路径。

```bash
python3 scheduler/dolphinscheduler/render_workflow_payload.py \
  --contract scheduler/dolphinscheduler/backfill_workflow_contract.json \
  --output runtime/dolphinscheduler/ecommerce_aggregate_backfill.json
```

质量 Gate、Model Ready Gate 和最终 Serving 对账固定为不自动重试；它们失败时必须阻断下游或工作流终态。DataX、模型计算和 Doris 装载允许一次基础设施类重试。同一 Workflow 使用 `SERIAL_WAIT`，避免两个补数实例并发覆盖相同 Hive 分区。

`datax_env` 与 `doris_env` 只传递目标机上权限受控的私有环境文件路径；`doris_connector_jar` 传递已验证 Connector 的绝对路径。不得把密码写入 Workflow Global Parameter、Contract 或仓库文件。

运行日志位于各角色目录下的 `logs/`。回滚时停止 DolphinScheduler 角色即可；不得删除 MySQL Metadata Schema、Registry 表或历史任务实例。
