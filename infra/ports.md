# Milestone 1 端口基线

状态含义：`confirmed` 表示当前集群记录或现场快照已有确认事实；`configured` 表示配置已采集但本次快照未确认监听；`accepted` 表示已经决定但尚待组件安装验证；`planned` 表示必须随精确版本配置现场确认。端口状态不等于组件整体 `verified`。

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
| MySQL | `hadoop201` | 3306 | `confirmed` | 2026-09-13 监听 `0.0.0.0`；安全组仍只允许 `10.20.1.0/24` 和本机 |
| Hive Metastore | `hadoop201` | 9083 | `confirmed` | Hive 3.1.3、MySQL Metastore schema 3.1.0 已通过 Runtime 验收 |
| HiveServer2 | `hadoop201` | 10000 | `confirmed` | HiveServer2/Beeline 功能已通过 Runtime 验收 |
| HiveServer2 Web UI | `hadoop201` | 10002 | `confirmed` | 私网，使用 SSH 隧道 |
| Kafka Broker | 三节点 | 9092 | `confirmed` | KRaft 私网 listener；生产消费和单 Broker 故障恢复已通过 |
| Kafka Controller | 三节点 | 9093 | `confirmed` | 三节点 Controller quorum 已通过 Runtime 验收 |
| Doris FE HTTP | `hadoop201` | 18030 | `confirmed` | 避开 YARN 8030；FE/BE SQL 与受控重启恢复已通过 |
| Doris FE edit log / RPC / query | `hadoop201` | 9010 / 9020 / 9030 | `confirmed` | 2026-09-13 监听，仅限私网 |
| Doris BE HTTP | `hadoop202`、`hadoop203` | 18040 | `confirmed` | 2026-09-13 监听，避开 NodeManager 8040 |
| Doris BE heartbeat / service / BRPC | `hadoop202`、`hadoop203` | 9050 / 9060 / 8060 | `confirmed` | 2026-09-13 监听，仅限私网 |
| DolphinScheduler API | `hadoop201` | 12345 | `confirmed` | 私网，API Health 与 UI 已验证；公网访问使用 SSH 隧道 |
| DolphinScheduler Master RPC | `hadoop201` | 5678 / 5679 | `confirmed` | 私网；MySQL JDBC Registry 模式 |
| DolphinScheduler Alert RPC | `hadoop201` | 50052 / 50053 | `confirmed` | 私网 |

未列出的 DolphinScheduler 端口不得直接采用经验默认值；Worker 监听与安全组仍以现场配置为准。Flink 已完成 Runtime 兼容性验收，但本基线不虚构验收记录未提供的固定服务端口。
