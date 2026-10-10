请基于本对话中已经真实发生的实时链路建设过程，整理截至当前时刻的实时链路 Current Baseline，并生成一份可以直接交给 ChatGPT Work 用于维护 ecommerce-data-warehouse 项目目录的标准交接包。

核心原则

这次任务不是继续开发，也不是重新规划，而是建立实时链路当前唯一可信事实基线。

状态必须严格区分：

VERIFIED

DOING

DESIGNED

HISTORY

UNKNOWN

只有具有明确工程验证证据的内容才能进入 VERIFIED。

特别注意区分：

组件安装验收

链路能力验收

临时测试 Job

正式业务 Job

正式生产提交方式

SQL Client / YARN Session 等验收手段

最终业务使用的 YARN Application 等方式

后续 Step 序号较大的真实验证结果，如果明确取代较早版本，以后期最终工程状态为准。

输出格式

01. Current Status

分别列出：

VERIFIED

每项包括：

阶段/能力

最终版本

最终运行方式

节点部署

数据流

Job/Application 情况

Checkpoint/容错情况

验收结果

关键证据

重点覆盖已确认过的：

Flink on YARN

MySQL CDC

Kafka

Flink CDC Pipeline

Kafka → Flink → Kafka

Doris

Kafka → Flink → Doris

Checkpoint / TaskManager 故障恢复

但必须根据本对话真实证据判断，不允许仅因为这里列出来就自动写 VERIFIED。

DOING

重点判断：

当前正式业务实时链路已经开发到哪个 Job / DWD 表

哪部分是正式业务开发

当前具体阻塞在哪里

下一步应该从哪继续

DESIGNED

列出已经确定但尚未完成工程验证的 DWD/DIM/DWS/ADS 或业务模型设计。

HISTORY

包括但不限于：

被最终方案替代的 Job 提交方式

早期兼容性方案

旧 CDC Runtime 或旧 Connector 方案

已经被业务设计 V2 替代的实现

与当前指标体系不一致的旧实现

UNKNOWN

所有无法确认真实状态的内容。

02. Current Realtime Data Flow

给出当前经过真实验证的技术链路。

区分两层：

Infrastructure / Capability Baseline

例如：

MySQL Binlog → Flink CDC → Kafka → Flink → Doris

Current Business Pipeline

只描述目前真实业务开发已经推进到的位置。

不要把“基础链路验收成功”等同于“业务实时数仓全部完成”。

03. Runtime Baseline

整理最终仍然有效的运行环境：

组件

最终版本

节点

Runtime/路径

最终运行方式

VERIFIED

重点处理：

Hadoop/YARN

Flink

Flink CDC

Kafka

MySQL

Doris

Connector

Checkpoint 路径

如果存在普通 Flink Runtime 和 CDC 独立 Runtime，必须明确区别。

04. Verified Files

表格：

文件

功能

是否正式业务文件

实际路径

建议仓库路径

VERIFIED

是否脱敏

备注

必须区分：

验收脚本

正式 Job

SQL Client 临时 SQL

配置文件

Connector 配置

Checkpoint 配置

CDC Pipeline YAML

临时探针表/Topic

不确定的不要补写。

05. Final Commands

只保留：

最终组件启动/检查命令

最终 Job 提交命令

YARN 查看命令

Kafka 检查命令

Doris 验证命令

Checkpoint/恢复验证相关关键命令

明确标记：

ENGINEERING
或
ACCEPTANCE-ONLY

避免把临时验收命令当成正式运维脚本。

06. Evidence

对每个核心 VERIFIED 能力整理：

验证目标

Job ID / Application ID（有明确记录时）

Topic / Table

输入

输出

关键结果

故障恢复结果

能证明什么

证据重点是“足以证明”，不是日志越多越好。

07. Repository Handoff

分为：

正式工程文件

可以直接维护进仓库。

验收资产

建议进入：

scripts/acceptance/

docs/evidence/

或其他合适位置

历史资产

不要混入正式业务目录。

不确定资产

暂不处理。

给每项明确建议路径。

08. Documentation Updates

明确哪些文档应根据当前最终工程状态更新。

特别指出：

哪些架构内容已经 VERIFIED

哪些只是 DESIGNED

哪些旧描述已经失效

plan.md 暂时不要强行适配旧 M1/M2/M3 结构

如果需要，应新建 Current Baseline / Status 文档

09. Next Development Point

只给出实时链路当前唯一下一开发入口：

当前 Job / 层级

上游

下游

输入 Topic/Table

输出 Table

业务口径依赖

验收标准

不要重新开启架构重构。

10. Work Handoff Summary

生成一段可以直接复制给 Work 的摘要，使 Work 无需重新阅读历史聊天即可知道：

实时链路已经真正完成什么

正在做什么

哪些是历史方案

哪些文件可信

哪些证据可信

Work 应该更新哪些内容

Work 不能自行推断什么

Chat 下一步从哪里继续
