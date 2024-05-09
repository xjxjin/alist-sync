# alist-sync
## 功能

* 可以将自己挂载的alist 下的各个目录相互间进行同步，原理是采用alist原始api调用执行，
* 同步原理是匹配文件名称是否相同，相同会跳过同步，不同就会将文件同步过去
* 目前存在的一个问题，有文件会随机同步失败，但同一个文件不会一直同步失败，建议每天同步一次，可以将同步漏了的文件补上


## 参数

```bash
--base_url  服务器基础URL(结尾不带/)
--username 用户名
--password  密码
--dir_pairs  源目录和目标目录的配对(源目录和目标目录的配对，用分号隔开，冒号分隔)
```
### demo
```bash
--dir_pairs aaaa/bbbb/cccc:dddd/eeee/fff;qwe/asd:gds/sdf
```


* 这个的意思是 需要将
* 源目录 aaaa/bbbb/cccc 下的文件夹以及文件，同步到目标目录dddd/eeee/fff 下
* 源目录qwe/asd下的文件夹以及文件，同步到目标目录gds/sdf下


## 本地python执行命令           

```bash
python3 alist-sync.py --base_url "$BASE_URL" --username "$USERNAME" --password "$PASSWORD" --dir_pairs "$DIR_PAIRS"
```



