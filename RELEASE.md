## Docker 部署
```bash
docker pull xjxjin/alist-sync:latest
```

或使用 docker-compose:
```yaml
version: '3'
services:
  alist-sync-web:
    image: xjxjin/alist-sync:latest
    container_name: alist-sync-web
    restart: unless-stopped
    ports:
      - "52441:52441"
    volumes:
      - /DATA/AppData/alist-sync-web/data:/app/data
    environment:
      - TZ=Asia/Shanghai
```

## 支持的平台
- linux/386
- linux/amd64
- linux/arm/v6
- linux/arm/v7
- linux/arm64
- linux/ppc64le
- linux/s390x 