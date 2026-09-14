# Implementation Plan

## Evidence Inbox Initialization — First Step

Work 会话开始后首先执行：

```powershell
New-Item -ItemType Directory -Force -Path ".local-notes\m1-evidence\inbox\m1-cas-02-mysql" | Out-Null
```

不得清空已有内容。Work 会话不填充 VM Runtime 证据；用户后续放入完整 run 目录。

1. 消费 `M1-CAS-01` 公共库，不修改其接口。
2. 实现 CLI、Secret 与三节点 Preflight。
3. 实现配置白名单和 Binlog 变量断言。
4. 实现临时对象、固定 I/U/D 与 Row Event 核对。
5. 实现精确确认 Token、重启、轮询和哨兵检查。
6. 实现安全 Cleanup、摘要和非零失败。
7. 完成语法与 Contract 检查，不在本地声称 Runtime 通过。

## Completion Gate

- 脚本与 `--help` 完整。
- 静态检查通过；VM Runtime 等待用户执行。
- Handoff 报告 Evidence Inbox 的绝对路径及本地静态证据范围。

## Recommended Next Task

`M1-CAS-03`。
