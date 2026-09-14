# Technical Design

## Flow

1. Preflight：三节点版本、进程、端口、Cluster ID、Broker 和 Quorum。
2. Configuration：只采集 KRaft、Listener、Replication、minISR 等白名单项。
3. Functional：创建临时 Topic，发送固定消息，完整消费并从指定 Offset 重放。
4. Recovery：确认另两节点健康后，授权停止指定 Broker；验证降级读写，恢复后等待 ISR=3。
5. Cleanup：仅删除本次临时 Topic。

## Hard Safety Guards

- 源码和测试均禁止出现可执行的 Storage Format 路径。
- Kafka Data Directory 永远只读采集路径/权限/摘要，不执行删除。
- Failure Node 只允许 `hadoop201/202/203`，且不得是当前 Quorum 唯一健康节点。

## Status

未运行单 Broker 恢复为 `PARTIAL`；恢复闭环全部通过才为 `PASS`。

## Rollback

优先恢复指定 Broker 并等待 Quorum/ISR；删除严格前缀临时 Topic；保留证据。

## Evidence Inbox Contract

- 路径：`.local-notes/m1-evidence/inbox/m1-cas-04-kafka-kraft/`。
- Work 会话只创建目录并可写入标记为 `local_static` 的脚本测试输出。
- 用户将 Kafka VM 完整 run 目录原样放入。
- 协调会话只读核对三节点、Cluster ID、Quorum、RF/ISR、Replay、Broker Recovery、Hash 和退出码。
