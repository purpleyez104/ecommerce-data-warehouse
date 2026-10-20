# 部署说明

本文档是部署、环境和兼容性资料的导航入口，不替代组件级安装与验收记录。

## 当前部署入口

- [部署拓扑](deployment-topology.md)：三节点角色、资源、Java 和安全边界。
- [集群事实基线](cluster-baseline.md)：ECS、网络、磁盘、用户和 Hadoop 当前事实。
- [组件兼容性矩阵](compatibility-matrix.md)：精确版本、兼容依据和验收状态。
- [安装与排障记录](installation-troubleshooting.md)：实际问题、修复、复测和回滚。
- [最终工程架构 V1.0](architecture/final-architecture.md)：总体技术路线与历史技术验收边界。

## 状态边界

Milestone 1 已完成。DolphinScheduler 3.4.2 + MySQL JDBC Registry 已通过成功/失败任务与受控重启复跑；M6 正式 DAG 已证明一次自动重试及失败阻断，Aggregate Backfill 已通过 Model Ready、DWS/ADS 与 Quality。当前 Doris `frame.count()` EOF、调度后对账和质量失败注入仍待验证。目录存在、配置示例或静态检查不等于 Runtime 已验证，运行结论必须以记录环境中的命令、退出状态和结果核对为准。
