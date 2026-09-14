# Implementation Plan

## Evidence Inbox Initialization — First Step

Work 会话开始后首先执行：

```powershell
New-Item -ItemType Directory -Force -Path ".local-notes\m1-evidence\inbox\m1-cas-04-kafka-kraft" | Out-Null
```

不得清空已有内容。Work 会话不填充 VM Runtime 证据；用户后续放入完整 run 目录。

1. 消费冻结的公共库。
2. 实现三节点 Preflight、Cluster ID、Quorum、Broker 和配置采集。
3. 实现临时 Topic、固定 Producer/Consumer 和 Offset Replay。
4. 实现 Failure Node 白名单、精确确认、停止/恢复和 ISR 轮询。
5. 实现安全 Topic Cleanup、摘要和非零失败。
6. 添加 Storage Format/Data Directory 静态禁令并运行语法检查。

## Completion Gate

- 脚本不包含任何格式化或 Data Directory 删除能力。
- VM Runtime 等待用户执行。
- Handoff 报告 Evidence Inbox 的绝对路径及本地静态证据范围。

## Recommended Next Task

`M1-CAS-05`。
