#!/bin/bash

# start.sh

# 检查是否提供了必要的环境变量
if [ -z "$BASE_URL" ] || [ -z "$USERNAME" ] || [ -z "$PASSWORD" ] || [ -z "$DIR_PAIRS" ] || [ -z "$CRON_SCHEDULE" ]; then
    echo "Error: Missing one of the required environment variables."
    exit 1
fi

# 使用环境变量CRON_SCHEDULE创建crontab条目
/usr/local/bin/python3 /app/alist-sync-test.py --base_url \"$BASE_URL\" --username \"$USERNAME\" --password \"$PASSWORD\" --dir_pairs \"$DIR_PAIRS\" --cron_schedule \"$CRON_SCHEDULE\"
