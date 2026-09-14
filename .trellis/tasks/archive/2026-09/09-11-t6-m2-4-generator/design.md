# T6 M2.4 参数化 Generator 设计

## Boundary

T6 仅生成可在后续隔离 MySQL 测试库中使用的 SQL 文本，并在生成前用纯 Python 校验跨行和流程规则。它不执行 SQL、不打开数据库连接、不创建 DDL，也不改写 T5 的固定 Seed、预期结果或测试。

## CLI Contract

提供一个只使用 Python 标准库的 CLI，接收：

- `--seed`：非负整数随机种子。
- `--start-date`：必填 `yyyy-MM-dd` 业务开始日期。
- `--days`：正整数业务日期数量。
- `--scale`：正整数；`1` 表示以 T4 的小型验收规模为基线，较大值仅产生更多候选数据，不构成 Benchmark 结论。
- `--output`：必填 SQL 输出文件路径。

相同的全部参数必须产生字节一致的 UTF-8、LF SQL 文件。业务与审计时间均由 `start-date`、`days` 和固定时刻构造，不读取系统当前日期。参数或规则错误写入 stderr 并以非零退出。

## Data and Rule Model

Generator 在内存中建立最小的 19 表关系数据，再按 `DR-020` 的父表到子表顺序渲染 `INSERT` SQL。`scale=1` 覆盖 T4 已确认的四日期、五主题及金额/状态/优惠券规则；不要求与 T5 固定 SQL 的业务键或行内容相同，但必须遵守其表、日期、金额精度和规则边界。

纯 Python 规则模块负责：`Decimal` 两位小数 `HALF_UP`、订单级优惠按明细金额比例分摊及确定性尾差、允许状态迁移、单订单最多一笔成功支付、累计退单数量与成功退款金额上限、优惠券锁定/使用/释放/过期与一次成功使用。违反规则必须在 SQL 输出前失败。

## Compatibility and Risks

T5 当前未提交，故它只是只读集成输入；其后续契约变化需在集成阶段复核。SQL 文本通过静态测试证明结构与纯 Python 规则，不证明 MySQL 8.0.46 语法或约束行为。M2.5 才执行真实 MySQL 验收。

## Rollback

T6 仅新建 `generator/` 与其专属测试；回滚时移除这些新文件即可。不得删除或修改 T5 文件，亦不得对共享工作区做 MySQL 清理操作。
