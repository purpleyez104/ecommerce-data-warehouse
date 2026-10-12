# R1 Order DWD first load

Status: historical limited-scope Runtime completed; current cluster state unknown. See [R1 realtime acceptance](../../../../../docs/acceptance/r1-realtime-acceptance.md).

Current repository location: `archive/pilot-v1/realtime/flink/order-dwd-job/`. The commands below preserve the original ECS execution path as historical provenance; they are not current deployment instructions.

The job was built and submitted in the target ECS environment. YARN Application `application_1790055138808_0001` was observed `RUNNING` at 2026-09-22 13:44 Asia/Shanghai, and Doris contained 100 orders (`PAID=69`, `CANCELED=31`, 100 distinct IDs). This is historical evidence, not proof that the application is currently running. The repository contains source and scripts, **not** compiled JARs or credentials.

The following instructions describe the original first-load path. Do not run them against the current non-empty table or an existing checkpoint. Before any retry, inspect the current YARN Application, Flink Job, Checkpoint and Doris state and define a recovery boundary.

Original prerequisites: Doris `ecommerce_serving.dwd_order` was empty; both BEs were Alive; Kafka `ods_cdc_m2_clean_v1` contained the frozen 1,178-message snapshot and live incremental events; the CDC application was running. The build requires Flink 1.20.5, Kafka SQL connector 3.3.0-1.20 and Doris Flink connector 26.1.1 in `/data/module/flink-1.20.5-cdc/lib/`.

On hadoop201:

```bash
unzip -n r1-order-dwd-job.zip -d /data/projects/ecommerce-data-warehouse/flink/jobs/r1/
cd /data/projects/ecommerce-data-warehouse/flink/jobs/r1/r1-order-dwd-job
bash build.sh
bash run.sh
```

Before running check that `yarn application -list -appStates RUNNING` does not show an existing R1 DWD writer. `run.sh` checks empty table and new checkpoint path, but cannot identify other external writers.

Only a current YARN/Flink state plus Doris reconciliation and completed checkpoints can extend the historical acceptance. Do not submit a second copy or reset the job checkpoint after partial writes. On failure, inspect the YARN Application and checkpoint and reconcile Doris before retrying. Flink root Doris access with an empty password is DEVELOPMENT ONLY: restrict FE networking and provision a least-privilege account before exposing the system.

The job accepts `c`,`u`,`r` for `biz_order`, rejects physical deletes and unexpected orders rather than silently dropping them; it ignores CDC for other tables. Sequence is Kafka offset and *only* valid while all `biz_order` events remain on partition 0 and the topic is not recreated. Source starts from earliest for initial load. Doris sink explicitly forces 2PC on with `enable2PC()` (Unique Key may otherwise disable it) and uses a fixed label prefix for a single job lineage. Future failover/restarts must restore from the corresponding checkpoint and must not start a fresh concurrent copy.

After RUNNING and completed checkpoint, inspect:

```bash
mysql --protocol=TCP -h hadoop201 -P 9030 -u root -e "SELECT COUNT(*) AS rows, SUM(order_status='PAID') AS paid, SUM(order_status='CANCELED') AS canceled, COUNT(DISTINCT order_id) AS ids FROM ecommerce_serving.dwd_order;"
```

The historical first load produced rows=100, paid=69, canceled=31, ids=100. The pending row-level comparison is archived at `archive/pilot-v1/realtime/acceptance/check_dwd_order_consistency.sh`. That script is `implemented / not_run` until executed on the target ECS. The first load does not prove `biz_order` UPDATE handling, completed checkpoints or recovery. `event_key=CDC_R1_...` on unrelated `biz_product_change_event` must not appear in `dwd_order`.
