# Milestone 1 安装与排障记录

版本：`0.1-draft`
状态：`in progress`
更新时间：2026-09-05

## 使用范围

本文件只记录目标 ECS 上真实发生的安装、启动、连通、最小任务和重启问题。候选风险、未执行命令和学习笔记不得写成已经发生的故障。

每条记录必须包含：

- 编号、日期、组件、节点和精确版本。
- 触发命令、预期退出状态、实际退出状态和关键错误。
- 根因证据，不以猜测代替。
- 实际修复、复测命令、复测结果和日志位置。
- 影响范围、已知限制和回滚方式。
- 是否需要新增或替代正式决策。

原始日志保存在 ECS 本地 `/data/logs/ecommerce-data-warehouse/m1/`，不提交 Git。仓库只保留去敏摘要。

## 已知约束，不是已发生故障

### Hadoop 使用独立 JDK 11

- 三节点默认环境为 OpenJDK 17。
- Hadoop 3.4.1 的当前运行配置在 `hadoop-env.sh` 中固定使用 OpenJDK 11。
- M1 脚本不得用修改全局 `JAVA_HOME` 的方式修复 Hadoop，也不得把客户端 Java 17 输出误当成守护进程 Java 版本。

### YARN 与 Doris FE 端口冲突

- YARN ResourceManager Scheduler 已使用 `8030`。
- Doris FE HTTP 端口已决定使用 `18030`。
- Doris 安装前必须在三节点执行端口占用检查，并同步配置、健康检查、安全组和 SSH 隧道说明。

### DolphinScheduler 的 ZooKeeper 边界

- 单节点 ZooKeeper 只作为 DolphinScheduler 的开发环境注册中心。
- Kafka 必须保持 KRaft 模式，不得连接或依赖该 ZooKeeper。
- 单节点 ZooKeeper 不构成高可用，必须在文档和面试表述中保留该限制。

## 排障记录

## M1-ISSUE-001：Hadoop 服务未启动导致非中断验证失败

- 日期：2026-09-05
- 组件与版本：Hadoop 3.4.1
- 节点：`hadoop201`、`hadoop202`、`hadoop203`
- 状态：resolved
- 日志位置：ECS `/data/logs/ecommerce-data-warehouse/m1/m1-hadoop-20260905-01/`；原始副本位于本地忽略目录

### 触发与现象

执行 `scripts/m1/collect-hadoop-evidence.sh`，预期退出状态为 0，实际退出状态为 255。三节点 SSH 采集成功，但三节点 `jps -lv` 均只有 `Jps`；`hdfs dfsadmin -report` 连接 `hadoop201:8020` 被拒绝，脚本未进入 HDFS 固定文件和 MapReduce 验证。

### 根因证据

用户确认执行前尚未启动 Hadoop 进程。`hadoop201-remote.txt`、`hadoop202-remote.txt` 和 `hadoop203-remote.txt` 均包含正确节点、用户和时间，排除本次失败由 SSH 不通导致；`hdfs-report.txt` 明确记录 NameNode RPC 连接拒绝。

### 修复与复测

由 `yee@hadoop201` 按既有方式启动 HDFS、YARN 和 JobHistoryServer。使用新运行编号 `m1-hadoop-20260905-02` 复测，脚本退出状态为 0 且 `summary.env` 为 `PASS`：HDFS 固定文件上传前后 SHA-256 一致，2 个 DataNode 为 Live，2 个 NodeManager 为 RUNNING，MapReduce WordCount application `application_1788593194299_0001` 最终状态为 `SUCCEEDED`，聚合日志状态为 `SUCCEEDED`，固定结果为 `alpha=2`、`beta=2`、`gamma=1`。

### 影响与限制

第一次失败不否定已确认的 Hadoop 版本和拓扑，但说明验证脚本要求服务处于运行状态。第二次通过只满足非中断门禁；在受控重启及哨兵读取完成前，Hadoop 整体仍不得标记为 `verified`。

### 回滚

本次恢复只启动既有服务，没有修改配置或格式化 NameNode。若服务启动后状态异常，应停止后续门禁并保留日志；不得通过删除 Hadoop 元数据恢复验证。

## M1-ISSUE-002：受控重启脚本误判 hadoop201 进程缺失

- 日期：2026-09-05
- 组件与版本：Hadoop 3.4.1；`scripts/m1/restart-hadoop-and-verify.sh`
- 节点：`hadoop201`、`hadoop202`、`hadoop203`
- 状态：resolved
- 日志位置：ECS `/data/logs/ecommerce-data-warehouse/m1/m1-hadoop-restart-20260905-01/`、`m1-hadoop-restart-20260905-02/`；原始副本位于本地忽略目录

### 触发与现象

执行受控重启脚本，预期退出状态为 0，实际退出状态为 8，日志报告 `Expected process is missing on hadoop201: NameNode`。脚本已完成停止和启动动作，并生成重启前后的拓扑文件，但没有生成 `restart-sentinel.env`。

### 根因证据

`after-restart.txt` 实际包含 `org.apache.hadoop.hdfs.server.namenode.NameNode`、`SecondaryNameNode`、`ResourceManager` 和 `JobHistoryServer`，同时包含 2 个 Live DataNode 和 2 个 RUNNING NodeManager。原脚本使用的表达式要求进程短名称前必须为空白，而 `jps -lv` 输出中短名称前是 Java 包名分隔符 `.`，因此产生假失败。该失败发生在哨兵 SHA-256 核对之前，所以不能仅凭拓扑恢复把本轮提升为通过。

### 修复与复测

进程断言已调整为同时接受行首、Java 包名分隔符或空白作为进程短名称边界，并继续要求名称后为空白或行尾。修复提交拉取到 `hadoop201` 后，使用运行编号 `m1-hadoop-restart-20260905-02` 完整复测：脚本退出状态为 0，`summary.env` 为 `PASS`，`restart-sentinel.env` 中预期与实际 SHA-256 一致，重启前后均为 2 个 Live DataNode、2 个 RUNNING NodeManager 和 `hadoop201` 四个控制进程，临时 HDFS 路径已删除。

### 影响与限制

复测证明集群恢复既定进程和节点拓扑，并完成哨兵文件读取与比较。启动日志仍提示旧的 `HADOOP_NAMENODE_OPTS`、`HADOOP_DATANODE_OPTS` 和 `HADOOP_SECONDARYNAMENODE_OPTS` 已由对应 `HDFS_*` 名称替代；该警告未影响本次验证结果，但后续配置维护不得把它描述为已消除。Hadoop 状态提升为 `verified`，当前进入 MySQL 门禁。

### 回滚

若新表达式在目标 ECS 上仍误判，恢复本次单行匹配修改，保留两次运行证据并改用从 `jps` 第二列提取短类名的显式检查。回滚脚本不得停止服务、删除既有 HDFS 数据或格式化 NameNode。

## 记录模板

```markdown
## M1-ISSUE-001：简短标题

- 日期：yyyy-MM-dd
- 组件与版本：
- 节点：
- 状态：open / resolved / accepted-limit
- 日志位置：

### 触发与现象

### 根因证据

### 修复与复测

### 影响与限制

### 回滚
```
