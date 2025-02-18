from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import logging
import os
import json
import hashlib
import croniter
import datetime
import time
from functools import wraps
import importlib.util
import sys
from typing import Dict, List, Optional, Any
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from logging.handlers import TimedRotatingFileHandler
import shutil
import http.client
import urllib.parse
import re
import socket


# 替换 passlib 的密码哈希功能
def hash_password(password: str) -> str:
    """使用 SHA-256 哈希密码"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hash: str) -> bool:
    """验证密码哈希"""
    return hash_password(password) == hash


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
    alist_sync = import_from_file('alist_sync', os.path.join(current_dir, 'alist_sync.py'))
    AlistSync = alist_sync.AlistSync
except Exception as e:
    print(f"导入alist_sync.py失败: {e}")
    print(f"当前目录: {current_dir}")
    print(f"尝试导入的文件路径: {os.path.join(current_dir, 'alist_sync.py')}")
    raise

app = Flask(__name__)
app.secret_key = os.urandom(24)  # 用于session加密

# 设置日志记录器
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 假设配置数据存储在当前目录下的config_data目录中，你可以根据实际需求修改
STORAGE_DIR = os.path.join(app.root_path, 'data/config')
if not os.path.exists(STORAGE_DIR):
    os.makedirs(STORAGE_DIR)

# 用户配置文件路径
USER_CONFIG_FILE = os.path.join(os.path.dirname(__file__), STORAGE_DIR, 'alist_sync_users_config.json')

# 确保配置目录存在
os.makedirs(os.path.dirname(USER_CONFIG_FILE), exist_ok=True)

# 如果用户配置文件不存在,创建默认配置
if not os.path.exists(USER_CONFIG_FILE):
    default_config = {
        "users": [
            {
                "username": "admin",
                "password": hash_password("admin")  # 使用新的哈希函数
            }
        ]
    }
    with open(USER_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(default_config, f, indent=2, ensure_ascii=False)

# 添加版本配置文件路径常量
VERSION_CONFIG_FILE = os.path.join(os.path.dirname(__file__), STORAGE_DIR, 'alist_sync_version.json')

# 确保配置目录存在
os.makedirs(os.path.dirname(VERSION_CONFIG_FILE), exist_ok=True)

# 如果版本配置文件不存在，创建默认配置
if not os.path.exists(VERSION_CONFIG_FILE):
    default_version_config = {
        "latest_version": "",
        "update_time": "",
        "source": "github"
    }
    with open(VERSION_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(default_version_config, f, indent=2, ensure_ascii=False)


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


# 优化日志配置
def setup_logger():
    """配置日志记录器"""
    log_dir = os.path.join(app.root_path, 'data/log')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'alist_sync.log')

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # 文件处理器
    file_handler = TimedRotatingFileHandler(
        filename=log_file,
        when='midnight',
        interval=1,
        backupCount=7,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # 配置根日志记录器
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# 优化用户认证相关代码
class UserManager:
    def __init__(self, config_file: str):
        self.config_file = config_file
        self._ensure_config_exists()

    def _ensure_config_exists(self):
        """确保用户配置文件存在"""
        if not os.path.exists(self.config_file):
            default_config = {
                "users": [{
                    "username": "admin",
                    "password": hash_password("admin")
                }]
            }
            self.save_config(default_config)

    def load_config(self) -> Dict:
        """加载用户配置"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载用户配置失败: {e}")
            return {"users": []}

    def save_config(self, config: Dict) -> bool:
        """保存用户配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"保存用户配置失败: {e}")
            return False

    def verify_user(self, username: str, password: str) -> bool:
        """验证用户凭据"""
        config = self.load_config()
        user = next((u for u in config['users'] if u['username'] == username), None)
        return user and verify_password(password, user['password'])

    def change_user_password(self, username: str, new_username: str,
                             old_password: str, new_password: str) -> tuple[bool, str]:
        """修改用户密码"""
        config = self.load_config()
        user = next((u for u in config['users'] if u['username'] == username), None)

        if not user:
            return False, "用户不存在"

        if not verify_password(old_password, user['password']):
            return False, "原密码错误"

        if username != new_username:
            exists_user = next((u for u in config['users']
                                if u['username'] == new_username and u != user), None)
            if exists_user:
                return False, "新用户名已存在"

        user['username'] = new_username
        user['password'] = hash_password(new_password)

        if self.save_config(config):
            return True, "修改成功"
        return False, "保存配置失败"


# 创建用户管理器实例
user_manager = UserManager(USER_CONFIG_FILE)


# 优化登录接口
@app.route('/api/login', methods=['POST'])
def api_login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'code': 400, 'message': '用户名和密码不能为空'})

        if user_manager.verify_user(username, password):
            session['user_id'] = username
            return jsonify({'code': 200, 'message': '登录成功'})
        return jsonify({'code': 401, 'message': '用户名或密码错误'})

    except Exception as e:
        logger.error(f"登录失败: {e}")
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


# 优化修改密码接口
@app.route('/api/change-password', methods=['POST'])
@login_required
def change_password():
    try:
        data = request.get_json()
        if not all(data.get(k) for k in ['oldUsername', 'newUsername', 'oldPassword', 'newPassword']):
            return jsonify({'code': 400, 'message': '所有字段都不能为空'})

        success, message = user_manager.change_user_password(
            data['oldUsername'],
            data['newUsername'],
            data['oldPassword'],
            data['newPassword']
        )

        if success:
            if data['oldUsername'] != data['newUsername']:
                session['user_id'] = data['newUsername']
            return jsonify({'code': 200, 'message': message})
        return jsonify({'code': 400, 'message': message})

    except Exception as e:
        logger.error(f"修改密码失败: {e}")
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
    if config_manager.save('alist_sync_base_config', data):
        return jsonify({"code": 200, "message": "基础配置保存成功"})
    return jsonify({"code": 500, "message": "保存失败"})


# 查询基础连接配置接口
@app.route('/api/get-base-config', methods=['GET'])
@login_required
def get_base_config():
    config = config_manager.load('alist_sync_base_config')
    if config:
        return jsonify({"code": 200, "data": config})
    return jsonify({"code": 404, "message": "配置文件不存在"})


@app.route('/api/get-sync-config', methods=['GET'])
@login_required
def get_sync_config():
    config = config_manager.load('alist_sync_sync_config')
    if config:
        return jsonify({"code": 200, "data": config})
    return jsonify({"code": 404, "message": "配置文件不存在"})


# 定义超时处理函数
def timeout_handler(signum, frame):
    raise TimeoutError("连接测试超时")


# 测试连接接口
@app.route('/api/test-connection', methods=['POST'])
@login_required
def test_connection():
    try:
        data = request.get_json()
        alist = AlistSync(
            data.get('baseUrl'),
            data.get('username'),
            data.get('password'),
            data.get('token')
        )

        return jsonify({
            "code": 200 if alist.login() else 500,
            "message": "连接测试成功" if alist.login() else "地址或用户名或密码或令牌错误"
        })
    except Exception as e:
        logger.error(f"连接测试失败: {str(e)}")
        return jsonify({"code": 500, "message": f"连接测试失败: {str(e)}"})
    finally:
        if 'alist' in locals():
            alist.close()


# 添加以下函数来管理定时任务
def schedule_sync_tasks():
    """从配置文件读取并调度所有同步任务"""
    scheduler_manager.reload_tasks()


# 优化配置管理
class ConfigManager:
    def __init__(self, storage_dir: str):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

    def load(self, config_name: str) -> Optional[Dict]:
        """加载配置文件"""
        config_file = os.path.join(self.storage_dir, f'{config_name}.json')
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"配置文件不存在: {config_file}")
            return None
        except Exception as e:
            logger.error(f"读取配置失败: {str(e)}")
            return None

    def save(self, config_name: str, data: Dict) -> bool:
        """保存配置文件"""
        # 遍历 tasks 列表，检查 syncMode 是否为 file_move，如果是则将 syncDelAction 修改为 none
        for task in data.get("tasks", []):
            if task.get("syncMode") == "file_move":
                task["syncDelAction"] = "none"

        config_file = os.path.join(self.storage_dir, f'{config_name}.json')
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {str(e)}")
            return False


# 优化任务执行管理
class TaskManager:
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager

    def execute_task(self, task_id: Optional[int] = None) -> bool:
        """执行同步任务"""
        try:
            logger.info("开始执行同步任务")

            # 加载配置
            sync_config = self.config_manager.load('alist_sync_sync_config')
            base_config = self.config_manager.load('alist_sync_base_config')

            if not sync_config or not base_config:
                logger.error("配置为空，无法执行同步任务")
                return False

            # 设置基础环境变量
            self._setup_env_vars(base_config)

            # 处理任务
            tasks = sync_config.get('tasks', [])
            if not tasks:
                logger.error("没有配置同步任务")
                return False

            for task in tasks:
                if task_id is not None and task_id != task['id']:
                    continue

                self._execute_single_task(task)

            return True

        except Exception as e:
            logger.error(f"执行同步任务失败: {str(e)}")
            return False

    def _setup_env_vars(self, base_config: Dict):
        """设置环境变量"""
        # 清除旧的环境变量
        for key in list(os.environ.keys()):
            if key.startswith('DIR_PAIRS'):
                del os.environ[key]

        # 设置新的环境变量
        os.environ.update({
            'BASE_URL': base_config.get('baseUrl', ''),
            'USERNAME': base_config.get('username', ''),
            'PASSWORD': base_config.get('password', ''),
            'TOKEN': base_config.get('token', '')
        })

    def _execute_single_task(self, task: Dict):
        """执行单个任务"""
        task_name = task.get('taskName', '未知任务')
        sync_del_action = task.get('syncDelAction', 'none')
        logger.info(f"[{task_name}] 开始处理任务，差异处置策略: {sync_del_action}")

        os.environ['SYNC_DELETE_ACTION'] = sync_del_action
        os.environ['EXCLUDE_DIRS'] = task.get('excludeDirs', '')

        # 添加正则表达式环境变量
        if task.get('regexPatterns'):
            os.environ['REGEX_PATTERNS'] = task.get('regexPatterns')

        if task['syncMode'] == 'data':
            self._handle_data_sync(task)
        elif task['syncMode'] == 'file':
            self._handle_file_sync(task)
        elif task['syncMode'] == 'file_move':
            self._handle_file_move(task)

    def _handle_data_sync(self, task: Dict):
        """处理数据同步模式"""
        source = task['sourceStorage']
        sync_dirs = task['syncDirs']
        exclude_dirs = task['excludeDirs']

        if source not in exclude_dirs:
            exclude_dirs = f'{source}/{exclude_dirs}'
        exclude_dirs = exclude_dirs.replace('//', '/')

        dir_pairs = []
        for target in task['targetStorages']:
            if source != target:
                dir_pair = f"{source}/{sync_dirs}:{target}/{sync_dirs}".replace('//', '/')
                dir_pairs.append(dir_pair)

        if dir_pairs:
            os.environ['DIR_PAIRS'] = ';'.join(dir_pairs)
            alist_sync.main()

    def _handle_file_sync(self, task: Dict):
        """处理文件同步模式"""
        dir_pairs = [f"{path['srcPath']}:{path['dstPath']}" for path in task['paths']]
        if dir_pairs:
            os.environ['DIR_PAIRS'] = ';'.join(dir_pairs)
            alist_sync.main()

    def _handle_file_move(self, task: Dict):
        """处理文件移动模式"""
        dir_pairs = [f"{path['srcPathMove']}:{path['dstPathMove']}" for path in task['paths']]
        if dir_pairs:
            os.environ['MOVE_FILE'] = 'true'
            os.environ['DIR_PAIRS'] = ';'.join(dir_pairs)
            alist_sync.main()


# 创建管理器实例
config_manager = ConfigManager(STORAGE_DIR)
task_manager = TaskManager(config_manager)


# 优化配置相关接口
@app.route('/api/save-sync-config', methods=['POST'])
@login_required
def save_sync_config():
    data = request.get_json()
    if config_manager.save('alist_sync_sync_config', data):
        schedule_sync_tasks()
        return jsonify({"code": 200, "message": "同步配置保存成功并已更新调度"})
    return jsonify({"code": 500, "message": "保存失败"})


@app.route('/api/run-task', methods=['POST'])
@login_required
def run_task():
    try:
        task_id = request.get_json().get('id')
        if task_manager.execute_task(task_id):
            return jsonify({"code": 200, "message": "同步任务执行成功"})
        return jsonify({"code": 500, "message": "同步任务执行失败"})
    except Exception as e:
        logger.error(f"执行任务失败: {str(e)}")
        return jsonify({"code": 500, "message": f"执行任务时发生错误: {str(e)}"})


# 修改存储列表获取接口
@app.route('/api/storages', methods=['GET'])
@login_required
def get_storages():
    try:
        config = config_manager.load('alist_sync_base_config')  # 使用 config_manager 替代 load_config
        if not config:
            return jsonify({"code": 404, "message": "基础配置不存在"})

        alist = AlistSync(
            config.get('baseUrl'),
            config.get('username'),
            config.get('password'),
            config.get('token')
        )

        if alist.login():
            storage_list = alist.get_storage_list()
            return jsonify({"code": 200, "data": storage_list})
        return jsonify({"code": 500, "message": "获取存储列表失败：登录失败"})

    except Exception as e:
        logger.error(f"获取存储列表失败: {str(e)}")
        return jsonify({"code": 500, "message": f"获取存储列表失败: {str(e)}"})
    finally:
        if 'alist' in locals():
            alist.close()


# 优化时间处理相关代码
class TimeUtils:
    @staticmethod
    def get_timestamp() -> int:
        """获取当前时间戳"""
        return int(time.time())

    @staticmethod
    def datetime_to_timestamp(dt_str: str, fmt: str = "%Y-%m-%d %H:%M:%S") -> int:
        """时间字符串转时间戳"""
        try:
            return int(time.mktime(time.strptime(dt_str, fmt)))
        except Exception as e:
            logger.error(f"时间转换失败: {e}")
            raise

    @staticmethod
    def timestamp_to_datetime(ts: int, fmt: str = '%Y-%m-%d %H:%M:%S') -> str:
        """时间戳转时间字符串"""
        return time.strftime(fmt, time.localtime(ts))

    @staticmethod
    def get_next_run_times(cron_expr: str, count: int = 5) -> List[str]:
        """获取下次运行时间列表"""
        try:
            now = datetime.datetime.now()
            cron = croniter.croniter(cron_expr, now)
            return [
                cron.get_next(datetime.datetime).strftime("%Y-%m-%d %H:%M:%S")
                for _ in range(count)
            ]
        except Exception as e:
            logger.error(f"获取运行时间失败: {e}")
            raise


# 优化调度器管理
class SchedulerManager:
    def __init__(self, config_manager: ConfigManager, task_manager: TaskManager):
        self.scheduler = BackgroundScheduler()
        self.config_manager = config_manager
        self.task_manager = task_manager

    def start(self):
        """启动调度器"""
        try:
            self.scheduler.start()
            self.reload_tasks()
            logger.info("调度器启动成功")
        except Exception as e:
            logger.error(f"调度器启动失败: {e}")
            raise

    def stop(self):
        """停止调度器"""
        try:
            self.scheduler.shutdown()
            logger.info("调度器已停止")
        except Exception as e:
            logger.error(f"停止调度器失败: {e}")

    def reload_tasks(self):
        """重新加载所有任务"""
        try:
            self.scheduler.remove_all_jobs()
            sync_config = self.config_manager.load('alist_sync_sync_config')

            if not sync_config or 'tasks' not in sync_config:
                logger.warning("没有找到有效的同步任务配置")
                return

            for task in sync_config['tasks']:
                self._add_task(task)

        except Exception as e:
            logger.error(f"重新加载任务失败: {e}")

    def _add_task(self, task: Dict):
        """添加单个任务"""
        try:
            if 'cron' not in task:
                logger.warning(f"任务 {task.get('taskName', 'unknown')} 没有配置cron表达式")
                return

            job_id = f"sync_task_{task['id']}"
            self.scheduler.add_job(
                func=self.task_manager.execute_task,
                trigger=CronTrigger.from_crontab(task['cron']),
                id=job_id,
                replace_existing=True,
                args=[task['id']]
            )
            logger.info(f"成功添加任务 {task['taskName']}, ID: {job_id}, Cron: {task['cron']}")

        except Exception as e:
            logger.error(f"添加任务失败: {e}")


# 创建调度器管理器实例
scheduler_manager = SchedulerManager(config_manager, task_manager)


# 优化相关接口
@app.route('/api/next-run-time', methods=['POST'])
@login_required
def next_run_time():
    try:
        data = request.get_json()
        cron_expr = data.get('cron', '').strip()

        # 如果没有提供cron表达式，尝试从配置中获取
        if not cron_expr:
            task_id = data.get('id')
            if task_id is not None:
                sync_config = config_manager.load('alist_sync_sync_config')
                if sync_config and 'tasks' in sync_config:
                    task = next((t for t in sync_config['tasks'] if t['id'] == task_id), None)
                    if task and 'cron' in task:
                        cron_expr = task['cron']

        if not cron_expr:
            return jsonify({"code": 400, "message": "缺少cron参数"})

        next_times = TimeUtils.get_next_run_times(cron_expr)
        return jsonify({
            "code": 200,
            "data": next_times,
            "cron": cron_expr  # 返回使用的cron表达式
        })
    except Exception as e:
        logger.error(f"解析cron表达式失败: {e}")
        return jsonify({"code": 500, "message": f"解析出错: {str(e)}"})


# 将日志接口移到主函数之前
@app.route('/api/logs', methods=['GET'])
@login_required
def get_logs():
    try:
        date_str = request.args.get('date')
        log_dir = os.path.join(app.root_path, 'data/log')

        if not date_str or date_str == 'current':
            log_file = os.path.join(log_dir, 'alist_sync.log')
            date_str = 'current'
        else:
            log_file = os.path.join(log_dir, f'alist_sync.log.{date_str}')

        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
            return jsonify({
                'code': 200,
                'data': [{
                    'date': date_str,
                    'content': content
                }]
            })
        return jsonify({
            'code': 404,
            'message': '日志文件不存在'
        })

    except Exception as e:
        logger.error(f"获取日志失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f"获取日志失败: {str(e)}"
        })


# 添加导出配置文件接口
@app.route('/api/export-config', methods=['POST'])
@login_required
def export_config():
    try:
        config_type = request.json.get('type')
        if not config_type:
            return jsonify({'code': 400, 'message': '请指定配置类型'})

        # 获取当前时间戳
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

        # 根据类型确定源文件和目标文件
        if config_type == 'sync':
            src_file = os.path.join(STORAGE_DIR, 'alist_sync_sync_config.json')
            dst_file = f'alist_sync_sync_config_{timestamp}.json'
        elif config_type == 'base':
            src_file = os.path.join(STORAGE_DIR, 'alist_sync_base_config.json')
            dst_file = f'alist_sync_base_config_{timestamp}.json'
        else:
            return jsonify({'code': 400, 'message': '无效的配置类型'})

        if not os.path.exists(src_file):
            return jsonify({'code': 404, 'message': '配置文件不存在'})

        # 读取配置文件内容
        with open(src_file, 'r', encoding='utf-8') as f:
            config_data = json.load(f)

        return jsonify({
            'code': 200,
            'data': {
                'content': config_data,
                'filename': dst_file
            }
        })

    except Exception as e:
        logger.error(f"导出配置失败: {str(e)}")
        return jsonify({'code': 500, 'message': f'导出配置失败: {str(e)}'})


# 添加导入配置文件接口
@app.route('/api/import-config', methods=['POST'])
@login_required
def import_config():
    try:
        data = request.get_json()
        config_type = data.get('type')
        config_content = data.get('content')

        if not config_type or not config_content:
            return jsonify({'code': 400, 'message': '请提供配置类型和内容'})

        # 检查基础配置文件是否存在
        base_config_file = os.path.join(STORAGE_DIR, 'alist_sync_base_config.json')
        if config_type == 'sync' and not os.path.exists(base_config_file):
            return jsonify({'code': 400, 'message': '请先导入基础配置文件'})

        # 根据类型确定目标文件
        if config_type == 'sync':
            dst_file = os.path.join(STORAGE_DIR, 'alist_sync_sync_config.json')
        elif config_type == 'base':
            dst_file = os.path.join(STORAGE_DIR, 'alist_sync_base_config.json')
        else:
            return jsonify({'code': 400, 'message': '无效的配置类型'})

        # 备份原配置文件
        backup_file = None
        if os.path.exists(dst_file):
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = f"{dst_file}.{timestamp}.bak"
            shutil.copy2(dst_file, backup_file)

        try:
            # 写入新配置
            with open(dst_file, 'w', encoding='utf-8') as f:
                json.dump(config_content, f, indent=2, ensure_ascii=False)

            # 如果是同步配置,需要重新加载调度任务
            if config_type == 'sync':
                scheduler_manager.reload_tasks()

            # 清理超过7天的备份文件
            cleanup_backup_files(STORAGE_DIR)

            return jsonify({'code': 200, 'message': '导入配置成功'})

        except Exception as e:
            # 如果写入失败且有备份,恢复备份
            if backup_file and os.path.exists(backup_file):
                shutil.copy2(backup_file, dst_file)
            raise

    except Exception as e:
        logger.error(f"导入配置失败: {str(e)}")
        return jsonify({'code': 500, 'message': f'导入配置失败: {str(e)}'})


# 添加清理备份文件的函数
def cleanup_backup_files(directory: str, days: int = 7):
    """清理指定目录下超过指定天数的备份文件"""
    try:
        current_time = datetime.datetime.now()
        for filename in os.listdir(directory):
            if filename.endswith('.bak'):
                file_path = os.path.join(directory, filename)
                file_time = datetime.datetime.fromtimestamp(os.path.getctime(file_path))
                if (current_time - file_time).days > days:
                    try:
                        os.remove(file_path)
                        logger.info(f"已删除过期备份文件: {filename}")
                    except Exception as e:
                        logger.error(f"删除备份文件失败 {filename}: {str(e)}")
    except Exception as e:
        logger.error(f"清理备份文件失败: {str(e)}")


def get_current_version():
    """获取当前运行版本"""
    try:
        logger.info("开始获取当前版本...")

        # 1. 尝试从环境变量直接获取
        version = os.getenv('VERSION')
        if version:
            logger.info(f"从环境变量获取到版本号: {version}")
            return version.lstrip('v')

        # 2. 如果环境变量没有，则从VERSION文件获取
        version_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'VERSION')
        logger.info(f"尝试从VERSION文件获取版本号，文件路径: {version_file}")
        if os.path.exists(version_file):
            with open(version_file, 'r') as f:
                version = f.read().strip()
                logger.info(f"从VERSION文件获取到版本号: {version}")
                return version.lstrip('v')
        else:
            logger.warning(f"VERSION文件不存在: {version_file}")

        return "unknown"

    except Exception as e:
        logger.error(f"获取当前版本失败: {e}")
        return "unknown"


def load_version_config():
    """加载版本配置"""
    try:
        with open(VERSION_CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载版本配置失败: {e}")
        return {
            "latest_version": "",
            "update_time": "",
            "source": "github"
        }


def save_version_config(config):
    """保存版本配置"""
    try:
        with open(VERSION_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"保存版本配置失败: {e}")
        return False


def should_update_version(update_time):
    """检查是否需要更新版本信息"""
    if not update_time:
        return True
    try:
        last_update = datetime.datetime.fromisoformat(update_time)
        now = datetime.datetime.now()
        return (now - last_update).days >= 7
    except Exception as e:
        logger.error(f"检查更新时间失败: {e}")
        return True


def get_latest_version_from_github():
    """从 GitHub 获取最新版本"""
    # 首先尝试从 GitHub 获取
    parsed_url = urllib.parse.urlparse("https://api.github.com/repos/xjxjin/alist-sync/tags")
    logger.info(f"尝试从GitHub获取: {parsed_url.geturl()}")
    conn = http.client.HTTPSConnection(parsed_url.netloc)

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; AlistSync/1.0;)'
        }
        conn.request("GET", parsed_url.path, headers=headers)
        response = conn.getresponse()
        logger.info(f"GitHub API响应状态码: {response.status}")

        if response.status == 200:
            data = json.loads(response.read().decode())
            if data:
                version_tags = []
                for tag in data:
                    tag_name = tag['name'].lstrip('v')
                    if re.match(r'^\d+\.\d+\.\d+(\.\d+)?$', tag_name):
                        version_tags.append(tag_name)
                if version_tags:
                    version_tags.sort(key=lambda v: [int(x) for x in v.split('.')])
                    latest = version_tags[-1]
                    logger.info(f"从GitHub获取到最新版本: {latest}")
                    return latest
            logger.warning("GitHub返回数据中没有有效的版本标签")

    except (socket.timeout, TimeoutError) as e:
        logger.error(f"从GitHub获取版本超时: {e}")
        return None
    except Exception as e:
        logger.error(f"从GitHub获取版本失败: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()


def get_latest_version_from_gitee():
    """从 Gitee 获取最新版本"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; AlistSync/1.0;)'
        }
        # 如果从 GitHub 获取失败，尝试从 Gitee 获取
        logger.info("从GitHub获取失败，尝试从Gitee获取...")
        parsed_url = urllib.parse.urlparse("https://gitee.com/api/v5/repos/xjxjin/alist-sync/tags")
        logger.info(f"尝试从Gitee获取: {parsed_url.geturl()}")
        conn = http.client.HTTPSConnection(parsed_url.netloc)
        conn.request("GET", parsed_url.path, headers=headers)
        response = conn.getresponse()
        logger.info(f"Gitee API响应状态码: {response.status}")

        if response.status == 200:
            data = json.loads(response.read().decode())
            if data:
                version_tags = []
                for tag in data:
                    tag_name = tag['name'].lstrip('v')
                    if re.match(r'^\d+\.\d+\.\d+(\.\d+)?$', tag_name):
                        version_tags.append(tag_name)
                if version_tags:
                    version_tags.sort(key=lambda v: [int(x) for x in v.split('.')])
                    latest = version_tags[-1]
                    logger.info(f"从Gitee获取到最新版本: {latest}")
                    return latest
            logger.warning("Gitee返回数据中没有有效的版本标签")

        logger.warning("无法从GitHub和Gitee获取最新版本")
        return "unknown"
    except (socket.timeout, TimeoutError) as e:
        logger.error(f"从Gitee获取版本超时: {e}")
        return None
    except Exception as e:
        logger.error(f"从Gitee获取版本失败: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()


def get_latest_version():
    """获取最新版本号"""
    try:
        logger.info("开始获取最新版本...")
        # 首先尝试从 GitHub 获取
        parsed_url = urllib.parse.urlparse("https://api.github.com/repos/xjxjin/alist-sync/tags")
        logger.info(f"尝试从GitHub获取: {parsed_url.geturl()}")
        conn = http.client.HTTPSConnection(parsed_url.netloc)

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; AlistSync/1.0;)'
            }
            conn.request("GET", parsed_url.path, headers=headers)
            response = conn.getresponse()
            logger.info(f"GitHub API响应状态码: {response.status}")

            if response.status == 200:
                data = json.loads(response.read().decode())
                if data:
                    version_tags = []
                    for tag in data:
                        tag_name = tag['name'].lstrip('v')
                        if re.match(r'^\d+\.\d+\.\d+(\.\d+)?$', tag_name):
                            version_tags.append(tag_name)
                    if version_tags:
                        version_tags.sort(key=lambda v: [int(x) for x in v.split('.')])
                        latest = version_tags[-1]
                        logger.info(f"从GitHub获取到最新版本: {latest}")
                        return latest
                logger.warning("GitHub返回数据中没有有效的版本标签")

            # 如果从 GitHub 获取失败，尝试从 Gitee 获取
            logger.info("从GitHub获取失败，尝试从Gitee获取...")
            parsed_url = urllib.parse.urlparse("https://gitee.com/api/v5/repos/xjxjin/alist-sync/tags")
            logger.info(f"尝试从Gitee获取: {parsed_url.geturl()}")
            conn = http.client.HTTPSConnection(parsed_url.netloc)
            conn.request("GET", parsed_url.path, headers=headers)
            response = conn.getresponse()
            logger.info(f"Gitee API响应状态码: {response.status}")

            if response.status == 200:
                data = json.loads(response.read().decode())
                if data:
                    version_tags = []
                    for tag in data:
                        tag_name = tag['name'].lstrip('v')
                        if re.match(r'^\d+\.\d+\.\d+(\.\d+)?$', tag_name):
                            version_tags.append(tag_name)
                    if version_tags:
                        version_tags.sort(key=lambda v: [int(x) for x in v.split('.')])
                        latest = version_tags[-1]
                        logger.info(f"从Gitee获取到最新版本: {latest}")
                        return latest
                logger.warning("Gitee返回数据中没有有效的版本标签")

            logger.warning("无法从GitHub和Gitee获取最新版本")
            return "unknown"

        finally:
            conn.close()

    except Exception as e:
        logger.error(f"获取最新版本失败: {e}")
        return "unknown"


# 添加新的API路由
@app.route('/api/version', methods=['GET'])
def get_version():
    try:
        current_version = get_current_version()
        # latest_version = get_latest_version()
        source = "github"
        # 检查是否需要更新版本信息

        version_config = load_version_config()
        if should_update_version(version_config.get('update_time')):
            latest_version = get_latest_version_from_github()
            if not latest_version:
                latest_version = get_latest_version_from_gitee()
                source = "gitee"
            if latest_version:
                version_config.update({
                    'latest_version': latest_version,
                    'update_time': datetime.datetime.now().isoformat(),
                    'source': source
                })

            else:
                # 如果获取失败，使用缓存的版本
                latest_version = version_config.get('latest_version', 'unknown')
            save_version_config(version_config)
        else:
            # 使用缓存的版本
            latest_version = version_config.get('latest_version', 'unknown')

        return jsonify({
            'code': 200,
            'data': {
                'current_version': current_version,
                'latest_version': latest_version
            }
        })
    except Exception as e:
        logger.error(f"获取版本信息失败: {e}")
        return jsonify({
            'code': 500,
            'message': f"获取版本信息失败: {str(e)}"
        })


# 主函数
if __name__ == '__main__':
    try:
        # 启动调度器
        scheduler_manager.start()
        # 启动Web服务
        app.run(host='0.0.0.0', port=52441, debug=False)
    except Exception as e:
        logger.error(f"启动失败: {e}")
    finally:
        # 确保调度器正确关闭
        scheduler_manager.stop()
