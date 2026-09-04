# Milestone 1 安装与排障记录

版本：`0.1-draft`
状态：`in progress`
更新时间：2026-09-04

## 使用范围

本文件只记录目标 ECS 上真实发生的安装、启动、连通、最小任务和重启问题。候选风险、未执行命令和学习笔记不得写成已经发生的故障。

每条记录必须包含：

- 编号、日期、组件、节点和精确版本。
- 触发命令、预期退出状态、实际退出状态和关键错误。
- 根因证据，不以猜测代替。
- 实际修复、复测命令、复测结果和日志位置。
- 影响范围、已知限制和回滚方式。
- 是否需要新增或替代正式决策。

原始日志保存在 ECS 本地 `/data/logs/ecommerce-data-warehouse/m1/`，不提交 Git。仓库只保留去敏摘要。

## 已知约束，不是已发生故障

### Hadoop 使用独立 JDK 11

- 三节点默认环境为 OpenJDK 17。
- Hadoop 3.4.1 的当前运行配置在 `hadoop-env.sh` 中固定使用 OpenJDK 11。
- M1 脚本不得用修改全局 `JAVA_HOME` 的方式修复 Hadoop，也不得把客户端 Java 17 输出误当成守护进程 Java 版本。

### YARN 与 Doris FE 端口冲突

- YARN ResourceManager Scheduler 已使用 `8030`。
- Doris FE HTTP 端口已决定使用 `18030`。
- Doris 安装前必须在三节点执行端口占用检查，并同步配置、健康检查、安全组和 SSH 隧道说明。

### DolphinScheduler 的 ZooKeeper 边界

- 单节点 ZooKeeper 只作为 DolphinScheduler 的开发环境注册中心。
- Kafka 必须保持 KRaft 模式，不得连接或依赖该 ZooKeeper。
- 单节点 ZooKeeper 不构成高可用，必须在文档和面试表述中保留该限制。

## 排障记录

当前暂无来自本仓库 M1 执行的真实故障记录。

## 记录模板

```markdown
## M1-ISSUE-001：简短标题

- 日期：yyyy-MM-dd
- 组件与版本：
- 节点：
- 状态：open / resolved / accepted-limit
- 日志位置：

### 触发与现象

### 根因证据

### 修复与复测

### 影响与限制

### 回滚
```
