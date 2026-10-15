# 电商离线实时一体化数仓工程基线

> Status: CONFIRMED\
> Purpose: 后续业务源开发、数据生成、ETL、实时链路建设唯一工程依据

本文件固定总体技术路线和已确认的部署方式；业务规则、指标口径、21 表字段、Milestone 门禁及完整交付顺序分别以 [业务基线](../business/business-baseline.md)、[指标口径](../business/metrics.md)、[源模型](../source/physical-model.md)、[阶段计划](../plan.md)和[Project 1 完整交付整改方案](../design/project1-completion-remediation-plan.md)为准。`CONFIRMED` 不等于正式业务链路已验收。BI、Dashboard、SQL Assistant、LLM/Agent 和 Project 2 实现不属于当前 Project 1 范围。

------------------------------------------------------------------------

# 1. 项目定位

构建标准自营商城模式电商数仓，覆盖：

-   交易分析
-   流量分析
-   用户分析
-   商品分析
-   退款售后分析
-   营销分析

支持：

-   T+1 离线分析
-   分钟级实时分析
-   轻量 Data Governance
-   可复现验收与简历证据

------------------------------------------------------------------------

# 2. 总体架构

``` text
模拟电商业务系统
        |
    MySQL 8.0.46
        |
-------------------------
|                       |
离线链路              实时链路
|                       |
DataX               MySQL Binlog
|                       |
HDFS                Flink CDC
|                       |
Hive                Kafka
|                       |
Spark SQL           Flink Application
        \             /
             Doris

MySQL / Hive / Doris + SQL / Config / Task Result
               |
 Metadata / Table Lineage / Metric Registry
```

------------------------------------------------------------------------

# 3. 技术栈版本

  组件              版本           状态
  ----------------- -------------- -----------
  OS                Ubuntu 24.04   Confirmed
  Java              17.0.20        Confirmed
  Hadoop            3.4.1          Confirmed
  YARN              3.4.1          Confirmed
  MySQL             8.0.46         Confirmed
  Kafka             3.9.1 KRaft    Confirmed
  Flink             1.20.5         Confirmed
  Flink CDC         3.6.0-1.20     Confirmed
  Doris             4.0.8          Confirmed
  Doris Connector   26.1.1         Confirmed

------------------------------------------------------------------------

# 4. Flink运行方案

## 最终方案

采用：

``` text
Flink Application Mode
+
DataStream API
+
Java Jar
```

原因：

-   生命周期清晰
-   与YARN资源管理结合
-   更接近正式实时任务部署方式

## 测试方案

保留：

``` text
Flink SQL Client + YARN Session
```

用于 Kafka SQL 验证。

不作为正式生产任务部署方式。

------------------------------------------------------------------------

# 5. 实时链路

## CDC链路

``` text
MySQL
 |
Binlog
 |
Flink CDC 3.6
 |
Kafka Raw CDC Topic
```

事件格式：

``` text
Debezium JSON
```

支持：

-   Snapshot
-   INSERT
-   UPDATE
-   DELETE

------------------------------------------------------------------------

# 6. Kafka设计

当前验证：

``` text
按表 Topic
```

示例：

``` text
ods_cdc_xxx
```

格式：

``` json
{
 "before": {},
 "after": {},
 "op": "u",
 "source": {}
}
```

正式Topic规划在实时模型阶段确定。

------------------------------------------------------------------------

# 7. Doris Serving层

部署：

``` text
hadoop201
  FE

hadoop202
  BE

hadoop203
  BE
```

定位：

-   ADS查询服务
-   BI展示
-   实时结果查询

不替代Hive。

------------------------------------------------------------------------

# 8. Flink Doris方案

正式方案：

``` text
Flink DataStream
        |
Doris Connector 26.1.1
        |
Doris 4.0.8
```

验证能力：

-   INSERT
-   Upsert
-   Checkpoint
-   TaskManager Recovery
-   Schema兼容

------------------------------------------------------------------------

# 9. Java策略

  组件             Java版本
  ---------------- ----------------
  Hadoop/YARN      Java 11
  Hive             当前 Runtime 为 Java 17；Java 11 切换未验证
  Flink Client     Java 17
  Flink User Jar   target Java 11
  Doris            Java 17

原则：

保持 Hadoop 生态稳定，不为了 Flink 修改全局 JDK。Hadoop/YARN 守护进程使用 Java 11；Hive 3.1.3 在当前 Java 17 环境中已通过验收，不把设计偏好改写为运行事实。

------------------------------------------------------------------------

# 10. 已完成工程验证

## Step 8

状态：

``` text
CONFIRMED
```

验证：

-   Flink on YARN
-   Application Mode
-   HDFS读写
-   WordCount

## Step 9

状态：

``` text
CONFIRMED
```

验证：

-   MySQL Binlog
-   Flink CDC
-   Kafka Raw Topic
-   Snapshot/INSERT/UPDATE/DELETE

## Step 10

状态：

``` text
CONFIRMED_WITH_NOTE
```

验证：

-   Kafka Source
-   Flink SQL处理
-   Kafka Sink

备注：

未验证Exactly Once。

## Step 11

状态：

``` text
CONFIRMED
```

验证：

-   FE启动
-   BE注册
-   SQL查询
-   聚合计算
-   受控重启与 FE/BE 恢复

此处采用已确认的 Step 11 Runtime 结论；不代表正式 Doris 业务服务表或端到端实时链路通过。

## Step 12

状态：

``` text
CONFIRMED
```

验证：

-   Flink Doris Connector
-   Kafka→Flink→Doris
-   Checkpoint
-   Recovery
-   Upsert

------------------------------------------------------------------------

# 11. 后续开发阶段

## Phase 1 数据源设计

-   创建业务源模型
-   生成90天历史数据
-   模拟交易事件

## Phase 2 离线数仓

-   DataX同步
-   Hive ODS
-   DWD/DIM/DWS/ADS

## Phase 3 实时数仓

-   CDC接入
-   Kafka Topic设计
-   Flink实时计算
-   Doris实时表

## Phase 4 治理与交付证据

-   Metadata Snapshot
-   Table-level Lineage
-   Metric Registry
-   数据质量、对账与任务结果关联
-   Evidence Index 与简历结论映射

------------------------------------------------------------------------

# Final Architecture

``` text
                    MySQL
                      |
          +-----------+-----------+
          |                       |
        DataX                   Binlog
          |                       |
      HDFS / Hive              Flink CDC
          |                       |
      Spark SQL                 Kafka
          |                       |
   ODS → DWD → DWS → ADS         Flink
          |                       |
          |                       |
     Spark-Doris             Flink-Doris
      Connector               Connector
          |                       |
          +----------+------------+
                     |
                   Doris

       MySQL / Hive / Doris Runtime
       SQL / Config / Task Result
                     |
      Metadata / Lineage / Metric Registry
```

后续开发必须基于该版本；涉及基础架构的变化必须进入 Decision Register 并重新确认。轻量 Data Governance 不得演变为独立平台或 AI 应用。
