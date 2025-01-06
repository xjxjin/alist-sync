from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_bootstrap import Bootstrap
import logging
import os
import json

import croniter, datetime, time
from functools import wraps

# 动态导入alist-sync-ql.py
import importlib.util
import sys

from typing import Dict, List, Optional, Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from logging.handlers import TimedRotatingFileHandler
import glob

from passlib.hash import sha256_crypt

# 创建一个全局的调度器
scheduler = BackgroundScheduler()
scheduler.start()


def import_from_file(module_name: str, file_path: str) -> Any:
    """动态导入模块"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# 导入AlistSync类
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    alist_sync = import_from_file('alist_sync',
                                     os.path.join(current_dir, 'alist_sync.py'))
    AlistSync = alist_sync.AlistSync
except Exception as e:
    print(f"导入alist_sync.py失败: {e}")
    print(f"当前目录: {current_dir}")
    print(f"尝试导入的文件路径: {os.path.join(current_dir, 'alist_sync.py')}")
    raise

app = Flask(__name__)
app.secret_key = os.urandom(24)  # 用于session加密
Bootstrap(app)

# 设置日志记录器
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 假设配置数据存储在当前目录下的config_data目录中，你可以根据实际需求修改
STORAGE_DIR = os.path.join(app.root_path, 'data/config')
if not os.path.exists(STORAGE_DIR):
    os.makedirs(STORAGE_DIR)

# 用户配置文件路径
USER_CONFIG_FILE = os.path.join(os.path.dirname(__file__), STORAGE_DIR, 'users_config.json')

# 确保配置目录存在
os.makedirs(os.path.dirname(USER_CONFIG_FILE), exist_ok=True)

# 如果用户配置文件不存在,创建默认配置
if not os.path.exists(USER_CONFIG_FILE):
    default_config = {
        "users": [
            {
                "username": "admin",
                "password": sha256_crypt.hash("admin")
            }
        ]
    }
    with open(USER_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(default_config, f, indent=2, ensure_ascii=False)


def load_users():
    """加载用户配置"""
    try:
        with open(USER_CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载用户配置失败: {e}")
        return {"users": []}


def save_users(config):
    """保存用户配置"""
    try:
        with open(USER_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"保存用户配置失败: {e}")
        return False


# 登录验证装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


# 默认路由重定向到登录页
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')


# 登录页面路由
@app.route('/login')
def login():
    return render_template('login.html')


# 登录接口
@app.route('/api/login', methods=['POST'])
def api_login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'code': 400, 'message': '用户名和密码不能为空'})

        # 加载用户配置
        config = load_users()

        # 查找用户并验证密码
        user = next((user for user in config['users']
                     if user['username'] == username), None)

        if user and sha256_crypt.verify(password, user['password']):
            session['user_id'] = username
            return jsonify({'code': 200, 'message': '登录成功'})
        else:
            return jsonify({'code': 401, 'message': '用户名或密码错误'})

    except Exception as e:
        print(f"登录失败: {e}")
        return jsonify({'code': 500, 'message': '服务器错误'})


# 检查登录状态接口
@app.route('/api/check-login')
def check_login():
    if 'user_id' in session:
        return jsonify({'code': 200, 'message': 'logged in'})
    return jsonify({'code': 401, 'message': 'not logged in'})


# 获取当前用户信息接口
@app.route('/api/current-user')
@login_required
def current_user():
    try:
        username = session['user_id']
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'username': username
            }
        })
    except Exception as e:
        print(f"获取当前用户信息失败: {e}")
        return jsonify({'code': 500, 'message': '服务器错误'})


# 修改密码接口
@app.route('/api/change-password', methods=['POST'])
@login_required
def change_password():
    try:
        data = request.get_json()
        old_username = data.get('oldUsername')
        new_username = data.get('newUsername')
        old_password = data.get('oldPassword')
        new_password = data.get('newPassword')

        if not all([old_username, new_username, old_password, new_password]):
            return jsonify({'code': 400, 'message': '所有字段都不能为空'})

        # 加载用户配置
        config = load_users()

        # 查找当前用户
        username = session['user_id']
        user = next((user for user in config['users']
                     if user['username'] == username), None)

        if not user:
            return jsonify({'code': 404, 'message': '用户不存在'})

        # 验证原密码
        if not sha256_crypt.verify(old_password, user['password']):
            return jsonify({'code': 400, 'message': '原密码错误'})

        # 如果修改了用户名,确保新用户名不存在
        if old_username != new_username:
            exists_user = next((u for u in config['users']
                                if u['username'] == new_username
                                and u != user), None)
            if exists_user:
                return jsonify({'code': 400, 'message': '新用户名已存在'})

        # 更新用户名和密码
        user['username'] = new_username
        user['password'] = sha256_crypt.hash(new_password)

        # 保存配置
        if save_users(config):
            # 如果修改了用户名,更新session
            if old_username != new_username:
                session['user_id'] = new_username
            return jsonify({'code': 200, 'message': '修改成功'})
        else:
            return jsonify({'code': 500, 'message': '保存配置失败'})

    except Exception as e:
        print(f"修改密码失败: {e}")
        return jsonify({'code': 500, 'message': '服务器错误'})


# 登出接口
@app.route('/api/logout')
def logout():
    session.clear()
    return jsonify({'code': 200, 'message': 'success'})


# 保存基础连接配置接口
@app.route('/api/save-base-config', methods=['POST'])
@login_required
def save_base_config():
    data = request.get_json()
    base_url = data.get('baseUrl')
    username = data.get('username')
    password = data.get('password')
    config_file_path = os.path.join(STORAGE_DIR, 'base_config.json')
    try:
        with open(config_file_path, 'w') as f:
            json.dump({
                "baseUrl": base_url,
                "username": username,
                "password": password
            }, f)
        return jsonify({"code": 200, "message": "基础配置保存成功"})
    except Exception as e:
        return jsonify({"code": 500, "message": f"保存失败: {str(e)}"})


# 查询基础连接配置接口
@app.route('/api/get-base-config', methods=['GET'])
@login_required
def get_base_config():
    config_file_path = os.path.join(STORAGE_DIR, 'base_config.json')
    try:
        with open(config_file_path, 'r') as f:
            config_data = json.load(f)
        return jsonify({"code": 200, "data": config_data})
    except FileNotFoundError:
        return jsonify({"code": 404, "message": "配置文件不存在"})
    except Exception as e:
        return jsonify({"code": 500, "message": f"读取配置失败: {str(e)}"})


@app.route('/api/get-sync-config', methods=['GET'])
@login_required
def get_sync_config():
    config_file_path = os.path.join(STORAGE_DIR, 'sync_config.json')
    try:
        with open(config_file_path, 'r') as f:
            config_data = json.load(f)
        return jsonify({"code": 200, "data": config_data})
    except FileNotFoundError:
        return jsonify({"code": 404, "message": "配置文件不存在"})
    except Exception as e:
        return jsonify({"code": 500, "message": f"读取配置失败: {str(e)}"})


# 定义超时处理函数
def timeout_handler(signum, frame):
    raise TimeoutError("连接测试超时")


# 测试连接接口
@app.route('/api/test-connection', methods=['POST'])
@login_required
def test_connection():
    try:

        data = request.get_json()
        base_url = data.get('baseUrl')
        username = data.get('username')
        password = data.get('password')

        # 创建 AlistSync 实例
        alist = AlistSync(base_url, username, password)

        # 尝试登录
        if alist.login():
            return jsonify({"code": 200, "message": "连接测试成功"})
        else:
            return jsonify({"code": 500, "message": "地址或用户名或密码错误"})

    except Exception as e:
        return jsonify({"code": 500, "message": f"连接测试失败: {str(e)}"})
    finally:
        if 'alist' in locals():
            alist.close()


# 添加以下函数来管理定时任务
def schedule_sync_tasks():
    """
    从配置文件读取并调度所有同步任务
    """
    try:
        # 清除所有现有的任务
        scheduler.remove_all_jobs()

        # 加载同步配置
        sync_config = load_sync_config()
        if not sync_config or 'tasks' not in sync_config:
            logger.warning("没有找到有效的同步任务配置")
            return

        # 为每个任务创建调度
        for task in sync_config['tasks']:
            if 'cron' not in task:
                logger.warning(f"任务 {task.get('taskName', 'unknown')} 没有配置cron表达式")
                continue

            try:
                job_id = f"sync_task_{task['id']}"
                # 修改这里，直接传递函数而不是调用结果
                scheduler.add_job(
                    func=execute_sync_task,  # 不要加括号调用
                    trigger=CronTrigger.from_crontab(task['cron']),
                    id=job_id,
                    replace_existing=True,
                    args=[task['id']]  # 通过 args 传递参数
                )
                logger.info(f"成功调度任务 {task['taskName']}, ID: {job_id}, Cron: {task['cron']}")
            except Exception as e:
                logger.error(f"调度任务 {task.get('taskName', 'unknown')} 失败: {str(e)}")

    except Exception as e:
        logger.error(f"调度同步任务时发生错误: {str(e)}")


# 修改保存同步配置接口，使其在保存后重新调度任务
@app.route('/api/save-sync-config', methods=['POST'])
@login_required
def save_sync_config():
    data = request.get_json()
    sync_config_file_path = os.path.join(STORAGE_DIR, 'sync_config.json')
    try:
        with open(sync_config_file_path, 'w') as f:
            json.dump(data, f)
        # 重新调度所有任务    
        schedule_sync_tasks()
        return jsonify({"code": 200, "message": "同步配置保存成功并已更新调度"})
    except Exception as e:
        return jsonify({"code": 500, "message": f"保存失败: {str(e)}"})


# 假设存储器列表数据也是存储在文件中，这里模拟返回一些示例数据，你可根据实际替换读取逻辑
@app.route('/api/storages', methods=['GET'])
@login_required
def get_storages():
    try:
        config = get_base_config()
        data = config.get_json().get("data")

        # data = request.get_json()
        base_url = data.get('baseUrl')
        username = data.get('username')
        password = data.get('password')
        # 创建 AlistSync 实例
        alist = AlistSync(base_url, username, password)

        # 登录并获取存储列表
        if alist.login():
            storage_list = alist.get_storage_list()
            return jsonify({"code": 200, "data": storage_list})
        else:
            return jsonify({"code": 500, "message": "获取存储列表失败：登录失败"})
    except Exception as e:
        return jsonify({"code": 500, "message": f"获取存储列表失败: {str(e)}"})
    finally:
        if 'alist' in locals():
            alist.close()


@app.route('/api/next-run-time', methods=['POST'])
def next_run_time():
    # Cron 表达式解析与时间计算
    try:
        data = request.get_json()
        cron_expression = data.get('cron')
        if not cron_expression:
            return jsonify({"code": 400, "message": "缺少cron参数"}), 400
        next_time_list = crontab_run_next_time(cron_expression)
        return jsonify({"code": 200, "data": next_time_list})
    except Exception as e:
        return jsonify({"code": 500, "message": f"解析出错: {str(e)}"}), 500


def datetime_to_timestamp(timestring, format="%Y-%m-%d %H:%M:%S"):
    """ 将普通时间格式转换为时间戳(10位), 形如 '2016-05-05 20:28:54'，由format指定 """
    try:
        # 转换成时间数组
        timeArray = time.strptime(timestring, format)
    except Exception:
        raise
    else:
        # 转换成10位时间戳
        return int(time.mktime(timeArray))


def get_current_timestamp():
    """ 获取本地当前时间戳(10位): Unix timestamp：是从1970年1月1日（UTC/GMT的午夜）开始所经过的秒数，不考虑闰秒 """
    return int(time.mktime(datetime.datetime.now().timetuple()))


def timestamp_after_timestamp(timestamp=None, seconds=0, minutes=0, hours=0, days=0):
    """ 给定时间戳(10位),计算该时间戳之后多少秒、分钟、小时、天的时间戳(本地时间) """
    # 1. 默认时间戳为当前时间
    timestamp = get_current_timestamp() if timestamp is None else timestamp
    # 2. 先转换为datetime
    d1 = datetime.datetime.fromtimestamp(timestamp)
    # 3. 根据相关时间得到datetime对象并相加给定时间戳的时间
    d2 = d1 + datetime.timedelta(seconds=int(seconds), minutes=int(minutes), hours=int(hours), days=int(days))
    # 4. 返回某时间后的时间戳
    return int(time.mktime(d2.timetuple()))


def timestamp_datetime(timestamp, format='%Y-%m-%d %H:%M:%S'):
    """ 将时间戳(10位)转换为可读性的时间 """
    # timestamp为传入的值为时间戳(10位整数)，如：1332888820
    timestamp = time.localtime(timestamp)
    return time.strftime(format, timestamp)


def crontab_run_next_time(cron_expression, timeFormat="%Y-%m-%d %H:%M:%S", queryTimes=5):
    """计算定时任务下次运行时间
    sched str: 定时任务时间表达式
    timeFormat str: 格式为"%Y-%m-%d %H:%M"
    queryTimes int: 查询下次运行次数
    """
    try:
        now = datetime.datetime.now()
    except ValueError:
        raise
    else:
        # 以当前时间为基准开始计算
        cron = croniter.croniter(cron_expression, now)
        return [cron.get_next(datetime.datetime).strftime(timeFormat) for i in range(queryTimes)]


# def CrontabRunTime(sched, ctime, timeFormat="%Y-%m-%d %H:%M:%S"):
#     """计算定时任务运行次数
#     sched str: 定时任务时间表达式
#     ctime str: 定时任务创建的时间，与timeFormat格式对应
#     timeFormat str: 格式为"%Y-%m-%d %H:%M"
#     """
#     try:
#         ctimeStrp = datetime.datetime.strptime(ctime, timeFormat)
#     except ValueError:
#         raise
#     else:
#         # 根据定时任务创建时间开始计算
#         cron = croniter.croniter(sched, ctimeStrp)
#         now = get_current_timestamp()
#         num = 0
#         while 1:
#             timestring = cron.get_next(datetime.datetime).strftime(timeFormat)
#             timestamp = datetime_to_timestamp(timestring, "%Y-%m-%d %H:%M:%S")
#             if timestamp > now:
#                 break
#             else:
#                 num += 1
#         return num


# 执行任务接口
@app.route('/api/run-task', methods=['POST'])
@login_required
def run_task():
    """立即执行同步任务"""
    try:
        if execute_sync_task():
            return jsonify({"code": 200, "message": "同步任务执行成功"})
        else:
            return jsonify({"code": 500, "message": "同步任务执行失败"})
    except Exception as e:
        return jsonify({"code": 500, "message": f"执行任务时发生错误: {str(e)}"})


def execute_sync_task(id: int | None = None):
    """执行同步任务"""
    try:
        logger.info("开始执行同步任务")

        # 加载同步配置获取任务名称和差异处置策略
        sync_config = load_sync_config()
        task_name = "未知任务"
        sync_del_action = "none"  # 默认值

        if id is not None and sync_config and 'tasks' in sync_config:
            task = next((t for t in sync_config['tasks'] if t['id'] == id), None)
            if task:
                task_name = task.get('taskName', '未知任务')
                sync_del_action = task.get('syncDelAction', 'none')

        logger.info(f"任务名称: {task_name}, 差异处置策略: {sync_del_action}")

        # 加载基础配置
        base_config = load_base_config()
        if not base_config:
            logger.error("基础配置为空，无法执行同步任务")
            return False

        # logger.info(f"已加载基础配置: {base_config}")
        logger.info(f"已加载基础配置")

        # 清除可能存在的旧环境变量
        for i in range(1, 51):
            if f'DIR_PAIRS{i}' in os.environ:
                del os.environ[f'DIR_PAIRS{i}']
        if 'DIR_PAIRS' in os.environ:
            del os.environ['DIR_PAIRS']

        # 设置基础环境变量
        os.environ['BASE_URL'] = base_config.get('baseUrl', '')
        os.environ['USERNAME'] = base_config.get('username', '')
        os.environ['PASSWORD'] = base_config.get('password', '')

        # 加载同步配置
        sync_config = load_sync_config()
        if not sync_config:
            logger.error("同步配置为空，无法执行同步任务")
            return False

        # 处理任务列表
        tasks = sync_config.get('tasks', [])
        if not tasks:
            logger.error("没有配置同步任务")
            return False

        for task in tasks:
            try:
                if id is None or id == task['id']:
                    task_name = task.get('taskName', '未知任务')
                    sync_del_action = task.get('syncDelAction', 'none')
                    logger.info(f"[{task_name}] 开始处理任务，差异处置策略: {sync_del_action}")

                    # 更新环境变量中的差异处置策略
                    os.environ['SYNC_DELETE_ACTION'] = sync_del_action

                    if task['syncMode'] == 'data':
                        dir_pairs = ''
                        exclude_dirs = task['excludeDirs']
                        os.environ['EXCLUDE_DIRS'] = exclude_dirs
                        # 数据同步模式：一个源存储同步到多个目标存储
                        syncDirs = task['syncDirs']
                        source = task['sourceStorage']

                        if source not in exclude_dirs:
                            exclude_dirs = f'{source}/{exclude_dirs}'
                        exclude_dirs = exclude_dirs.replace('//', '/')

                        for target in task['targetStorages']:
                            if source != target:
                                dir_pair = f"{source}/{syncDirs}:{target}/{syncDirs}"
                                dir_pair = dir_pair.replace('//', '/')
                                if f'DIR_PAIRS' in os.environ:
                                    os.environ['DIR_PAIRS'] += f";{dir_pair}"
                                else:
                                    os.environ['DIR_PAIRS'] = dir_pair

                                if dir_pairs != '':
                                    dir_pairs += f";{dir_pair}"
                                else:
                                    dir_pairs = dir_pair
                                logger.info(f"[{task_name}] 添加同步目录对: {dir_pair}")
                        # 调用 alist_sync 的 main 函数
                        alist_sync.main(dir_pairs, sync_del_action, exclude_dirs)
                    elif task['syncMode'] == 'file':
                        dir_pairs = ''
                        exclude_dirs = task['excludeDirs']
                        os.environ['EXCLUDE_DIRS'] = exclude_dirs
                        # 文件同步模式：多个源路径同步到对应的目标路径
                        paths = task['paths']
                        for path in paths:
                            dir_pair = f"{path['srcPath']}:{path['dstPath']}"
                            if 'DIR_PAIRS' in os.environ:
                                os.environ['DIR_PAIRS'] += f";{dir_pair}"
                            else:
                                os.environ['DIR_PAIRS'] = dir_pair

                            if dir_pairs != '':
                                dir_pairs += f";{dir_pair}"
                            else:
                                dir_pairs = dir_pair

                            logger.info(f"[{task_name}] 添加同步目录对: {dir_pair}")
                        alist_sync.main(dir_pairs, sync_del_action, exclude_dirs)

            except KeyError as e:
                logger.error(f"[{task_name}] 任务配置错误: {e}")
                continue

        # 检查是否有有效的同步目录对
        if 'DIR_PAIRS' not in os.environ or not os.environ['DIR_PAIRS']:
            logger.error("没有有效的同步目录对")
            return False

        logger.info(f"[{task_name}] 开始执行同步任务，同步目录对: {os.environ['DIR_PAIRS']}")

        # 调用 alist_sync 的 main 函数
        alist_sync.main()
        logger.info(f"[{task_name}] 同步任务执行完成")
        return True

    except Exception as e:
        logger.error(f"[{task_name}] 执行同步任务失败: {str(e)}")
        return False


def load_base_config() -> dict:
    """加载基础配置"""
    try:
        config_file_path = os.path.join(STORAGE_DIR, 'base_config.json')
        if not os.path.exists(config_file_path):
            logger.warning(f"基础配置文件不存在: {config_file_path}")
            return {}

        with open(config_file_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            # logger.info(f"成功加载基础配置: {config}")
            logger.info(f"成功加载基础配置")
            return config
    except Exception as e:
        logger.error(f"加载基础配置失败: {e}")
        return {}


def load_sync_config() -> dict:
    """加载同步配置"""
    try:
        sync_config_file_path = os.path.join(STORAGE_DIR, 'sync_config.json')
        if not os.path.exists(sync_config_file_path):
            logger.warning(f"同步配置文件不存在: {sync_config_file_path}")
            return {"tasks": []}

        with open(sync_config_file_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            logger.info(f"成功加载同步配置: {config}")
            return config
    except Exception as e:
        logger.error(f"加载同步配置失败: {e}")
        return {"tasks": []}


# 在 if __name__ == '__main__': 之前添加初始化调度的代码
def init_scheduler():
    """
    初始化调度器并加载现有任务
    """
    try:
        schedule_sync_tasks()
        logger.info("调度器初始化完成")
    except Exception as e:
        logger.error(f"初始化调度器失败: {str(e)}")


# 修改日志配置部分
def setup_logger():
    """配置日志记录器"""
    # 创建日志目录
    log_dir = os.path.join(app.root_path, 'data/log')
    os.makedirs(log_dir, exist_ok=True)

    # 设置日志文件路径
    log_file = os.path.join(log_dir, 'alist_sync.log')

    # 创建 TimedRotatingFileHandler
    file_handler = TimedRotatingFileHandler(
        filename=log_file,
        when='midnight',
        interval=1,
        backupCount=7,
        encoding='utf-8'
    )

    # 创建控制台处理器
    console_handler = logging.StreamHandler()

    # 设置日志格式
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # 配置根日志记录器
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # 清除现有的处理器
    logger.handlers.clear()

    # 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# 在 app 创建后调用
logger = setup_logger()


# 添加获取日志的接口
@app.route('/api/logs', methods=['GET'])
@login_required
def get_logs():
    try:
        # 获取请求参数中的日期
        date_str = request.args.get('date')

        # 构建日志文件路径
        log_dir = os.path.join(app.root_path,'data/log')

        # 如果是请求当前日志或没有指定日期
        if not date_str or date_str == 'current':
            log_file = os.path.join(log_dir, 'alist_sync.log')
            date_str = 'current'
        else:
            # 历史日志文件
            log_file = os.path.join(log_dir, f'alist_sync.log.{date_str}')

        logs = []
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
            logs.append({
                'date': date_str,
                'content': content
            })

        return jsonify({
            'code': 200,
            'data': logs
        })

    except Exception as e:
        logger.error(f"获取日志失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f"获取日志失败: {str(e)}"
        })


if __name__ == '__main__':
    init_scheduler()
    app.run(host='0.0.0.0', port=52441, debug=False)
