# Implementation Plan：M1 虚拟机与组件现场采集

## 1. Pre-development

- [x] 加载 `trellis-before-dev` 并再次确认 Data Engineering guidelines。
- [x] 复查当前 Git 状态，确保不覆盖 `.gitignore`、`AGENTS.md` 和 T6/T7 Task。
- [x] 复用 `scripts/m1/collect-hadoop-evidence.sh` 的参数、输出目录、`umask`、日志与 summary 模式。

## 2. Implementation

- [x] 新增 `scripts/m1/collect-vm-environment-evidence.sh`。
- [x] 实现参数、执行用户、执行节点、输出目录和依赖保护。
- [x] 实现三节点 SSH 只读采集和单节点失败隔离。
- [x] 实现 VM system/network/time/storage/runtime/process/port 采集。
- [x] 实现五个组件的路径、版本、进程、端口与白名单配置采集。
- [x] 实现敏感键屏蔽、JDBC URL 去敏和 `COLLECTED / PARTIAL / FAIL` 汇总。
- [x] 更新 `scripts/m1/README.md` 的虚拟机现场采集章节和 `DR-007` 证据回传路径。
- [x] 新增 `tests/m1/test_collect_vm_environment_evidence.ps1` 静态 Contract Test。

## 3. Verification

- [x] 运行：`powershell -NoProfile -ExecutionPolicy Bypass -File tests/m1/test_collect_vm_environment_evidence.ps1`。
- [x] 使用现有 Git Bash 运行：`bash -n scripts/m1/collect-vm-environment-evidence.sh`。
- [x] 运行：`git diff --check -- scripts/m1/collect-vm-environment-evidence.sh scripts/m1/README.md tests/m1/test_collect_vm_environment_evidence.ps1 .trellis/tasks/09-13-m1-vm-evidence-collection`。
- [x] 人工检查脚本不包含 install/start/stop/restart、NameNode format、数据库/Topic 创建或远程配置写入。
- [x] 人工检查输出契约不复制完整配置，不暴露 Secret。

## 4. Runtime Boundary

- [x] Windows 本地静态检查不构成 ECS 运行验收。
- [x] 用户在 `hadoop201` 运行并回传完整目录后，已评审 `summary.env` 和去敏证据，三节点 VM 基线通过。
- [x] 五个组件继续保持 `candidate`；后续功能验收另立范围。

## 5. Evidence Closeout

- [x] 对照 Step 1-12 总结识别版本替换、配置漂移、重要修复与正式决策。
- [x] 同步 README、规格、架构、集群基线、兼容矩阵、排障、端口、环境示例、CHANGELOG 和决策记录。
- [x] 修正 DataX 历史入口识别并新增 Hive/Java 漂移采集。
- [x] 复跑 PowerShell Contract、Bash syntax/help 和 `git diff --check`。

## 6. Rollback

- [ ] 删除本 Task 新增脚本和测试，并只撤销 `scripts/m1/README.md` 的本次新增段落。
- [ ] 不触碰用户已有未提交修改和 ECS 既有日志/服务/配置。
