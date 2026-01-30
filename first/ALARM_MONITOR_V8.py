import imaplib
import email
import requests
import socket
from email.header import decode_header
from datetime import datetime, timedelta, timezone
import re
import time
import sys
import os
import json
import ctypes
import threading
import logging
from logging.handlers import RotatingFileHandler


# 检查是否以管理员身份运行
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


# 请求管理员权限重启程序
def run_as_admin():
    try:
        script = os.path.abspath(sys.argv[0])
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, script, None, 1
        )
        return True
    except Exception as e:
        print(f"请求管理员权限失败: {str(e)}")
        return False


# ==================== 编码设置 - 终极修复版本 ====================
def setup_encoding():
    """
    终极解决方案：完全避免直接访问sys.stdout和sys.stderr的encoding属性
    只通过环境变量和安全的方式设置编码，确保不会触发AttributeError
    """
    # 设置环境变量确保UTF-8优先（最安全的方式）
    os.environ["PYTHONUTF8"] = "1"
    os.environ["LC_ALL"] = "en_US.UTF-8"
    os.environ["LANG"] = "en_US.UTF-8"

    # Windows控制台编码设置（最简化版本）
    if sys.platform.startswith('win32'):
        try:
            # 只在确定有控制台的情况下尝试设置
            if sys.stdout is not None:
                kernel32 = ctypes.windll.kernel32
                kernel32.SetConsoleOutputCP(65001)
                kernel32.SetConsoleCP(65001)
        except:
            pass  # 任何错误都忽略


# 先执行编码设置
setup_encoding()

# ==================== 路径配置 - 强制指定 ====================
# 基础目录
BASE_DIR = "D:\\云平台电话告警"
# 关键字文件路径
KEYWORD_FILE = os.path.join(BASE_DIR, "ALARM_KEYWORDS.json")
# 日志文件路径
LOG_FILE = os.path.join(BASE_DIR, "monitor.log")
# 邮件状态文件路径
EMAIL_STATE_FILE = os.path.join(BASE_DIR, "email_state.json")


# 确保基础目录存在
def ensure_base_dir():
    try:
        if not os.path.exists(BASE_DIR):
            print(f"创建目录: {BASE_DIR}")
            os.makedirs(BASE_DIR, exist_ok=True)
        return True
    except PermissionError:
        print(f"权限错误: 无法创建目录 {BASE_DIR}")
        print("请以管理员身份运行程序或检查目录权限")
        if input("是否尝试以管理员身份重启? (y/n): ").lower() == 'y':
            if run_as_admin():
                sys.exit(0)
        return False
    except Exception as e:
        print(f"创建目录时出错: {str(e)}")
        return False


# 确保关键字文件存在
def ensure_keyword_file():
    if not os.path.exists(KEYWORD_FILE):
        try:
            print(f"创建默认关键字文件: {KEYWORD_FILE}")
            # 创建默认空列表
            with open(KEYWORD_FILE, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
            return True
        except PermissionError:
            print(f"权限错误: 无法创建关键字文件 {KEYWORD_FILE}")
            return False
        except Exception as e:
            print(f"创建关键字文件时出错: {str(e)}")
            return False
    return True


# ==================== 日志配置 ====================
def setup_logging():
    class UnicodeSafeFormatter(logging.Formatter):
        def format(self, record):
            if isinstance(record.msg, str):
                record.msg = record.msg.encode('utf-8', errors='replace').decode('utf-8')
            elif isinstance(record.msg, bytes):
                record.msg = record.msg.decode('utf-8', errors='replace')
            return super().format(record)

    log_format = UnicodeSafeFormatter(
        '%(asctime)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    try:
        # 测试日志文件可写性
        test_log_write()

        # 配置日志处理器
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        file_handler.setFormatter(log_format)
        file_handler.setLevel(logging.DEBUG)

        # 安全创建控制台处理器（仅当stdout存在时）
        handlers = [file_handler]
        if sys.stdout is not None:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(log_format)
            console_handler.setLevel(logging.INFO)
            handlers.append(console_handler)
        else:
            print("注意: 未找到标准输出流，仅记录文件日志")

        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        for handler in handlers:
            logger.addHandler(handler)

        print(f"日志文件已配置: {LOG_FILE}")
        return logger

    except PermissionError:
        print(f"权限错误: 无法写入日志文件 {LOG_FILE}")
        print("=" * 60)
        print("请按照以下步骤解决:")
        print("1. 右键点击文件夹 D:\\云平台电话告警 -> 属性 -> 安全")
        print("2. 点击'编辑' -> 选择你的用户名")
        print("3. 在'允许'列勾选'完全控制'或至少'读取'和'写入'")
        print("4. 点击'确定'保存设置")
        print("=" * 60)

        if input("是否尝试以管理员身份重启程序? (y/n): ").lower() == 'y':
            if run_as_admin():
                sys.exit(0)
        return None
    except Exception as e:
        print(f"配置日志时发生错误: {str(e)}")
        return None


# 测试日志文件写入
def test_log_write():
    try:
        # 尝试写入一个测试日志条目
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"测试日志写入: {datetime.now()}\n")
        return True
    except Exception as e:
        raise e


# ==================== 视频资源处理 - 命令行打包专用 ====================
def get_packed_video_path():
    """
    获取通过命令行打包的视频文件路径
    支持开发环境直接访问和打包后从EXE资源中访问
    """
    try:
        # 视频文件名（必须与打包时指定的文件名一致）
        video_filename = "告警.mp4"

        # 判断是否是打包后的环境
        if getattr(sys, 'frozen', False):
            # 打包后视频文件所在的目录
            base_path = sys._MEIPASS
            video_path = os.path.join(base_path, video_filename)

            # 验证视频文件是否存在
            if os.path.exists(video_path):
                logger.debug(f"打包环境中找到视频文件: {video_path}")
                return video_path
            else:
                logger.error(f"打包环境中未找到视频文件: {video_path}")
                return None
        else:
            # 开发环境中直接使用当前目录下的视频文件
            dev_video_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), video_filename)
            if os.path.exists(dev_video_path):
                logger.debug(f"开发环境中找到视频文件: {dev_video_path}")
                return dev_video_path
            else:
                logger.error(f"开发环境中未找到视频文件: {dev_video_path}")
                return None
    except Exception as e:
        logger.error(f"获取视频文件路径失败: {str(e)}", exc_info=True)
        return None


# ==================== 初始化检查 ====================
# 检查并创建基础目录
if not ensure_base_dir():
    print("无法创建基础目录，程序将在10秒后退出")
    time.sleep(10)
    sys.exit(1)

# 检查并创建关键字文件
if not ensure_keyword_file():
    print("无法创建关键字文件，程序将在10秒后退出")
    time.sleep(10)
    sys.exit(1)

# 检查管理员权限
if not is_admin():
    print("注意: 程序未以管理员身份运行，可能导致文件操作失败")
    time.sleep(2)

# 初始化日志
logger = setup_logging()
if not logger:
    print("日志初始化失败，程序将在15秒后退出...")
    time.sleep(15)
    sys.exit(1)


# ==================== 时间处理函数 ====================
def to_beijing_time(utc_dt):
    beijing_tz = timezone(timedelta(hours=8))
    return utc_dt.astimezone(beijing_tz)


# ==================== 安全字符串处理函数 ====================
def safe_str(s, encoding='utf-8'):
    if s is None:
        return ""

    if isinstance(s, bytes):
        try:
            return s.decode(encoding, errors='replace')
        except (UnicodeDecodeError, LookupError):
            return s.decode('utf-8', errors='replace')

    if not isinstance(s, str):
        s = str(s)

    try:
        s.encode(encoding)
        return s
    except UnicodeEncodeError:
        return s.encode(encoding, errors='replace').decode(encoding)


# ==================== 全局配置 ====================
current_play_thread = None
thread_lock = threading.Lock()

IMAP_SERVER = 'imap.qq.com'
IMAP_PORT = 993
EMAIL = '2332586642@qq.com'
PASSWORD = 'vzibdhsssvtzdhge'  # 确保是正确的授权码
CHECK_FOLDERS = ['INBOX']
TIME_RANGE_MINUTES = 3  # 检查最近3分钟的邮件
LOOP_INTERVAL = 45

MAX_EMAILS_PER_PROCESS = 1000
ALARM_KEYWORDS = []

ALARM_URL = "https://push.spug.cc/send/Xyd9M8Apv0rKbDBk"
ALARM_TARGET = "18228188727"


# ==================== 邮件状态管理 ====================
def load_processed_emails():
    try:
        if os.path.exists(EMAIL_STATE_FILE):
            with open(EMAIL_STATE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    logger.debug(f"加载已处理邮件：{len(data)}条")
                    return data
        return []
    except Exception as e:
        logger.error(f"加载已处理邮件失败：{str(e)}", exc_info=True)
        return []


def save_processed_email(email_id):
    try:
        with thread_lock:
            processed = load_processed_emails()
            if email_id not in processed:
                processed.append(email_id)
                if len(processed) > 10000:
                    processed = processed[-10000:]
                with open(EMAIL_STATE_FILE, 'w', encoding='utf-8') as f:
                    json.dump(processed, f, ensure_ascii=False, indent=2)
                logger.debug(f"已保存邮件ID：{email_id}")
                return True
            return False
    except PermissionError:
        logger.error(f"没有权限写入文件 {EMAIL_STATE_FILE}，请检查文件权限", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"保存已处理邮件失败：{str(e)}", exc_info=True)
        return False


# ==================== 工具函数 ====================
def json_file_to_list():
    """从固定路径加载关键字文件"""
    try:
        with open(KEYWORD_FILE, 'r', encoding='utf-8') as file:
            data = json.load(file)
            if isinstance(data, list):
                logger.info(f"从{KEYWORD_FILE}加载关键字：{len(data)}个")
                return data
            else:
                logger.warning(f"{KEYWORD_FILE}内容不是列表，转换为单元素列表")
                return [data]
    except PermissionError:
        logger.error(f"没有权限读取文件 {KEYWORD_FILE}，请检查文件权限", exc_info=True)
    except FileNotFoundError:
        logger.error(f"关键字文件不存在：{KEYWORD_FILE}，将创建新文件")
        ensure_keyword_file()
        return []
    except json.JSONDecodeError:
        logger.error(f"{KEYWORD_FILE}不是有效的JSON格式", exc_info=True)
        ensure_keyword_file()
        return []
    except Exception as e:
        logger.error(f"读取关键字文件失败：{str(e)}", exc_info=True)
    return []


def decode_str(encoded_str):
    if not encoded_str:
        return ""
    try:
        decoded_parts = decode_header(encoded_str)
        result = []
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                try:
                    if encoding:
                        result.append(part.decode(encoding, errors='replace'))
                    else:
                        for enc in ['utf-8', 'gbk', 'gb2312', 'gb18030']:
                            try:
                                result.append(part.decode(enc, errors='replace'))
                                break
                            except UnicodeDecodeError:
                                continue
                        else:
                            result.append(part.decode('utf-8', errors='replace'))
                except Exception:
                    result.append(part.decode('utf-8', errors='replace'))
            else:
                result.append(safe_str(part))
        return ''.join(result)
    except Exception as e:
        logger.error(f"解码字符串失败：{safe_str(encoded_str)}", exc_info=True)
        return safe_str(encoded_str)


def html_to_string(html):
    """增强版HTML转文本，移除干扰标签并清理空白字符"""
    if not html:
        return ""
    try:
        from bs4 import BeautifulSoup
        # 限制最大处理长度
        if len(html) > 100000:
            html = html[:100000] + "...（内容过长已截断）"

        soup = BeautifulSoup(html, 'html.parser')

        # 移除脚本和样式标签
        for script in soup(["script", "style"]):
            script.decompose()

        # 获取文本并清理
        text = soup.get_text(separator=' ', strip=False)

        # 清理空白字符
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)

        return text
    except Exception as e:
        logger.error("HTML转文本失败", exc_info=True)
        return html


def extract_specific_values(content_str):
    extracted = {
        "资源名称": None,
        "告警主机": None,
        "告警实例": None
    }
    try:
        patterns = {
            "资源名称": r"资源名称[:：]\s*([^,，]+)",
            "告警主机": r"告警主机[:：]\s*([^,，]+)",
            "告警实例": r"告警实例[:：]\s*([^,，]+)"
        }
        for key, pattern in patterns.items():
            match = re.search(pattern, content_str)
            if match:
                extracted[key] = match.group(1).strip()
        return extracted
    except Exception as e:
        logger.error("提取特定值失败", exc_info=True)
        return extracted


def check_keywords(content_str):
    """增强版关键字检查，增加详细日志"""
    if not ALARM_KEYWORDS:
        logger.warning("告警关键字列表为空，跳过检查")
        return []
    try:
        content_lower = content_str.lower()
        matched = []
        # 记录所有关键字检查结果
        for kw in ALARM_KEYWORDS:
            if kw.lower() in content_lower:
                matched.append(kw)
                logger.debug(f"关键字匹配成功: {kw}")
            else:
                logger.debug(f"关键字未匹配: {kw}")
        return matched
    except Exception as e:
        logger.error("关键字检查失败", exc_info=True)
        return []


# ==================== 告警触发 ====================
def trigger_alarm(value):
    global current_play_thread
    if not value:
        logger.warning("没有有效的告警值，不触发告警")
        return

    try:
        if not isinstance(value, str):
            value = str(value)
        value = safe_str(value)

        data = {
            'key1': value,
            'targets': ALARM_TARGET
        }
        for _ in range(2):
            try:
                response = requests.post(
                    ALARM_URL,
                    json=data,
                    timeout=10,
                    headers={'Content-Type': 'application/json; charset=utf-8'}
                )
                response.raise_for_status()
                logger.info(f"告警触发成功，key1值：{value}，响应：{response.text[:100]}")
                break
            except requests.exceptions.RequestException as e:
                logger.warning(f"告警请求失败（重试中）：{str(e)}")
                time.sleep(2)
        else:
            logger.error(f"告警请求多次失败，key1值：{value}")
            return

        with thread_lock:
            if current_play_thread is None or not current_play_thread.is_alive():
                # 获取打包的视频路径
                video_path = get_packed_video_path()
                if video_path:
                    current_play_thread = threading.Thread(
                        target=lambda: play_video_in_background(video_path, 60),
                        daemon=True
                    )
                    current_play_thread.start()
                    logger.info("视频播放线程已启动")
                else:
                    logger.error("无法获取视频文件路径，无法播放告警视频")
            else:
                logger.info("视频播放线程正在运行，本次不重复启动")

    except Exception as e:
        logger.error(f"告警触发失败：{str(e)}", exc_info=True)


# ==================== 视频播放线程 ====================
def play_video_in_background(video_path, repeat_count=10):
    logger.info(f"准备播放视频：{video_path}（重复{repeat_count}次）")

    if not os.path.exists(video_path):
        logger.error(f"视频文件不存在：{video_path}")
        return

    instance = None
    player = None
    try:
        import vlc
        instance = vlc.Instance("--vout=direct3d11 --quiet --no-video-title-show")
        player = instance.media_player_new()

        if sys.platform.startswith('win32'):
            hwnd = ctypes.windll.user32.GetDesktopWindow()
            player.set_hwnd(hwnd)

        for i in range(repeat_count):
            logger.debug(f"视频播放第{i + 1}/{repeat_count}次")
            media = instance.media_new(video_path)
            player.set_media(media)
            player.play()

            start_time = time.time()
            while player.get_state() != vlc.State.Playing:
                if time.time() - start_time > 5:
                    logger.warning("视频播放启动超时")
                    break
                time.sleep(0.1)

            while True:
                state = player.get_state()
                if state in [vlc.State.Ended, vlc.State.Stopped, vlc.State.Error]:
                    break
                if time.time() - start_time > 300:
                    logger.warning("视频播放超时，强制停止")
                    player.stop()
                    break
                time.sleep(0.5)

        logger.info("视频播放完成")

    except Exception as e:
        logger.error(f"视频播放出错：{str(e)}", exc_info=True)
    finally:
        if player:
            player.stop()
            player.release()
        if instance:
            instance.release()
        logger.info("视频播放资源已释放")


# ==================== 邮件处理 ====================
def process_emails():
    logger.info("\n" + "=" * 50)
    logger.info(f"开始处理邮件 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 50)

    processed_emails = load_processed_emails()
    mail = None

    try:
        socket.setdefaulttimeout(30)

        # 计算时间范围
        current_time = datetime.now()
        start_time = current_time - timedelta(minutes=TIME_RANGE_MINUTES)
        imap_start_date = start_time.strftime('%d-%b-%Y')

        logger.info(f"当前时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"搜索范围: {start_time.strftime('%Y-%m-%d %H:%M:%S')} 至 当前时间")
        logger.info(f"IMAP服务器筛选日期: {imap_start_date}及之后")

        # 连接邮箱
        for _ in range(2):
            try:
                mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
                mail.login(EMAIL, PASSWORD)
                logger.info(f"成功登录邮箱：{EMAIL}")

                # ========== 修正：登录后同步（移除EXPUNGE，仅保留合法命令） ==========
                logger.info("🔄 触发IMAP服务器同步...")
                mail.noop()  # 激活会话，触发心跳（AUTH状态合法）
                mail.status('INBOX', '(MESSAGES UNSEEN)')  # 获取收件箱状态（AUTH状态合法）
                time.sleep(1.5)  # 等待同步完成
                # ======================================================

                break
            except imaplib.IMAP4.error as e:
                logger.error(f"邮箱登录失败：{str(e)}（检查授权码和IMAP设置）")
                if mail:
                    try:
                        mail.logout()
                    except:
                        pass
                time.sleep(5)
        else:
            logger.error("多次登录失败，跳过本次邮件处理")
            return

        all_recent_emails = []

        for folder in CHECK_FOLDERS:
            try:
                # 选择文件夹
                status, select_data = mail.select(folder, readonly=True)
                if status != 'OK':
                    logger.error(f"无法选择文件夹：{folder}")
                    continue

                # ========== 修正：在SELECTED状态下执行EXPUNGE（合法） ==========
                logger.info(f"🔄 刷新文件夹 {folder} 缓存...")
                mail.expunge()  # 清理已删除邮件缓存（SELECTED状态合法）
                mail.noop()  # 二次激活同步
                time.sleep(0.5)  # 等待缓存刷新
                # ======================================================

                folder_email_count = int(select_data[0].decode()) if select_data else 0
                logger.info(f"文件夹 {folder} 总邮件数: {folder_email_count}")

                # 执行搜索
                search_criteria = f'SINCE "{imap_start_date}"'
                status, messages = mail.search(None, search_criteria)
                if status != 'OK':
                    logger.error(f"搜索邮件失败 in {folder}")
                    continue

                email_ids = messages[0].split() if (messages and messages[0]) else []
                total_count = len(email_ids)
                logger.info(f"从 {folder} 搜索到符合日期条件的邮件数: {total_count}")

                if not email_ids:
                    continue

                if total_count > MAX_EMAILS_PER_PROCESS:
                    email_ids = email_ids[-MAX_EMAILS_PER_PROCESS:]
                    logger.info(f"邮件数超过上限，仅处理最新{MAX_EMAILS_PER_PROCESS}封")

                processed_set = set(processed_emails)
                in_range_count = 0

                # 遍历邮件ID
                for email_id in email_ids:
                    try:
                        email_id_str = email_id.decode()

                        # 已处理的邮件直接跳过
                        if email_id_str in processed_set:
                            continue

                        # 获取邮件内部时间
                        status, data = mail.fetch(email_id, '(INTERNALDATE)')
                        if status != 'OK' or not data or not data[0]:
                            continue

                        # 解析时间
                        raw_data = data[0].decode(errors='replace')
                        match = re.search(r'INTERNALDATE "([^"]+)"', raw_data)
                        if not match:
                            continue

                        try:
                            internal_date = datetime.strptime(match.group(1), '%d-%b-%Y %H:%M:%S %z')
                            local_time = internal_date.astimezone().replace(tzinfo=None)

                            if local_time >= start_time:
                                all_recent_emails.append({
                                    'id': email_id_str,
                                    'folder': folder,
                                    'recv_time': internal_date
                                })
                                in_range_count += 1

                        except ValueError:
                            continue

                    except Exception:
                        continue

                logger.info(f"{folder} 处理完成：符合时间范围的新邮件数 = {in_range_count}")

            except Exception as e:
                logger.error(f"处理文件夹 {folder} 时出错", exc_info=True)
                continue

        # 处理筛选后的邮件
        all_recent_emails.sort(key=lambda x: x['recv_time'], reverse=True)
        processed_set = set(processed_emails)
        new_emails = [e for e in all_recent_emails if e['id'] not in processed_set]

        logger.info(f"本次处理共发现 {len(new_emails)} 封新邮件（时间范围内且未处理）")

        if not new_emails:
            return

        # 详细处理所有新邮件
        for i, email_info in enumerate(new_emails, 1):
            try:
                logger.info(f"\n{'=' * 40}")
                logger.info(f"处理新邮件 {i}/{len(new_emails)}，ID: {email_info['id']}")

                mail.select(email_info['folder'], readonly=True)
                status, data = mail.fetch(email_info['id'].encode(), '(RFC822)')
                if status != 'OK':
                    logger.error(f"获取邮件内容失败")
                    continue

                if not data or len(data) < 2 or not data[0][1]:
                    logger.error(f"邮件内容为空")
                    continue

                msg = email.message_from_bytes(data[0][1])
                sender = decode_str(msg.get('From', '未知发件人'))
                subject = decode_str(msg.get('Subject', '无主题'))
                recipients = decode_str(msg.get('To', '未知收件人'))
                recv_time_bj = to_beijing_time(email_info['recv_time']).strftime('%Y-%m-%d %H:%M:%S')

                # 打印邮件基本信息
                logger.info(f"主题：{subject}")
                logger.info(f"发件人：{sender}")
                logger.info(f"收件人：{recipients}")
                logger.info(f"接收时间（北京时间）：{recv_time_bj}")

                # 提取正文
                body_str = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        if content_type in ['text/plain', 'text/html']:
                            payload = part.get_payload(decode=True)
                            if payload:
                                # 解码邮件内容
                                charset = part.get_content_charset() or 'utf-8'
                                try:
                                    part_str = payload.decode(charset, errors='replace')
                                except:
                                    part_str = payload.decode('utf-8', errors='replace')

                                # 如果是HTML内容，转换为文本
                                if content_type == 'text/html':
                                    part_str = html_to_string(part_str)

                                body_str += part_str + "\n"
                else:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        charset = msg.get_content_charset() or 'utf-8'
                        try:
                            body_str = payload.decode(charset, errors='replace')
                        except:
                            body_str = payload.decode('utf-8', errors='replace')

                        # 如果是HTML内容，转换为文本
                        if msg.get_content_type() == 'text/html':
                            body_str = html_to_string(body_str)

                # 显示部分正文内容
                if body_str:
                    preview = body_str[:300].replace('\n', ' ')
                    logger.info(f"邮件内容预览：{preview}...")
                    # 调试时可临时开启完整内容日志
                    # logger.debug(f"完整邮件内容：{body_str}")

                # 检查关键字
                matched_keywords = check_keywords(body_str)
                if matched_keywords:
                    logger.warning(f"✅ 检测到告警关键字：{', '.join(matched_keywords)}")
                    extracted_values = extract_specific_values(body_str)
                    alarm_value = (extracted_values['资源名称'] or
                                   extracted_values['告警主机'] or
                                   extracted_values['告警实例'] or subject)
                    trigger_alarm(alarm_value)
                else:
                    logger.info(f"❌ 未检测到告警关键字")

                # 标记为已处理
                save_processed_email(email_info['id'])
                logger.info(f"{'=' * 40}")

            except Exception as e:
                logger.error(f"处理邮件时出错", exc_info=True)
                continue

    except Exception as e:
        logger.error(f"邮件处理主流程错误：{str(e)}", exc_info=True)
    finally:
        if mail:
            try:
                mail.logout()
                logger.info("邮箱连接已关闭")
            except Exception as e:
                logger.error(f"关闭邮箱连接失败：{str(e)}")


# ==================== 主循环 ====================
def main_loop():
    global ALARM_KEYWORDS
    ALARM_KEYWORDS = json_file_to_list()
    logger.info(f"告警关键字列表: {ALARM_KEYWORDS}")

    logger.info(f"程序启动：每{LOOP_INTERVAL}秒检查一次收件箱（最近{TIME_RANGE_MINUTES}分钟），按Ctrl+C停止")
    logger.info(f"关键字文件路径: {KEYWORD_FILE}")
    logger.info(f"日志文件路径: {LOG_FILE}")

    try:
        while True:
            # 每次循环都重新加载关键字，支持动态更新
            ALARM_KEYWORDS = json_file_to_list()
            process_emails()
            logger.info(f"等待{LOOP_INTERVAL}秒后进行下一次检查...\n")
            time.sleep(LOOP_INTERVAL)
    except KeyboardInterrupt:
        logger.info("程序已手动停止")
    except Exception as e:
        logger.critical("主循环崩溃", exc_info=True)
    finally:
        logger.info("程序退出")


# ==================== 程序入口 ====================
if __name__ == '__main__':
    main_loop()