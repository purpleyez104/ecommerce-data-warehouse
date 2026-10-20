# Hive 目录说明

本目录保存 Hive 表 Contract、DDL 生成入口与分层模型定义，不复制保存远端
Metastore 元数据或 HDFS 中的 ORC 数据。因此，部分层级目录为空不表示 Hive 表未建立。

| 路径 | 当前职责 |
| --- | --- |
| `ods/` | 22 张 ODS 表的 Contract、DDL/发布 SQL 生成入口及说明 |
| `model/` | DIM、DWD、DWS、ADS 的逻辑/物理 Contract、DDL 生成入口与迁移 SQL |
| `dim/`、`dwd/`、`dws/`、`ads/` | 已保留的层级导航目录；当前不重复存放由 Contract 生成的 SQL |

主要离线转换由 `spark/scripts/` 下的 Renderer 按显式业务日期生成并通过 Spark SQL
on YARN 执行。真实表、分区和数据分别位于远端 Hive Metastore 与 HDFS；其是否
`VERIFIED` 以 `docs/status/offline-current.md` 和 `docs/acceptance/` 中的运行证据为准，
不能仅凭本地目录或文件存在判断。
