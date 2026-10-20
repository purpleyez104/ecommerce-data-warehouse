# M1 DolphinScheduler MySQL JDBC Registry 验收

日期：2026-10-19  
状态：`VERIFIED`

## 环境与 Contract

- DolphinScheduler：3.4.2，OpenJDK 17。
- Registry：MySQL JDBC Registry，决策见 `DR-049`。
- Metadata：MySQL 8.0.46，`dolphinscheduler` Schema 共 64 张表。
- 控制节点：`hadoop201` 运行 Master、API、Alert。
- 执行节点：`hadoop202`、`hadoop203` 各运行一个 Worker。
- 三节点 `dolphinscheduler_env.sh` SHA-256 一致：`4701180bc497d54c7d9b8b1de27ac457a786f7dee3a240da858cad2baf72c5cb`。

## Acceptance → Evidence

| Acceptance | 实际证据 | 结果 |
| --- | --- | --- |
| JDBC Registry 可用 | `dolphinscheduler-registry-jdbc-3.4.2.jar` 存在；四张 JDBC Registry 表可查询 | `VERIFIED` |
| 五个角色注册 | 5 条 Client Heartbeat、10 条 Registry Data | `VERIFIED` |
| API 健康 | `/dolphinscheduler/actuator/health` 返回 HTTP 200 | `VERIFIED` |
| 成功任务 | Workflow `187355051058912`，实例 `6` 为 `SUCCESS` | `VERIFIED` |
| 失败任务不误报成功 | Workflow `187355051288288`，实例 `7` 为 `FAILURE`，Shell 固定退出 `17` | `VERIFIED` |
| 受控重启恢复 | 五个角色重启后 API 200，Registry 重新注册 | `VERIFIED` |
| 重启后复跑 | 相同 Project/Workflow Code 的实例 `8=SUCCESS`、`9=FAILURE` | `VERIFIED` |

固定 Project Code 为 `187355050810080`。API、Task 和服务日志保留在目标集群；仓库不保存 Cookie、Token、密码或原始运行日志。

## 限制与安全项

- JDBC Registry 与 Metadata 共用 MySQL，是开发环境接受的单点依赖，不代表生产级 HA。
- 初始化管理员仍使用默认凭据；已确认需要后续轮换，但账号修改必须单独授权，当前没有执行。
- 本验收不证明 M6 正式 T+1 DAG、失败重试、连续补数、质量阻断或 Doris 对账已经接入 DolphinScheduler。
- 回滚只停止 DolphinScheduler 角色；不得删除 Metadata Schema、Registry 表或任务历史。
