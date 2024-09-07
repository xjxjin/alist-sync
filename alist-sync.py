import http.client
import json
import re

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import time
from datetime import datetime
import os

# 解析命令行参数
base_url = os.environ.get('BASE_URL')
username = os.environ.get('USERNAME')
password = os.environ.get('PASSWORD')
cron_schedule = os.environ.get('CRON_SCHEDULE')

sync_delete_action = os.environ.get('SYNC_DELETE_ACTION', 'none').lower()
sync_delete = sync_delete_action != 'none'
trash_folder = os.environ.get('TRASH_FOLDER', '/trash')

if cron_schedule:
    # 创建一个后台调度器实例
    scheduler = BackgroundScheduler()

    # 创建一个CronTrigger实例
    trigger = CronTrigger.from_crontab(cron_schedule)


def xiaojin():
    pt = """

                                   ..
                                  ....                       
                               .:----=:                      
                      ...:::---==-:::-+.                     
                  ..:=====-=+=-::::::==               .:-.   
              .-==*=-:::::::::::::::=*-:           .:-=++.   
           .-==++++-::::::::::::::-++:-==:.       .=-=::=-.  
   ....:::-=-::-++-:::::::::::::::--:::::==:      -:.:=..+:  
  ==-------::::-==-:::::::::::::::::::::::-+-.  .=:   .:=-.. 
  ==-::::+-:::::==-:::::::::::::::::::::::::=+.:+-    :-:    
   :--==+*::::::-=-::::::::::::::::::::::::::-*+:    .+.     
      ..-*:::::::==::::::::::::::::::::::::::-+.     -+.     
        -*:::::::-=-:::::::--:::::::::::::::=-.      +-      
        :*::::::::-=::::::-=:::::=:::::::::-:       .*.      
        .+=:::::::::::::::-::::-*-::......::        --       
         :+::-:::::::::::::::::*=:-::......         -.       
          :-:-===-:::::::::::.:+==--:......        .+.       
        .==:...-+#+::.......   .   .......         .=-       
        -*.....::............::-.                 ...=-      
        .==-:..       :=-::::::=.                  ..:+-     
          .:--===---=-:::-:::--:.                   ..:+:    
             =--+=:+*+:. ......                      ..-+.   
            .#. .+#- .:.                             .::=:   
             -=:.-:                                  ..::-.  
              .-=.               xjxjin              ...:-:  
               ...                                    ...:-  



    """
    print(pt)


def get_dir_pairs_from_env():
    # 初始化列表来存储环境变量的值
    dir_pairs_list = []

    # 尝试从环境变量中获取DIR_PAIRS的值
    dir_pairs = os.environ.get('DIR_PAIRS')

    # 检查DIR_PAIRS是否不为空
    print("本次同步目录有：")
    if dir_pairs:
        # 将DIR_PAIRS的值添加到列表中
        dir_pairs_list.append(dir_pairs)
        print(dir_pairs)

    # 循环尝试获取DIR_PAIRS1到DIR_PAIRS50的值
    for i in range(1, 51):
        # 构造环境变量名
        env_var_name = f'DIR_PAIRS{i}'
        # 尝试获取环境变量的值
        env_var_value = os.environ.get(env_var_name)
        # 如果环境变量的值不为空，则添加到列表中
        if env_var_value:
            dir_pairs_list.append(env_var_value)
            print(dir_pairs)

    return dir_pairs_list


def create_connection(base_url):
    # 使用正则表达式解析URL，获取主机名和端口
    match = re.match(r'(?:http[s]?://)?([^:/]+)(?::(\d+))?', base_url)
    host = match.group(1)
    port_part = match.group(2)
    port = int(port_part) if port_part else (80 if 'http://' in base_url else 443)

    # 根据URL的协议类型创建HTTP或HTTPS连接
    return http.client.HTTPSConnection(host, port) if base_url.startswith('https://') else http.client.HTTPConnection(
        host, port)


def make_request(connection, method, path, headers=None, payload=None):
    # 发送HTTP请求并返回JSON解析后的响应内容
    try:
        connection.request(method, path, body=payload, headers=headers)
        response = connection.getresponse()
        return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        print(f"请求失败: {e}")
        return None


def get_token(connection, path, username, password):
    # 获取认证token
    payload = json.dumps({"username": username, "password": password})
    headers = {
        'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
        'Content-Type': 'application/json'
    }
    response = make_request(connection, "POST", path, headers, payload)
    return response["data"]["token"] if response else None


def directory_operation(connection, token, operation, **kwargs):
    # (connection, token, "mkdir", directory_path, path=directory_path)
    # 一个通用函数，用于执行目录操作
    headers = {
        'Authorization': token,
        'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
        'Content-Type': 'application/json'
    }
    payload = json.dumps(kwargs)
    path = f"/api/fs/{operation}"  # 构建API路径
    response = make_request(connection, "POST", path, headers, payload)
    return response


def get_directory_contents(connection, token, directory_path):
    # 获取目录下的文件和文件夹列表
    return directory_operation(connection, token, "list", path=directory_path).get("data", [])


def create_directory(connection, token, directory_path):
    # 创建新文件夹
    response = directory_operation(connection, token, "mkdir", path=directory_path)
    print(f"文件夹【{directory_path}】创建成功" if response else "文件夹创建失败")


def copy_item(connection, token, src_dir, dst_dir, item_name):
    # 复制文件或文件夹
    response = directory_operation(connection, token, "copy", src_dir=src_dir, dst_dir=dst_dir, names=[item_name])
    print(f"文件【{item_name}】复制成功" if response else "文件复制失败")

def move_item(connection, token, src_dir, dst_dir, item_name):
    # 移动文件或文件夹
    response = directory_operation(connection, token, "move", src_dir=src_dir, dst_dir=dst_dir, names=[item_name])
    print(f"文件【{item_name}】移动成功" if response else "文件移动失败")


def is_path_exists(connection, token, path):
    # 判断路径是否存在，包括文件和文件夹
    response = directory_operation(connection, token, "get", path=path)
    return response and response.get("message", "") == "success"


def is_directory_size(connection, token, directory_path):
    # 判断文件大小
    response = directory_operation(connection, token, "get", path=directory_path)
    return response["data"]["size"]


def directory_remove(connection, token, directory_path):
    # 删除文件
    response = directory_operation(connection, token, "remove", path=directory_path)
    return response and response.get("message", "") == "success"


def recursive_copy(src_dir, dst_dir, connection, token, sync_delete=False):
    # 递归复制文件夹内容
    try:
        src_contents = get_directory_contents(connection, token, src_dir)["content"]
        if sync_delete:
            dst_contents = get_directory_contents(connection, token, dst_dir)["content"]
    except Exception as e:
        print(f"获取目录内容失败: {e}")
        if sync_delete:
            print(f"获取目录【{src_dir}】或【{dst_dir}】失败")
        else:
            print(f"获取目录【{src_dir}】失败")
        return
    # 空目录跳过
    if not src_contents:
        return

    for item in src_contents:
        item_name = item["name"]
        item_path = f"{src_dir}/{item_name}"
        dst_item_path = f"{dst_dir}/{item_name}"

        if item["is_dir"]:
            if not is_path_exists(connection, token, dst_item_path):
                create_directory(connection, token, dst_item_path)
            else:
                print(f'文件夹【{dst_item_path}】已存在，跳过创建')

            # 递归复制文件夹
            recursive_copy(item_path, dst_item_path, connection, token)
        else:
            if not is_path_exists(connection, token, dst_item_path):
                copy_item(connection, token, src_dir, dst_dir, item_name)
            else:
                src_size = item["size"]
                dst_size = is_directory_size(connection, token, dst_item_path)
                if src_size == dst_size:
                    print(f'文件【{item_name}】已存在，跳过复制')
                else:
                    print(f'文件【{item_name}】文件存在变更，删除文件')
                    directory_remove(connection, token, dst_item_path)
                    copy_item(connection, token, src_dir, dst_dir, item_name)
    
    # 如果启用了同步删除，删除目标目录中不存在于源目录的文件
    if sync_delete:
        for dst_item in dst_contents:
            item_name = dst_item["name"]
            src_item_path = f"{src_dir}/{item_name}"
            trash_dir=f"{dst_dir}{trash_folder}"

            if not is_path_exists(connection, token, src_item_path):
                dst_item_path = f"{dst_dir}/{item_name}"
                if dst_item["is_dir"]:
                    if sync_delete_action == "delete":
                        directory_remove(connection, token, dst_item_path)
                    else:
                        recursive_move_item(connection, token, dst_item_path, trash_dir)
                else:
                    if sync_delete_action == "delete":
                        directory_remove(connection, token, dst_item_path)
                    else:
                        # 确保目标目录存在
                        if not is_path_exists(connection, token, dst_dir):
                          create_directory(connection, token, dst_dir)
                        move_item(connection, token, dst_dir, trash_dir, item_name)

def recursive_move_item(connection, token, src_dir, dst_dir):

    # 确保目标目录存在
    if not is_path_exists(connection, token, dst_dir):
      create_directory(connection, token, dst_dir)

    try:
      # 获取源项目的信息
      src_contents = get_directory_contents(connection, token, src_dir)["content"]
    except Exception as e:
        print(f"获取目录内容失败: {e}")
        print(f"获取目录【{src_dir}】失败")
        return

    # 空目录跳过
    if not src_contents:
        return

    for item in src_contents:
        item_name = item["name"]
        src_item_path = f"{src_dir}/{item_name}"
        dst_item_path = f"{dst_dir}/{item_name}"

        if item["is_dir"]:
            recursive_move_item(connection, token, src_item_path, dst_item_path)
        else:
            # 如果是文件,直接移动
            move_item(connection, token, src_dir, dst_dir, item_name)
    # 移动完所有子项目后,删除源目录
    directory_remove(connection, token, src_dir)

    print(f"已移动 {src_dir} 到 {dst_dir}")
        

def main():
    xiaojin()
    print(f"同步任务运行开始 {datetime.now()}")
    conn = create_connection(base_url)
    token = get_token(conn, "/api/auth/login", username, password)

    dir_pairs_list = get_dir_pairs_from_env()
    # 遍历dir_pairs_list中的每个值
    for value in dir_pairs_list:
        # 将当前遍历到的值赋给变量dir_pairs
        dir_pairs = value
        # 执行需要使用dir_pairs的代码
        # 例如，打印dir_pairs的值
        # print(dir_pairs)
        data_list = dir_pairs.split(';')
        for item in data_list:
            pair = item.split(':')
            if len(pair) == 2:
                src_dir, dst_dir = pair[0], pair[1]
                if not is_path_exists(conn, token, dst_dir):
                    create_directory(conn, token, dst_dir)
                print(f"【{src_dir}】---->【 {dst_dir}】")
                print(f"同步源目录: {src_dir}, 到目标目录: {dst_dir}")
                recursive_copy(src_dir, dst_dir, conn, token, sync_delete)
            else:
                print(f"源目录或目标目录不存在: {item}")

    conn.close()
    print(f"同步任务运行结束 {datetime.now()}")


if __name__ == '__main__':
    # ... 解析命令行参数 ...

    # 检查CRON_SCHEDULE是否为空或者为null
    if not cron_schedule or cron_schedule is None or cron_schedule == "None":
        print("CRON_SCHEDULE为空，将执行一次同步任务。")
        main()  # 执行一次同步任务
    else:
        # 添加任务到调度器，使用创建的CronTrigger实例
        scheduler.add_job(main, trigger=trigger)

        # 开始调度器
        scheduler.start()
        try:
            # 这会阻塞主线程，但调度器在后台线程中运行
            while True:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            # 如果主线程被中断（例如用户按Ctrl+C），则关闭调度器
            scheduler.shutdown()
