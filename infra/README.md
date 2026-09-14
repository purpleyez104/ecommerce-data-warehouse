# Milestone 1 基础设施配置

本目录保存当前项目可维护、可去敏和可复现的基础设施配置。目录存在表示 Milestone 1 已开始，不表示所有组件已经安装或验证。

当前内容：

- `hosts.example`：三节点私网主机名基线。
- `ports.md`：已确认和已决策的端口边界。

2026-09-14 已按 `DR-026` 接受 Step 2～12 Runtime 验收基线：Hadoop、MySQL、Hive、Spark、DataX、Kafka、Flink、Flink CDC、Flink Kafka source/sink、Doris 和 Flink Doris Connector 已证明支持后续工作；当前 M1 仅剩 DolphinScheduler 3.4.2。结论已同步到 `docs/cluster-baseline.md` 和 `docs/compatibility-matrix.md`；原始输出继续保存在 Git 忽略的 `.local-notes/m1-evidence/inbox/`。

后续只有在确有维护需求且内容已去敏时，才加入组件配置模板。DolphinScheduler 通过、Milestone 1 全部组件真实验证完成前，不创建 `versions.env`。

禁止提交：

- 密码、私钥、Token 和 `.env`。
- `hadoop201` 公网 IP、管理员公网出口 IP和阿里云资源 ID。
- 数据盘 UUID、真实证书和渲染后的秘密配置。
- 原始运行日志。
