# 使用 Python 精简版作为基础镜像
FROM python:3.10-slim AS builder

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装构建依赖和项目依赖
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        python3-dev \
        build-essential \
        libssl-dev \
        libffi-dev \
    && pip install --upgrade pip \
    && pip install --no-cache-dir wheel setuptools \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove \
        gcc \
        python3-dev \
        build-essential \
        libssl-dev \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY . .

# 使用精简版运行时镜像
FROM python:3.10-slim

WORKDIR /app

# 复制已安装的依赖和项目文件
COPY --from=builder /usr/local/lib/python3.10/site-packages/ /usr/local/lib/python3.10/site-packages/
COPY --from=builder /app /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1

# 暴露端口
EXPOSE 52441

# 修改启动命令，使用正确的文件名
CMD ["python", "alist-sync-web.py"]