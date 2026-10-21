# Flink CDC

本目录保存 Formal Realtime Foundation Contract 的严格 Validator。正式 CDC 作业、Source 配置和业务表接续仍受 Milestone 8-9 门禁约束；静态验证和既有环境验收都不能外推为正式业务链路。

执行：

```powershell
python flink/cdc/validate_realtime_foundation_contract.py --contract kafka/realtime_foundation_contract.json
```

成功输出包含 `static_verified`、`runtime=not_run`、21 个 Raw CDC Topic 和 7 个 Standard Domain。Validator 对 Namespace、Topic/主键、Kafka durability、Envelope、结构化 `event_version`、Checkpoint/Savepoint Root 及 Pilot State 禁用规则执行严格匹配；任何 Contract 漂移都返回非零状态。
