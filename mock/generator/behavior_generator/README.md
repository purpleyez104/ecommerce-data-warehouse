# Behavior Generator

独立生成 V2 用户行为 JSONL，可运行 Bootstrap 历史模式或 Continuous 批次模式。本目录可单独复制、安装和运行，不依赖 `Business Generator`。

```powershell
cd mock\generator\behavior_generator
python -m pip install -e .
ecommerce-behavior-generator bootstrap --config config\smoke.json --seed 20260928 --generated-at 2026-09-28T10:00:00+08:00 --output output\smoke.jsonl
```

Continuous 示例：

```powershell
ecommerce-behavior-generator continuous --config config\v2_spec.json --seed 20260929 --generated-at 2026-09-29T10:00:00+08:00 --start 2026-03-01T00:00:00 --end 2026-03-01T00:59:59.999 --events 10000 --output output\behavior-20260301-00.jsonl
```

验证：

```powershell
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests -v
```

边界：正式 Kafka Topic、Partition、Key、Schema 尚受 Milestone 8 门禁约束，因此当前只生成可检查和回放的 JSONL，不内置 Kafka Producer，也不伪装 MySQL CDC。
