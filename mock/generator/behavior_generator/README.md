# Behavior Generator

生成正式用户行为 JSONL，可运行 Bootstrap 历史模式或 Continuous 批次模式。运行时必须读取 Business Generator 输出的版本化 `entity_manifest.json`，不得根据相同数量重新构造第二套实体 ID 空间。

```powershell
cd mock\generator\behavior_generator
python -m pip install -e .
ecommerce-behavior-generator bootstrap --config config\smoke.json --entity-manifest ..\business_generator\output\smoke\entity_manifest.json --seed 20260928 --generated-at 2026-09-28T10:00:00+08:00 --output output\smoke.jsonl
```

Continuous 示例：

```powershell
ecommerce-behavior-generator continuous --config config\formal.json --entity-manifest ..\business_generator\output\formal\entity_manifest.json --seed 20260929 --generated-at 2026-09-29T10:00:00+08:00 --start 2026-03-01T00:00:00 --end 2026-03-01T00:59:59.999 --events 10000 --output output\behavior-20260301-00.jsonl
```

正式设计规模使用 `formal.json`。`smoke.json` 只作为快速单元测试 Fixture，不是独立数据规模档位。

验证：

```powershell
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests -v
```

2026-10-12 使用同轮 Business Entity Manifest 完成本地正式下限验证：生成 3,000,000 条事件、938,435,690 bytes、256,992 条映射事件和 2,785,149 个 Session；全量检查实体引用、30 分钟 Session 边界和 `event_id` 唯一性均为 0 违规，Manifest SHA-256 绑定通过。

边界：Entity Manifest 版本、时间范围、时区、实体数量、唯一性和身份映射时序不兼容时会 fail-fast。配置中的实体数量只用于核对，不再用于构造 ID。正式 Kafka Topic、Partition、Key、Schema 尚受 Milestone 8 门禁约束，因此当前只生成可检查和回放的 JSONL，不内置 Kafka Producer，也不伪装 MySQL CDC。
