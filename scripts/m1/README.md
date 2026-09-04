# Milestone 1 运行入口

这些脚本必须在目标 Ubuntu ECS 上由 `yee` 执行。当前 Windows 工作区不提供 Bash 运行证明；脚本只有在目标集群执行并核对结果后才能视为通过。

## 第一门禁：Hadoop 非中断验证

在 `hadoop201` 的仓库根目录执行：

```bash
bash scripts/m1/collect-hadoop-evidence.sh \
  --run-id m1-hadoop-20260904-01 \
  --output-dir /data/logs/ecommerce-data-warehouse/m1/m1-hadoop-20260904-01
```

固定输入：

```text
alpha beta beta
gamma alpha
```

预期 `wordcount`：

```text
alpha 2
beta 2
gamma 1
```

成功条件：

- 当前用户为 `yee`，当前节点为 `hadoop201`。
- 三节点可通过免密 SSH 访问，主机名与目标一致。
- Hadoop 版本、进程、HDFS report 和 YARN 节点信息成功采集。
- HDFS 上传后 SHA-256 与本地固定文件一致。
- MapReduce 作业退出状态为 0，结果与固定预期一致。
- 找到 YARN application ID 并保存聚合日志。
- 脚本只删除自己创建的 `/tmp/ecommerce_data_warehouse/m1/<run-id>`。

结果位置：`--output-dir` 指定目录。`summary.env` 中 `status=PASS` 且脚本退出状态为 0 才表示本门禁通过。

## 第二门禁：受控重启验证

仅在第一门禁结果完成评审后执行：

```bash
bash scripts/m1/restart-hadoop-and-verify.sh \
  --run-id m1-hadoop-restart-20260904-01 \
  --output-dir /data/logs/ecommerce-data-warehouse/m1/m1-hadoop-restart-20260904-01 \
  --confirm-restart EXISTING_HADOOP_CLUSTER
```

该脚本会停止并重新启动现有 HDFS、YARN 和 JobHistoryServer。确认参数不完全匹配时脚本返回非零且不改变服务。

成功条件：

- 重启前创建的 HDFS 固定文件在重启后仍可读取且 SHA-256 一致。
- HDFS 恢复 2 个 Live DataNode。
- YARN 恢复 2 个 RUNNING NodeManager。
- `hadoop201` 恢复 NameNode、SecondaryNameNode、ResourceManager 和 JobHistoryServer。
- 脚本退出状态为 0，`summary.env` 为 `status=PASS`。

## 失败处理

- 不执行 NameNode 格式化，不删除现有 Hadoop 数据或配置。
- 保留输出目录中的日志和 `summary.env`。
- 将失败命令、退出状态和日志路径记录到 `docs/installation-troubleshooting.md`。
- 在当前门禁修复并重新验证前，不进入 MySQL 安装。
