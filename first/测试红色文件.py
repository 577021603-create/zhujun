import requests
import hmac
import hashlib
import datetime
import base64
from urllib.parse import quote, urlparse
import re

# 禁用 SSL 警告（适配内网 HTTP 环境）
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)


def generate_s3_v2_signature(secret_key, method, bucket_name, date_str):
    """
    生成 14.2 兼容的极简 S3 v2 签名（仅保留核心字段）
    """
    # 14.2 仅兼容 「/桶名」 格式的规范资源，无多余路径
    canonical_resource = f"/{bucket_name}"
    # 极简待签名字符串（仅 method + 空行 + date + 资源，无多余字段）
    string_to_sign = f"{method}\n\n\n{date_str}\n{canonical_resource}"

    # 生成 HMAC-SHA1 签名（14.2 唯一兼容算法）
    signature = hmac.new(
        secret_key.encode('utf-8'),
        string_to_sign.encode('utf-8'),
        hashlib.sha1
    ).digest()
    signature_b64 = base64.b64encode(signature).decode('utf-8')

    return signature_b64, string_to_sign


def create_bucket_142_compatible(endpoint, access_key, secret_key, bucket_name):
    """
    适配 Ceph 14.2 的 S3 API 创建桶（极致精简请求，解决 416 错误）
    """
    print(f"\n===== 开始创建桶: {bucket_name} (14.2 API 极简适配) =====")

    # 解析 endpoint（仅保留 IP+端口，移除多余路径）
    parsed_url = urlparse(endpoint)
    host = parsed_url.hostname
    port = parsed_url.port or 80
    protocol = parsed_url.scheme

    # 14.2 兼容的请求 URL（仅 IP:端口/桶名，无 endpoint 路径）
    # 核心修复：移除 endpoint 中的自定义路径，仅保留 RGW 根路径
    request_url = f"{protocol}://{host}:{port}/{quote(bucket_name)}"

    # 生成 14.2 严格兼容的日期格式（RFC 1123，无毫秒，严格英文星期/月份）
    now = datetime.datetime.utcnow()
    date_str = now.strftime('%a, %d %b %Y %H:%M:%S GMT')
    # 修复中文环境可能的星期/月份翻译问题（强制英文）
    date_str = re.sub(r'[一二三四五六日]', lambda x: {
        '一': 'Mon', '二': 'Tue', '三': 'Wed', '四': 'Thu',
        '五': 'Fri', '六': 'Sat', '日': 'Sun'
    }[x.group()], date_str)
    date_str = re.sub(r'[年月]', lambda x: {
        '年': '', '月': ''
    }[x.group()], date_str)

    # 生成签名
    signature_b64, string_to_sign = generate_s3_v2_signature(
        secret_key, "PUT", bucket_name, date_str
    )
    auth_header = f"AWS {access_key}:{signature_b64}"

    # 14.2 极简请求头（仅保留 3 个必需头，多一个都可能触发 416）
    # 核心修复：移除 Content-Length 头（14.2 对空 Content-Length 解析异常）
    headers = {
        'Host': f"{host}:{port}",  # 仅 IP:端口，无多余域名
        'Date': date_str,  # 严格 RFC 1123 格式
        'Authorization': auth_header  # 极简 v2 签名
    }

    # 打印调试信息（核心字段）
    print(f"请求 URL: {request_url}")
    print(f"日期头: {date_str}")
    print(f"待签名字符串:\n{string_to_sign}")
    print(f"Authorization: {auth_header}")
    print(f"请求头: {headers}")

    # 发送请求（核心：空请求体 + 无 Content-Length + 短超时）
    session = requests.Session()
    session.verify = False
    session.headers = {}  # 清空默认头，避免干扰

    try:
        # 14.2 兼容的请求：PUT + 空字节体 + 极简头
        response = session.put(
            request_url,
            data=b'',  # 空体，不设置 Content-Length
            headers=headers,
            timeout=10,
            stream=False  # 禁用流式传输
        )

        # 解析响应
        print(f"\n=== 响应信息 ===")
        print(f"状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        print(f"响应内容: {response.text[:500]}")

        # 14.2 兼容的状态码判断
        if response.status_code in [200, 204]:
            print(f"\n✅ 桶 {bucket_name} 创建成功！(14.2 API 适配)")
            return True
        elif response.status_code == 409:
            print(f"\nℹ️ 桶 {bucket_name} 已存在，无需重复创建！")
            return True
        elif response.status_code == 403:
            print(f"\n❌ 权限错误：AK/SK 错误或无创建桶权限！")
            return False
        elif response.status_code == 416:
            print(f"\n⚠️  最后尝试：强制跳过 Range 解析（14.2 终极修复）")
            # 终极兜底：添加 Range: bytes=0-0 头（欺骗 14.2 解析器）
            headers['Range'] = 'bytes=0-0'
            response = session.put(request_url, data=b'', headers=headers, timeout=10)
            if response.status_code in [200, 204, 409]:
                print(f"✅ 桶 {bucket_name} 创建成功（Range 兜底修复）！")
                return True
            else:
                print(f"❌ 所有 API 方案均失败，状态码: {response.status_code}")
                return False
        else:
            print(f"\n❌ 创建失败，状态码: {response.status_code}")
            return False

    except Exception as e:
        print(f"\n❌ 请求异常: {str(e)}")
        return False


def main():
    # -------------------------- 你的配置（直接替换） --------------------------
    ENDPOINT = "http://10.1.26.236:20003/"  # 你的 RGW 地址
    ACCESS_KEY = "31qfugp5qGDyjlBbuIf6"  # 你的 AK
    SECRET_KEY = "Pd0T7I4BwucrX0peXP6cTCMCU9jpPZNWNJWxQOO7"  # 你的 SK
    BUCKET_NAME = "test-bucket-142-final"  # 桶名（小写+数字，无特殊字符）

    # 执行创建桶
    create_bucket_142_compatible(ENDPOINT, ACCESS_KEY, SECRET_KEY, BUCKET_NAME)


if __name__ == "__main__":
    main()