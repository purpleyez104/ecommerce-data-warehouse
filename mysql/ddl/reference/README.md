# 21 表 DDL：仅结构参考，不是部署脚本

候选 DDL 与本目录的隔离库参考 DDL 来自已有的 M2-03 物理设计文件，文件头原文标为 REVIEW ONLY / NOT EXECUTED；当前 hadoop201 的 21 表已存在且有真实写入，因此**禁止直接重跑这些 CREATE TABLE**。本包没有连接集群导出 SHOW CREATE TABLE，不保证这些文件与当前数据库逐字一致。正式修订请在当前 MySQL 导出真实 DDL 后进行 diff 和评审。

- `../001_ecommerce_oltp_v1.sql`：设计目标 `ecommerce_oltp`。
- `001_ecommerce_oltp_m2_acceptance.sql`：设计目标 `ecommerce_oltp_m2_acceptance`。

未收录早期固定种子文件 `001_ecommerce_oltp_m2_acceptance.sql`（旧 seed）：它曾使用 `FOREIGN_KEY_CHECKS=0`，且与当前已运行的 Python Generator 不是同一套基线，避免同名混淆。
