# DataX

`jobs/` 用于存放经验证的 DataX 任务配置，`scripts/` 用于参数化执行入口。两个目录当前都只有占位说明，没有可运行 Job。

新增任务前需确认 DataX 版本、MySQLReader、目标存储写入器、DECIMAL 类型、分区策略、失败重试和幂等重跑行为；验证结论应同步记录到项目文档。
