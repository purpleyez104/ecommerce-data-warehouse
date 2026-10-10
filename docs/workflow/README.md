# Project Workflow

本项目采用 **Development Chat + ChatGPT Work + Git Repository** 的协作方式。

目标是把“开发推进”和“仓库维护”分开，避免因为历史聊天、旧计划、模糊文件名、临时命令和阶段调整造成项目状态混乱。

---

## 1. Roles

### Development Chat

Development Chat 分为：

- Offline Chat
- Realtime Chat

主要负责：

- 推进真实工程开发；
- 编写和调整 SQL / Shell / Python / Flink Job 等；
- 执行命令；
- 排查故障；
- 完成阶段验收；
- 判断哪些结果已经 VERIFIED；
- 维护 File Fact Ledger；
- 在阶段结束后生成 Work Handoff Package。

Development Chat 是**工程事实的产生端**。

---

### ChatGPT Work

Work 主要负责：

- 维护项目目录；
- 根据 Handoff Package 更新正式工程文件；
- 更新项目文档；
- 维护 Current Status；
- 维护 File Baseline；
- 区分正式工程资产、验收资产和历史资产；
- 记录冲突和待处理问题。

Work 是**工程事实的维护端**。

Work 不负责重新推导开发历史，也不根据旧计划自行判断项目进度。

---

### Git Repository

Git Repository 用于保存：

- 当前正式工程文件；
- 项目文档；
- Current Status；
- File Baseline；
- Workflow 规则；
- 必要的验收资产；
- 历史变更记录。

Git 历史负责保存过去发生过什么。

`docs/status/` 负责表达：

> 项目现在是什么状态。

---

# 2. Core Workflow

标准流程：

```text
Development Chat
      │
      ├── 开发
      ├── 执行
      ├── 排错
      ├── 验收
      │
      ├── 更新 File Fact Ledger
      │
      └── 生成 Work Handoff Package
                    │
                    ▼
                  Work
                    │
                    ├── 更新工程文件
                    ├── 更新 docs/status/
                    ├── 更新必要文档
                    └── 返回变更摘要
                    │
                    ▼
             Development Chat
                    │
                    └── 从 NEXT 继续开发
```

开发过程中不要求仓库实时同步每一条临时命令。

只有阶段形成明确工程结果后，才通过 Handoff 同步给 Work。

---

# 3. Current Status

当前工程状态统一维护在：

```text
docs/status/
├── offline-current.md
├── realtime-current.md
└── file-baseline.md
```

---

## `offline-current.md`

回答：

> 当前离线链路真实做到哪里了？

主要维护：

- VERIFIED
- DOING
- DESIGNED
- HISTORY
- NEXT

---

## `realtime-current.md`

回答：

> 当前实时链路真实做到哪里了？

主要维护：

- VERIFIED
- DOING
- DESIGNED
- HISTORY
- NEXT

---

## `file-baseline.md`

回答：

> 当前真正可信、仍然有效的工程文件有哪些？

主要维护：

- 当前正式工程文件；
- 当前验收文件；
- 待确认文件；
- 已被替代文件；
- 模糊或存在冲突的文件。

---

# 4. Status Definitions

项目统一使用以下状态。

## VERIFIED

已经真实执行并通过验收。

必须存在明确工程证据。

例如：

- 命令成功执行；
- Job 成功运行；
- 数据结果符合预期；
- 表、Topic、Checkpoint 或 Application 状态已经验证。

---

## DOING

当前正在开发或验收，但还没有形成完整闭环。

---

## DESIGNED

方案已经确认，但尚未完成真实工程验证。

---

## HISTORY

已经被后续版本替代的：

- 旧方案；
- 旧脚本；
- 旧架构；
- 旧阶段设计；
- 早期实现。

---

## UNKNOWN

当前证据不足，无法确认真实状态。

不允许为了让项目看起来完整而自行补全。

---

# 5. File Fact Management

项目文件不能只通过“仓库里是否存在”判断状态。

统一原则：

```text
FILE EXISTS ≠ VERIFIED
```

Development Chat 负责维护完整的 **File Fact Ledger**。

文件事实需要区分：

- VERIFIED_EXECUTED
- CONFIRMED_CREATED
- CHAT_GENERATED
- MENTIONED_ONLY
- SUPERSEDED
- UNKNOWN

Work 只把已经得到明确确认的文件同步到：

```text
docs/status/file-baseline.md
```

---

# 6. Chat-only Commands

开发过程中允许命令直接出现在 Chat 中。

例如：

```bash
spark-sql ...
```

或者：

```sql
SELECT ...
```

这些命令不自动等于正式工程文件。

只有满足以下条件后，才考虑固化成：

- `.sh`
- `.sql`
- `.py`
- `.json`
- `.yaml`

等正式文件：

1. 后续仍需要重复执行；
2. 已经真实验证；
3. 具有稳定工程价值。

临时调试命令无需全部进入仓库。

---

# 7. Handoff Package

每个离线或实时开发阶段完成后，Development Chat 必须生成一次：

**Work Handoff Package**

Handoff 只描述：

> 本阶段新增或发生变化的工程事实。

不重新总结整个项目。

标准内容包括：

```text
01-status.md
02-files.md
03-commands.md
04-evidence.md
05-doc-updates.md
06-next.md
```

---

## Handoff 中必须说明

- 本阶段新增的 VERIFIED；
- 当前 DOING；
- 被替代的旧方案；
- 本阶段真实使用的文件；
- 最终成功命令；
- 最小验收证据；
- Work 需要更新的文件；
- 下一开发入口。

---

# 8. Work Rules

Work 收到 Handoff 后，只处理本次 Handoff 涉及的范围。

Work 不应：

- 主动重新设计目录；
- 根据旧 plan 推断当前开发阶段；
- 修改未涉及的指标；
- 修改未涉及的架构；
- 根据文件名猜测真实用途；
- 创建“理论上应该存在”的文件；
- 把临时验收代码当正式工程代码；
- 因为目录不整齐而进行大规模重构。

发现额外问题时，只记录为：

```text
Deferred Issue
```

不要影响 Development Chat 继续推进项目。

---

# 9. Documentation Rules

不同文档承担不同职责。

## `docs/status/`

维护：

**现在是什么状态。**

---

## `docs/architecture/architecture.md`

维护：

**当前架构是什么。**

应明确区分：

- VERIFIED architecture
- DESIGNED architecture

---

## `docs/business/metrics.md`

维护：

**当前冻结的指标和业务口径。**

只有指标定义真实发生变化时才修改。

---

## `docs/decision-register.md`

维护：

**影响工程方向的重要决策。**

普通开发进展不需要记录。

---

## `docs/plan.md`

旧 Plan 不再作为判断实际开发进度的唯一依据。

如果真实工程路径已经发生变化：

```text
真实 VERIFIED 事实 > 旧 Plan
```

不要为了让旧 Plan 看起来一致而修改真实工程状态。

新的阶段规划可以后续单独形成 Current Plan / Plan V2。

---

# 10. Engineering Assets and Evidence

必须区分两类资产。

## Engineering Assets

未来还会继续运行或维护。

例如：

- SQL
- Shell
- Python
- Java / Flink Job
- DataX Job
- DDL
- YAML
- 配置模板

---

## Evidence Assets

只用于证明某阶段已经成功。

例如：

- Application ID
- Job ID
- Kafka Offset
- COUNT 结果
- Spark SQL 输出
- Doris 查询结果
- Checkpoint 状态
- 验收日志摘要

Evidence 不应混入正式业务代码目录。

---

# 11. Sensitive Information

公开项目仓库不得保存：

- 密码；
- Token；
- AccessKey；
- Secret；
- 私钥；
- 真实认证信息；
- 不适合公开的服务器连接信息。

正式工程需要配置时，使用：

```text
.env.example
*.example.yaml
*.example.conf
${ENV_VAR}
<YOUR_HOST>
<YOUR_PASSWORD>
```

真实 Secret 保留在服务器私有目录，不提交 Git。

---

# 12. Bootstrap

当前项目已经存在历史文件和旧方案，因此第一次启用本 Workflow 时需要先执行一次 Bootstrap。

Bootstrap 目标不是重构项目，而是：

1. Development Chat 分别整理 Offline / Realtime Current Baseline；
2. Development Chat 完成 File Fact Ledger；
3. Work 阅读当前仓库；
4. Work 根据两份 Current Baseline Handoff 对齐：
   - `offline-current.md`
   - `realtime-current.md`
   - `file-baseline.md`
5. 冲突内容保持 UNKNOWN；
6. 不明确的问题进入 Deferred Issues。

Bootstrap 完成后，项目进入正常 Incremental Handoff 模式。

---

# 13. Incremental Workflow

Bootstrap 完成后，每个阶段固定执行：

```text
开发
↓
真实执行
↓
验收
↓
更新 File Fact Ledger
↓
生成 Stage Handoff
↓
Work 更新仓库
↓
更新 Current Status
↓
返回变更摘要
↓
进入 NEXT
```

不再重复重新整理整个项目。

---

# 14. Workflow Prompts

Development Chat 使用：

```text
docs/workflow/chat/
├── offline-current-baseline-handoff-prompt.md
├── realtime-current-baseline-handoff-prompt.md
├── offline-stage-handoff-prompt.md
├── realtime-stage-handoff-prompt.md
└── file-fact-ledger-prompt.md
```

Work 使用：

```text
docs/workflow/work/
└── handoff-receiver-prompt.md
```

这些 Prompt 定义具体操作方式。

本 README 只定义总体协作原则。

---

# 15. Final Principle

本项目始终遵循：

```text
Chat 负责产生工程事实
Work 负责维护工程事实
Status 负责表达当前事实
Git 负责保存历史事实
```

当旧计划、旧文件、历史文档与后续真实工程结果冲突时：

**以后续经过验证的工程事实为准。**

项目管理的目标不是保证历史过程完全整齐，而是保证：

- 当前状态可信；
- 文件来源清楚；
- 下一步明确；
- 开发可以持续推进。
