# M1 DolphinScheduler 3.4.2 精简门禁

## Task Identity

- Task ID：`M1-DS-GATE`
- Status：`planning`
- Evidence Policy：`DR-027` Risk-based Acceptance

## Goal

以最小充分证据确认 DolphinScheduler 3.4.2 在当前三节点开发环境中具备后续 Milestone 6 所需的启动、调度、失败识别和受控恢复能力；本 Task 当前只完成规划，不授权实施。

## Scope

- 核对 DolphinScheduler 3.4.2、MySQL Metadata 依赖和仅供 DolphinScheduler 使用的单节点 ZooKeeper 3.8.4。
- 核对 Master、Worker、API 及任务执行所需的必要进程和私网监听。
- 执行一个固定成功任务并核对最终成功状态。
- 执行一个固定预期失败任务并核对最终失败状态，不能只依赖提交命令退出码。
- 经用户显式授权后执行受控 restart，并核对服务与任务查询恢复。
- 保留 Secret 去敏、失败传播和临时对象 Cleanup Hard Gate。

## Out of Scope

- 不在当前 planning 状态安装、启动、停止或重启任何服务。
- 不修改 DolphinScheduler、ZooKeeper、MySQL、JDK 或网络永久配置。
- 不创建 Milestone 6 正式 T+1 DAG、业务 SQL、补数流程或 Project 2 Task Contract。
- 不证明生产级 HA、容量、性能、Exactly-Once 或长期稳定性。
- 不为每条内部命令强制生成独立文件、逐文件 Hash 或完整时间链。

## Acceptance Criteria

### Hard Gates

- [ ] 版本、MySQL Metadata 和单节点 ZooKeeper 依赖与已确认拓扑一致。
- [ ] Master、至少一个可调度 Worker、API 和必要私网监听处于可用状态。
- [ ] 固定成功任务达到可查询的最终成功状态，并保存任务标识和关键结果。
- [ ] 固定预期失败任务达到可查询的最终失败状态，不被误报为成功。
- [ ] 只有用户提供精确确认参数后才允许 restart；恢复后服务健康且历史任务状态仍可查询。
- [ ] Secret 不进入日志或 Git；临时对象只清理当前 run 所有目标；必需断言失败返回非零或明确失败态。

### Process Checks

- [ ] 运行前由协调会话确认影响范围、命令、Secret 路径要求和回滚方式。
- [ ] 运行结果经协调会话按 `DR-027` 核对，并同步 M1 与 `infra/versions.env` 门禁状态。

### Optional Evidence

- 完整服务日志、每步独立输出、逐文件 Hash、Manifest 和完整时间链只在失败诊断、状态冲突或发布审计需要时补充。

## Verification

- 最小证据包：`summary.env` 或等价摘要、成功/失败任务 ID 与最终状态、restart 前后健康摘要、最终 exit code、脚本 Git revision 或 SHA-256。
- Reviewer 重点检查最终任务状态、restart 授权、Secret 去敏和 Cleanup 边界。
- 若结果矛盾、脚本身份不明或失败传播不可靠，再增加 targeted evidence；不默认全量补采。

## Parallelism

- 可以保持 `planning`，与已通过直接门禁的 M2 本地工作并行。
- Runtime 验收涉及共享 ECS 服务，执行时不得与其他中断型 M1 测试并行。

## Worktree

- 当前只规划，不需要 Worktree。
- 若后续仅新增独立脚本且与当前分支有并行写入，实施前再决定专属 Worktree。

## Conflicting Files / Modules

- `docs/compatibility-matrix.md`
- `docs/cluster-baseline.md`
- `docs/installation-troubleshooting.md`
- `docs/plan.md`
- `docs/spec.md`
- `README.md`
- `infra/versions.env`（只有全部 M1 门禁通过后才允许创建）

## Activation Gate

- 保持 `planning`，不设置为当前 Task。
- 实施前必须重新读取现场状态并由用户确认命令、文件范围、restart 影响和回滚方式。
