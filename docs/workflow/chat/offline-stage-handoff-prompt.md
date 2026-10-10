刚刚完成了一个离线链路开发阶段。

现在不要继续开发，也不要扩展需求。请根据本轮对话中刚刚真实执行并成功验证的内容，生成一份标准 Work Handoff Package，供 ChatGPT Work 更新 ecommerce-data-warehouse 项目目录。

规则

只记录本阶段新增或发生变化的内容。

不要重新总结整个项目。

只允许把有明确运行结果的内容标记为 VERIFIED。

以下内容不能自动视为 VERIFIED：

仅讨论过的设计

仅由你生成但我没有执行的文件

失败版本

临时猜测

没有输出结果的命令

旧计划中的预期结果

如果本阶段改变了之前的工程方案，要明确：

SUPERSEDES: <旧方案>

旧方案转入 HISTORY，不要覆盖历史事实。

输出以下 6 个固定部分

01-status.md

记录本阶段：

阶段名称

开始状态

最终状态

新增 VERIFIED 能力

尚未完成内容

是否改变当前架构/技术方案/数据口径

下一阶段入口

状态只使用：

VERIFIED

DOING

DESIGNED

HISTORY

UNKNOWN

02-files.md

只记录本阶段真实涉及的文件。

表格：

文件

本阶段作用

是否实际执行

当前路径

建议仓库路径

操作

操作 只能使用：

ADD

UPDATE

MOVE

RENAME

KEEP

HISTORY

IGNORE

如果无法确认真实文件，不允许补造。

如果命令只存在聊天中但值得复用，单独标记：

CHAT-ONLY → 建议后续固化

不要自动生成不存在的脚本。

03-commands.md

只记录本阶段最终成功且以后仍有价值的命令。

每条注明：

命令

节点

用途

ENGINEERING 或 ACCEPTANCE-ONLY

是否建议固化为 .sh/.sql/.py

失败调试命令不收录，除非它代表重要故障案例。

04-evidence.md

为本阶段 VERIFIED 结果建立最小证据。

每项包含：

验证目标

输入

操作

关键输出

行数/金额/分区/Application ID/时间等关键结果

PASS 条件

实际结果

结论

不要复制大量无关日志。

05-doc-updates.md

告诉 Work 本阶段只需要更新哪些文档。

每个文档说明：

文件路径

ADD / UPDATE / KEEP

更新内容

不应修改的部分

除非本阶段确实改变总体规划，否则不要修改旧 plan.md。

指标没有变化时，不要修改 metrics.md。

架构没有变化时，不要修改 architecture.md。

06-next.md

只记录下一阶段：

目标

上游输入

需要产出

验收标准

明确不做什么

保持 3～7 条即可。

最后追加：

WORK HANDOFF

生成一段完整、可直接复制给 ChatGPT Work 的操作说明。

必须明确：

本阶段新增了什么

Work 要操作哪些文件

哪些文件只是历史/证据

哪些东西不能自行推断

完成维护后 Work 应返回什么变更摘要
