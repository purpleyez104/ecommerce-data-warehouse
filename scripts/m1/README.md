# Milestone 1 运行入口

执行真实组件命令的验收脚本必须在目标 Ubuntu ECS 上由 `yee` 运行。本地 Git Bash 只用于 syntax 和 Contract Test。按 `DR-026`，组件门禁以目标集群已展示并经用户确认的核心能力为主；完整运行目录继续用于复现、审计和故障诊断，不以非核心附件缺失单独否定已确认能力。

## 当前 M1 Runtime 状态

M1 已确认 Hadoop、MySQL、Hive、Spark、DataX、Kafka、Flink、Flink CDC、Flink Kafka source/sink、Doris、Flink Doris Connector 和 DolphinScheduler 3.4.2 + MySQL JDBC Registry 的核心能力。仓库现有自动化脚本及共享 Evidence Contract 继续用于可重复复测；未提供专用入口的已确认组件不因此被降级，也不虚构 M6 正式 DAG 已完成。

## 共享组件验收 Evidence Contract

`scripts/m1/lib/evidence-common.sh` 是 MySQL、Hive、Kafka KRaft、Spark on YARN 和 DataX 验收入口共同使用的最小公共库，当前状态为 `implemented`，并已通过本地 Git Bash syntax、正常路径、强制失败、未初始化调用和 Cleanup Owner 定向测试。本地结果不代表任何组件已经在 VM Runtime 通过。

公共库负责：

- 校验组件名、`run-id`、绝对输出根和全新运行目录，并设置 `umask 077`。
- 创建统一 Evidence Layout，记录步骤日志、断言、命令退出码和 SHA-256。
- 对 Password、Secret、Token、Private Key、JDBC Password 和 Authorization 信息进行去敏。
- 写入包含固定核心字段的 `summary.env`，状态只使用 `PASS`、`PARTIAL` 或 `FAIL`。
- 注册并执行带 Owner、`m1_accept_<run-id>` 前缀、当前 run-id 和禁止目标 Guard 的 Cleanup。

每次组件运行使用以下结构：

```text
<output-root>/<run-id>/
  summary.env
  commands.log
  assertions.log
  versions/
  configuration/
  runtime/
  functional/
  recovery/
  cleanup/
```

组件脚本只能调用已经冻结的公共 API，不得复制、绕过或自行改变公共安全逻辑。公共库不包含组件命令、服务生命周期或业务对象操作。公共 Contract 已完成本地验证；后续仅在接口变化、状态矛盾、脚本身份不明或失败传播无法确认等风险触发时补充 targeted cross-script verification。项目运行不得依赖 `.local-notes/` 中的本地验收记录。

## 虚拟机与组件安装现场采集

在编写 MySQL、Hive、Kafka KRaft、Spark on YARN 和 DataX 的组件级功能验收前，先从 `hadoop201` 采集三节点虚拟机环境与已安装组件现场：

```bash
bash scripts/m1/collect-vm-environment-evidence.sh \
  --run-id m1-vm-20260913-01 \
  --output-dir /data/logs/ecommerce-data-warehouse/m1/m1-vm-20260913-01 \
  --max-clock-skew-seconds 5
```

前置条件：

- 当前用户为 `yee`，当前节点为 `hadoop201`。
- `hadoop201` 能通过主机名免密 SSH 到三个节点。
- 输出目录必须为 `/data/logs/ecommerce-data-warehouse/m1/` 下的新绝对路径；非空目录、过宽目录和解析后逃逸该证据根目录的路径会被拒绝。
- `--max-clock-skew-seconds` 可选，默认值为 5，必须为非负整数。

脚本只读采集：

- OS、Kernel、CPU、Memory、Swap、Load、Timezone、网络解析和节点时间差。
- Block device、Filesystem、Mount、容量以及 `/data` 和关键目录的权限。
- Java 8/11/17、关键 Java 进程实际使用的可执行文件和监听端口。
- MySQL、Hive、Kafka、Spark、DataX 的命令、稳定路径、版本或构建标识、Plugin 路径；DataX 同时识别 `/data/module/datax` 与历史 `/data/module/datax-current` 入口。
- 三节点 Hive 稳定软链接是否一致，以及节点上并存的 Hive 版本目录。
- 配置文件中的白名单关键项；敏感键、完整 Credential 和业务数据不采集。

输出位于 `--output-dir`。每个节点拥有独立 evidence 文件，根目录的 `summary.env` 给出：

- `COLLECTED`：三节点采集完成，并且五个组件至少在一个节点被发现。
- `PARTIAL`：三节点采集完成，但至少一个组件为 `NOT_FOUND` 或 `UNKNOWN`；脚本退出状态仍为 0，必须人工核对。
- `FAIL`：SSH、节点身份、必要采集或时间偏差检查失败；脚本返回非零。

`COLLECTED` 只表示现场证据已收集，不表示任何组件达到 `verified`。本脚本不执行组件功能验收，不启动、停止或重启服务，不安装软件，不修改配置，不创建数据库、表或 Kafka Topic，也不操作 HDFS 临时对象。

`summary.env` 中的 `component.hive.stable_path_consistency` 只比较三个节点 `/data/module/hive` 的解析目标。`DRIFT` 表示节点指向不同版本，必须先人工确认最终版本；它不会自动修改软链接。DataX 按 `python3 bin/datax.py` 的实际运行方式探测：入口文件可读即可记录为已发现，并同时记录 Python 路径与版本；只有 Plugin 目录而没有可读入口时仍判定为 `NOT_FOUND`，避免把源码包或不完整运行包误判为运行包。

若失败，保留本次输出目录和 `summary.env`，不要在修复前覆盖或复用相同目录。运行层面的回滚仅是人工确认 `run-id` 后删除该次证据目录；脚本本身不提供删除入口。

采集完成后，按 `DR-007` 保留原目录结构，通过 MobaXterm 将整个运行目录下载到 Windows 工作区：

```text
.local-notes/m1-evidence/inbox/m1-vm-20260913-01/
```

按 `DR-027`，后续验收至少回传 `summary.env`、关键命令或断言的汇总输出、最终退出状态，以及可定位本次执行逻辑的 Git revision 或脚本 SHA-256。三个节点的完整 evidence 目录属于复现、审计和故障诊断材料；除非它是判断某项 Hard Gate 的唯一依据，否则缺失时不单独阻断验收。`.local-notes/` 已由 Git 忽略，原始日志、现场 UUID 和未审查配置不得加入 Git。下载后可在 Windows 工作区确认忽略规则：

```powershell
git check-ignore -v .local-notes/m1-evidence/inbox/m1-vm-20260913-01
```

## 第一门禁：Hadoop 非中断验证

在 `hadoop201` 的仓库根目录执行：

```bash
bash scripts/m1/collect-hadoop-evidence.sh \
  --run-id m1-hadoop-20260904-01 \
  --output-dir /data/logs/ecommerce-data-warehouse/m1/m1-hadoop-20260904-01
```

固定输入：

```text
alpha beta beta
gamma alpha
```

预期 `wordcount`：

```text
alpha 2
beta 2
gamma 1
```

成功条件：

- 当前用户为 `yee`，当前节点为 `hadoop201`。
- 三节点可通过免密 SSH 访问，主机名与目标一致。
- Hadoop 版本、进程、HDFS report 和 YARN 节点信息成功采集。
- HDFS 上传后 SHA-256 与本地固定文件一致。
- MapReduce 作业退出状态为 0，结果与固定预期一致。
- 找到 YARN application ID 并保存聚合日志。
- 脚本只删除自己创建的 `/tmp/ecommerce_data_warehouse/m1/<run-id>`。

结果位置：`--output-dir` 指定目录。`summary.env` 中 `status=PASS` 且脚本退出状态为 0 才表示本门禁通过。

## 第二门禁：受控重启验证

仅在第一门禁结果完成评审后执行：

```bash
bash scripts/m1/restart-hadoop-and-verify.sh \
  --run-id m1-hadoop-restart-20260904-01 \
  --output-dir /data/logs/ecommerce-data-warehouse/m1/m1-hadoop-restart-20260904-01 \
  --confirm-restart EXISTING_HADOOP_CLUSTER
```

该脚本会停止并重新启动现有 HDFS、YARN 和 JobHistoryServer。确认参数不完全匹配时脚本返回非零且不改变服务。

成功条件：

- 重启前创建的 HDFS 固定文件在重启后仍可读取且 SHA-256 一致。
- HDFS 恢复 2 个 Live DataNode。
- YARN 恢复 2 个 RUNNING NodeManager。
- `hadoop201` 恢复 NameNode、SecondaryNameNode、ResourceManager 和 JobHistoryServer。
- 脚本退出状态为 0，`summary.env` 为 `status=PASS`。

## 失败处理

- 不执行 NameNode 格式化，不删除现有 Hadoop 数据或配置。
- 保留输出目录中的日志和 `summary.env`。
- 将失败命令、退出状态和日志路径记录到 `docs/operations/troubleshooting.md`。
- 若 Hadoop 复测失败，停止依赖该能力的新运行并先完成修复；不得据此覆盖已经保留的历史验收记录。
