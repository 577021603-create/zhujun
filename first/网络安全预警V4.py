# 导入HTTP请求库，用于发送请求抓取网页内容
import requests
# 导入BeautifulSoup，用于解析HTML文档，提取所需文本和节点
from bs4 import BeautifulSoup
# 导入日志模块，用于记录程序运行状态（成功/失败/警告等）
import logging
# 导入异常堆栈打印模块，用于详细输出错误信息，方便调试
import traceback
# 导入正则表达式模块，用于文本匹配和清洗（如过滤无效内容）
import re
# 导入SMTP邮件发送模块，用于通过SMTP协议发送邮件
import smtplib
# 导入时间模块，用于设置重试延迟等时间相关操作
import time
# 导入邮件文本内容构建类，用于创建纯文本或HTML格式的邮件正文
from email.mime.text import MIMEText
# 导入多部分邮件构建类，用于组合邮件的多个部分（如正文+附件，此处用于HTML正文）
from email.mime.multipart import MIMEMultipart
# 导入邮件头编码类，用于处理邮件主题、发件人/收件人中文乱码问题
from email.header import Header
# 导入类型注解模块，用于规范函数参数和返回值的类型（提升代码可读性和稳定性）
from typing import List, Dict, Optional, Tuple
# 导入日期时间类，预留用于时间相关操作（本脚本未实际使用）
from datetime import datetime
# 导入lxml的etree模块，用于支持XPath语法，精准定位HTML节点提取数据
from lxml import etree

# -------------------------- 全局配置（请根据实际情况修改！）--------------------------
# 邮件配置字典：存储企业邮箱的核心参数，用于发送漏洞通知邮件
EMAIL_CONFIG = {
    "smtp_server": "smtp.cecloud.com",  # 企业邮箱SMTP服务器地址（需根据实际邮箱服务商修改）
    "smtp_port": 465,  # SSL加密端口（常用465或994，需与SMTP服务器匹配）
    "sender_email": "alarm_ganzi@cestc.cn",  # 发件人邮箱地址（漏洞通知发送方）
    "sender_auth_code": "0c68439f93bf0826",  # 邮箱授权码（替代登录密码，需在邮箱后台开启SMTP服务并获取）
    "receiver_emails": [ "577021603@qq.com","zhu_jun@cestc.cn"],  # 收件人邮箱列表（需接收漏洞通知的人员）
    "email_subject_template": "【甘孜云】【威胁通告】关于{}"  # 邮件主题模板（{}会动态填充漏洞标题）
}

# 日志配置：设置日志输出级别、格式和输出方式
logging.basicConfig(
    level=logging.INFO,  # 日志级别：INFO及以上（DEBUG/INFO/WARNING/ERROR/CRITICAL）会被记录
    format='%(asctime)s - %(levelname)s - %(message)s',  # 日志格式：时间-日志级别-日志内容
    handlers=[logging.StreamHandler()]  # 日志输出方式：仅输出到控制台（不写入文件）
)

# -------------------------- 核心配置（仅修改TABLE_FIELDS，添加危害描述字段）--------------------------
# 表格字段配置：列表存储元组，每个元组为(字段名称, XPath路径)，用于从网页表格提取基础漏洞信息
TABLE_FIELDS: List[Tuple[str, str]] = [
    ("漏洞名称", "/html/body/section/div/article/div[3]/table/tbody/tr[2]/td[2]/p"),  # 漏洞名称的XPath定位
    ("漏洞编号", "/html/body/section/div/article/div[3]/table/tbody/tr[3]/td[2]/p"),  # 漏洞编号（如CVE编号）的XPath定位
    ("公开时间", "/html/body/section/div/article/div[3]/table/tbody/tr[4]/td[2]/p"),  # 漏洞公开时间的XPath定位
    ("影响量级", "/html/body/section/div/article/div[3]/table/tbody/tr[4]/td[4]/p"),  # 漏洞影响范围量级的XPath定位
    ("奇安信评级", "/html/body/section/div/article/div[3]/table/tbody/tr[5]/td[2]/p/strong"),  # 奇安信给出的漏洞评级XPath
    ("CVSS3.1分数", "/html/body/section/div/article/div[3]/table/tbody/tr[5]/td[4]/p/strong"),  # CVSS3.1评分（漏洞严重程度）XPath
    ("威胁类型", "/html/body/section/div/article/div[3]/table/tbody/tr[6]/td[2]/p"),  # 漏洞威胁类型（如远程代码执行）XPath
    ("利用可能性", "/html/body/section/div/article/div[3]/table/tbody/tr[6]/td[4]/p/strong/strong"),  # 漏洞被利用的可能性XPath
    ("PoC状态", "/html/body/section/div/article/div[3]/table/tbody/tr[7]/td[2]/p"),  # 漏洞PoC（验证脚本）是否存在的XPath
    ("在野利用状态", "/html/body/section/div/article/div[3]/table/tbody/tr[7]/td[4]/p"),  # 漏洞是否被在野利用的XPath
    ("EXP状态", "/html/body/section/div/article/div[3]/table/tbody/tr[8]/td[2]/p/strong"),  # 漏洞EXP（攻击脚本）是否存在的XPath
    ("技术细节状态", "/html/body/section/div/article/div[3]/table/tbody/tr[8]/td[4]/p/strong"),  # 漏洞技术细节是否公开的XPath
    ("危害描述", "/html/body/section/div/article/div[3]/table/tbody/tr[9]/td/p/text()")  # 新增：漏洞危害描述的XPath定位（直接提取文本）
]

# 详细信息分类标题：定义最终展示的漏洞详细信息分类（与后续提取逻辑对应）
FINAL_TITLES = [
    "影响组件", "漏洞描述", "影响范围",
    "其他受影响组件", "复现情况", "受影响资产情况", "处置建议"
]

# 定位标记字典：存储各详细信息分类的起始/结束标记，用于在网页中精准截取对应内容
POSITION_MARKERS = {
    "影响组件": "影响组件",  # “影响组件”分类的起始标记
    "漏洞描述": "漏洞描述",  # “漏洞描述”分类的起始标记
    "影响范围_start": "02 影响范围",  # “影响范围”分类的起始标记
    "影响范围_end": "其他受影响组件",  # “影响范围”分类的结束标记
    "其他受影响组件": "其他受影响组件",  # “其他受影响组件”分类的起始标记
    "其他受影响组件_end": "03 复现情况",  # “其他受影响组件”分类的结束标记
    "复现情况_start": "03 复现情况",  # “复现情况”分类的起始标记
    "复现情况_end": "04 受影响资产情况",  # “复现情况”分类的结束标记
    "受影响资产情况_start": "04 受影响资产情况",  # “受影响资产情况”分类的起始标记
    "受影响资产情况_end": "05 处置建议",  # “受影响资产情况”分类的结束标记
    "处置建议_start": "05 处置建议",  # “处置建议”分类的起始标记
    "处置建议_end": "06 参考资料",  # “处置建议”分类的结束标记
    "END_MARKER": "06 参考资料"  # 所有详细信息的最终结束标记
}

# 标题标签列表：定义网页中可能作为分类标题的HTML标签（用于定位标记节点）
TITLE_TAGS = ['strong', 'b', 'h3', 'h4', 'span', 'p']

# 标题匹配正则模板：用于适配网页中不同格式的标题文本（如“影响组件”“【影响组件】”“02 影响范围”等）
TITLE_CONTEXT_PATTERNS = [
    r'^[\s]*{}[:：]?[\s]*$',  # 匹配“影响组件”“影响组件：”“ 影响组件 ”等格式
    r'^[\s]*[【（(]{}[】）)]?[:：]?[\s]*$',  # 匹配“【影响组件】”“(影响组件)”“ （影响组件）： ”等格式
    r'^[\s]*{}[\s]*[:：][\s]*',  # 匹配“影响组件 ： ”“ 影响组件: ”等带空格和冒号的格式
    r'^[\s]*\d+[\s]*{}[:：]?[\s]*$'  # 匹配“02 影响范围”“ 3 处置建议： ”等带数字前缀的格式
]

# -------------------------- 样式与忽略配置 --------------------------
# 分隔符常量：用于控制台打印时的视觉分隔，提升可读性
SEPARATOR_MAIN = "=" * 150  # 主分隔符（150个等号）
SEPARATOR_SUB = "-" * 150   # 子分隔符（150个减号）
SEPARATOR_CATEGORY = "-" * 100  # 分类分隔符（100个减号）

# 文本样式常量：用于控制台打印时的标题前缀和内容缩进
TITLE_PREFIX = "🔍 "  # 分类标题前缀（放大镜图标）
CONTENT_INDENT = "  "  # 内容缩进（两个空格）

# 控制台颜色常量：使用ANSI转义码设置文本颜色（加粗效果），提升控制台输出可读性
BIG_TITLE_COLOR = "\033[1;31m"  # 大标题颜色：红色加粗
CATEGORY_COLOR_TAG = "\033[1;34m"  # 分类标题颜色：蓝色加粗
TABLE_COLOR_TAG = "\033[1;33m"  # 表格信息颜色：黄色加粗
EMAIL_CONTENT_COLOR = "\033[1;32m"  # 邮件内容颜色：绿色加粗
RESET_COLOR = "\033[0m"  # 颜色重置：恢复控制台默认文本颜色

# 忽略标签列表：解析HTML时需要跳过的无效标签（这些标签的内容不参与漏洞信息提取）
IGNORE_TAGS = ['script', 'style', 'noscript', 'iframe', 'link', 'meta', 'br']

# 忽略内容正则：匹配仅包含符号、空白符的无效文本（如“，；：”“\n\r”“  ”等），用于过滤无效内容
IGNORE_CONTENT_PATTERN = r'^[。，；：""''（）()、·…—\s\\n\\r]+$'

# -------------------------- 核心功能函数 --------------------------
# 定义函数：抓取网页内容，自动处理编码和网络异常
def fetch_web_content(url: str) -> str:
    """抓取网页内容（自动处理编码和网络异常）"""
    # 构建请求头：模拟Chrome浏览器访问，避免被目标网站反爬
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Cache-Control': 'no-cache',  # 禁用缓存，确保获取最新内容
        'Pragma': 'no-cache',  # 兼容HTTP/1.0，禁用缓存
        'Upgrade-Insecure-Requests': '1'  # 自动将HTTP请求升级为HTTPS
    }

    try:
        # 记录日志：正在抓取目标网页
        logging.info(f'正在抓取网页: {url}')
        # 发送GET请求：设置超时30秒，禁用SSL证书验证（避免证书问题导致抓取失败）
        response = requests.get(url, headers=headers, timeout=30, verify=False)
        # 检查响应状态码：非200（如404、500）会抛出异常
        response.raise_for_status()
        # 自动处理编码：优先使用网页的实际编码，其次使用响应头编码，最后默认UTF-8
        response.encoding = response.apparent_encoding or response.encoding or 'utf-8'

        # 验证网页内容长度：小于1000字符可能是反爬页面或无效URL，抛出异常
        if len(response.text.strip()) < 1000:
            raise ValueError('网页内容过短，可能被反爬或URL无效')

        # 记录日志：网页抓取成功，输出内容长度
        logging.info(f'网页抓取成功，内容长度: {len(response.text):,} 字符')
        # 返回抓取到的网页HTML文本
        return response.text
    except Exception as e:
        # 记录日志：网页抓取失败，输出错误信息
        logging.error(f'网页抓取失败: {str(e)}')
        # 抛出异常，让调用方处理
        raise

# 定义函数：从HTML中提取网页大标题（h1标签内容）
def extract_big_title(html: str) -> str:
    """提取网页大标题（h1标签）"""
    try:
        # 将HTML文本解析为etree对象，用于XPath查询
        tree = etree.HTML(html)
        # 使用XPath提取h1标签的文本内容
        title_list = tree.xpath('/html/body/section/div/article/h1/text()')
        # 若未找到h1标签，记录警告日志
        if not title_list:
            logging.warning('未找到h1大标题节点')
            return "未获取到漏洞标题"

        # 清洗标题列表：去除空字符串、仅含无效字符的标题
        clean_titles = [title.strip() for title in title_list if
                        title.strip() and not re.match(IGNORE_CONTENT_PATTERN, title.strip())]
        # 返回第一个有效标题（若有），否则返回默认值
        return clean_titles[0] if clean_titles else "未获取到漏洞标题"
    except Exception as e:
        # 记录日志：大标题提取失败
        logging.error(f'大标题提取失败: {str(e)}')
        # 返回默认值
        return "未获取到漏洞标题"

# 定义函数：从HTML中提取表格中的漏洞基础信息
def extract_table_info(html: str) -> Dict[str, str]:
    """提取表格中的漏洞基础信息"""
    # 初始化表格信息字典：存储提取的漏洞基础字段
    table_info = {}
    try:
        # 将HTML文本解析为etree对象
        tree = etree.HTML(html)
        # 遍历TABLE_FIELDS中的每个字段（字段名称+XPath）
        for field_name, xpath in TABLE_FIELDS:
            try:
                # 使用XPath查询当前字段对应的节点
                nodes = tree.xpath(xpath)
                # 若未找到节点，记录警告日志，字段值设为“未找到该字段”
                if not nodes:
                    table_info[field_name] = "（未找到该字段）"
                    logging.warning(f'表格字段「{field_name}」未找到匹配节点（XPath：{xpath}）')
                    continue

                # 初始化文本列表：存储当前字段的有效文本
                text_list = []
                # 遍历每个查询到的节点
                for node in nodes:
                    # 处理文本节点（XPath直接返回文本）或元素节点（需要提取文本）
                    if isinstance(node, str):
                        # 若节点是字符串（XPath使用/text()直接获取文本），直接清洗
                        clean_text = node.strip()
                    else:
                        # 若节点是元素节点，使用tostring提取文本，编码为UTF-8并清洗
                        clean_text = etree.tostring(node, method='text', encoding='utf-8').decode('utf-8').strip()

                    # 若清洗后的文本有效（非空且不是无效字符），添加到文本列表
                    if clean_text and not re.match(IGNORE_CONTENT_PATTERN, clean_text):
                        text_list.append(clean_text)

                # 去除文本列表中的重复项（保持原有顺序）
                unique_text = list(dict.fromkeys(text_list))
                # 字段值：用“|”连接所有唯一有效文本，若无则设为“字段值为空”
                table_info[field_name] = " | ".join(unique_text) if unique_text else "（字段值为空）"
                # 记录日志：当前字段提取成功，输出字段值
                logging.info(f'表格字段「{field_name}」提取成功：{table_info[field_name]}')
            except Exception as e:
                # 若当前字段提取失败，记录错误日志，字段值设为“提取失败”
                table_info[field_name] = "（提取失败）"
                logging.error(f'表格字段「{field_name}」提取失败：{str(e)}（XPath：{xpath}）')
        # 返回提取的表格信息字典
        return table_info
    except Exception as e:
        # 若表格整体提取失败，记录错误日志，所有字段值设为“表格解析失败”
        logging.error(f'表格信息整体提取失败：{str(e)}')
        return {field: "（表格解析失败）" for field, _ in TABLE_FIELDS}

# 定义函数：定位详细信息的标记节点，用于后续按区间提取内容
def find_all_marker_nodes(soup: BeautifulSoup) -> Dict[str, Optional[BeautifulSoup]]:
    """定位详细信息的标记节点，用于区间提取"""
    # 初始化标记节点字典：存储每个标记对应的HTML节点
    marker_nodes = {}
    # 获取网页全部文本（去除多余空白，用于辅助判断标记是否存在）
    full_text = soup.get_text(separator='\n', strip=True)

    # 初始化候选节点列表：存储可能作为标记的HTML节点
    candidate_nodes = []
    # 遍历所有可能的标题标签（TITLE_TAGS）
    for tag in TITLE_TAGS:
        # 查找当前标签的所有节点
        for node in soup.find_all(tag):
            # 跳过父节点是忽略标签（IGNORE_TAGS）的节点（避免无效节点）
            if node.find_parents(IGNORE_TAGS):
                continue
            # 提取节点文本并清洗
            node_text = node.get_text(strip=True)
            # 筛选有效候选节点：文本长度4-25字符（符合标题长度特征）
            if node_text and 4 <= len(node_text) <= 25:
                candidate_nodes.append((node, node_text))

    # 遍历每个定位标记（POSITION_MARKERS），寻找匹配的节点
    for marker_key, marker_text in POSITION_MARKERS.items():
        # 初始化最佳匹配节点和最高匹配分数
        best_match = None
        highest_score = 0
        # 遍历所有候选节点
        for node, node_text in candidate_nodes:
            # 初始化匹配分数
            score = 0
            # 完全匹配：分数+7（最高优先级）
            if marker_text == node_text:
                score += 7
            # 部分匹配（标记文本在节点文本中）：分数+4
            elif marker_text in node_text:
                score += 4

            # 提取标记文本的核心部分（去除数字前缀，如“02 影响范围”→“影响范围”）
            core_text = marker_text.split()[-1] if ' ' in marker_text else marker_text
            # 正则匹配：若节点文本符合标题模板，分数+3
            for pattern in TITLE_CONTEXT_PATTERNS:
                if re.match(pattern.format(re.escape(core_text)), node_text, re.IGNORECASE):
                    score += 3
                    break

            # 标签优先级：标题标签在TITLE_TAGS中越靠前，分数越高（+1到+len(TITLE_TAGS)）
            score += len(TITLE_TAGS) - TITLE_TAGS.index(node.name)
            # 文本存在校验：标记文本在网页全文中，分数+1
            if marker_text in full_text:
                score += 1

            # 更新最佳匹配：若当前分数高于最高分数，且分数≥5（有效匹配）
            if score > highest_score and score >= 5:
                highest_score = score
                best_match = node

        # 存储当前标记对应的最佳匹配节点
        marker_nodes[marker_key] = best_match
        # 记录日志：找到或未找到标记节点
        if best_match:
            logging.info(f'找到标记「{marker_text}」，所在标签：<{best_match.name}>')
        else:
            logging.warning(f'未找到标记「{marker_text}」')

    # 返回所有标记节点的定位结果
    return marker_nodes

# 定义函数：按区间提取漏洞详细信息（根据标记节点的起始和结束位置）
def extract_content_by_ranges(marker_nodes: Dict[str, Optional[BeautifulSoup]], soup: BeautifulSoup) -> List[Dict]:
    """按区间提取漏洞详细信息（删除危害描述）"""
    # 初始化提取结果列表：存储每个分类的标题和内容
    extracted_content = []
    # 定义提取规则：每个分类的标题、起始标记键、结束标记键
    content_ranges = [
        {"title": "影响组件", "start_key": "影响组件", "end_key": "漏洞描述"},
        {"title": "漏洞描述", "start_key": "漏洞描述", "end_key": "影响范围_start"},
        {"title": "影响范围", "start_key": "影响范围_start", "end_key": "影响范围_end"},
        {"title": "其他受影响组件", "start_key": "其他受影响组件", "end_key": "其他受影响组件_end"},
        {"title": "复现情况", "start_key": "复现情况_start", "end_key": "复现情况_end"},
        {"title": "受影响资产情况", "start_key": "受影响资产情况_start", "end_key": "受影响资产情况_end"},
        {"title": "处置建议", "start_key": "处置建议_start", "end_key": "处置建议_end"}
    ]

    # 遍历每个提取规则
    for rule in content_ranges:
        # 获取当前分类的标题、起始标记键、结束标记键
        title = rule["title"]
        start_node = marker_nodes.get(rule["start_key"])
        end_node = marker_nodes.get(rule["end_key"])

        # 若未找到起始标记节点，记录未找到信息，添加到结果列表
        if not start_node:
            extracted_content.append({"title": title, "content": f'{CONTENT_INDENT}（未找到该标题的起始标记）'})
            continue

        # 初始化内容列表：存储当前分类的有效文本
        content_parts = []
        # 捕获标志：是否开始捕获文本（遇到起始节点后设为True）
        capture_flag = False
        # 遍历网页中所有文本节点（递归查找所有string类型节点）
        for text_node in soup.find_all(string=True, recursive=True):
            # 跳过父节点是忽略标签的文本节点
            if text_node.parent.name in IGNORE_TAGS:
                continue

            # 若当前文本节点的父节点是起始标记节点，设置捕获标志为True（开始捕获）
            if text_node.parent == start_node:
                capture_flag = True
                continue
            # 若当前文本节点的父节点是结束标记节点，设置捕获标志为False（停止捕获）并跳出循环
            if end_node and text_node.parent == end_node:
                capture_flag = False
                break

            # 若处于捕获状态，处理当前文本节点
            if capture_flag:
                # 清洗文本：去除多余空白
                clean_text = text_node.strip()
                # 筛选有效文本：非空、不是仅含无效字符、不是单个数字（如“01”“3”）
                if clean_text and not re.match(r'^0[1-9]$', clean_text) and not re.match(IGNORE_CONTENT_PATTERN, clean_text):
                    content_parts.append(clean_text)

        # 处理提取到的内容：去除重复项，格式化输出
        if content_parts:
            # 去除重复内容（保持原有顺序）
            unique_content = list(dict.fromkeys(content_parts))
            # 格式化：每个内容项前添加缩进
            formatted_content = '\n'.join([f'{CONTENT_INDENT}{part}' for part in unique_content])
        else:
            # 若无有效内容，设置为“暂无公开内容”
            formatted_content = f'{CONTENT_INDENT}（暂无公开内容）'

        # 将当前分类的标题和内容添加到结果列表
        extracted_content.append({"title": title, "content": formatted_content})

    # 返回所有分类的详细信息
    return extracted_content

# 定义函数：生成邮件主题、纯文本正文、HTML正文
def generate_email_content(big_title: str, table_info: Dict[str, str], content_info: List[Dict], url: str) -> Tuple[str, str, str]:
    """生成邮件主题、纯文本正文、HTML正文（删除信息来源和生成时间）"""
    # 生成动态邮件主题：使用模板填充漏洞大标题
    email_subject = EMAIL_CONFIG["email_subject_template"].format(big_title)

    # 构建纯文本正文（用于控制台打印和邮件备选正文）
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

    # 遍历详细信息，添加到纯文本正文
    for idx, item in enumerate(content_info, 1):
        title = item["title"]
        # 去除内容中的缩进，避免重复缩进
        content = item["content"].replace(CONTENT_INDENT, "").strip()
        text_content += f"""
{idx}. {title}
{content}

"""

    # 添加邮件说明部分
    text_content += f"""
四、说明
本邮件由系统自动发送，请勿回复。
如有疑问可联系：甘孜云 朱军  18228188727
"""

    # 构建HTML正文（用于邮件发送，支持富文本格式）
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

    # 遍历详细信息，添加到HTML正文
    for idx, item in enumerate(content_info, 1):
        title = item["title"]
        # 去除内容中的缩进，将换行符替换为HTML换行标签<br>
        content = item["content"].replace(CONTENT_INDENT, "").replace("\n", "<br>")
        html_content += f"""
    <div class="content-item">
        <div class="content-title">{idx}. {title}</div>
        <div class="content-text">{content}</div>
    </div>
    """

    # 添加HTML正文的页脚说明
    html_content += f"""
    <div class="footer">
        本邮件由系统自动生成，请勿直接回复。如有疑问可联系：甘孜云 朱军  18228188727。<br>
    </div>
</body>
</html>
"""

    # 返回邮件主题、纯文本正文、HTML正文（元组形式）
    return email_subject, text_content.strip(), html_content

# 定义函数：在控制台打印正式邮件正文（带颜色和格式）
def print_email_content(email_subject: str, email_text_content: str):
    """控制台打印正式邮件正文"""
    # 打印邮件发送信息（绿色加粗）
    print(f'\n{EMAIL_CONTENT_COLOR}{SEPARATOR_MAIN}')
    print(f'📧 正式邮件正文（发送至：{", ".join(EMAIL_CONFIG["receiver_emails"])}）')
    print(f'📌 邮件主题：{email_subject}')
    print(f'{SEPARATOR_MAIN}{RESET_COLOR}')
    # 打印纯文本邮件正文（默认颜色）
    print(email_text_content)
    # 打印邮件正文统计信息（绿色加粗）
    print(f'\n{EMAIL_CONTENT_COLOR}{SEPARATOR_MAIN}')
    print(f'📧 邮件正文打印完毕（共 {len(email_text_content)} 字符）')
    print(f'{SEPARATOR_MAIN}{RESET_COLOR}')

# 定义函数：发送漏洞通知邮件（支持重试和授权码认证）
def send_vulnerability_email(email_subject: str, html_content: str) -> bool:
    """发送邮件（适配授权码认证的SMTP服务器，优化连接稳定性）"""
    # 配置重试参数：最大重试2次，重试间隔3秒
    max_retries = 2
    retry_delay = 3

    # 循环重试发送邮件
    for retry in range(max_retries):
        # 初始化SMTP服务器对象为None
        server = None
        try:
            # 记录日志：开始发送邮件（第N次尝试）
            logging.info(f'\n{"=" * 40} 开始发送邮件（第{retry + 1}次尝试） {"=" * 40}')
            logging.info(f'邮件主题：{email_subject}')
            logging.info(f'收件人：{", ".join(EMAIL_CONFIG["receiver_emails"])}')

            # 创建多部分邮件对象（支持HTML正文）
            msg = MIMEMultipart()
            # 设置发件人：使用Header编码，避免中文乱码
            msg['From'] = Header(EMAIL_CONFIG["sender_email"], 'utf-8')
            # 设置收件人：多个收件人用逗号分隔，Header编码
            msg['To'] = Header(", ".join(EMAIL_CONFIG["receiver_emails"]), 'utf-8')
            # 设置邮件主题：Header编码，避免中文乱码
            msg['Subject'] = Header(email_subject, 'utf-8')

            # 向邮件对象添加HTML正文（指定编码为UTF-8）
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))

            # ------------ 核心修改：授权码认证 + 稳定连接 ------------
            # 1. 连接SMTP服务器：使用SSL加密，设置超时120秒（避免连接超时）
            server = smtplib.SMTP_SSL(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"], timeout=120)
            # 发送EHLO指令：与SMTP服务器建立稳定连接（解决部分服务器断开问题）
            server.ehlo()
            # 设置socket层超时：120秒（避免读取/写入超时）
            server.sock.settimeout(120)

            # 2. 可选：开启调试模式（排查邮件发送问题时启用，会输出详细SMTP交互日志）
            # server.set_debuglevel(1)

            try:
                # 3. 登录SMTP服务器：使用邮箱授权码（而非登录密码）认证
                server.login(EMAIL_CONFIG["sender_email"], EMAIL_CONFIG["sender_auth_code"])

                # 4. 发送邮件：发件人、收件人、邮件内容（编码为UTF-8避免中文乱码）
                server.sendmail(
                    EMAIL_CONFIG["sender_email"],
                    EMAIL_CONFIG["receiver_emails"],
                    msg.as_string().encode('utf-8')
                )
                # 记录日志：邮件发送成功
                logging.info(f'✅ 邮件发送成功！')
                # 控制台打印成功信息（绿色加粗）
                print(
                    f'\n{EMAIL_CONTENT_COLOR}✅ 邮件已成功发送至：{", ".join(EMAIL_CONFIG["receiver_emails"])}（主题：{email_subject}）{RESET_COLOR}')
                # 返回True表示发送成功
                return True
            finally:
                # 确保SMTP连接关闭（无论发送成功与否）
                if server:
                    try:
                        server.quit()
                    except:
                        # 忽略关闭连接时的异常（避免影响主流程）
                        pass

        except smtplib.SMTPAuthenticationError:
            # 处理SMTP认证失败（授权码错误/账号错误）
            logging.error(f'❌ 邮件发送失败：SMTP认证失败（授权码错误）！')
            logging.error(f'❌ 详细错误堆栈：\n{traceback.format_exc()}')
            print(f'\n❌ 邮件发送失败：SMTP认证失败')
            print(f'❌ 排查建议：1. 确认邮箱账号正确 2. 确认授权码有效（非登录密码） 3. 检查邮箱是否开启SMTP服务')
            # 认证失败无需重试，直接返回False
            return False
        except smtplib.SMTPServerDisconnected:
            # 处理SMTP服务器连接断开异常
            logging.error(f'❌ 邮件发送失败：SMTP服务器连接断开（第{retry + 1}次）！')
            # 若未达到最大重试次数，等待后重试
            if retry < max_retries - 1:
                logging.info(f'⏳ {retry_delay}秒后重试...')
                time.sleep(retry_delay)
        except smtplib.SMTPConnectError:
            # 处理SMTP服务器连接失败异常
            logging.error(f'❌ 邮件发送失败：无法连接SMTP服务器（第{retry + 1}次）！')
            # 若未达到最大重试次数，等待后重试
            if retry < max_retries - 1:
                logging.info(f'⏳ {retry_delay}秒后重试...')
                time.sleep(retry_delay)
        except Exception as e:
            # 处理其他未知异常
            error_msg = f'{type(e).__name__} - {str(e)}'
            logging.error(f'❌ 邮件发送失败（第{retry + 1}次）：{error_msg}')
            logging.error(f'❌ 详细错误堆栈：\n{traceback.format_exc()}')
            # 若未达到最大重试次数，等待后重试
            if retry < max_retries - 1:
                logging.info(f'⏳ {retry_delay}秒后重试...')
                time.sleep(retry_delay)

    # 多次重试后仍失败，打印提示信息
    print(f'\n❌ 多次重试后仍发送失败，请检查网络或联系邮箱服务商')
    # 返回False表示发送失败
    return False

# 定义函数：结构化打印漏洞提取结果（控制台友好格式）
def print_structured_result(big_title: str, table_info: Dict[str, str], content_info: List[Dict], url: str):
    """结构化打印提取结果（删除信息来源和生成时间）"""
    # 打印大标题（红色加粗）
    print(f'\n{SEPARATOR_MAIN}')
    print(f'{BIG_TITLE_COLOR}{" " * 50}{big_title}{RESET_COLOR}')
    print(f'📋 漏洞信息提取结果')
    print(f'{SEPARATOR_MAIN}')

    # 打印表格信息（黄色加粗）
    print(f'\n{TABLE_COLOR_TAG}{SEPARATOR_CATEGORY}')
    print(f' 📊 基础信息与评级（表格提取）')
    print(f'{SEPARATOR_CATEGORY}{RESET_COLOR}')
    # 分组打印表格字段：基础信息、评级信息、利用状态信息
    basic_fields = ["漏洞名称", "漏洞编号", "公开时间", "影响量级", "危害描述"]
    rating_fields = ["奇安信评级", "CVSS3.1分数", "威胁类型", "利用可能性"]
    exploit_fields = ["PoC状态", "在野利用状态", "EXP状态", "技术细节状态"]

    # 打印基础信息字段
    for field in basic_fields:
        print(f'{CONTENT_INDENT}{field}：{table_info[field]}')
    print()
    # 打印评级信息字段
    for field in rating_fields:
        print(f'{CONTENT_INDENT}{field}：{table_info[field]}')
    print()
    # 打印利用状态信息字段
    for field in exploit_fields:
        print(f'{CONTENT_INDENT}{field}：{table_info[field]}')

    # 打印详细信息（蓝色加粗）
    print(f'\n{CATEGORY_COLOR_TAG}{SEPARATOR_CATEGORY}')
    print(f' 📝 详细信息（区间提取）')
    print(f'{SEPARATOR_CATEGORY}{RESET_COLOR}')
    # 遍历每个详细信息分类，打印标题和内容
    for idx, item in enumerate(content_info, 1):
        title = item["title"]
        content = item["content"]
        print(f'\n{CATEGORY_COLOR_TAG}{"-" * 50}')
        print(f' {idx:02d}. {TITLE_PREFIX}{title}')
        print(f'{"-" * 50}{RESET_COLOR}')
        print(content)

    # 统计提取结果并打印
    total_table = len(TABLE_FIELDS)  # 表格字段总数
    # 统计成功提取的表格字段数（排除未找到/提取失败的字段）
    success_table = sum(
        1 for v in table_info.values() if "（未找到" not in v and "（提取失败" not in v and "（表格解析失败" not in v)
    total_content = len(content_info)  # 详细信息分类总数
    # 统计成功提取的详细信息分类数（排除未找到的分类）
    success_content = sum(1 for item in content_info if '（未找到' not in item['content'])
    # 统计详细信息总字符数（去除缩进和换行符）
    total_chars = sum(len(item['content'].replace(CONTENT_INDENT, '').replace('\n', '')) for item in content_info)

    # 打印统计信息
    print(f'\n{SEPARATOR_SUB}')
    print(f'📊 提取统计信息')
    print(f'   • 表格字段：{total_table} 个（成功：{success_table} 个）')
    print(f'   • 详细信息：{total_content} 个分类（成功：{success_content} 个）')
    print(f'   • 详细信息总字符数：{total_chars} 字')
    print(f'{SEPARATOR_MAIN}')

# 定义函数：批量处理多个URL的漏洞信息（抓取→提取→打印→发送邮件）
def batch_extract(urls: List[str], send_email: bool = True):
    """批量处理流程：抓取 → 提取 → 打印 → 发送邮件"""
    # 遍历每个目标URL（带索引）
    for idx, url in enumerate(urls, 1):
        # 打印当前处理进度
        print(f'\n{"=" * 60} 处理第 {idx}/{len(urls)} 个网页 {"=" * 60}')
        try:
            # 1. 抓取网页内容
            html = fetch_web_content(url)
            # 2. 提取网页大标题
            big_title = extract_big_title(html)
            # 3. 提取表格中的漏洞基础信息
            table_info = extract_table_info(html)
            # 4. 提取详细信息：创建BeautifulSoup对象→定位标记节点→按区间提取内容
            soup = BeautifulSoup(html, 'html.parser')
            marker_nodes = find_all_marker_nodes(soup)
            content_info = extract_content_by_ranges(marker_nodes, soup)
            # 5. 在控制台结构化打印提取结果
            print_structured_result(big_title, table_info, content_info, url)
            # 6. 生成邮件内容（主题、纯文本正文、HTML正文）并打印邮件正文
            email_subject, email_text, email_html = generate_email_content(big_title, table_info, content_info, url)
            print_email_content(email_subject, email_text)
            # 7. 若send_email为True，发送邮件
            if send_email:
                send_vulnerability_email(email_subject, email_html)

        except Exception as e:
            # 处理当前URL的处理异常，打印错误信息
            print(f'❌ 第 {idx} 个网页处理失败：{str(e)}')
            print(f'{"-" * 150}')
            # 打印详细异常堆栈，方便调试
            traceback.print_exc()
            # 继续处理下一个URL
            continue

# -------------------------- 执行入口 --------------------------
# 若脚本直接运行（而非被导入），执行以下逻辑
if __name__ == "__main__":
    # 目标URL列表：存储需要抓取的漏洞网页URL（可添加多个）
    TARGET_URLS = [
        'https://www.secrss.com/articles/85995',
        # 可添加更多漏洞网页URL
    ]
    # 调用批量处理函数：处理所有目标URL，发送邮件（send_email=True）
    batch_extract(TARGET_URLS, send_email=True)