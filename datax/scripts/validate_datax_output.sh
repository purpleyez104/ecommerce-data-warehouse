#!/bin/bash

set -euo pipefail


if [ $# -ne 1 ]
then
    echo "Usage:"
    echo "$0 <hdfs_path>"
    exit 1
fi


TARGET=$1


echo "Checking:"
echo ${TARGET}


if ! hdfs dfs -test -d ${TARGET}
then
    echo "ERROR: path not exists"
    exit 1
fi


COUNT=$(

hdfs dfs -ls ${TARGET} |
awk '$1 ~ /^-/ {count++} END {print count+0}'

)


SIZE=$(

hdfs dfs -du -s -h ${TARGET}

)


echo "files=${COUNT}"
echo "size=${SIZE}"


if [ ${COUNT} -eq 0 ]
then
    echo "ERROR: empty output"
    exit 1
fi


echo "OUTPUT CHECK PASS"
