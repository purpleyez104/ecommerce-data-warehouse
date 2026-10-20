# Milestone 1 基础设施配置

本目录保存当前项目可维护、可去敏和可复现的基础设施配置。目录存在表示 Milestone 1 已开始，不表示所有组件已经安装或验证。

当前内容：

- `hosts.example`：三节点私网主机名基线。
- `ports.md`：已确认和已决策的端口边界。

2026-10-19 已按 `DR-049` 完成 DolphinScheduler 3.4.2 + MySQL JDBC Registry 的成功/失败任务与受控重启验收，M1 组件门禁闭合。结论已同步到 `docs/cluster-baseline.md`、`docs/compatibility-matrix.md` 和 `docs/acceptance/m1-dolphinscheduler-jdbc-acceptance.md`；原始输出继续保存在 Git 忽略的本地或 ECS 日志目录。

后续只有在确有维护需求且内容已去敏时，才加入组件配置模板。`versions.env` 仍须在最终版本清单完成去敏复核后单独生成。

禁止提交：

- 密码、私钥、Token 和 `.env`。
- `hadoop201` 公网 IP、管理员公网出口 IP和阿里云资源 ID。
- 数据盘 UUID、真实证书和渲染后的秘密配置。
- 原始运行日志。
