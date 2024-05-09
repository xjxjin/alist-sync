#!/bin/bash

# start.sh

# 检查是否提供了必要的环境变量
if [ -z "$BASE_URL" ] || [ -z "$USERNAME" ] || [ -z "$PASSWORD" ] || [ -z "$DIR_PAIRS" ]; then
    echo "Error: Missing one of the required environment variables."
    exit 1
fi

# 使用环境变量CRON_SCHEDULE创建crontab条目
CRON_LINE="$CRON_SCHEDULE /usr/local/bin/python3 /app/alist-sync.py --base_url \"$BASE_URL\" --username \"$USERNAME\" --password \"$PASSWORD\" --dir_pairs \"$DIR_PAIRS\""
echo $CRON_LINE | crontab -

# 启动cron服务
cron -f
