# 部署说明

本文档是部署、环境和兼容性资料的导航入口，不替代组件级安装与验收记录。

## 当前部署入口

- [部署拓扑](topology.md)：三节点角色、资源、Java 和安全边界。
- [集群事实基线](cluster-baseline.md)：ECS、网络、磁盘、用户和 Hadoop 当前事实。
- [组件兼容性矩阵](compatibility-matrix.md)：精确版本、兼容依据和验收状态。
- [安装与排障记录](troubleshooting.md)：实际问题、修复、复测和回滚。
- [工程架构基线](../architecture/baseline.md)：总体技术路线与历史技术验收边界。

## 状态边界

Milestone 1 已完成。DolphinScheduler 3.4.2 + MySQL JDBC Registry 已通过成功/失败任务与受控重启复跑；M6 Aggregate Backfill Instance `17` 已完成 Model Ready、DWS/ADS、Quality、Doris 与 Reconciliation，质量失败 Instance `18` 已验证 Quality 非零失败、Doris/Reconciliation 下游阻断及服务数据不变，M6 Stage Gate 已完成。目录存在、配置示例或静态检查不等于 Runtime 已验证，运行结论必须以记录环境中的命令、退出状态和结果核对为准。
