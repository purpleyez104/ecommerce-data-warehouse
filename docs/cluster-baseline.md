# Milestone 1 集群事实基线

版本：`0.1`
状态：`in progress`
更新时间：2026-09-04

## 1. 来源与适用范围

本文件是 Project 1 在 Milestone 1 使用的集群事实入口。事实来源为：

- 来源文件：`C:\Users\user\.codex\.chatgpt-projects\g-p-6a94df9d0890819184d69f8cc329aabf\alibaba-ecs-hadoop-cluster-rebuild-spec.md`
- 来源快照日期：2026-09-04
- SHA-256：`0556E06CBF754D01E4CCD451356E0EB15F6BE6A3E7B49E91632FA85313F25264`
- 采用依据：用户确认该文件是本项目当前集群的实际搭建记录，其中 `CONFIRMED` 可以作为确认事实。

本仓库只提取 Milestone 1 所需的拓扑、配置、状态和验证边界，不整份复制外部文件。未迁入阿里云账号级资源 ID、磁盘 UUID、公网 IP、密钥、真实密码、Project 2 实现规划和通用复建教程。

## 2. 状态映射

| 来源状态 | 本仓库处理 |
| --- | --- |
| `CONFIRMED` | 作为当前集群的确认事实，不降级为候选，也不要求重新证明事实是否存在 |
| `CONFIGURED` | 作为当前已采用配置；不自动补足来源文件明确缺失的功能测试证据 |
| `PLANNED` | 保持计划或候选状态，不描述为已经安装、启动或验证 |
| `UNKNOWN` | 必须从控制台或节点现场获取，不写入猜测值 |

Hadoop 的版本、进程和节点拓扑已经确认，但仓库要求的 HDFS 固定文件校验、完整 MapReduce 结果和重启恢复证据尚未保存，因此 Hadoop 整体暂记为 `implemented`。补齐上述证据后才能标记为 `verified`。

## 3. 云、网络与访问

| 项目 | 当前事实 | 状态 |
| --- | --- | --- |
| 云平台与地域 | Alibaba Cloud ECS，杭州地域 | `CONFIRMED` |
| 操作系统 | Ubuntu 24.04 LTS，x86_64 | `CONFIRMED` |
| VPC | `10.20.0.0/16` | `CONFIRMED` |
| vSwitch | `10.20.1.0/24` | `CONFIRMED` |
| 时区 | `Asia/Shanghai` | `CONFIRMED` |
| Swap | 关闭，预检为 `0 B` | `CONFIRMED` |
| 公网管理入口 | 仅 `hadoop201` 的 SSH 22 | `CONFIRMED` |
| worker 管理 | 通过 `hadoop201` 跳板访问私网地址 | `CONFIRMED` |
| 集群端口授权源 | `10.20.1.0/24` | `CONFIGURED` |
| 公网 SSH 授权源 | 管理员当前公网出口 IP `/32` | `CONFIGURED`，实际地址不入库 |

集群内部连接只使用私网主机名。`/etc/hosts` 的统一映射见 `infra/hosts.example`。不得把公网 IP 写入组件配置。

## 4. 节点与角色

| 节点 | 私网 IPv4 | 资源 | 当前 Hadoop 角色 | 后续计划角色 |
| --- | --- | --- | --- | --- |
| `hadoop201` | `10.20.1.201` | 4 vCPU / 16 GiB；系统盘 50 GiB；数据盘 80 GiB | NameNode、SecondaryNameNode、ResourceManager、JobHistoryServer | MySQL、Hive Metastore、HiveServer2、Kafka Broker/Controller 1、Doris FE、DolphinScheduler Master/API/Alert、Spark/Flink 客户端 |
| `hadoop202` | `10.20.1.202` | 8 vCPU / 16 GiB；系统盘 50 GiB；数据盘 120 GiB | DataNode、NodeManager | Kafka Broker/Controller 2、Doris BE 1、DolphinScheduler Worker、DataX、Spark/Flink YARN 容器 |
| `hadoop203` | `10.20.1.203` | 8 vCPU / 16 GiB；系统盘 50 GiB；数据盘 120 GiB | DataNode、NodeManager | Kafka Broker/Controller 3、Doris BE 2、DolphinScheduler Worker、DataX、Spark/Flink YARN 容器 |

`hadoop201` 不加入 Hadoop `workers`，不运行 DataNode 或 NodeManager。SecondaryNameNode 不构成 Hadoop HA，本项目也不宣称生产级高可用。

## 5. 用户、磁盘、目录与 Java

- 大数据组件统一由 `yee` 运行；`yee` 具备无密码 `sudo`，但 Hadoop 不以 `root` 运行。
- `yee@hadoop201` 已通过 `~/.ssh/id_ed25519` 对三节点免密 SSH；私钥不得进入仓库。
- 系统盘为 `/dev/vda`，根分区为 ext4 并挂载到 `/`。
- 数据盘为 `/dev/vdb`，格式化为 ext4 并挂载到 `/data`。
- `/etc/fstab` 使用各节点现场 UUID；UUID 不得从其他节点复制或写入仓库。
- `/data` 属主为 `yee:yee`，权限基线为 `755`。
- 安装包保存到 `/data/software`，组件安装到 `/data/module/<component>-<version>`，通过 `/data/module/<component>` 稳定软链接访问。
- 默认 Java 为 OpenJDK 17；Hadoop 在 `hadoop-env.sh` 中固定使用 `/usr/lib/jvm/java-11-openjdk-amd64`。
- `nofile` 和 `nproc` 的 soft/hard 基线均为 `65536`。

主要数据目录：

```text
/data/hadoop
/data/kafka
/data/flink
/data/doris
/data/dolphinscheduler
/data/datax
/data/logs
/data/tmp
```

## 6. Hadoop 当前事实

| 项目 | 当前值 | 状态 |
| --- | --- | --- |
| Hadoop | `3.4.1`，revision `4d7825309348956336b8f06a08322b78422849b1` | `CONFIRMED` |
| HDFS | 1 NameNode、1 SecondaryNameNode、2 DataNode | `CONFIRMED` |
| Live DataNode | `hadoop202`、`hadoop203` | `CONFIRMED` |
| HDFS 副本数 | `2` | `CONFIGURED` |
| HDFS 可配置容量 | 合计约 `235.12 GiB` | `CONFIRMED` |
| YARN | `hadoop201` ResourceManager，两个 worker 各 1 个 NodeManager | `CONFIRMED` |
| YARN 节点 | 2 个，均为 `RUNNING` | `CONFIRMED` |
| MapReduce | YARN 模式；JobHistoryServer 位于 `hadoop201` | `CONFIRMED`，完整最小作业输出待补 |
| Hadoop Java | OpenJDK 11 | `CONFIRMED` |

关键配置：

- `fs.defaultFS=hdfs://hadoop201:8020`
- NameNode 数据目录：`/data/hadoop/dfs/name`
- DataNode 数据目录：`/data/hadoop/dfs/data`
- NodeManager 本地目录：`/data/hadoop/yarn/local`
- NodeManager 日志目录：`/data/hadoop/yarn/logs`
- 每个 worker 的 YARN 资源：`10240 MiB`、`6 vCore`
- 单容器最大资源：`4096 MiB`、`4 vCore`
- YARN 聚合日志 HDFS 目录：`/tmp/logs`，保留 7 天

NameNode 已存在。任何 M1 脚本都不得执行 `hdfs namenode -format` 或删除 `/data/hadoop/dfs/name`。

## 7. 当前门禁与验证边界

当前 M1 门禁是补齐 Hadoop 的项目级验收证据：

1. 固定 UTF-8 文件的本地与 HDFS SHA-256 一致。
2. 固定输入的 MapReduce `wordcount` 完成，结果、application ID、退出状态和聚合日志已保存。
3. 受控重启后，原有拓扑恢复，HDFS 文件仍可读取。

执行入口：

```bash
bash scripts/m1/collect-hadoop-evidence.sh \
  --run-id m1-hadoop-20260904-01 \
  --output-dir /data/logs/ecommerce-data-warehouse/m1/m1-hadoop-20260904-01
```

首次非中断验证通过并完成评审后，再单独执行重启验证。Hadoop 达到 `verified` 后才进入 MySQL 安装门禁。

## 8. 已知未知项

- `hadoop201` 公网 IP/EIP、三台实例 ID、可用区和实例规格族。
- VPC、vSwitch 和安全组资源 ID。
- 三块数据盘 ID 与各自 ext4 UUID。
- 阿里云密钥对名称、绑定关系、初始镜像管理用户名。
- 管理员当前公网出口 IP `/32`。
- JDK 11、17 的具体补丁版本。

这些值只在需要验证对应行为时现场采集，并按秘密或环境专属信息边界处理。

## 9. 回滚

若本次事实提取存在错误，回滚只撤销本文件及关联仓库配置，并通过新的决策记录修正。不得因此停止现有 Hadoop、格式化 NameNode、删除 HDFS 数据、修改云盘或覆盖 ECS 配置。
