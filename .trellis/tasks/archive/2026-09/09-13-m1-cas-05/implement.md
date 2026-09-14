# Implementation Plan

## Evidence Inbox Initialization — First Step

Work 会话开始后首先执行：

```powershell
New-Item -ItemType Directory -Force -Path ".local-notes\m1-evidence\inbox\m1-cas-05-spark-yarn" | Out-Null
```

不得清空已有内容。Work 会话不填充 VM Runtime 证据；用户后续放入完整 run 目录。

1. 消费冻结的公共库。
2. 实现 Spark/YARN/Hive Preflight。
3. 实现固定成功 SQL、临时输入输出和结果断言。
4. 实现 Application ID、终态、Diagnostics 和日志采集。
5. 实现固定失败 Application 与非零断言。
6. 实现安全 Cleanup、摘要和超时。
7. 完成语法与 Contract 检查。

## Completion Gate

- 成功与失败路径均可由脚本独立触发和识别。
- VM Runtime 等待用户执行。
- Handoff 报告 Evidence Inbox 的绝对路径及本地静态证据范围。

## Recommended Next Task

`M1-CAS-06`。
