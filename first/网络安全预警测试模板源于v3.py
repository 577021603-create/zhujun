import requests
from bs4 import BeautifulSoup
import logging
import traceback
import re
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from lxml import etree

# -------------------------- 全局配置（请根据实际情况修改！）--------------------------
EMAIL_CONFIG = {
    "smtp_server": "smtp.cecloud.com",  # 企业邮箱SMTP服务器
    "smtp_port": 465,  # SSL加密端口
    "sender_email": "alarm_ganzi@cestc.cn",  # 发件人邮箱
    "sender_auth_code": "AAE4292D192ED3FF",  # 替换为实际授权码（核心修改：授权码替代密码）
    "receiver_emails": ["2332586642@qq.com",
"lijing07@cestc.cn"],
    "email_subject_template": "【甘孜云】【威胁通告】关于{}"  # 动态主题
}

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# -------------------------- 核心配置（仅修改TABLE_FIELDS，添加危害描述字段）--------------------------
TABLE_FIELDS: List[Tuple[str, str]] = [
    ("漏洞名称", "/html/body/section/div/article/div[3]/table/tbody/tr[2]/td[2]/p"),
    ("漏洞编号", "/html/body/section/div/article/div[3]/table/tbody/tr[3]/td[2]/p"),
    ("公开时间", "/html/body/section/div/article/div[3]/table/tbody/tr[4]/td[2]/p"),
    ("影响量级", "/html/body/section/div/article/div[3]/table/tbody/tr[4]/td[4]/p"),
    ("奇安信评级", "/html/body/section/div/article/div[3]/table/tbody/tr[5]/td[2]/p/strong"),
    ("CVSS3.1分数", "/html/body/section/div/article/div[3]/table/tbody/tr[5]/td[4]/p/strong"),
    ("威胁类型", "/html/body/section/div/article/div[3]/table/tbody/tr[6]/td[2]/p"),
    ("利用可能性", "/html/body/section/div/article/div[3]/table/tbody/tr[6]/td[4]/p/strong/strong"),
    ("PoC状态", "/html/body/section/div/article/div[3]/table/tbody/tr[7]/td[2]/p"),
    ("在野利用状态", "/html/body/section/div/article/div[3]/table/tbody/tr[7]/td[4]/p"),
    ("EXP状态", "/html/body/section/div/article/div[3]/table/tbody/tr[8]/td[2]/p/strong"),
    ("技术细节状态", "/html/body/section/div/article/div[3]/table/tbody/tr[8]/td[4]/p/strong"),
    ("危害描述", "/html/body/section/div/article/div[3]/table/tbody/tr[9]/td/p/text()")  # 新增：危害描述字段及XPath
]

FINAL_TITLES = [
    "影响组件", "漏洞描述", "影响范围",
    "其他受影响组件", "复现情况", "受影响资产情况", "处置建议"
]

POSITION_MARKERS = {
    "影响组件": "影响组件",
    "漏洞描述": "漏洞描述",
    "影响范围_start": "02 影响范围",
    "影响范围_end": "其他受影响组件",
    "其他受影响组件": "其他受影响组件",
    "其他受影响组件_end": "03 复现情况",
    "复现情况_start": "03 复现情况",
    "复现情况_end": "04 受影响资产情况",
    "受影响资产情况_start": "04 受影响资产情况",
    "受影响资产情况_end": "05 处置建议",
    "处置建议_start": "05 处置建议",
    "处置建议_end": "06 参考资料",
    "END_MARKER": "06 参考资料"
}

TITLE_TAGS = ['strong', 'b', 'h3', 'h4', 'span', 'p']
TITLE_CONTEXT_PATTERNS = [
    r'^[\s]*{}[:：]?[\s]*$',
    r'^[\s]*[【（(]{}[】）)]?[:：]?[\s]*$',
    r'^[\s]*{}[\s]*[:：][\s]*',
    r'^[\s]*\d+[\s]*{}[:：]?[\s]*$'
]

# -------------------------- 样式与忽略配置 --------------------------
SEPARATOR_MAIN = "=" * 150
SEPARATOR_SUB = "-" * 150
SEPARATOR_CATEGORY = "-" * 100
TITLE_PREFIX = "🔍 "
CONTENT_INDENT = "  "
BIG_TITLE_COLOR = "\033[1;31m"
CATEGORY_COLOR_TAG = "\033[1;34m"
TABLE_COLOR_TAG = "\033[1;33m"
EMAIL_CONTENT_COLOR = "\033[1;32m"
RESET_COLOR = "\033[0m"

IGNORE_TAGS = ['script', 'style', 'noscript', 'iframe', 'link', 'meta', 'br']
IGNORE_CONTENT_PATTERN = r'^[。，；：""''（）()、·…—\s\\n\\r]+$'


# -------------------------- 核心功能函数 --------------------------
def fetch_web_content(url: str) -> str:
    """抓取网页内容（自动处理编码和网络异常）"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'Upgrade-Insecure-Requests': '1'
    }

    try:
        logging.info(f'正在抓取网页: {url}')
        response = requests.get(url, headers=headers, timeout=30, verify=False)
        response.raise_for_status()
        response.encoding = response.apparent_encoding or response.encoding or 'utf-8'

        if len(response.text.strip()) < 1000:
            raise ValueError('网页内容过短，可能被反爬或URL无效')

        logging.info(f'网页抓取成功，内容长度: {len(response.text):,} 字符')
        return response.text
    except Exception as e:
        logging.error(f'网页抓取失败: {str(e)}')
        raise


def extract_big_title(html: str) -> str:
    """提取网页大标题（h1标签）"""
    try:
        tree = etree.HTML(html)
        title_list = tree.xpath('/html/body/section/div/article/h1/text()')
        if not title_list:
            logging.warning('未找到h1大标题节点')
            return "未获取到漏洞标题"

        clean_titles = [title.strip() for title in title_list if
                        title.strip() and not re.match(IGNORE_CONTENT_PATTERN, title.strip())]
        return clean_titles[0] if clean_titles else "未获取到漏洞标题"
    except Exception as e:
        logging.error(f'大标题提取失败: {str(e)}')
        return "未获取到漏洞标题"


def extract_table_info(html: str) -> Dict[str, str]:
    """提取表格中的漏洞基础信息"""
    table_info = {}
    try:
        tree = etree.HTML(html)
        for field_name, xpath in TABLE_FIELDS:
            try:
                nodes = tree.xpath(xpath)
                if not nodes:
                    table_info[field_name] = "（未找到该字段）"
                    logging.warning(f'表格字段「{field_name}」未找到匹配节点（XPath：{xpath}）')
                    continue

                text_list = []
                for node in nodes:
                    # 处理文本节点（直接获取text()结果）或元素节点（通过tostring提取）
                    if isinstance(node, str):
                        # 若XPath直接返回文本（如/text()），直接处理
                        clean_text = node.strip()
                    else:
                        # 若XPath返回元素节点，提取文本
                        clean_text = etree.tostring(node, method='text', encoding='utf-8').decode('utf-8').strip()

                    if clean_text and not re.match(IGNORE_CONTENT_PATTERN, clean_text):
                        text_list.append(clean_text)

                unique_text = list(dict.fromkeys(text_list))
                table_info[field_name] = " | ".join(unique_text) if unique_text else "（字段值为空）"
                logging.info(f'表格字段「{field_name}」提取成功：{table_info[field_name]}')
            except Exception as e:
                table_info[field_name] = "（提取失败）"
                logging.error(f'表格字段「{field_name}」提取失败：{str(e)}（XPath：{xpath}）')
        return table_info
    except Exception as e:
        logging.error(f'表格信息整体提取失败：{str(e)}')
        return {field: "（表格解析失败）" for field, _ in TABLE_FIELDS}


def find_all_marker_nodes(soup: BeautifulSoup) -> Dict[str, Optional[BeautifulSoup]]:
    """定位详细信息的标记节点，用于区间提取"""
    marker_nodes = {}
    full_text = soup.get_text(separator='\n', strip=True)

    candidate_nodes = []
    for tag in TITLE_TAGS:
        for node in soup.find_all(tag):
            if node.find_parents(IGNORE_TAGS):
                continue
            node_text = node.get_text(strip=True)
            if node_text and 4 <= len(node_text) <= 25:
                candidate_nodes.append((node, node_text))

    for marker_key, marker_text in POSITION_MARKERS.items():
        best_match = None
        highest_score = 0
        for node, node_text in candidate_nodes:
            score = 0
            if marker_text == node_text:
                score += 7
            elif marker_text in node_text:
                score += 4

            core_text = marker_text.split()[-1] if ' ' in marker_text else marker_text
            for pattern in TITLE_CONTEXT_PATTERNS:
                if re.match(pattern.format(re.escape(core_text)), node_text, re.IGNORECASE):
                    score += 3
                    break

            score += len(TITLE_TAGS) - TITLE_TAGS.index(node.name)
            if marker_text in full_text:
                score += 1

            if score > highest_score and score >= 5:
                highest_score = score
                best_match = node

        marker_nodes[marker_key] = best_match
        if best_match:
            logging.info(f'找到标记「{marker_text}」，所在标签：<{best_match.name}>')
        else:
            logging.warning(f'未找到标记「{marker_text}」')

    return marker_nodes


def extract_content_by_ranges(marker_nodes: Dict[str, Optional[BeautifulSoup]], soup: BeautifulSoup) -> List[Dict]:
    """按区间提取漏洞详细信息（删除危害描述）"""
    extracted_content = []
    content_ranges = [
        {"title": "影响组件", "start_key": "影响组件", "end_key": "漏洞描述"},
        {"title": "漏洞描述", "start_key": "漏洞描述", "end_key": "影响范围_start"},
        {"title": "影响范围", "start_key": "影响范围_start", "end_key": "影响范围_end"},
        {"title": "其他受影响组件", "start_key": "其他受影响组件", "end_key": "其他受影响组件_end"},
        {"title": "复现情况", "start_key": "复现情况_start", "end_key": "复现情况_end"},
        {"title": "受影响资产情况", "start_key": "受影响资产情况_start", "end_key": "受影响资产情况_end"},
        {"title": "处置建议", "start_key": "处置建议_start", "end_key": "处置建议_end"}
    ]

    for rule in content_ranges:
        title = rule["title"]
        start_node = marker_nodes.get(rule["start_key"])
        end_node = marker_nodes.get(rule["end_key"])

        if not start_node:
            extracted_content.append({"title": title, "content": f'{CONTENT_INDENT}（未找到该标题的起始标记）'})
            continue

        content_parts = []
        capture_flag = False
        for text_node in soup.find_all(string=True, recursive=True):
            if text_node.parent.name in IGNORE_TAGS:
                continue

            if text_node.parent == start_node:
                capture_flag = True
                continue
            if end_node and text_node.parent == end_node:
                capture_flag = False
                break

            if capture_flag:
                clean_text = text_node.strip()
                if clean_text and not re.match(r'^0[1-9]$', clean_text) and not re.match(IGNORE_CONTENT_PATTERN,
                                                                                         clean_text):
                    content_parts.append(clean_text)

        if content_parts:
            unique_content = list(dict.fromkeys(content_parts))
            formatted_content = '\n'.join([f'{CONTENT_INDENT}{part}' for part in unique_content])
        else:
            formatted_content = f'{CONTENT_INDENT}（暂无公开内容）'

        extracted_content.append({"title": title, "content": formatted_content})

    return extracted_content


def generate_email_content(big_title: str, table_info: Dict[str, str], content_info: List[Dict], url: str) -> Tuple[
    str, str, str]:
    """生成邮件主题、纯文本正文、HTML正文（删除信息来源和生成时间）"""
    # 动态主题
    email_subject = EMAIL_CONFIG["email_subject_template"].format(big_title)

    # 纯文本正文（用于控制台打印，删除信息来源和生成时间）
    text_content = f"""
{big_title}

一、漏洞基础信息
1. 漏洞名称：{table_info["漏洞名称"]}
2. 漏洞编号：{table_info["漏洞编号"]}
3. 公开时间：{table_info["公开时间"]}
4. 影响量级：{table_info["影响量级"]}
5. 奇安信评级：{table_info["奇安信评级"]}
6. CVSS3.1分数：{table_info["CVSS3.1分数"]}
7. 威胁类型：{table_info["威胁类型"]}
8. 利用可能性：{table_info["利用可能性"]}
9. PoC状态：{table_info["PoC状态"]}
10. 在野利用状态：{table_info["在野利用状态"]}
11. EXP状态：{table_info["EXP状态"]}
12. 技术细节状态：{table_info["技术细节状态"]}
13. 危害描述：{table_info["危害描述"]}

二、漏洞详细信息
"""

    for idx, item in enumerate(content_info, 1):
        title = item["title"]
        content = item["content"].replace(CONTENT_INDENT, "").strip()
        text_content += f"""
{idx}. {title}
{content}

"""

    text_content += f"""
四、说明
本邮件由系统自动发送，请勿回复。
如有疑问可联系：甘孜云 朱军  18228188727
"""

    # HTML正文（用于邮件发送，删除信息来源和生成时间）
    html_content = f"""
<html>
<head>
    <meta charset="utf-8">
    <title>如下威胁通告请委办局业务排查是否涉及相关组件，若不涉及，忽略即可</title>
    <style>
        .big-title {{ font-size: 18px; font-weight: bold; color: #d32f2f; margin: 15px 0; }}
        .section-title {{ font-size: 15px; font-weight: bold; color: #1976d2; margin: 12px 0 8px 0; }}
        .table-info {{ border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 14px; }}
        .table-info td {{ border: 1px solid #ddd; padding: 6px; }}
        .table-info td:first-child {{ font-weight: bold; background-color: #f5f5f5; width: 30%; }}
        .content-item {{ margin: 8px 0; font-size: 14px; }}
        .content-title {{ font-weight: bold; color: #388e3c; margin: 5px 0; }}
        .content-text {{ margin-left: 15px; line-height: 1.7; }}
        .footer {{ margin-top: 20px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="big-title">如下威胁通告请委办局业务排查是否涉及相关组件，若不涉及，忽略即可</div>

    <div class="section-title">一、漏洞基础信息</div>
    <table class="table-info">
        <tr><td>漏洞名称</td><td>{table_info["漏洞名称"]}</td></tr>
        <tr><td>漏洞编号</td><td>{table_info["漏洞编号"]}</td></tr>
        <tr><td>公开时间</td><td>{table_info["公开时间"]}</td></tr>
        <tr><td>影响量级</td><td>{table_info["影响量级"]}</td></tr>
        <tr><td>奇安信评级</td><td>{table_info["奇安信评级"]}</td></tr>
        <tr><td>CVSS3.1分数</td><td>{table_info["CVSS3.1分数"]}</td></tr>
        <tr><td>威胁类型</td><td>{table_info["威胁类型"]}</td></tr>
        <tr><td>利用可能性</td><td>{table_info["利用可能性"]}</td></tr>
        <tr><td>PoC状态</td><td>{table_info["PoC状态"]}</td></tr>
        <tr><td>在野利用状态</td><td>{table_info["在野利用状态"]}</td></tr>
        <tr><td>EXP状态</td><td>{table_info["EXP状态"]}</td></tr>
        <tr><td>技术细节状态</td><td>{table_info["技术细节状态"]}</td></tr>
        <tr><td>危害描述</td><td>{table_info["危害描述"]}</td></tr>
    </table>

    <div class="section-title">二、漏洞详细信息</div>
    """

    for idx, item in enumerate(content_info, 1):
        title = item["title"]
        content = item["content"].replace(CONTENT_INDENT, "").replace("\n", "<br>")
        html_content += f"""
    <div class="content-item">
        <div class="content-title">{idx}. {title}</div>
        <div class="content-text">{content}</div>
    </div>
    """

    html_content += f"""
    <div class="footer">
        本邮件由系统自动生成，请勿直接回复。如有疑问可联系：甘孜云 朱军  18228188727。<br>
    </div>
</body>
</html>
"""

    return email_subject, text_content.strip(), html_content


def print_email_content(email_subject: str, email_text_content: str):
    """控制台打印正式邮件正文"""
    print(f'\n{EMAIL_CONTENT_COLOR}{SEPARATOR_MAIN}')
    print(f'📧 正式邮件正文（发送至：{", ".join(EMAIL_CONFIG["receiver_emails"])}）')
    print(f'📌 邮件主题：{email_subject}')
    print(f'{SEPARATOR_MAIN}{RESET_COLOR}')
    print(email_text_content)
    print(f'\n{EMAIL_CONTENT_COLOR}{SEPARATOR_MAIN}')
    print(f'📧 邮件正文打印完毕（共 {len(email_text_content)} 字符）')
    print(f'{SEPARATOR_MAIN}{RESET_COLOR}')


def send_vulnerability_email(email_subject: str, html_content: str) -> bool:
    """发送邮件（适配授权码认证的SMTP服务器，优化连接稳定性）"""
    max_retries = 2  # 重试次数
    retry_delay = 3  # 重试间隔（秒）

    for retry in range(max_retries):
        server = None
        try:
            logging.info(f'\n{"=" * 40} 开始发送邮件（第{retry + 1}次尝试） {"=" * 40}')
            logging.info(f'邮件主题：{email_subject}')
            logging.info(f'收件人：{", ".join(EMAIL_CONFIG["receiver_emails"])}')

            # 构建邮件对象
            msg = MIMEMultipart()
            msg['From'] = Header(EMAIL_CONFIG["sender_email"], 'utf-8')  # 发件人（带编码）
            msg['To'] = Header(", ".join(EMAIL_CONFIG["receiver_emails"]), 'utf-8')  # 收件人（带编码）
            msg['Subject'] = Header(email_subject, 'utf-8')  # 主题编码保证中文正常

            # 添加HTML正文
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))

            # ------------ 核心修改：授权码认证 + 稳定连接 ------------
            # 1. 连接SMTP服务器（SSL加密，延长超时至120秒）
            server = smtplib.SMTP_SSL(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"], timeout=120)
            server.ehlo()  # 主动发送EHLO指令，维持连接（解决断开问题）
            server.sock.settimeout(120)  # 设置socket层超时

            # 2. 可选：开启调试模式（排查问题时启用）
            # server.set_debuglevel(1)

            try:
                # 3. 授权码认证登录（核心：用授权码替代密码）
                server.login(EMAIL_CONFIG["sender_email"], EMAIL_CONFIG["sender_auth_code"])

                # 4. 发送邮件（UTF-8编码避免中文乱码）
                server.sendmail(
                    EMAIL_CONFIG["sender_email"],
                    EMAIL_CONFIG["receiver_emails"],
                    msg.as_string().encode('utf-8')
                )
                logging.info(f'✅ 邮件发送成功！')
                print(
                    f'\n{EMAIL_CONTENT_COLOR}✅ 邮件已成功发送至：{", ".join(EMAIL_CONFIG["receiver_emails"])}（主题：{email_subject}）{RESET_COLOR}')
                return True
            finally:
                # 确保连接关闭
                if server:
                    try:
                        server.quit()
                    except:
                        pass

        except smtplib.SMTPAuthenticationError:
            logging.error(f'❌ 邮件发送失败：SMTP认证失败（授权码错误）！')
            logging.error(f'❌ 详细错误堆栈：\n{traceback.format_exc()}')
            print(f'\n❌ 邮件发送失败：SMTP认证失败')
            print(f'❌ 排查建议：1. 确认邮箱账号正确 2. 确认授权码有效（非登录密码） 3. 检查邮箱是否开启SMTP服务')
            return False  # 认证失败无需重试
        except smtplib.SMTPServerDisconnected:
            logging.error(f'❌ 邮件发送失败：SMTP服务器连接断开（第{retry + 1}次）！')
            if retry < max_retries - 1:
                logging.info(f'⏳ {retry_delay}秒后重试...')
                time.sleep(retry_delay)
        except smtplib.SMTPConnectError:
            logging.error(f'❌ 邮件发送失败：无法连接SMTP服务器（第{retry + 1}次）！')
            if retry < max_retries - 1:
                logging.info(f'⏳ {retry_delay}秒后重试...')
                time.sleep(retry_delay)
        except Exception as e:
            error_msg = f'{type(e).__name__} - {str(e)}'
            logging.error(f'❌ 邮件发送失败（第{retry + 1}次）：{error_msg}')
            logging.error(f'❌ 详细错误堆栈：\n{traceback.format_exc()}')
            if retry < max_retries - 1:
                logging.info(f'⏳ {retry_delay}秒后重试...')
                time.sleep(retry_delay)

    print(f'\n❌ 多次重试后仍发送失败，请检查网络或联系邮箱服务商')
    return False


def print_structured_result(big_title: str, table_info: Dict[str, str], content_info: List[Dict], url: str):
    """结构化打印提取结果（删除信息来源和生成时间）"""
    print(f'\n{SEPARATOR_MAIN}')
    print(f'{BIG_TITLE_COLOR}{" " * 50}{big_title}{RESET_COLOR}')
    print(f'📋 漏洞信息提取结果')
    print(f'{SEPARATOR_MAIN}')

    # 打印表格信息（新增危害描述到基础信息）
    print(f'\n{TABLE_COLOR_TAG}{SEPARATOR_CATEGORY}')
    print(f' 📊 基础信息与评级（表格提取）')
    print(f'{SEPARATOR_CATEGORY}{RESET_COLOR}')
    basic_fields = ["漏洞名称", "漏洞编号", "公开时间", "影响量级", "危害描述"]
    rating_fields = ["奇安信评级", "CVSS3.1分数", "威胁类型", "利用可能性"]
    exploit_fields = ["PoC状态", "在野利用状态", "EXP状态", "技术细节状态"]

    for field in basic_fields:
        print(f'{CONTENT_INDENT}{field}：{table_info[field]}')
    print()
    for field in rating_fields:
        print(f'{CONTENT_INDENT}{field}：{table_info[field]}')
    print()
    for field in exploit_fields:
        print(f'{CONTENT_INDENT}{field}：{table_info[field]}')

    # 打印详细信息
    print(f'\n{CATEGORY_COLOR_TAG}{SEPARATOR_CATEGORY}')
    print(f' 📝 详细信息（区间提取）')
    print(f'{SEPARATOR_CATEGORY}{RESET_COLOR}')
    for idx, item in enumerate(content_info, 1):
        title = item["title"]
        content = item["content"]
        print(f'\n{CATEGORY_COLOR_TAG}{"-" * 50}')
        print(f' {idx:02d}. {TITLE_PREFIX}{title}')
        print(f'{"-" * 50}{RESET_COLOR}')
        print(content)

    # 统计信息（自动适配新增字段）
    total_table = len(TABLE_FIELDS)
    success_table = sum(
        1 for v in table_info.values() if "（未找到" not in v and "（提取失败" not in v and "（表格解析失败" not in v)
    total_content = len(content_info)
    success_content = sum(1 for item in content_info if '（未找到' not in item['content'])
    total_chars = sum(len(item['content'].replace(CONTENT_INDENT, '').replace('\n', '')) for item in content_info)

    print(f'\n{SEPARATOR_SUB}')
    print(f'📊 提取统计信息')
    print(f'   • 表格字段：{total_table} 个（成功：{success_table} 个）')
    print(f'   • 详细信息：{total_content} 个分类（成功：{success_content} 个）')
    print(f'   • 详细信息总字符数：{total_chars} 字')
    print(f'{SEPARATOR_MAIN}')


def batch_extract(urls: List[str], send_email: bool = True):
    """批量处理流程：抓取 → 提取 → 打印 → 发送邮件"""
    for idx, url in enumerate(urls, 1):
        print(f'\n{"=" * 60} 处理第 {idx}/{len(urls)} 个网页 {"=" * 60}')
        try:
            # 1. 抓取网页
            html = fetch_web_content(url)
            # 2. 提取大标题
            big_title = extract_big_title(html)
            # 3. 提取表格信息
            table_info = extract_table_info(html)
            # 4. 提取详细信息
            soup = BeautifulSoup(html, 'html.parser')
            marker_nodes = find_all_marker_nodes(soup)
            content_info = extract_content_by_ranges(marker_nodes, soup)
            # 5. 打印结构化结果
            print_structured_result(big_title, table_info, content_info, url)
            # 6. 生成并打印邮件正文
            email_subject, email_text, email_html = generate_email_content(big_title, table_info, content_info, url)
            print_email_content(email_subject, email_text)
            # 7. 发送邮件
            if send_email:
                send_vulnerability_email(email_subject, email_html)

        except Exception as e:
            print(f'❌ 第 {idx} 个网页处理失败：{str(e)}')
            print(f'{"-" * 150}')
            traceback.print_exc()  # 打印详细堆栈
            continue


# -------------------------- 执行入口 --------------------------
if __name__ == "__main__":
    TARGET_URLS = [
        'https://www.secrss.com/articles/86949',
        # 可添加更多漏洞网页URL
    ]
    batch_extract(TARGET_URLS, send_email=True)