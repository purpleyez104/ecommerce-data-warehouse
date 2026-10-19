# Hive Model Contract

本目录保存 DIM/DWD/DWS/ADS 的语义 Contract、物理 Contract、确定性 DDL Generator，以及 M5-02 退款事实迁移与回滚入口。业务指标定义仍以 `docs/business/metrics.md` 为唯一入口；本目录不重复定义指标公式。

## 当前状态

- 6 张 DIM、8 张 DWD、6 张 DWS 与 1 张 ADS 均有真实 Spark on YARN Runtime。
- 当前 `dwd_refund` 粒度为每个 `refund_request_id` 一行，成功资金字段允许为空。
- 当前模型通过 60/60 Model Gate；六域 6 DWS + 1 ADS 通过首次及幂等重跑后的 41/41 Aggregate Gate。
- 三张旧 Contract 表保留为 `m5_20261018_history_*`；当前受影响表使用 `/warehouse/ecommerce/model/m5_20261018/` 下的显式 Location。
- 完整证据见 `docs/acceptance/m5-refund-contract-migration-acceptance.md`。

## 文件职责

| 文件 | 职责 |
| --- | --- |
| `model_contract.json` | DIM/DWD 粒度、业务键、来源、历史策略与 Gate 语义 |
| `model_physical_contract.json` | DIM/DWD 列、类型、Database 与显式 Location |
| `aggregate_contract.json` | DWS/ADS 粒度、业务键和可复用度量 |
| `aggregate_physical_contract.json` | DWS/ADS 列、类型、Database 与显式 Location |
| `generate_model_ddl.py` | 生成 DIM/DWD EXTERNAL ORC + Snappy DDL |
| `generate_aggregate_ddl.py` | 生成 DWS/ADS EXTERNAL ORC + Snappy DDL |
| `migrate_m5_refund_contract.sql` | 将旧表保留为 HISTORY 并创建当前 M5 表 |
| `rollback_m5_refund_contract.sql` | 只回滚 Hive 元数据名称；不删除新旧 HDFS 数据 |

## 本地验证

```bash
python hive/model/validate_model_contract.py \
  --contract hive/model/model_contract.json \
  --ods-contract datax/config/ods_tables.json

python hive/model/generate_model_ddl.py \
  --semantic-contract hive/model/model_contract.json \
  --physical-contract hive/model/model_physical_contract.json

python hive/model/generate_aggregate_ddl.py \
  --semantic-contract hive/model/aggregate_contract.json \
  --physical-contract hive/model/aggregate_physical_contract.json
```

完整本地测试入口为 `bash tests/run_unit.sh`。文件生成或静态测试通过不等于 Runtime `VERIFIED`。

## 迁移安全边界

迁移前必须确认 HISTORY 表名和新 Location 均未占用，并保存旧 DDL/HDFS 备份。`rollback_m5_refund_contract.sql` 依赖旧 HISTORY 表仍存在；不得把它改成删除旧 EXTERNAL 数据或清理 HDFS 路径的脚本。任何再次执行迁移、回滚或清理都属于外部 Database/HDFS 写入，需要单独授权。
