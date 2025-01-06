# 使用 Python Alpine 作为构建镜像
FROM python:3.10-alpine AS builder

# 设置工作目录
WORKDIR /app

# 安装构建依赖
RUN apk add --no-cache \
    gcc \
    musl-dev \
    python3-dev \
    libffi-dev \
    openssl-dev

# 复制依赖文件
COPY requirements.txt .

# 安装依赖到指定目录
RUN pip install --no-cache-dir -r requirements.txt --target=/install

# 使用更小的运行时镜像
FROM python:3.10-alpine

# 设置工作目录
WORKDIR /app

# 复制安装的依赖
COPY --from=builder /install /usr/local/lib/python3.10/site-packages

# 只复制必要的项目文件
COPY alist-sync-web.py alist_sync.py ./
COPY static ./static
COPY templates ./templates

# 创建必要的目录
RUN mkdir -p /app/data/config /app/data/log && \
    # 设置权限
    chmod -R 755 /app/data && \
    # 清理不必要的文件
    find /usr/local/lib/python3.10/site-packages -name "*.pyc" -delete && \
    find /usr/local/lib/python3.10/site-packages -name "__pycache__" -exec rm -r {} + && \
    # 删除测试文件和文档
    find /usr/local/lib/python3.10/site-packages -name "tests" -type d -exec rm -r {} + && \
    find /usr/local/lib/python3.10/site-packages -name "*.txt" -delete && \
    find /usr/local/lib/python3.10/site-packages -name "*.md" -delete

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app:$PATH"

# 暴露端口
EXPOSE 52441

# 设置启动命令
CMD ["python", "alist-sync-web.py"]