# DataX Job 发现入口

本目录保存不含 Secret、可审计的 DataX job 导出。正式运行仍由 `datax/scripts/run_ods_batch.py` 在私有 Runtime 中生成 job，并在子进程启动前临时注入凭据；包含密码的临时文件使用 `0600` 权限并在子进程结束后删除。

目录约定：

```text
datax/jobs/<batch_id>/
├── job_manifest.json
└── <source_table>_<batch_id>.json
```

仓库中的 JSON 只能包含 `${MYSQL_JDBC_URL}`、`${MYSQL_USER}`、`${MYSQL_PASSWORD}` 和 `${HDFS_DEFAULT_FS}` 占位符。`job_manifest.json` 绑定 Batch、Dataset、21 个 job 文件及 SHA-256；运行事实以私有 Runtime 的 `state.json`、日志和独立 ODS Gate 为准，仓库文件存在本身不代表 `VERIFIED`。
