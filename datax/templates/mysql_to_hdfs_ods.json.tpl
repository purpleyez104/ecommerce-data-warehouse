{
  "job": {
    "setting": {"speed": {"channel": 1}},
    "content": [
      {
        "reader": {
          "name": "mysqlreader",
          "parameter": {
            "username": "${MYSQL_USER}",
            "password": "${MYSQL_PASSWORD}",
            "connection": [{"jdbcUrl": ["${MYSQL_JDBC_URL}"], "querySql": ["${QUERY_SQL}"]}]
          }
        },
        "writer": {
          "name": "hdfswriter",
          "parameter": {
            "defaultFS": "${HDFS_DEFAULT_FS}",
            "path": "${OUTPUT_PATH}",
            "fileName": "${FILE_NAME}",
            "fileType": "orc",
            "compress": "SNAPPY",
            "fieldDelimiter": "\u0001",
            "writeMode": "nonConflict",
            "column": ${WRITER_COLUMNS}
          }
        }
      }
    ]
  }
}
