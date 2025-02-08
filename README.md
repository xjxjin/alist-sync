# Alist-Sync

一个基于 Web 界面的 Alist 存储同步工具，支持多任务管理、定时同步、差异处理等功能。

<div align="center">
  
[![github tag][gitHub-tag-image]][github-url] [![docker pulls][docker-pulls-image]][docker-url] [![docker image size][docker-image-size-image]][docker-url]  
**如果好用，请Star！非常感谢！**  [GitHub](https://github.com/xjxjin/alist-sync) [Gitee](https://gitee.com/xjxjin/alist-sync) [DockerHub](https://hub.docker.com/r/xjxjin/alist-sync)
---

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
- 🐉 支持青龙面板定时任务





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
    image: xjxjin/alist-sync:1.1.2
    container_name: alist-sync
    restart: unless-stopped
    ports:
      - "52441:52441"
    volumes:
      - /DATA/AppData/alist-sync/data:/app/data
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
- 令牌：Alist 令牌

### 2. 同步任务配置

支持两种同步模式：

#### 数据同步模式
- 各个网盘之间同目录数据备份
- 选择源存储器和目标存储器
- 配置同步目录
- 支持排除目录
- 支持多目标存储同步
- 参照最后图片

#### 文件同步模式
- 需要填写全路径
- 手动配置源路径和目标路径
- 支持多个路径对
- 支持排除目录
- 参照最后图片

#### 文件移动模式
- 需要填写全路径
- 手动配置源路径和目标路径
- 支持多个路径对
- 支持排除目录
- 注：文件移动实现方式是先复制到目标路径，然后在下次自动执行任务时，判断目标路径是否已存在文件，如果存在则删除源路径文件


### 3. 差异处理策略

提供三种差异处理方式：
- 不处理：保留目标目录中的差异文件
- 移动到回收站：将差异文件移动到目标存储的回收站(trash)
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
- `alist_sync_base_config.json`：基础连接配置
- `alist_sync_sync_config.json`：同步任务配置
- `alist_sync_users_config.json`：用户认证配置

日志文件存储在 `data/log` 目录：
- `alist_sync.log`：当前日志
- `alist_sync.log.YYYY-MM-DD`：历史日志

## 注意事项

1. 首次使用请修改默认登录密码
2. 建议定期备份配置文件
3. 请确保 Alist 服务正常可访问
4. 建议先测试连接再保存配置
5. 可以通过日志查看同步执行情况

## 青龙使用

<details>
    <summary>点击这里展开/折叠内容</summary>

### 参数

```bash
BASE_URL: 服务器基础URL(结尾不带/)
USERNAME: 用户名
PASSWORD: 密码
TOKEN: 令牌
DIR_PAIRS: 源目录和目标目录的配对(源目录和目标目录的配对，用分号隔开，冒号分隔)
CRON_SCHEDULE: 调度日期，参考cron语法   "分 时 日 月 周" 非必填，不填为一次调度
--以下参数用于目标目录有，但源目录不存在的文件处理，可选参数--
SYNC_DELETE_ACTION: 同步删除动作，可选值为move,delete。
当SYNC_DELETE_ACTION设置为move时，文件将移动到trash目录下；比如存储器目录为 /dav/quark，则源目录多余的文件将会移动到/dav/quark/trash 目录下
EXCLUDE_DIRS: 排除目录
MOVE_FILE: 是否移动文件，会删除源目录，且与SYNC_DELETE_ACTION 不能同时生效

```

国内执行

```bash
ql raw https://gitee.com/xjxjin/alist-sync/raw/main/alist-sync-ql.py
```
国际执行

```bash
ql raw https://github.com/xjxjin/alist-sync/raw/main/alist-sync-ql.py
```

</details>

## 更新记录

### v1.1.2
- 2025-02-08
- 优化文件移动模式下保留源目录

### v1.1.1
- 2025-02-06
- 修复 docker 镜像打包文件缺失

### v1.1.0
- 2025-02-06
- 新增文件移动功能，由【[kuke2733](https://github.com/kuke2733)】小哥提供
- 新增版本号展示
- 执行前会重新执行失败任务
- 执行中排除已创建任务文件
- 修复排除目录会在目标目录创建 bug

### v1.0.8
- 2025-01-09
- 修复源目录不存在 bug
- 修复删除模式下目标目录为空判断报错异常
- 修复页面刷新任务展示异常

### v1.0.7
- 2025-01-08
- 新增令牌验证
- 新增导入导出配置文件功能
- 修复登录后无法显示存储器下拉列表
- 修改配置文件以 alist_sync开头

### v1.0.6
- 2025-01-07
- 在删除模式下，修复源目录为空，目标目录多余文件不能正确删除问题
- 简单适配移动端 UI

### v1.0.5
- 2025-01-05
- 初始UI版本发布
- 支持基础的同步功能
- 支持 Web 界面管理


### 2024-12-16更新
- 当源文件和目标文件大小不一致时，如果目标文件修改时间晚于源文件，则跳过覆盖

### 2024-11-13更新

- 修复删除目标目录多余文件重复删除问题 
- 优化移动目标目录多余文件到存储器根目录
- 优化设置多目录，一个目录失败导致所有目录失败问题


### 2024-09-06更新
- 新增参数，处理目标目录有多的文件或者文件夹，但是源目录没有的处理方式,功能由【[RWDai](https://github.com/RWDai)】小哥提供 
- none 什么也不做 
- move 移动到目标目录下的trash目录 
- delete 真实删除 

### 2024-06-29更新
- 新增DIR_PAIRS参数个数,最多到50，参数内容和之前一致(源目录和目标目录的配对(源目录和目标目录的配对，用分号隔开，冒号分隔)),参数格式为
- ```bash
    DIR_PAIRS
    DIR_PAIRS1
    DIR_PAIRS2
    DIR_PAIRS3
    .....
    DIR_PAIRS50
    ```
  
### 2024-05-23更新
- 新增青龙调度

### 2024-05-13更新
- 1.新增文件存在判断逻辑
  - 文件名称 
  - 文件大小
- 2.CRON_SCHEDULE 变更为参数可选
  - 当参数不传变更为一次调度，可以配合青龙远程调度


## 问题反馈

如果您在使用过程中遇到任何问题，请提交 Issue。


## 警告
* **在两个目录相互备份的情况下使用删除功能时请格外谨慎。可能导致文件永久丢失，后果自负。**



## Tips
- 前端页面均为 AI 生成，使用过程中可能有小瑕疵，欢迎前端大神提交代码修复
- 初次使用，保存基础配置后，可以点击添加任务，刷新源存储器和目标存储器下拉列表
- 如果忘记密码，请删除data/config/alist_sync_users_config.json 文件，会默认变成 admin/admin
- 令牌从 Alist 的 管理-设置-其他 获取，获取后不要重置令牌
- 有其他新增功能欢迎提交 Issue。
- 文件同步填写全目录，参照最后面图片
- 如果无法获取docker镜像，可以参考以下脚本换源，国内执行如下代码
```bash
bash <(curl -sSL https://gitee.com/xjxjin/scripts/raw/main/check_docker_registry.sh)
```
- 国际执行如下代码
```bash
bash <(curl -sSL https://github.com/xjxjin/scripts/raw/main/check_docker_registry.sh)
```


## License

MIT License


## 数据同步
<img src="https://raw.githubusercontent.com/xjxjin/alist-sync/main/static/images/数据同步.png" width="700" alt="数据同步">

## 文件同步
<img src="https://raw.githubusercontent.com/xjxjin/alist-sync/main/static/images/文件同步.png" width="700" alt="文件同步">

## 文件移动
<img src="https://raw.githubusercontent.com/xjxjin/alist-sync/main/static/images/文件移动.png" width="700" alt="文件移动">

## 令牌获取
<img src="https://raw.githubusercontent.com/xjxjin/alist-sync/main/static/images/令牌.png" width="700" alt="令牌获取">

## 查看任务进度
<img src="https://raw.githubusercontent.com/xjxjin/alist-sync/main/static/images/查看任务进度.png" width="700" alt="查看任务进度">
