import requests
import os
import hmac
import hashlib
import datetime
import base64
from urllib.parse import quote


def create_canonical_request(method, path, query_string, headers, payload_hash):
    """创建规范请求"""
    canonical_headers = '\n'.join([f'{k.lower()}:{headers[k].strip()}' for k in sorted(headers)])
    signed_headers = ';'.join([k.lower() for k in sorted(headers)])
    canonical_request = f"{method}\n{path}\n{query_string}\n{canonical_headers}\n\n{signed_headers}\n{payload_hash}"

    # 打印规范请求（调试用）
    print("\n=== 规范请求 (Canonical Request) ===")
    print(canonical_request)
    print("====================================\n")

    return canonical_request, signed_headers


def create_string_to_sign(canonical_request, region, service, date_str, credential_scope):
    """创建待签名的字符串"""
    algorithm = "AWS4-HMAC-SHA256"
    string_to_sign = f"{algorithm}\n{date_str}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"

    # 打印待签名的字符串（调试用）
    print("\n=== 待签名的字符串 (String to Sign) ===")
    print(string_to_sign)
    print("=======================================\n")

    return string_to_sign


def get_signature_key(secret_key, date_stamp, region_name, service_name):
    """生成签名密钥"""
    k_date = hmac.new(('AWS4' + secret_key).encode('utf-8'), date_stamp.encode('utf-8'), hashlib.sha256).digest()
    k_region = hmac.new(k_date, region_name.encode('utf-8'), hashlib.sha256).digest()
    k_service = hmac.new(k_region, service_name.encode('utf-8'), hashlib.sha256).digest()
    k_signing = hmac.new(k_service, b'aws4_request', hashlib.sha256).digest()
    return k_signing


def upload_file_with_requests(endpoint, access_key, secret_key, region, bucket, file_path, object_name=None):
    """使用requests库直接上传文件到S3兼容存储，并打印完整请求/响应信息"""
    print(f"\n===== 开始上传文件: {file_path} =====")

    # 检查文件
    if not os.path.exists(file_path):
        print(f"错误: 文件 {file_path} 不存在")
        return False

    file_size = os.path.getsize(file_path)
    if file_size == 0:
        print(f"错误: 文件 {file_path} 为空")
        return False

    if object_name is None:
        object_name = os.path.basename(file_path)

    print(f"文件信息: {file_path} (大小: {file_size} 字节)")

    # 解析endpoint
    from urllib.parse import urlparse
    parsed_url = urlparse(endpoint)
    host = parsed_url.hostname
    port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)
    protocol = parsed_url.scheme
    endpoint_path = parsed_url.path.rstrip('/')

    # 构建请求参数
    method = 'PUT'
    path = f"{endpoint_path}/{bucket}/{quote(object_name)}"
    query_string = ''

    # 生成日期
    now = datetime.datetime.utcnow()
    date_str = now.strftime('%Y%m%dT%H%M%SZ')
    date_stamp = now.strftime('%Y%m%d')

    print(f"请求日期: {date_str}")

    # 计算文件哈希
    print("计算文件SHA256哈希...")
    with open(file_path, 'rb') as f:
        file_content = f.read()
        payload_hash = hashlib.sha256(file_content).hexdigest()
    print(f"文件哈希: {payload_hash}")

    # 设置请求头
    headers = {
        'Host': host,
        'Date': date_str,
        'Content-Type': 'application/octet-stream',
        'Content-Length': str(file_size),
        'x-amz-content-sha256': payload_hash,
        'x-amz-date': date_str
    }

    print("\n=== 请求头 ===")
    for key, value in headers.items():
        print(f"{key}: {value}")

    # 创建规范请求和签名
    print("\n=== 生成签名 ===")
    canonical_request, signed_headers = create_canonical_request(
        method, path, query_string, headers, payload_hash
    )
    credential_scope = f"{date_stamp}/{region}/s3/aws4_request"
    string_to_sign = create_string_to_sign(
        canonical_request, region, 's3', date_str, credential_scope
    )
    signing_key = get_signature_key(secret_key, date_stamp, region, 's3')
    signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

    # 添加授权头
    headers[
        'Authorization'] = f"AWS4-HMAC-SHA256 Credential={access_key}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"
    print(f"Authorization: {headers['Authorization']}")

    # 发送请求
    url = f"{protocol}://{host}:{port}{path}"
    print(f"\n=== 发送请求 ===")
    print(f"请求方法: {method}")
    print(f"请求URL: {url}")

    # 创建会话并禁用SSL验证（生产环境建议启用）
    session = requests.Session()
    session.verify = False

    # 发送请求并捕获详细响应
    try:
        with session.put(url, data=file_content, headers=headers) as response:
            print(f"\n=== 响应信息 ===")
            print(f"状态码: {response.status_code}")

            print("\n响应头:")
            for key, value in response.headers.items():
                print(f"{key}: {value}")

            print("\n响应内容:")
            print(response.text)

            if response.status_code == 200:
                print(f"\n✅ 文件 {file_path} 已成功上传到 {bucket}/{object_name}")
                return True
            else:
                print(f"\n❌ 上传失败，状态码: {response.status_code}")
                return False

    except Exception as e:
        print(f"\n❌ 请求异常: {e}")
        return False


def main():
    endpoint = 'https://ossaz1.gzy-hlw.intranet.gzcloud.cn:6069/'
    access_key = 'ZfwLQJcALh46LLUafdHA'
    secret_key = 'swJy0gLct4Ser0jCMTQpykdKTF5nhkbPUQzsNVDh'
    region = 'az1'
    bucket = 'zhujun'
    file_path = 'D:\\1.txt'

    upload_file_with_requests(endpoint, access_key, secret_key, region, bucket, file_path)


if __name__ == "__main__":
    main()