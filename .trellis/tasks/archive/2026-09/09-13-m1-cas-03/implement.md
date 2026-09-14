# Implementation Plan

## Evidence Inbox Initialization — First Step

Work 会话开始后首先执行：

```powershell
New-Item -ItemType Directory -Force -Path ".local-notes\m1-evidence\inbox\m1-cas-03-hive" | Out-Null
```

不得清空已有内容。Work 会话不填充 VM Runtime 证据；用户后续放入完整 run 目录。

1. 消费冻结的公共库。
2. 实现服务、端口、Beeline、版本、配置和 Java Preflight。
3. 实现临时 Hive SQL、固定数据和 YARN MapReduce。
4. 实现 ORC/Snappy、Application ID、日志和 Container Java 断言。
5. 实现受限生命周期命令、精确确认和恢复轮询。
6. 实现安全 Cleanup、摘要和非零失败。
7. 完成语法与 Contract 检查。

## Completion Gate

- 脚本实现完整且不改变 Java/配置。
- VM Runtime 等待用户执行。
- Handoff 报告 Evidence Inbox 的绝对路径及本地静态证据范围。

## Recommended Next Task

`M1-CAS-04`。
