<div align="center">
  
# alist网盘自动同步
</div>

* alist可以设置目录定时转存到各个网盘，做到夸网盘，多备份的效果
* 可以将自己挂载的alist 下的各个目录相互间进行同步，原理是采用alist原始api调用执行
* 同步原理1.匹配文件名称是否相同,2.文件大小是否相同，相同会跳过同步，不同会将目标文件删除后再进行文件同步
* 目前存在的一个问题，有文件会随机同步失败，但同一个文件不会一直同步失败，建议每天同步一次，可以将同步漏了的文件补上

<div align="center">
  
[![github tag][gitHub-tag-image]][github-url] [![docker pulls][docker-pulls-image]][docker-url] [![docker image size][docker-image-size-image]][docker-url]

[gitHub-tag-image]: https://img.shields.io/github/v/tag/xjxjin/alist-sync
[docker-pulls-image]: https://img.shields.io/docker/pulls/xjxjin/alist-sync
[docker-image-size-image]: https://img.shields.io/docker/image-size/xjxjin/alist-sync
[github-url]: https://github.com/xjxjin/alist-sync
[docker-url]: https://hub.docker.com/r/xjxjin/alist-sync
</div>

## 参数

```bash
BASE_URL  服务器基础URL(结尾不带/)
USERNAME 用户名
PASSWORD  密码
DIR_PAIRS  源目录和目标目录的配对(源目录和目标目录的配对，用分号隔开，冒号分隔)
CRON_SCHEDULE 调度日期，参考cron语法   "分 时 日 月 周" 非必填，不填为一次调度
```
### demo
```bash
docker run -d --name alist-sync \
-e TZ=Asia/Shanghai \
-e BASE_URL=http://192.168.xxx.xx:5244 \
-e USERNAME=xxx \
-e PASSWORD=xxx \
-e DIR_PAIRS=/dav/aliyundrive/同步目录/工作:/dav/quark/同步目录1/工作;/dav/quark/同步目录1/工作:/dav/aliyundrive/同步目录/工作 \
-e "CRON_SCHEDULE=5 16 * * *" \
xjxjin/alist-sync:latest
```

### docker-compose.yml 

```bash
name: alist-sync
services:
    alist-sync:
        container_name: alist-sync
        environment:
            - TZ=Asia/Shanghai
            - BASE_URL=http://192.168.xxx.xx:5244
            - USERNAME=xxx
            - PASSWORD=xxx
            - DIR_PAIRS=/dav/aliyundrive/同步目录/工作:/dav/quark/同步目录1/工作;/dav/quark/同步目录1/工作:/dav/aliyundrive/同步目录/工作
            - CRON_SCHEDULE=5 16 * * *
        image: xjxjin/alist-sync:latest
```

* 这个的意思是 需要将
* 源目录 /dav/aliyundrive/同步目录/工作 下的文件夹以及文件，同步到目标目录/dav/quark/同步目录1/工作 下
* 源目录/dav/quark/同步目录1/工作，同步到目标目录/dav/aliyundrive/同步目录/工作下
* 也就是说两个目录相互备份

### 注意 DIR_PAIRS格式为  ，用分号隔开，冒号分隔，英文冒号，英文分号



## 执行完成后可以在复制页面查看进度
<img width="1628" alt="image" src="https://github.com/xjxjin/alist-sync/assets/35513148/f2b907a2-8d84-4b01-a748-8d08e570af5e">


## 2024-05-13更新
### 1.新增文件存在判断逻辑  
 * 文件名称 
 * 文件大小
### 2.CRON_SCHEDULE 变更为参数可选
 * 当参数不传变更为一次调度，可以配合青龙远程调度

## 2024-05-23更新
* 新增青龙调度

需要在环境变量处设置参数

```bash
BASE_URL
USERNAME
PASSWORD
DIR_PAIRS
```


国内执行

```bash
ql raw https://gitee.com/xjxjin/alist-sync/raw/main/alist-sync-ql.py
```
国际执行

```bash
ql raw https://github.com/xjxjin/alist-sync/raw/main/alist-sync-ql.py
```
<img width="1278" alt="image" src="https://github.com/xjxjin/alist-sync/assets/35513148/aad05ef8-dcfb-4d86-a12f-ebeed22d0a90">
