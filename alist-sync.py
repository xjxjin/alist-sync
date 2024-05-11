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
dir_pairs = os.environ.get('DIR_PAIRS')
cron_schedule = os.environ.get('CRON_SCHEDULE')


# print(f'base_url={base_url}')
# print(f'username={username}')
# print(f'password={password}')
print(f'dir_pairs={dir_pairs}')
print(f'cron_schedule={cron_schedule}')
# 创建一个后台调度器实例
scheduler = BackgroundScheduler()

# 创建一个CronTrigger实例
trigger = CronTrigger.from_crontab(cron_schedule)



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


def is_directory_exists(connection, token, directory_path):
    # 判断文件夹是否存在
    response = directory_operation(connection, token, "get", path=directory_path)
    return response and response.get("message", "") == "success"


def recursive_copy(src_dir, dst_dir, connection, token):
    # 递归复制文件夹内容
    try:
        src_contents = get_directory_contents(connection, token, src_dir)["content"]
    except Exception as e:
        print(f"获取目录内容失败: {e}")
        print(f"获取目录【 {src_dir}】failed")
        return
    # 空目录跳过
    if not src_contents:
        return

    for item in src_contents:
        item_name = item["name"]
        item_path = f"{src_dir}/{item_name}"
        dst_item_path = f"{dst_dir}/{item_name}"

        if item["is_dir"]:
            if not is_directory_exists(connection, token, dst_item_path):
                create_directory(connection, token, dst_item_path)
            else:
                print(f'文件夹【{dst_item_path}】已存在，跳过创建')

            # 递归复制文件夹
            recursive_copy(item_path, dst_item_path, connection, token)
        else:
            if not is_directory_exists(connection, token, dst_item_path):
                copy_item(connection, token, src_dir, dst_dir, item_name)
            else:
                print(f'文件【{item_name}】已存在，跳过复制')


def main():
    print(f"同步任务运行开始 {datetime.now()}")
    conn = create_connection(base_url)
    token = get_token(conn, "/api/auth/login", username, password)

    data_list = dir_pairs.split(';')
    for item in data_list:
        pair = item.split(':')
        if len(pair) == 2:
            src_dir, dst_dir = pair[0], pair[1]
            if not is_directory_exists(conn, token, dst_dir):
                create_directory(conn, token, dst_dir)
            print(f"同步源目录: {src_dir}, 到目标目录: {dst_dir}")
            recursive_copy(src_dir, dst_dir, conn, token)
        else:
            print(f"源目录或目标目录不存在: {item}")

    conn.close()
    print(f"同步任务运行结束 {datetime.now()}")



if __name__ == '__main__':
    # 添加任务到调度器，使用创建的CronTrigger实例
    scheduler.add_job(main, trigger=trigger)

    # 开始调度器
    # print(f'开始调度器{datetime.now()}')
    scheduler.start()
    # print(f'结束调度器{datetime.now()}')
    try:
        # 这会阻塞主线程，但调度器在后台线程中运行
        while True:
            time.sleep(2)  # 防止主线程过快退出，仅为示例，实际应用中可能不需要
    except (KeyboardInterrupt, SystemExit):
        # 如果主线程被中断（例如用户按Ctrl+C），则关闭调度器
        scheduler.shutdown()
