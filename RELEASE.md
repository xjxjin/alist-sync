## Docker 部署
```bash
docker pull ${DOCKER_IMAGE}:${VERSION}
```

或使用 docker-compose:
```yaml
version: '3'
services:
  alist-sync-web:
    image: ${DOCKER_IMAGE}:${VERSION}
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
${PLATFORMS} 