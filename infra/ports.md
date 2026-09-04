# Milestone 1 端口基线

状态含义：`confirmed` 表示当前集群记录已有确认事实；`accepted` 表示已经决定但尚待组件安装验证；`planned` 表示必须随精确版本配置现场确认。

| 组件 | 节点 | 端口 | 状态 | 边界 |
| --- | --- | ---: | --- | --- |
| SSH | `hadoop201` | 22 | `confirmed` | 唯一公网入口，仅管理员出口 IP `/32` |
| HDFS NameNode RPC | `hadoop201` | 8020 | `confirmed` | 私网 |
| HDFS NameNode UI | `hadoop201` | 9870 | `confirmed` | 私网，使用 SSH 隧道 |
| SecondaryNameNode UI | `hadoop201` | 9868 | `confirmed` | 私网，使用 SSH 隧道 |
| YARN RM Scheduler | `hadoop201` | 8030 | `confirmed` | 私网，不得为 Doris 改动 |
| YARN RM ResourceTracker | `hadoop201` | 8031 | `confirmed` | 私网 |
| YARN RM Client | `hadoop201` | 8032 | `confirmed` | 私网 |
| YARN RM Admin | `hadoop201` | 8033 | `confirmed` | 私网 |
| YARN RM UI | `hadoop201` | 8088 | `confirmed` | 私网，使用 SSH 隧道 |
| JobHistory RPC | `hadoop201` | 10020 | `confirmed` | 私网 |
| JobHistory UI | `hadoop201` | 19888 | `confirmed` | 私网，使用 SSH 隧道 |
| MySQL | `hadoop201` | 3306 | `accepted` | 只允许 `10.20.1.0/24` 和本机 |
| Hive Metastore | `hadoop201` | 9083 | `planned` | 安装时核对 Hive 4.1.0 配置 |
| HiveServer2 | `hadoop201` | 10000 | `planned` | 安装时核对认证和监听地址 |
| Kafka Broker | 三节点 | 9092 | `planned` | KRaft 私网 listener，安装时确认 |
| Kafka Controller | 三节点 | 9093 | `planned` | KRaft controller listener，安装时确认 |
| Doris FE HTTP | `hadoop201` | 18030 | `accepted` | 避开 YARN 8030，安装前检查占用 |
| ZooKeeper | `hadoop201` | 2181 | `accepted` | 仅 DolphinScheduler，私网 |

未列出的 Doris、DolphinScheduler 和 Flink 端口不得直接采用经验默认值；必须在对应候选版本进入验证门禁时补充官方依据、监听地址、安全组和健康检查。
