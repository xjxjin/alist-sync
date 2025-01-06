# Alist-Sync-Web

一个基于 Web 界面的 Alist 存储同步工具，支持多任务管理、定时同步、差异处理等功能。


<div align="center">
  
[![github tag][gitHub-tag-image]][github-url] [![docker pulls][docker-pulls-image]][docker-url] [![docker image size][docker-image-size-image]][docker-url]

[gitHub-tag-image]: https://img.shields.io/github/v/tag/xjxjin/alist-sync
[docker-pulls-image]: https://img.shields.io/docker/pulls/xjxjin/alist-sync
[docker-image-size-image]: https://img.shields.io/docker/image-size/xjxjin/alist-sync
[github-url]: https://github.com/xjxjin/alist-sync
[docker-url]: https://hub.docker.com/r/xjxjin/alist-sync
</div>



## 功能特点

- 📱 美观的 Web 管理界面
- 🔄 支持多任务管理
- ⏰ 支持 Cron 定时任务
- 📂 支持数据同步和文件同步两种模式
- 🗑️ 支持多种差异处理策略（保留/移动到回收站/删除）
- 📝 详细的同步日志记录
- 🔒 支持用户认证和密码管理
- 🐳 支持 Docker 部署




## 快速开始

### Docker 部署（推荐）

1. 创建必要的目录：

```bash
mkdir -p /DATA/AppData/alist-sync-web/data 
```

2. 创建 docker-compose.yml：

```bash
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

3. 启动服务：

```bash
docker-compose up -d
```

4. 访问 Web 界面：

http://localhost:52441

默认登录账号：
- 用户名：admin
- 密码：admin

## 使用说明

### 1. 基础配置

首次使用需要配置 Alist 的基本连接信息：
- 服务地址：Alist 服务的访问地址
- 用户名：Alist 管理员账号
- 密码：Alist 管理员密码

### 2. 同步任务配置

支持两种同步模式：

#### 数据同步模式
- 选择源存储器和目标存储器
- 配置同步目录
- 支持排除目录
- 支持多目标存储同步
- 参照最后图片

#### 文件同步模式
- 手动配置源路径和目标路径
- 支持多个路径对
- 支持排除目录
- 参照最后图片

### 3. 差异处理策略

提供三种差异处理方式：
- 不处理：保留目标目录中的差异文件
- 移动到回收站：将差异文件移动到目标存储的回收站
- 删除：直接删除目标目录中的差异文件
- 移动/删除 在有的存储源会失效欢迎提交Issue，我反馈到 Alist 作者

### 4. 定时任务

- 支持 Cron 表达式配置定时任务
- 可查看未来 5 次执行时间
- 支持立即执行功能

### 5. 日志查看

- 支持查看当前日志
- 支持查看历史日志
- 日志自动按天切割

## 配置文件说明

所有配置文件存储在 `data/config` 目录：
- `base_config.json`：基础连接配置
- `sync_config.json`：同步任务配置
- `users_config.json`：用户认证配置

日志文件存储在 `data/log` 目录：
- `alist_sync.log`：当前日志
- `alist_sync.log.YYYY-MM-DD`：历史日志

## 注意事项

1. 首次使用请修改默认登录密码
2. 建议定期备份配置文件
3. 请确保 Alist 服务正常可访问
4. 建议先测试连接再保存配置
5. 可以通过日志查看同步执行情况

## 更新记录

### v1.0.0
- 初始版本发布
- 支持基础的同步功能
- 支持 Web 界面管理

## 问题反馈

如果您在使用过程中遇到任何问题，请提交 Issue。

## Tips
- 前端页面均为 AI 生成，使用过程中可能有小瑕疵，欢迎前端大神提交代码修复
- 初次使用，保存基础配置后，可以点击添加任务，刷新源存储器和目标存储器下拉列表
- 如果忘记密码，请删除data/config/users_config.json 文件，会默认变成 admin/admin
- 有其他新增功能欢迎提交 Issue。
- 文件同步填写全目录，参照最后面图片
## License

MIT License


## 数据同步

<img src="https://raw.githubusercontent.com/xjxjin/alist-sync/main/static/images/数据同步.png" width="700" alt="数据同步">

## 文件同步
<img src="https://raw.githubusercontent.com/xjxjin/alist-sync/main/static/images/文件同步.png" width="700" alt="文件同步">
