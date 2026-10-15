# Business Generator

独立生成正式终态的 21 张业务表 CSV、`dataset_manifest.json` 与版本化 `entity_manifest.json`。`replay.py` 在不改变终态 Bundle 的前提下，生成前 60 天 Bootstrap、30 个左闭右开 Daily Package、Expected Result、ODS `ods_batch_contract.json` 与 SHA-256 Replay Manifest；`source_contract/` 保留可复核的 Dataset/Entity Manifest。本目录可单独复制、安装和运行，不依赖 `Behavior Generator`。

```powershell
cd mock\generator\business_generator
python -m pip install -e .
ecommerce-business-generator --config config\smoke.json --seed 20260928 --generated-at 2026-09-28T10:00:00+08:00 --output output\smoke
ecommerce-business-replay --config config\replay_smoke.json --seed 20260928 --generated-at 2026-10-14T09:00:00+08:00 --output output\replay-smoke
ecommerce-business-replay --config config\replay_formal_20260105.json --seed 20260105 --generated-at 2026-10-15T10:00:00+08:00 --output ..\..\..\runtime\formal-replay-seed-20260105-r2
```

历史 Source Gate 的正式终态规模继续使用 `formal.json + Seed 20260928`，不得改写该既存验收输入。新的正式 60/30 Replay 使用 `replay_formal_20260105.json + Seed 20260105`；Seed 派生的 `biz_coupon_event` 为 129,691 行，终态 Source Contract 合计 1,328,491 行，与历史已装载的 1,328,502 行不是同一 Dataset。`smoke.json` 与 `replay_smoke.json` 只作为快速单元测试 Fixture，不是独立数据规模档位。Replay 配置必须精确覆盖 90 个业务日；切换点固定为第 61 日零点。固定 `config + seed + generated-at` 会生成相同业务 Hash；输出目录必须不存在，Generator 不覆盖旧批次，失败会清理未完成目录。

验证：

```powershell
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests -v
```

2026-10-12 目标服务器正式规模验证生成 21 张 CSV、1,328,502 行和版本化 Entity Manifest；90 天时间边界违规为 0。Dataset Manifest 保存 Entity Manifest 的版本和 SHA-256；同一 bundle 已完成目标 MySQL `LOAD DATA` 与事务内、提交后独立 45-rule Shared Source Gate，证据见 [`source-load-gate-acceptance.md`](../../../docs/acceptance/source-load-gate-acceptance.md)。

边界：Replay Builder 与 MySQL Replay Dry-run 已本地执行并验证；不会执行 `LOAD DATA`、MySQL 写入或外部 Runtime。Bootstrap 只保留切换点前的当前状态与历史，Daily Package 记录操作、水位、受影响业务日期、逐日期行数和预期结果；`biz_identity_mapping` 每日输出全量快照。2026-10-15 使用 Dataset `v2.3-replay-formal-20260105-r2` 生成 438,869 行 Bootstrap 和 30 个 Daily Package，Business Hash 为 `c690b3257268e342d12772984d0dc93af806072acf4ead91c5c281b5a92293e0`，30 日共 1,189,936 个操作；Bootstrap 与 30 日 Package 均通过本地 Dry-run。Daily ODS Contract 只能在对应操作包已应用到另行授权的隔离 Source 后使用；数据库 Runtime 仍为 `not_run`。
