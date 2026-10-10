{
  "job": {
    "setting": {
      "speed": {
        "channel": 1
      }
    },

    "content": [
      {
        "reader": {
          "name": "mysqlreader",

          "parameter": {

            "username": "${MYSQL_USER}",

            "password": "${MYSQL_PASSWORD}",

            "connection": [
              {
                "jdbcUrl": [
                  "${MYSQL_JDBC_URL}"
                ],

                "querySql": [
                  "${QUERY_SQL}"
                ]
              }
            ]
          }
        },


        "writer": {

          "name": "hdfswriter",

          "parameter": {

            "defaultFS": "${HDFS_DEFAULT_FS}",

            "path": "${OUTPUT_PATH}",

            "fileName": "${FILE_NAME}",

            "fileType": "orc",

            "column": [
              {
                "name":"order_id",
                "type":"long"
              },
              {
                "name":"order_no",
                "type":"string"
              },
              {
                "name":"user_id",
                "type":"long"
              },
              {
                "name":"visitor_id",
                "type":"long"
              },
              {
                "name":"coupon_id",
                "type":"long"
              },
              {
                "name":"order_status",
                "type":"string"
              },
              {
                "name":"gross_amount_cents",
                "type":"long"
              },
              {
                "name":"discount_amount_cents",
                "type":"long"
              },
              {
                "name":"payable_amount_cents",
                "type":"long"
              },
              {
                "name":"created_at",
                "type":"string"
              },
              {
                "name":"payment_deadline_at",
                "type":"string"
              },
              {
                "name":"paid_at",
                "type":"string"
              },
              {
                "name":"canceled_at",
                "type":"string"
              },
              {
                "name":"updated_at",
                "type":"string"
              }
            ]
          }
        }
      }
    ]
  }
}
