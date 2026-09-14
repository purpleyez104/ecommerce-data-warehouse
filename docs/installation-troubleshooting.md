# Milestone 1 安装与排障记录

版本：`0.3`
状态：`in progress`
更新时间：2026-09-14

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

## M1-ISSUE-003：`sudo scp` 使用 root SSH 身份导致跨节点分发失败

- 日期：2026-09-09 至 2026-09-12
- 组件与版本：Hadoop、Flink、Doris 等跨节点配置分发
- 节点：`hadoop201` → `hadoop202`、`hadoop203`
- 状态：resolved
- 日志位置：本地忽略目录 `m1-vm-files-20260913` 的 Step 2、8、11 摘要；组件原始日志待归档

### 触发与现象

使用 `sudo scp` 后出现 `root@hadoop202: Permission denied (publickey)`；预期文件被复制到 worker，实际命令非零并且远端临时文件不存在。

### 根因证据

免密 SSH 配置的是 `yee → yee`。`sudo scp` 会以本机 root 身份发起连接，从而尝试使用 `root@worker`，与现有 SSH 身份不一致。

### 修复与复测

跨节点复制统一由 `yee` 执行普通 `scp` 到远端 `/tmp`；需要写系统目录时，再通过 `ssh yee@host 'sudo mv ...'` 完成最小权限移动。用户提供的后续分发摘要记录为成功。

### 影响与限制

该规则适用于当前集群文件分发，不授权 root 免密，也不允许把密码、私钥或渲染后的 Secret 复制进仓库。

### 回滚

若目标路径移动失败，保留 `/tmp` 临时文件和错误输出，修正目标属主或权限后重试；不得通过配置 root 免密绕过问题。

## M1-ISSUE-004：Hadoop XML 重复声明导致配置解析失败

- 日期：2026-09-05
- 组件与版本：Hadoop 3.4.1
- 节点：`hadoop201`
- 状态：resolved
- 日志位置：本地忽略目录 Step 2 摘要；原始 format 日志待补充定位

### 触发与现象

读取 `mapred-site.xml` 时出现 `Illegal processing instruction target ("xml")`。该文件曾以追加方式生成，包含第二个 XML declaration。

### 根因证据

检查配置发现 `<?xml version="1.0" encoding="UTF-8"?>` 不只出现在第一行；Hadoop 3.4.1 包中也没有安装步骤原先假设存在的 `mapred-site.xml.template`。

### 修复与复测

直接完整重写 `mapred-site.xml`，并检查四个 Hadoop XML 文件各自只有一个且位于第一行的 declaration。后续 Hadoop 功能与受控重启验收已通过。

### 影响与限制

不得再次 format 已存在的 NameNode。旧 `HADOOP_*_OPTS` 被 `HDFS_*_OPTS` 替代的 Warning 与本解析错误不同，仍按既有记录保留。

### 回滚

配置修改前保留去敏备份；若解析仍失败，仅恢复配置文件并重新执行语法检查，不删除 NameNode 元数据。

## M1-ISSUE-005：MySQL 数据目录迁移后被 AppArmor 拒绝

- 日期：2026-09-09
- 组件与版本：MySQL 8.0.46
- 节点：`hadoop201`
- 状态：resolved
- 日志位置：本地忽略目录 Step 3 摘要；mysqld 原始错误日志待组件验收归档

### 触发与现象

将 `/var/lib/mysql` 的实际存储迁移到 `/data/mysql` 后，mysqld 启动报 `Error: 13 (Permission denied)`。

### 根因证据

Linux owner/mode 已为 `mysql:mysql` 且父目录可遍历，错误由 Ubuntu AppArmor 的 mysqld profile 未允许新路径导致。

### 修复与复测

在 `/etc/apparmor.d/usr.sbin.mysqld` 为 `/data/mysql/` 增加读取、为 `/data/mysql/**` 增加 `rwk`，重新加载 profile。现场盘点确认 mysqld 正在运行、3306 监听，版本为 8.0.46。

### 影响与限制

端口与进程通过不等于 MySQL 完整验收；私网连接、固定 CRUD Binlog 和受控重启仍需独立证据。

### 回滚

回滚前必须先形成数据目录迁回计划并保留数据；不得直接删除 `/data/mysql` 或清空 AppArmor profile。

## M1-ISSUE-006：Hive 4.1.0 Metastore 与 Spark 3.5.9 client 不兼容

- 日期：2026-09-09
- 组件与版本：Hive 4.1.0、Spark 3.5.9
- 节点：`hadoop201`
- 状态：resolved
- 日志位置：本地忽略目录 Step 4、5 摘要；Spark application 原始日志待归档

### 触发与现象

Spark 访问 Hive 4.1.0 Metastore 时出现 `Invalid method name: get_table` 和 `Unsupported Hive Metastore version 4.1.0`。

### 根因证据

故障发生在 Spark Metastore client 调用边界，不是 HDFS 网络或 Hive 表不存在。降级后 Spark 能看到 `ecommerce` 数据库并读取 Hive ORC Smoke Test 表。

### 修复与复测

Hive 从 4.1.0 调整为 3.1.3，Spark 保持 3.5.9，并移除此前为 Hive 4.1.0 加入的 `spark.sql.hive.metastore.version`、`jars` 和 `jars.path` 覆盖项。

### 影响与限制

当前已验证组合为 Hadoop 3.4.1、Hive 3.1.3、Spark 3.5.9。此前 worker 软链接与 Java Runtime 待确认项已由最新 Runtime 验收记录取代：Hive 3.1.3 实际使用 JDK 17，MySQL Metastore schema 为 3.1.0。

### 回滚

不得把 Hive 4.1.0 软链接切回并宣称兼容；若必须重新评估，应使用独立 Metastore Schema 和临时配置完成，不覆盖当前 MySQL Metastore。

## M1-ISSUE-007：HiveServer2 启动未监听及 YARN Container Java 隔离

- 日期：2026-09-09
- 组件与版本：Hive 3.1.3（历史排障阶段也曾使用 4.1.0）
- 节点：`hadoop201`、YARN worker
- 状态：resolved
- 日志位置：本地忽略目录 Step 4、5 摘要；YARN Container 原始日志待归档

### 触发与现象

HiveServer2 曾存在 Java 进程但 10000 未监听，日志包含 Metastore notification API 未授权；Hive INSERT 的 MR Container 也曾因 Java class/version 或反射兼容错误失败。

### 根因证据

Metastore 服务端拒绝 notification API，且 Hive 服务进程与提交到 YARN 的 ApplicationMaster/Mapper/Reducer 使用的是不同 Runtime；只修改 HiveServer2 的 `JAVA_HOME` 不能改变 Container Java。

### 修复与复测

当前开发环境关闭 `hive.metastore.event.db.notification.api.auth` 和兼容键 `metastore.event.db.notification.api.auth`，并为 Hive 使用独立 Hadoop client 配置。摘要记录 ORC INSERT、YARN MapReduce 和 Hive 查询成功；2026-09-13 盘点确认 9083、10000、10002 正在监听。

### 影响与限制

关闭该鉴权仅适用于当前受控开发集群。最新验收记录确认 Hive 3.1.3 服务使用 JDK 17；Hadoop/YARN 守护进程保持 Java 11。后续版本漂移仍须按实际进程与 YARN application 记录。

### 回滚

若重新启用 notification API 鉴权，必须先配置并验证服务身份；不得只重启 HiveServer2 而遗漏 Metastore 服务端配置。

## M1-ISSUE-008：Kafka KRaft 三节点顺序启动无法形成 Controller Quorum

- 日期：2026-09-10
- 组件与版本：Kafka 3.9.1、Scala 2.12、KRaft
- 节点：三节点
- 状态：resolved
- 日志位置：本地忽略目录 Step 7 摘要；Kafka 原始 server log 待归档

### 触发与现象

逐台等待启动时出现 election timeout、Broker 注册 RPC timeout 和启动退出；三台始终没有同时进入 Controller 选举窗口。

### 根因证据

Controller quorum 配置要求 1、2、3 三个 voter；顺序启动流程在前一节点超时退出后才启动下一节点，无法形成多数派。

### 修复与复测

三节点 Kafka 改为并行发起启动并统一等待。摘要记录三节点完成 Leader/Follower 转换、Topic 三副本三 ISR、生产消费成功，以及单 Broker 停止后 ISR 降为 2、恢复后回到 3。

### 影响与限制

三节点已使用同一 KRaft Cluster ID format。后续脚本不得重新 format 或删除 `/data/kafka/kraft-combined-logs`。业务 Topic、Partition 和保留策略仍等待 Milestone 8。

### 回滚

启动失败时保留各节点日志并停止后续验收，不重新生成 Cluster ID；仅回滚启动编排脚本。

## M1-ISSUE-009：DataX 源码包误作运行包及 HDFS Writer ORC 类型限制

- 日期：2026-09-09
- 组件与版本：DataX datax_v202309
- 节点：`hadoop202`、`hadoop203`
- 状态：resolved
- 日志位置：本地忽略目录 Step 6 摘要；DataX Job 原始日志待归档

### 触发与现象

最初压缩包解压后只有 Maven 源码结构，缺少标准 `bin/datax.py` 和运行 Plugin 布局；换用运行包后，HDFS Writer 写 ORC 又因 Job 字段类型 `DECIMAL` 报 `No enum constant ... SupportHiveDataType.DECIMAL`。

### 根因证据

第一个问题是包类型错误；第二个问题发生在 MySQL Reader 已读取数据之后，属于当前 HDFS Writer ORC 类型枚举限制，不是 MySQL 或 HDFS 连通失败。

### 修复与复测

改用编译后的 `datax.tar.gz` 运行包。Smoke Test 将金额和时间暂按 `STRING` 写入 ORC，再由 Spark CAST 为 `DECIMAL(16,2)` 与 `TIMESTAMP`；摘要记录 3 行写入、Hive/Spark 读取及故意失败任务退出 1。

### 影响与限制

该 workaround 只证明当前测试字段组合可行，不自动决定全部正式 ODS Schema。正式 ODS 字段类型、审计字段、幂等发布和失败隔离仍由 Milestone 3 确认。当前实际 Runtime 入口为 `/data/module/datax-current`，MySQL→DataX→HDFS ORC + Snappy→Hive→Spark 的固定 3 行链路及失败非零已通过。

### 回滚

保留失败 Job 与日志；回滚只撤销测试表和脚本创建的临时 HDFS 路径，不删除 DataX 安装或正式 ODS 数据。

## M1 Step 8～12 已确认兼容性结论

用户确认的 Step 8～12 Runtime 记录已作为 M1 兼容性基线，但不作为 Milestone 8～9 的正式实时实现：

- Flink 1.20.5 on YARN：补齐 `HADOOP_CONF_DIR` 和 `HADOOP_CLASSPATH`；Application Mode 的本地退出 0 只代表提交成功，最终结果必须检查 YARN `Final-State`。
- Flink CDC 3.6.0：补齐 MySQL/Kafka Pipeline Connector 与 Connector/J 8.0.33；`Public Key Retrieval` 通过 JDBC 参数解决，不开放 root TCP 登录；`value.format` 使用 `debezium-json`。
- Flink SQL Kafka：普通 Kafka SQL Connector 与 CDC Pipeline Connector 分离；SQL Client + YARN Session source/sink 已通过，`yarn-application` 的 SQL `INSERT` 存在 `No ExecutorFactory` 限制，因此不得混用执行模式或声明 Exactly-Once。
- Doris 4.0.8：FE/BE HTTP 分别改为 18030/18040 以避开 YARN 8030/8040；BE 需要 `vm.max_map_count=2000000`；不得用简化值覆盖完整 `JAVA_OPTS_FOR_JDK_17`。FE/BE SQL 与受控重启恢复已通过。
- Flink Doris Connector 26.1.1：SQL Client Session DML 失败后改用 DataStream Jar + YARN Application；Flink 客户端使用 Java 17，YARN Container 与 User Jar target 使用 Java 11。insert/upsert、类型、schema、Checkpoint、TaskManager 故障与恢复已通过，但不确认正式 Doris 实时 Key 模型、Topic 设计或端到端 Exactly-Once。

上述结论足以确认 M1 组件组合支持后续工作；后续保留 application ID、日志和清理结果用于复现与故障诊断。正式业务 Topic、Schema、状态语义及端到端一致性仍由 Milestone 8～9 单独设计和验收。

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
