刚刚完成了一个实时链路开发阶段。

现在停止继续开发，根据本轮对话真实执行和验收结果生成一个标准 Work Handoff Package，供 ChatGPT Work 更新 ecommerce-data-warehouse 项目目录。

规则

只总结本阶段新增变化，不重新整理整个实时项目。

严格区分：

基础设施验收

Connector/Runtime 验收

临时测试 Job

正式业务 Job

正式数仓层建设

不能因为测试链路成功，就写成正式业务链路已经完成。

只有本轮有真实执行证据的内容可以进入 VERIFIED。

如果正式方案替代之前方案：

SUPERSEDES: <旧方案>

并说明旧方案进入 HISTORY 的原因。

固定输出

01-status.md

包括：

阶段名称

本阶段目标

最终完成范围

VERIFIED

DOING

DESIGNED

HISTORY

UNKNOWN

对实时整体链路产生的变化

下一阶段入口

02-files.md

表格：

文件

类型

本阶段用途

实际执行

当前路径

建议仓库路径

操作

文件类型明确标记：

BUSINESS-JOB

INFRA

ACCEPTANCE

CONFIG

SQL

YAML

SCRIPT

DOC

TEMP

操作：

ADD

UPDATE

MOVE

RENAME

KEEP

HISTORY

IGNORE

不要补造没有确认存在的文件。

03-commands.md

只保留最终成功命令。

每条注明：

执行节点

Runtime

命令

用途

ENGINEERING / ACCEPTANCE-ONLY

是否应固化

尤其明确：

Flink 提交方式

YARN Application / Session

CDC Runtime

Kafka 检查

Doris 检查

Checkpoint / Savepoint / 恢复操作

如果某种提交方式只是测试手段，要明确写 ACCEPTANCE-ONLY。

04-evidence.md

每个 VERIFIED 能力记录：

验证目标

上游

下游

Job/Application ID

Topic/Table

输入事件

输出结果

Checkpoint 状态

故障恢复情况

PASS 条件

最终结论

没有明确记录的 ID 不得猜测。

05-doc-updates.md

列出 Work 本阶段需要修改的文档。

原则：

技术栈变更 → compatibility / architecture

最终工程决策变更 → decision-register

指标口径变更 → metrics

当前状态变化 → current-status

普通业务 Job 完成 → 不要因此重写整个 plan

未发生变化的文档 KEEP

06-next.md

下一阶段只给：

当前实时层级

下一张表 / 下一 Job

Source

Transform

Sink

依赖的指标/业务 Contract

验收标准

不要重新展开长期项目规划。

最后输出：

WORK HANDOFF

生成一段可直接复制给 Work 的指令，明确：

这次新增哪些 VERIFIED 成果

Work 应更新哪些路径

哪些属于验收证据

哪些属于正式业务工程

哪些旧内容应标记 HISTORY

禁止 Work 根据旧 plan 自行重构当前开发顺序

完成后 Work 应返回一份变更清单和未处理问题
