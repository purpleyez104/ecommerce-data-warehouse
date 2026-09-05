# 修改日志

本文件记录项目中面向使用者和维护者的可交付变更。

日志遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 的分类方式；项目形成正式发布版本后再补充版本号和发布日期。开发中的变更统一记录在“未发布”章节，不把草案、占位文件或静态检查写成已经完成运行验证。

## [未发布]

### 新增

- 创建项目修改日志和决策记录入口。
- 建立 Agent 每次最终答复总结核心操作和核心决策、并在用户确认后按职责写入修改日志或决策记录的协作规则。
- 在 README、项目规格和阶段计划中补充修改日志与决策记录的路径、作用和 Milestone 0 验收边界。
- 增加仓库级 LF 换行约束，避免本机 Git 配置破坏文档格式基线。
- 新增 Milestone 2 预设计评审包，集中记录五个主题的业务过程、概念关系、30 项正式指标的过程依赖、验收场景和待确认决策。
- 新增 Milestone 1 集群事实基线、组件兼容性矩阵、安装排障记录、基础设施端口/hosts 边界和 Hadoop 验收脚本。
- 将 `.local-notes/` 纳入 Git 忽略范围，作为从 ECS 接收原始 M1 证据的本地隔离区，防止运行日志和现场值被误提交。

### 变更

- 离线主线调整为 DataX 直接写入 Hive ODS 对应的 HDFS ORC + Snappy 分区，并明确分区注册、审计字段、幂等发布和失败隔离责任。
- Milestone 0 已通过用户评审并标记为 `completed`；Milestone 1 保持 `pending`，进入门禁已满足但尚未开始实施。
- 在 Milestone 1、2 均保持 `pending` 的前提下，允许开展受限的 M2 文档预设计；该活动不豁免 MySQL 运行门禁，也不产生 DDL、seed 或其他可执行产物。
- Milestone 1 更新为 `in progress`；把当前 ECS 集群记录中的 `CONFIRMED` 作为确认事实，并将当前门禁调整为补齐 Hadoop HDFS、MapReduce 和重启证据。
- M1 统一沿用 `yee`、`/data` 和 Hadoop 独立 JDK 11 基线；Doris FE HTTP 使用 `18030`，DolphinScheduler 使用仅服务自身的单节点 ZooKeeper。
- 统一 M1 仓库与证据流转方式：`hadoop201` 仅拉取仓库并执行脚本，原始证据通过 MobaXterm 下载到 Windows 本地隔离区，仓库只接收经审查和去敏后的摘要或配置。
- Hadoop 3.4.1 已完成固定 HDFS 文件、MapReduce WordCount、YARN application、聚合日志、临时对象清理和受控重启验证，项目状态提升为 `verified`；M1 当前技术门禁切换到 MySQL 8.0.46。

### 修复

- 修复 Hadoop 受控重启验证对 `jps -lv` 完整 Java 类名的匹配错误，避免在 NameNode 等进程实际存在时误报缺失；修复后已在目标 ECS 完成复测。

### 移除

- 从正式离线架构中移除独立的 HDFS landing/staging Text/CSV 中间数据层。
