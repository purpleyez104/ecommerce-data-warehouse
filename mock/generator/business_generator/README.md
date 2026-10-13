# Business Generator

独立生成正式 Bootstrap 的 21 张业务表 CSV、`dataset_manifest.json` 与版本化 `entity_manifest.json`。本目录可单独复制、安装和运行，不依赖 `Behavior Generator`。

```powershell
cd mock\generator\business_generator
python -m pip install -e .
ecommerce-business-generator --config config\smoke.json --seed 20260928 --generated-at 2026-09-28T10:00:00+08:00 --output output\smoke
```

正式设计规模使用 `formal.json`。`smoke.json` 只作为快速单元测试 Fixture，不是独立数据规模档位。固定 `config + seed + generated-at` 会生成相同内容；输出目录必须不存在，Generator 不覆盖旧批次。

验证：

```powershell
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests -v
```

2026-10-12 目标服务器正式规模验证生成 21 张 CSV、1,328,502 行和版本化 Entity Manifest；90 天时间边界违规为 0。Dataset Manifest 保存 Entity Manifest 的版本和 SHA-256；同一 bundle 已完成目标 MySQL `LOAD DATA` 与事务内、提交后独立 45-rule Shared Source Gate，证据见 [`source-load-gate-acceptance.md`](../../../docs/acceptance/source-load-gate-acceptance.md)。

边界：21 CSV 字段已与 `mysql/ddl/001_ecommerce_oltp.sql` 候选稿逐表对齐，但候选 DDL 未部署。本生成器不执行 `LOAD DATA` 或 MySQL 写入。`biz_product_change_event` 优先满足 20%～30% SKU、每 SKU 1～3 个有效变化版本，实测行数写入 Manifest。
