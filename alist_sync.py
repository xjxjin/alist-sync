import http.client
import json
import re
from datetime import datetime, timedelta
import os
import logging
from typing import List, Dict, Optional, Union
from logging.handlers import TimedRotatingFileHandler


def setup_logger():
    """配置日志记录器"""
    # 获取当前文件所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 创建日志目录
    log_dir = os.path.join(current_dir, 'config_log')
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

    # 避免重复添加处理器
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger


# 初始化日志记录器
logger = setup_logger()


def parse_time_and_adjust_utc(date_str: str) -> datetime:
    """
    解析时间字符串，如果是UTC格式（包含'Z'）则加8小时
    """
    iso_8601_pattern = r'(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(\.\d+)?([+-]\d{2}:\d{2}|Z)?'
    match_iso = re.match(iso_8601_pattern, date_str)
    if match_iso:
        year, month, day, hour, minute, second, microsecond, timezone = match_iso.groups()
        if microsecond:
            microsecond = int(float(microsecond) * 1000000)
        else:
            microsecond = 0
        dt = datetime(int(year), int(month), int(day), int(hour), int(minute), int(second), microsecond)
        if timezone == "Z":
            dt = dt + timedelta(hours=8)  # UTC时间加8小时
        elif timezone:
            # 处理其他时区偏移量
            sign = 1 if timezone[0] == "+" else -1
            hours = int(timezone[1:3])
            minutes = int(timezone[4:6])
            offset = timedelta(hours=sign * hours, minutes=sign * minutes)
            dt = dt - offset
        return dt
    return None


class AlistSync:
    def __init__(self, base_url: str, username: str, password: str, sync_delete_action: str = "none"):
        """初始化AlistSync类"""
        self.base_url = base_url
        self.username = username
        self.password = password
        self.sync_delete_action = sync_delete_action.lower()
        self.sync_delete = self.sync_delete_action in ["move", "delete"]
        self.connection = self._create_connection()
        self.token = None

    def _create_connection(self) -> Union[http.client.HTTPConnection, http.client.HTTPSConnection]:
        """创建HTTP(S)连接"""
        try:
            match = re.match(r"(?:http[s]?://)?([^:/]+)(?::(\d+))?", self.base_url)
            if not match:
                raise ValueError("Invalid base URL format")

            host = match.group(1)
            port_part = match.group(2)
            port = int(port_part) if port_part else (443 if self.base_url.startswith("https://") else 80)

            logger.info(f"创建连接 - 主机: {host}, 端口: {port}")
            return (http.client.HTTPSConnection(host, port)
                    if self.base_url.startswith("https://")
                    else http.client.HTTPConnection(host, port))
        except Exception as e:
            logger.error(f"创建连接失败: {str(e)}")
            raise

    def _make_request(self, method: str, path: str, headers: Dict = None,
                      payload: str = None) -> Optional[Dict]:
        """发送HTTP请求并返回JSON响应"""
        try:
            logger.debug(f"发送请求 - 方法: {method}, 路径: {path}")
            self.connection.request(method, path, body=payload, headers=headers)
            response = self.connection.getresponse()
            result = json.loads(response.read().decode("utf-8"))
            logger.debug(f"请求响应: {result}")
            return result
        except Exception as e:
            logger.error(f"请求失败 - 方法: {method}, 路径: {path}, 错误: {str(e)}")
            return None

    def login(self) -> bool:
        """登录并获取token"""
        payload = json.dumps({"username": self.username, "password": self.password})
        headers = {
            "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
            "Content-Type": "application/json"
        }
        response = self._make_request("POST", "/api/auth/login", headers, payload)
        if response and response.get("data", {}).get("token"):
            self.token = response["data"]["token"]
            return True
        logger.error("获取token失败")
        return False

    def _directory_operation(self, operation: str, **kwargs) -> Optional[Dict]:
        """执行目录操作"""
        if not self.token:
            if not self.login():
                return None

        headers = {
            "Authorization": self.token,
            "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
            "Content-Type": "application/json"
        }
        payload = json.dumps(kwargs)
        path = f"/api/fs/{operation}"
        return self._make_request("POST", path, headers, payload)

    def get_directory_contents(self, directory_path: str) -> List[Dict]:
        """获取目录内容"""
        response = self._directory_operation("list", path=directory_path)
        return response.get("data", {}).get("content", []) if response else []

    def create_directory(self, directory_path: str) -> bool:
        """创建目录"""
        response = self._directory_operation("mkdir", path=directory_path)
        if response:
            logger.info(f"文件夹【{directory_path}】创建成功")
            return True
        logger.error("文件夹创建失败")
        return False

    def copy_item(self, src_dir: str, dst_dir: str, item_name: str) -> bool:
        """复制文件或目录"""
        response = self._directory_operation("copy",
                                             src_dir=src_dir,
                                             dst_dir=dst_dir,
                                             names=[item_name])
        if response:
            logger.info(f"文件【{item_name}】复制成功")
            return True
        logger.error("文件复制失败")
        return False

    def move_item(self, src_dir: str, dst_dir: str, item_name: str) -> bool:
        """移动文件或目录"""
        response = self._directory_operation("move",
                                             src_dir=src_dir,
                                             dst_dir=dst_dir,
                                             names=[item_name])
        if response:
            logger.info(f"文件从【{src_dir}/{item_name}】移动到【{dst_dir}/{item_name}】移动成功")
            return True
        logger.error("文件移动失败")
        return False

    def is_path_exists(self, path: str) -> bool:
        """检查路径是否存在"""
        response = self._directory_operation("get", path=path)
        return bool(response and response.get("message") == "success")

    def get_storage_list(self) -> List[str]:
        """获取存储列表"""
        if not self.token:
            if not self.login():
                return []

        headers = {
            "Authorization": self.token,
            "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
            "Content-Type": "application/json"
        }
        response = self._make_request("GET", "/api/admin/storage/list", headers)
        if response:
            storage_list = response["data"]["content"]
            return [item["mount_path"] for item in storage_list]
        logger.error("获取存储列表失败")
        return []

    def sync_directories(self, src_dir: str, dst_dir: str, exclude_dirs: str = None) -> bool:
        """同步两个目录"""
        try:
            logger.info(f"开始同步目录 - 源目录: {src_dir}, 目标目录: {dst_dir}")
            if not self.is_path_exists(dst_dir):
                logger.info(f"目标目录不存在，创建目录: {dst_dir}")
                if not self.create_directory(dst_dir):
                    return False
            result = self._recursive_copy(src_dir, dst_dir, exclude_dirs)
            logger.info(f"目录同步完成 - 源目录: {src_dir}, 目标目录: {dst_dir}, 结果: {'成功' if result else '失败'}")
            return result
        except Exception as e:
            logger.error(f"同步目录失败: {str(e)}")
            return False

    def _recursive_copy(self, src_dir: str, dst_dir: str, exclude_dirs: str = None) -> bool:
        """递归复制目录内容"""
        try:
            if src_dir == exclude_dirs:
                logger.info(f"排除目录: {src_dir}, 跳过同步")
                return True
            else:
                logger.info(f"开始递归复制 - 源目录: {src_dir}, 目标目录: {dst_dir}")
                src_contents = self.get_directory_contents(src_dir)
                if not src_contents:
                    logger.info(f"源目录为空或获取内容失败: {src_dir}")
                    return True

                if self.sync_delete:
                    self._handle_sync_delete(src_dir, dst_dir, src_contents)

                for item in src_contents:
                    if not self._copy_item_with_check(src_dir, dst_dir, item, exclude_dirs):
                        logger.error(f"复制项目失败: {item.get('name', '未知项目')}")
                        return False

                logger.info(f"递归复制完成 - 源目录: {src_dir}, 目标目录: {dst_dir}")
                return True
        except Exception as e:
            logger.error(f"递归复制失败: {str(e)}")
        return False

    def _handle_sync_delete(self, src_dir: str, dst_dir: str, src_contents: List[Dict]):
        """处理同步删除逻辑"""
        try:
            dst_contents = self.get_directory_contents(dst_dir)
            src_names = {item["name"] for item in src_contents}
            dst_names = {item["name"] for item in dst_contents}

            to_delete = dst_names - src_names
            if not to_delete:
                logger.info("没有需要删除的项目")
                return

            for name in to_delete:
                if self.sync_delete_action == "move":
                    logger.info(f"处理同步移动 - 目录: {dst_dir}")
                    logger.info(f"处理移动项目: {name}")
                    trash_dir = self._get_trash_dir(dst_dir)
                    if trash_dir:
                        if not self.is_path_exists(trash_dir):
                            logger.info(f"创建回收站目录: {trash_dir}")
                            self.create_directory(trash_dir)
                        logger.info(f"移动到回收站: {name}")
                        self.move_item(dst_dir, trash_dir, name)
                else:  # delete
                    logger.info(f"处理同步删除 - 目录: {dst_dir}")
                    logger.info(f"处理删除项目: {name}")
                    logger.info(f"直接删除项目: {name}")
                    self._directory_operation("remove", dir=dst_dir, names=[name])
        except Exception as e:
            logger.error(f"处理同步删除失败: {str(e)}")

    def _get_trash_dir(self, dst_dir: str) -> Optional[str]:
        """获取回收站目录路径"""
        storage_list = self.get_storage_list()
        for mount_path in storage_list:
            if dst_dir.startswith(mount_path):
                return f"{mount_path}/trash{dst_dir[len(mount_path):]}"
        return None

    def close(self):
        """关闭连接"""
        try:
            if hasattr(self, 'connection') and self.connection:
                self.connection.close()
                logger.debug("连接已关闭")
        except Exception as e:
            logger.error(f"关闭连接时发生错误: {str(e)}")

    def get_file_info(self, path: str) -> Optional[Dict]:
        """获取文件信息，包括大小和修改时间"""
        response = self._directory_operation("get", path=path)
        if response and response.get("message") == "success":
            return response.get("data", {})
        return None

    def _copy_item_with_check(self, src_dir: str, dst_dir: str, item: Dict, exclude_dirs: str = None) -> bool:
        """复制项目并进行检查"""
        try:
            item_name = item.get('name')
            if not item_name:
                logger.error("项目名称为空")
                return False

            logger.info(f"处理项目: {item_name}")
            if src_dir == exclude_dirs:
                logger.info(f"排除目录: {src_dir}, 跳过同步")
                return True

            # 如果是目录，递归处理
            if item.get('is_dir', False):
                src_subdir = f"{src_dir}/{item_name}".replace('//', '/')
                dst_subdir = f"{dst_dir}/{item_name}".replace('//', '/')

                # 确保目标子目录存在
                if not self.is_path_exists(dst_subdir):
                    logger.info(f"创建目标子目录: {dst_subdir}")
                    if not self.create_directory(dst_subdir):
                        return False
                else:
                    logger.info(f"文件夹【{dst_subdir}】已存在，跳过创建")

                # 递归复制子目录
                return self._recursive_copy(src_subdir, dst_subdir, exclude_dirs)
            else:
                # 处理文件
                dst_path = f"{dst_dir}/{item_name}".replace('//', '/')

                # 检查目标文件是否存在
                if not self.is_path_exists(dst_path):
                    logger.info(f"复制文件: {item_name}")
                    return self.copy_item(src_dir, dst_dir, item_name)
                else:
                    # 获取源文件和目标文件信息
                    src_size = item.get("size")
                    dst_info = self.get_file_info(dst_path)

                    if not dst_info:
                        logger.error(f"获取目标文件信息失败: {dst_path}")
                        return False

                    dst_size = dst_info.get("size")

                    # 比较文件大小
                    if src_size == dst_size:
                        logger.info(f"文件【{item_name}】已存在且大小相同，跳过复制")
                        return True
                    else:
                        # 比较修改时间
                        src_modified = parse_time_and_adjust_utc(item.get("modified"))
                        dst_modified = parse_time_and_adjust_utc(dst_info.get("modified"))

                        if src_modified and dst_modified and dst_modified > src_modified:
                            logger.info(f"文件【{item_name}】目标文件修改时间晚于源文件，跳过复制")
                            return True
                        else:
                            logger.info(f"文件【{item_name}】存在变更，删除并重新复制")
                            # 删除旧文件
                            if not self._directory_operation("remove", dir=dst_dir, names=[item_name]):
                                logger.error(f"删除目标文件失败: {dst_path}")
                                return False
                            # 复制新文件
                            return self.copy_item(src_dir, dst_dir, item_name)

        except Exception as e:
            logger.error(f"复制项目时发生错误: {str(e)}")
            return False


def get_dir_pairs_from_env() -> List[str]:
    """从环境变量获取目录对列表"""
    dir_pairs_list = []

    # 获取主DIR_PAIRS
    if dir_pairs := os.environ.get("DIR_PAIRS"):
        dir_pairs_list.extend(dir_pairs.split(";"))

    # 获取DIR_PAIRS1到DIR_PAIRS50
    for i in range(1, 51):
        if dir_pairs := os.environ.get(f"DIR_PAIRS{i}"):
            dir_pairs_list.extend(dir_pairs.split(";"))

    return dir_pairs_list


def main(dir_pairs: str = None, sync_del_action: str = None, exclude_dirs: str = None):
    """主函数，用于命令行执行"""
    code_souce()
    xiaojin()

    logger.info("开始执行同步任务")

    # 从环境变量获取配置
    base_url = os.environ.get("BASE_URL")
    username = os.environ.get("USERNAME")
    password = os.environ.get("PASSWORD")
    if sync_del_action:
        sync_delete_action = sync_del_action
    else:
        sync_delete_action = os.environ.get("SYNC_DELETE_ACTION", "none")

    if not exclude_dirs:
        exclude_dirs = os.environ.get("EXCLUDE_DIRS")

    if not all([base_url, username, password]):
        logger.error("必要的环境变量未设置")
        return

    logger.info(f"配置信息 - URL: {base_url}, 用户名: {username}, 删除动作: {sync_delete_action}")

    # 创建AlistSync实例
    alist_sync = AlistSync(base_url, username, password, sync_delete_action)

    try:
        # 获取同步目录对
        dir_pairs_list = []
        if dir_pairs:
            dir_pairs_list.extend(dir_pairs.split(";"))
        else:
            dir_pairs_list = get_dir_pairs_from_env()

        logger.info(f"")
        logger.info(f"")
        num = 1
        for pair in dir_pairs_list:
            logger.info(f"No.{num:02d}【{pair}】")
            num += 1

        # 执行同步
        i = 1
        for pair in dir_pairs_list:
            src_dir, dst_dir = pair.split(":")
            logger.info(f"")
            logger.info(f"")
            logger.info(f"")
            logger.info(f"")
            logger.info(f"")
            logger.info(f"第 [{i:02d}] 个 同步目录【{src_dir.strip()}】---->【 {dst_dir.strip()}】")
            logger.info(f"")
            logger.info(f"")
            i += 1
            alist_sync.sync_directories(src_dir.strip(), dst_dir.strip(), exclude_dirs)

        logger.info("所有同步任务执行完成")
    except Exception as e:
        logger.error(f"执行同步任务时发生错误: {str(e)}")
    finally:
        alist_sync.close()
        logger.info("关闭连接，任务结束")


def code_souce():
    logger.info("国内访问: https://gitee.com/xjxjin/alist-sync")
    logger.info("国际访问: https://github.com/xjxjin/alist-sync")


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
    logger.info(pt)


if __name__ == '__main__':
    main()
