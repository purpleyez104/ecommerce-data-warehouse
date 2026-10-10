# Business Generator

独立生成 V2 Bootstrap 的 21 张业务表 CSV 与 `dataset_manifest.json`。本目录可单独复制、安装和运行，不依赖 `Behavior Generator`。

```powershell
cd mock\generator\business_generator
python -m pip install -e .
ecommerce-business-generator --config config\smoke.json --seed 20260928 --generated-at 2026-09-28T10:00:00+08:00 --output output\smoke
```

正式设计规模将 `smoke.json` 替换为 `v2_spec.json`。固定 `config + seed + generated-at` 会生成相同内容；输出目录必须不存在，Generator 不覆盖旧批次。

验证：

```powershell
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests -v
```

边界：CSV 字段来自当前 21 表候选物理模型；正式 DDL 尚未完成逐字段核对。本生成器不执行 `LOAD DATA`、MySQL 写入或 Source Gate。`biz_product_change_event` 优先满足 20%–30% SKU、每 SKU 1–3 个有效变化版本，实测行数写入 Manifest。
