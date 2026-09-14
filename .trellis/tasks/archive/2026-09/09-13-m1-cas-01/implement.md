# Implementation Plan

## Evidence Inbox Initialization — First Step

Work 会话开始后首先执行：

```powershell
New-Item -ItemType Directory -Force -Path ".local-notes\m1-evidence\inbox\m1-cas-01-common-contract" | Out-Null
```

不得删除或覆盖已有证据；Handoff 必须报告该目录绝对路径。

1. 重新核对 Parent Evidence Schema 和现有 M1 Script Pattern。
2. 实现严格模式、常量、参数和输出目录校验。
3. 实现日志、断言、状态累计、摘要和去敏 Helper。
4. 实现临时对象注册与双重 Guard Cleanup。
5. 运行 `bash -n`，交由 `M1-CAS-07` 增加 Contract 测试。
6. 冻结公共函数名称、参数和 `summary.env` 字段后再启动组件 Task。

## Completion Gate

- Acceptance Criteria 全部满足。
- 公共 API 已冻结并在 Parent Design 中同步。
- 不启动任何 VM 服务或功能检查。
- 专属 Evidence Inbox 已创建；其中只有明确标记的本地静态证据。

## Recommended Next Task

`M1-CAS-02`。
