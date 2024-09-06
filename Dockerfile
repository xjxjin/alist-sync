# 使用官方的Python 3.12.2 Docker镜像作为基础镜像
FROM python:3.12.2-alpine

# 设置工作目录
WORKDIR /app

# 复制当前目录下的文件到工作目录
COPY alist-sync.py /app/

# 安装cron和其它可能需要的依赖
# RUN apk update && apk add --no-cache cron
RUN pip install --no-cache-dir apscheduler==3.10.4


# 通过环境变量传递参数
ENV BASE_URL=""
ENV USERNAME=""
ENV PASSWORD=""
ENV DIR_PAIRS=""
ENV CRON_SCHEDULE=""
ENV SYNC_DELETE_ACTION="none"
ENV TRASH_FOLDER=""

# 启动服务
# CMD ["python", "./alist-sync.py", "--base_url", "$BASE_URL", "--username", "$USERNAME", "--password", "$PASSWORD", "--dir_pairs", "$DIR_PAIRS", "--cron_schedule", "$CRON_SCHEDULE"]
# CMD ["python", "./alist-sync.py", "$1", "$2", "$3", "$4", "$5", "$6", "$7"]
# CMD ["python", "./alist-sync.py", "--cron_schedule", "${CRON_SCHEDULE}", "--base_url", "${BASE_URL}", "--username", "${USERNAME}", "--password", "${PASSWORD}", "--dir_pairs", "${DIR_PAIRS}"]
CMD ["python", "./alist-sync.py"]
