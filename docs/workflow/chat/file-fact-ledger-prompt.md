现在暂停继续开发。

当前这个 Chat 中已经出现过大量 SQL、Shell、Python、JSON、YAML、Markdown、配置文件和临时命令，但其中存在以下问题：

- 文件名模糊
- 文件路径不明确
- 同一功能存在多个版本
- 有些只是聊天代码，没有真正形成文件
- 有些由 Chat 生成过附件
- 有些由我按照命令在服务器创建
- 有些实际执行过
- 有些已经被新版替代
- 有些只讨论过但没有落地

现在请对**本对话自身的完整历史**做一次“文件事实审计”。

这次任务不是整理仓库，不是生成新文件，不是重命名，不是重新规划。

唯一目标是建立：

# FILE FACT LEDGER

即：这个 Chat 到目前为止到底真实涉及过哪些文件，以及我们对这些文件究竟知道什么。

---

# 一、严格区分文件事实等级

每个文件只能属于以下状态之一。

## F1 — VERIFIED_EXECUTED

能够从本对话明确确认：

- 文件真实存在过；
- 并且我实际执行/调用过；
- 有运行结果或验收结果支持。

这是最高可信等级。

---

## F2 — CONFIRMED_CREATED

能够确认文件真实被创建过，例如：

- Chat 实际生成并提供附件；
- 我明确执行了 `cat > file` / `nano file` / `vim file` 等创建操作；
- 本对话明确显示 `ls` / `cat` / `chmod` / 路径输出证明文件存在。

但是无法确认它已经成功执行。

---

## F3 — CHAT_GENERATED

Chat 曾经明确给出一个完整文件内容，或者生成过一个文件方案，但无法确认我是否真正保存到了服务器/项目目录。

必须和真实工程文件区分。

---

## F4 — MENTIONED_ONLY

只在设计、目录规划、命令示例或讨论中出现过文件名。

没有证据证明这个文件真正存在。

---

## F5 — SUPERSEDED

文件曾经真实存在或使用，但已经明确被更新版本、后续实现或最终方案替代。

必须指出：

`SUPERSEDED BY: <新文件/新方案>`

如果不知道新文件名，写 UNKNOWN。

---

## F6 — UNKNOWN

知道某个文件可能存在，但以下至少一项无法确认：

- 文件名
- 路径
- 内容
- 是否创建
- 是否执行
- 当前是否仍有效

禁止猜测补全。

---

# 二、逐条回溯本 Chat 的文件

请扫描本对话中所有明确出现过的：

- `.sql`
- `.sh`
- `.py`
- `.json`
- `.yaml`
- `.yml`
- `.conf`
- `.properties`
- `.env`
- `.md`
- `.xml`
- Java/Flink Job 工程
- DataX Job
- 验收脚本
- 配置文件
- README / docs
- 其他真实工程文件

不要只根据当前记忆总结。

需要根据本 Chat 中实际出现过的文件名、命令和执行记录判断。

---

# 三、建立 File Fact Ledger

按以下表格输出：

| Fact ID | 文件名 | 文件类型 | 状态 | 当前已知真实路径 | Chat 中的用途 | 是否真实创建 | 是否真实执行 | 是否成功 | 当前是否有效 | 后继版本 | 证据说明 |
|---|---|---|---|---|---|---|---|---|---|---|---|

Fact ID 使用：

`FILE-001`
`FILE-002`
……

---

# 四、路径必须严格处理

对于路径：

### 已明确出现完整路径

直接记录，例如：

`/data/projects/ecommerce-data-warehouse/...`

### 只知道文件名，不知道路径

写：

`PATH UNKNOWN`

### Chat 曾经建议一个仓库位置，但实际文件还在其他地方

必须区分：

`ACTUAL PATH`

和

`PROPOSED REPO PATH`

不要把建议路径冒充当前真实路径。

因此另外增加一张表：

| Fact ID | Actual Path | Proposed Repo Path | Path Confidence |
|---|---|---|---|

Path Confidence：

- HIGH
- MEDIUM
- LOW
- UNKNOWN

---

# 五、处理同名和模糊文件

重点搜索类似：

- `test.sql`
- `verify.sql`
- `run.sh`
- `check.sh`
- `job.sql`
- `config.yaml`
- `xxx-final.sql`
- `xxx-v2.sql`
- 没有清晰业务含义的文件

如果存在多个同名/近似文件：

不要自动合并。

建立：

## Ambiguous Files

| 名称 | 可能对应的文件 | 为什么无法区分 | 需要以后怎么确认 |
|---|---|---|---|

---

# 六、区分“文件”和“聊天命令”

例如本 Chat 中可能直接出现：

```bash
spark-sql ...
```

或者：

```sql
SELECT ...
```

但并没有形成文件。

这种内容不要放入 File Fact Ledger。

单独建立：

# CHAT-ONLY COMMANDS

表格：

| Command ID | 类型 | 用途 | 是否执行成功 | 是否值得固化成文件 | 建议文件名 | 建议位置 |
|---|---|---|---|---|---|---|

注意：

“建议文件名”只是 Proposal，不代表文件已存在。

---

# 七、区分正式工程文件和验收资产

对于 F1/F2 文件，再分类：

## ENGINEERING

未来还会继续执行或维护，例如：

- DataX Job
- Flink Job
- DDL
- ETL SQL
- 启动脚本
- 业务 SQL
- 配置模板

## ACCEPTANCE

主要用于：

- 验收
- 环境检查
- COUNT
- Topic 验证
- Connector 测试
- Smoke Test

## TEMP

一次性临时调试。

## DOC

设计/说明文档。

增加字段：

`Asset Type = ENGINEERING / ACCEPTANCE / TEMP / DOC`

---

# 八、识别最终有效版本

对同一功能存在多个版本时，例如：

`old.sh`
`new.sh`
`final.sh`

不要根据文件名里的 `final` 判断。

必须根据后续执行成功记录判断哪个是真正最终版本。

生成：

# FUNCTION → CURRENT FILE MAP

例如：

| 功能 | 当前可信文件 | Fact ID | 状态 | 旧版本 |
|---|---|---|---|---|

这张表非常重要。

目标是回答：

“以后如果我要执行这个功能，我究竟应该使用哪个文件？”

如果不能确认，明确写：

`CURRENT FILE UNKNOWN`

---

# 九、生成 Cleanup Candidates

这里只提出建议，不执行。

分为：

## KEEP

已经确认有效，应继续使用。

## REPO-CANDIDATE

真实存在/执行过，适合以后收入正式仓库。

## NEEDS-VERIFY

疑似有价值，但需要重新在服务器确认。

## HISTORY

已经被替代。

## DISCARD-CANDIDATE

明确属于临时调试且没有长期价值。

禁止直接删除。

---

# 十、生成最重要的 Server Verification List

对于所有影响当前开发，但文件事实仍不清楚的内容，生成一组**最少量 Linux 查询命令**，让我之后可以在服务器执行确认。

例如只在确实需要时使用：

```bash
find ...
ls -l ...
readlink -f ...
stat ...
sha256sum ...
grep ...
```

要求：

- 查询必须安全；
- 不修改文件；
- 不删除文件；
- 不移动文件；
- 尽量一次查询多个目标；
- 不做全盘无意义扫描；
- 优先限定：

`/data/projects/ecommerce-data-warehouse`

以及本 Chat 已知相关目录。

输出：

# SERVER VERIFICATION COMMANDS

并明确每条命令是在确认哪个 FILE Fact。

---

# 十一、输出最终 File Baseline

最后给出一个非常简洁的：

# FILE BASELINE

只包含当前继续开发真正需要知道的内容。

格式：

## 当前正式工程文件

`功能 → 文件 → 路径 → 状态`

## 当前验收文件

`功能 → 文件 → 路径 → 状态`

## 文件事实仍不清楚

列出必须以后确认的项目。

## 已停止使用

列出重要 superseded 文件。

---

# 十二、禁止行为

本次禁止：

- 生成新文件；
- 重写旧文件；
- 为模糊文件擅自起新名字；
- 根据项目目录规划反推文件一定存在；
- 根据记忆把“可能执行过”写成执行过；
- 根据旧 plan 判断文件状态；
- 为了完整而虚构路径；
- 把聊天代码块自动视为文件；
- 把建议仓库路径视为真实路径；
- 大规模规划目录结构。

如果无法确认，使用 UNKNOWN。

准确比完整重要。

---

完成之后，这份 File Fact Ledger 将成为本 Chat 后续唯一的文件事实来源。

以后每次阶段完成时：

1. 先更新 File Fact Ledger；
2. 再生成 Work Handoff Package；
3. Work 只接收 Ledger 中能够确认的文件事实。

不要再直接根据聊天印象给 Work 文件清单。
