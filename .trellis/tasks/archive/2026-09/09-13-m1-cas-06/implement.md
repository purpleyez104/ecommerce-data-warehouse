# Implementation Plan

## Evidence Inbox Initialization — First Step

Work 会话开始后首先执行：

```powershell
New-Item -ItemType Directory -Force -Path ".local-notes\m1-evidence\inbox\m1-cas-06-datax" | Out-Null
```

不得清空已有内容。Work 会话不填充 VM Runtime 证据；用户后续放入完整 run 目录。

1. 消费冻结的公共库。
2. 实现双 Worker Runtime/Plugin/Java/Python Preflight。
3. 实现 Secret 文件检查和临时 MySQL 输入。
4. 实现两份私有 Job JSON 和隔离 HDFS Writer Path。
5. 实现 Hive/Spark ORC+Snappy 与结果断言。
6. 实现固定失败 Job、去敏日志和非零断言。
7. 实现严格 Cleanup、摘要和语法检查。

## Completion Gate

- Secret、双 Worker、成功/失败和 Cleanup Contract 完整。
- VM Runtime 等待用户执行。
- Handoff 报告 Evidence Inbox 的绝对路径及本地静态证据范围。

## Recommended Next Task

`M1-CAS-07`。
