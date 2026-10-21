# Kafka

本目录保存 Formal Realtime Foundation 的 Kafka 静态 Contract。Kafka 3.9.1 KRaft 的组件级验收不等于业务 Topic 已创建或运行通过。

`realtime_foundation_contract.json` 冻结 21 个 Raw CDC Topic、Behavior Topic、Standard Topic Pattern、Partition/Key、Envelope 和 `event_version`。当前状态仅为 `implemented / static_verified`，Runtime 为 `not_run`；本目录不创建 Topic，也不把 Pilot Topic 或 Offset 当作正式状态。

静态验证：

```powershell
python flink/cdc/validate_realtime_foundation_contract.py --contract kafka/realtime_foundation_contract.json
```
