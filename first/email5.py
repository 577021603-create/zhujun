import imaplib
import email
import requests
from email.header import decode_header
from datetime import datetime, timedelta
import re
import time
import sys
from bs4 import BeautifulSoup

# 邮箱配置
IMAP_SERVER = 'imap.qq.com'
IMAP_PORT = 993
EMAIL = '2332586642@qq.com'
PASSWORD = 'vzibdhsssvtzdhge'  # 确保是正确的授权码
CHECK_FOLDERS = ['INBOX']
TIME_RANGE_MINUTES = 1
LOOP_INTERVAL = 45

# 告警配置
ALARM_KEYWORDS = [
    "脱落", "Link down", "交换机不可达","节点采集器",
    "节点重启", "交换机_在线状态","网络设备接口DOWN事件","异常节点总数",
    "物理服务器_在线状态", "ping loss","物理服务器_电源状态"
]
ALARM_URL = "https://push.spug.cc/send/Xyd9M8Apv0rKbDBk"
ALARM_TARGET = "18228188727"


def decode_str(encoded_str):
    """解码邮件主题、发件人等字段"""
    if not encoded_str:
        return ""
    decoded_parts = decode_header(encoded_str)
    result = ""
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            result += part.decode(encoding or 'utf-8', errors='replace')
        else:
            result += part
    return result


def html_to_string(html):
    """将HTML内容转换为纯字符串"""
    if not html:
        return ""
    soup = BeautifulSoup(html, 'html.parser')
    return soup.get_text(separator=' ', strip=False)


def extract_specific_values(content_str):
    """从字符串中提取"资源名称"和"告警主机"的值"""
    extracted = {
        "资源名称": None,
        "告警主机": None,
        "告警实例": None
    }

    # 提取资源名称
    target = "资源名称"
    index = content_str.find(target)
    if index != -1:
        after_target = content_str[index + len(target):].lstrip()
        comma_index = after_target.find("，")  # 中文逗号
        if comma_index == -1:
            comma_index = after_target.find(",")  # 英文逗号
        if comma_index != -1:
            extracted["资源名称"] = after_target[:comma_index].strip()
        else:
            extracted["资源名称"] = after_target.strip()

    # 提取资源名称
    target = "告警实例"
    index = content_str.find(target)
    if index != -1:
        after_target = content_str[index + len(target):].lstrip()
        comma_index = after_target.find("，")  # 中文逗号
        if comma_index == -1:
            comma_index = after_target.find(",")  # 英文逗号
        if comma_index != -1:
            extracted["告警实例"] = after_target[:comma_index].strip()
        else:
            extracted["告警实例"] = after_target.strip()

    # 提取告警主机
    target = "告警主机"
    index = content_str.find(target)
    if index != -1:
        after_target = content_str[index + len(target):].lstrip()
        comma_index = after_target.find("，")  # 中文逗号
        if comma_index == -1:
            comma_index = after_target.find(",")  # 英文逗号
        if comma_index != -1:
            extracted["告警主机"] = after_target[:comma_index].strip()
        else:
            extracted["告警主机"] = after_target.strip()

    return extracted


def check_keywords(content_str):
    """检查内容中是否包含告警关键字，返回匹配的关键字列表"""
    content_lower = content_str.lower()
    matched = []
    for keyword in ALARM_KEYWORDS:
        if keyword.lower() in content_lower:
            matched.append(keyword)
    return matched


def trigger_alarm(value):
    """触发电话告警（调用API）"""
    if not value:
        print("⚠️ 没有可用于告警的有效值，不触发告警")
        return

    try:
        data = {
            'key1': value,
            'targets': ALARM_TARGET
        }
        response = requests.post(ALARM_URL, json=data, timeout=10)
        response.raise_for_status()  # 抛出HTTP错误
        print(f"📢 告警触发成功！key1值：{value}，响应：{response.json()}")
    except Exception as e:
        print(f"❌ 告警触发失败：{str(e)}")


def process_emails():
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n{'=' * 50}")
    print(f"开始处理邮件 - {current_time}")
    print(f"{'=' * 50}\n")

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        try:
            mail.login(EMAIL, PASSWORD)
            print(f"✅ 成功登录邮箱：{EMAIL}")
        except imaplib.IMAP4.error as e:
            print(f"❌ 登录失败：{e}（请检查授权码和IMAP设置）")
            return

        # 时间范围计算
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=TIME_RANGE_MINUTES, seconds=10)
        imap_start_date = start_time.strftime('%d-%b-%Y')
        print(f"🔍 搜索范围：{start_time.strftime('%Y-%m-%d %H:%M:%S')} 至 {end_time.strftime('%Y-%m-%d %H:%M:%S')}")

        all_recent_emails = []

        # 获取符合条件的邮件
        for folder in CHECK_FOLDERS:
            try:
                status, _ = mail.select(folder, readonly=True)
                if status != 'OK':
                    continue

                mail.noop()
                status, messages = mail.search(None, f'SINCE "{imap_start_date}"')
                if status != 'OK':
                    continue

                email_ids = messages[0].split()
                if not email_ids:
                    continue

                for email_id in email_ids:
                    try:
                        status, data = mail.fetch(email_id, '(INTERNALDATE)')
                        if status != 'OK':
                            continue

                        raw_data = data[0].decode(errors='replace')
                        match = re.search(r'INTERNALDATE "([^"]+)"', raw_data)
                        if not match:
                            continue

                        internal_date = datetime.strptime(match.group(1), '%d-%b-%Y %H:%M:%S %z')
                        if internal_date.astimezone(tz=None).replace(tzinfo=None) >= start_time:
                            all_recent_emails.append({
                                'id': email_id.decode(),
                                'folder': folder,
                                'recv_time': internal_date
                            })
                    except:
                        continue

            except:
                continue

        # 处理邮件
        all_recent_emails.sort(key=lambda x: x['recv_time'])
        if not all_recent_emails:
            print(f"❌ 未找到最近{TIME_RANGE_MINUTES}分钟内的邮件")
            mail.logout()
            return

        print(f"\n🎉 共找到 {len(all_recent_emails)} 封邮件，开始处理...\n")
        for i, email_info in enumerate(all_recent_emails, 1):
            try:
                mail.select(email_info['folder'], readonly=True)
                status, data = mail.fetch(email_info['id'], '(RFC822)')
                if status != 'OK':
                    continue

                msg = email.message_from_bytes(data[0][1])
                sender = decode_str(msg.get('From', '未知发件人'))
                subject = decode_str(msg.get('Subject', '无主题'))
                recv_time = email_info['recv_time'].astimezone(tz=None).strftime('%Y-%m-%d %H:%M:%S')
                recipients = decode_str(msg.get('To', '未知收件人'))

                # 提取并转换正文为字符串
                body_str = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        if content_type in ['text/html', 'text/plain']:
                            charset = part.get_content_charset() or 'utf-8'
                            payload = part.get_payload(decode=True)
                            if payload:
                                part_str = payload.decode(charset, errors='replace')
                                if content_type == 'text/html':
                                    part_str = html_to_string(part_str)
                                body_str += part_str + "\n"
                else:
                    content_type = msg.get_content_type()
                    charset = msg.get_content_charset() or 'utf-8'
                    payload = msg.get_payload(decode=True)
                    if payload:
                        body_str = payload.decode(charset, errors='replace')
                        if content_type == 'text/html':
                            body_str = html_to_string(body_str)

                # 打印邮件基本信息
                print(f"{'=' * 60}")
                print(f"邮件 {i}/{len(all_recent_emails)} 详情")
                print(f"{'=' * 60}")
                print(f"主题：{subject}")
                print(f"发件人：{sender}")
                print(f"收件人：{recipients}")
                print(f"接收时间：{recv_time}")
                print(f"邮件ID：{email_info['id']}")
                print(f"\n--- 邮件完整内容开始 ---")
                # 限制内容长度，避免过长输出（可根据需要调整）
                if len(body_str) > 2000:
                    print(body_str[:2000] + "\n...（内容过长，已截断）")
                else:
                    print(body_str)
                print(f"--- 邮件完整内容结束 ---\n")

                # 提取指定值
                extracted_values = extract_specific_values(body_str)
                print(f"【提取结果】")
                print(f"资源名称: {extracted_values['资源名称'] if extracted_values['资源名称'] else '未找到'}")
                print(f"告警主机: {extracted_values['告警主机'] if extracted_values['告警主机'] else '未找到'}\n")
                print(f"告警实例: {extracted_values['告警实例'] if extracted_values['告警实例'] else '未找到'}\n")
                # 检查告警关键字
                matched_keywords = check_keywords(body_str)
                if matched_keywords:
                    print(f"⚠️ 检测到告警关键字：{', '.join(matched_keywords)}")
                    # 使用资源名称作为告警值，如果没有则使用告警主机
                    alarm_value = extracted_values['资源名称'] or extracted_values['告警主机'] or extracted_values['告警实例']
                    if alarm_value:
                        trigger_alarm(alarm_value)
                    else:
                        print("⚠️ 未找到可用的告警值，无法触发告警")
                else:
                    print("ℹ️ 未检测到任何告警关键字，不触发告警")

                print(f"\n{'=' * 60}\n")

            except Exception as e:
                print(f"⚠️ 处理邮件ID {email_info['id']} 时出错：{e}\n")
                continue

        mail.logout()
        print(f"✅ 所有邮件处理完成")

    except Exception as e:
        print(f"❌ 程序错误：{str(e)}")


def main_loop():
    print(f"程序启动：每分钟检查收件箱（最近{TIME_RANGE_MINUTES}分钟），按Ctrl+C停止\n")
    try:
        while True:
            process_emails()
            print(f"等待 {LOOP_INTERVAL} 秒后下一次检查...\n{'-' * 70}\n")
            time.sleep(LOOP_INTERVAL)
    except KeyboardInterrupt:
        print("\n程序已手动停止")


if __name__ == '__main__':
    # 检查依赖
    output_file = "D:\\log\\monitor_output.txt"
    original_stdout = sys.stdout
    with open("D:\\log.TXT", "a+", encoding="utf-8") as f:
        sys.stdout = f
    main_loop()
sys.stdout = original_stdout
