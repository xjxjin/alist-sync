# 使用官方的Python 3.8 Docker镜像作为基础镜像
FROM python:3.12.2-alpine

# 设置工作目录
WORKDIR /app

# 复制当前目录下的文件到工作目录
COPY alist-sync-test.py /app/

# 安装cron和其它可能需要的依赖
RUN apk update && apk add --no-cache cron

# 复制启动脚本
COPY start.sh /app/

# 赋予启动脚本执行权限
RUN chmod +x /app/start.sh

# 通过环境变量传递参数
ENV BASE_URL=""
ENV USERNAME=""
ENV PASSWORD=""
ENV DIR_PAIRS=""
ENV CRON_SCHEDULE="*/5 * * * *"

# 启动服务
CMD ["./start.sh"]
