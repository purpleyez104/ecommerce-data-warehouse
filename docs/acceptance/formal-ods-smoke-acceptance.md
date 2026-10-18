# Formal ODS Day 60～90 隔离 Stage Gate 验收

状态：`VERIFIED`（限定范围）  
验收日期：2026-10-18

## 验收范围

- Source：隔离 MySQL `ecommerce_oltp_ods_20260105_r1`。
- Target：隔离 Hive `ecommerce_ods_replay_20260105_r1`。
- 输入：正式 Replay Baseline 的 Day 60 Bootstrap 与 Day 61～90 Incremental Contract。
- 链路：MySQL → DataX HDFS Writer → ORC + Snappy staging → Spark Validation / Publish → Hive ODS。

## 结果

- Day 60 Source 为 438,869 行，45-rule Source Gate 为 45/45、0 违规；21 表 ODS Bootstrap 发布完成，独立 ODS Gate 输出 `ODS_GATE_PASS`，共 1,000 个断言结果。
- Day 61 Source Replay 提交 19,675 个 operations，事务内 Source Gate 为 45/45、0 违规，Ledger 与业务变更同事务提交。
- Day 61 DataX staging 与 Spark validation 通过；增量发布采用批次隔离的两阶段 ORC merge，避免 Spark 同表读写限制。
- Day 61 发布后独立 ODS Gate 输出 `ODS_GATE_PASS assertions=1034`，覆盖 21 表目标总量、全部现存业务日期分区、PK/分区级唯一性、审计字段、Hive 类型、DDL 外键和本批 staged-row 落表。
- Day 61 后目标期望总行数为 457,571；`full_snapshot` 表按 `(primary_key, dt)` 验证唯一性，其每日快照不会被误判为跨分区重复。
- Day 61 同日恢复重跑复用已绑定的 `r4` staging，不接触 MySQL、不重新执行 DataX，也不需要 Source Secret。Runner 状态历史为 `planned → staged_reused → validated → published`；重跑后的独立 Gate 再次得到 1,034 个断言结果和相同的 457,571 行目标基准。
- `--resume-from` 只接受同一 Runtime 根目录内、已完成 staging 且 batch、dataset、窗口、目标库和完整 partition plan 全部一致的运行证据；恢复仍强制重新执行 Validation，不能从失败状态直接跳到 Publish。
- Day 62～90 使用 Source Replay 与 ODS Batch 逐日交替推进；29/29 Checkpoint 完整，Range State 为 `verified`。Source Ledger 覆盖 Day 61～90 共 30 条，操作总数 1,210,882；最终 Source 21 表合计 1,328,491 行。
- Day 63 在最后一张 DataX 表执行期间因外部会话中断，已完成的批次 staging 未发布。恢复时只删除精确匹配该 `batch_id` 的 21 个隔离 staging 目录，保留失败日志并从 Day 63 重跑；随后 Day 63～90 连续发布成功，未重放 Day 62。
- Day 90 后基于最终 Source 按业务日期分组计数和 Day 60～90 `full_snapshot` 合约生成独立目标期望：21 表目标合计 1,632,345 行，`biz_identity_mapping` 为 31 个快照分区。最终 Spark ODS Gate 退出码为 0，1,498/1,498 条断言返回成功，`exception/error/failed` 关键词均为 0。
- 隔离库临时 MySQL grants 已撤销；hadoop201 Source env、hadoop202 `datax.env` 及中断目录中的 Secret job 已删除。公网地址、密码和原始日志未进入仓库。

## 失败隔离与修复证据

- Manifest 相对路径错误、0-row ORC Schema 推断和 Spark 同表 overwrite 均在 Publish 前或第一写入前 fail-fast，并保留独立运行状态与日志。
- Spark cache 不能切断同表读写血缘；最终采用“目标分区 + batch staging → 独立 `_merge` ORC → Hive 分区 overwrite”的物理边界。
- 失败的 `r1`～`r4` 与 recovery 记录保留在私有 Runtime；正式验收以 recovery publish 成功和独立 Gate r3 为准。

## 证据边界

本验收证明当前固定 Baseline 在记录环境中的 Day 60 Bootstrap、Day 61～90 连续增量、同日 staging 复用恢复、跨日中断恢复和最终 ODS Gate，满足 Milestone 3 的当前验收范围。它不证明硬删除同步、DIM/DWD/DWS/ADS、Doris 离线 Serving、DolphinScheduler 编排或正式实时链路；这些内容仍按后续 Milestone 验收。
