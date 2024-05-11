# alist网盘自动


* alist可以设置目录定时转存到各个网盘，做到夸网盘，多备份的效果
* 可以将自己挂载的alist 下的各个目录相互间进行同步，原理是采用alist原始api调用执行，
* 同步原理是匹配文件名称是否相同，相同会跳过同步，不同就会将文件同步过去
* 目前存在的一个问题，有文件会随机同步失败，但同一个文件不会一直同步失败，建议每天同步一次，可以将同步漏了的文件补上


[![github tag][gitHub-tag-image]][github-url] [![docker pulls][docker-pulls-image]][docker-url] [![docker image size][docker-image-size-image]][docker-url]

[gitHub-tag-image]: https://img.shields.io/github/v/tag/xjxjin/alist-sync
[docker-pulls-image]: https://img.shields.io/docker/pulls/xjxjin/alist-sync
[docker-image-size-image]: https://img.shields.io/docker/image-size/xjxjin/alist-sync
[github-url]: https://github.com/xjxjin/alist-sync
[docker-url]: https://hub.docker.com/r/xjxjin/alist-sync


## 参数

```bash
BASE_URL  服务器基础URL(结尾不带/)
USERNAME 用户名
PASSWORDd  密码
DIR_PAIRS  源目录和目标目录的配对(源目录和目标目录的配对，用分号隔开，冒号分隔)
CRON_SCHEDULE 调度日期，参考cron语法   "分 时 日 月 周"
```
### demo
```bash
docker run -d --name alist-sync -e TZ=Asia/Shanghai -e BASE_URL="http://192.168.xxx.xx:5244" -e USERNAME="xxx" -e PASSWORD="xxx" -e DIR_PAIRS="/dav/aliyundrive/同步目录/工作:/dav/quark/同步目录1/工作" -e CRON_SCHEDULE="5 16 * * *" xjxjin/alist-sync:latest
```


* 这个的意思是 需要将
* 源目录 aaaa/bbbb/cccc 下的文件夹以及文件，同步到目标目录dddd/eeee/fff 下
* 源目录qwe/asd下的文件夹以及文件，同步到目标目录gds/sdf下


### 注意 DIR_PAIRS格式为  ，用分号隔开，冒号分隔，英文冒号，英文分号



## 执行完成后可以在复制页面查看进度
<img width="1628" alt="image" src="https://github.com/xjxjin/alist-sync/assets/35513148/f2b907a2-8d84-4b01-a748-8d08e570af5e">


