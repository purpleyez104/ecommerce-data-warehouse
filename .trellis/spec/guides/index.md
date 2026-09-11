# Data Engineering Thinking Guides

在修改当前项目时，优先遵循 [Data Engineering 项目规范入口](../data-engineering/index.md)。

需要跨模块判断时，按以下顺序核查：

1. 业务语义、事实粒度、业务键、时间语义和状态机是否已有确认依据。
2. 目标 Milestone 的进入条件、交付物与阻断项是否允许该变更。
3. 输入、输出、业务日期参数、质量规则、对账和失败退出是否可验证。
4. 文档、代码、配置或证据冲突时，是否已停留为 `DECISION_REQUIRED`。

不存在对应实现时不创建抽象、接口或技术栈规范。
