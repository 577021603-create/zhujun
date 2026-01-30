import hmac
import hashlib
import base64
import datetime
import urllib.parse
from typing import Dict, List, Optional, Tuple


class SignatureGenerator:
    """对象存储服务签名生成器，支持 AWS S3"""

    def __init__(self, access_key: str, secret_key: str, region: str = 'us-east-1'):
        """
        初始化签名生成器

        Args:
            access_key: 访问密钥 ID
            secret_key: 秘密访问密钥
            region: 区域（默认 'us-east-1'）
        """
        self.access_key = "ZfwLQJcALh46LLUafdHA"
        self.secret_key = "swJy0gLct4Ser0jCMTQpykdKTF5nhkbPUQzsNVDh"
        self.region = "az1"

    def generate_aws_sigv4(
            self,
            method: str,
            host: str,
            path: str,
            query_params: Dict[str, str] = None,
            headers: Dict[str, str] = None,
            payload: bytes = b'',
            service: str = 's3',
            timestamp: Optional[datetime.datetime] = None
    ) -> Tuple[str, Dict[str, str]]:
        """
        生成 AWS S3 签名版本 4

        Args:
            method: HTTP 请求方法（GET、POST 等）
            host: 主机名
            path: 请求路径
            query_params: 查询参数
            headers: 请求头
            payload: 请求负载（字节）
            service: 服务名（默认 's3'）
            timestamp: 时间戳（默认当前时间）

        Returns:
            Tuple[Authorization头部, 包含必需头部的完整请求头]
        """
        # 默认值
        query_params = query_params or {}
        headers = headers or {}
        timestamp = timestamp or datetime.datetime.utcnow()

        # 格式化时间
        amz_date = timestamp.strftime('%Y%m%dT%H%M%SZ')
        date_stamp = timestamp.strftime('%Y%m%d')

        # 构建规范请求
        canonical_headers = self._get_canonical_headers(headers)
        signed_headers = ';'.join(sorted([k.lower() for k in headers.keys()]))

        # 对路径和查询参数进行编码
        encoded_path = self._encode_uri_component(path)
        canonical_querystring = self._get_canonical_querystring(query_params)

        # 计算 payload 哈希
        payload_hash = hashlib.sha256(payload).hexdigest()

        # 构建规范请求
        canonical_request = (
            f"{method}\n"
            f"{encoded_path}\n"
            f"{canonical_querystring}\n"
            f"{canonical_headers}\n\n"
            f"{signed_headers}\n"
            f"{payload_hash}"
        )

        # 构建待签字符串
        algorithm = 'AWS4-HMAC-SHA256'
        credential_scope = f"{date_stamp}/{self.region}/{service}/aws4_request"
        string_to_sign = (
            f"{algorithm}\n"
            f"{amz_date}\n"
            f"{credential_scope}\n"
            f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
        )

        # 生成签名密钥
        signing_key = self._get_signature_key(self.secret_key, date_stamp, self.region, service)

        # 计算签名
        signature = hmac.new(
            signing_key,
            string_to_sign.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        # 构建 Authorization 头部
        authorization_header = (
            f"{algorithm} Credential={self.access_key}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )

        # 添加必需的头部
        headers['x-amz-date'] = amz_date
        headers['Host'] = host

        return authorization_header, headers

    def _get_canonical_headers(self, headers: Dict[str, str]) -> str:
        """获取规范化的请求头"""
        canonical_headers = []
        for k, v in sorted(headers.items(), key=lambda x: x[0].lower()):
            key = k.lower().strip()
            value = v.strip()
            canonical_headers.append(f"{key}:{value}")
        return '\n'.join(canonical_headers)

    def _get_canonical_querystring(self, params: Dict[str, str]) -> str:
        """获取规范化的查询字符串"""
        if not params:
            return ''

        # 排序并编码参数
        sorted_params = sorted(params.items())
        encoded_params = []

        for k, v in sorted_params:
            # AWS 特殊编码规则
            encoded_k = urllib.parse.quote(k, safe='-_.~')
            encoded_v = urllib.parse.quote(v, safe='-_.~')
            encoded_params.append(f"{encoded_k}={encoded_v}")

        return '&'.join(encoded_params)

    def _get_signature_key(self, key: str, date_stamp: str, region_name: str, service_name: str) -> bytes:
        """生成 AWS 签名密钥"""
        k_date = hmac.new(('AWS4' + key).encode('utf-8'), date_stamp.encode('utf-8'), hashlib.sha256).digest()
        k_region = hmac.new(k_date, region_name.encode('utf-8'), hashlib.sha256).digest()
        k_service = hmac.new(k_region, service_name.encode('utf-8'), hashlib.sha256).digest()
        k_signing = hmac.new(k_service, b'aws4_request', hashlib.sha256).digest()
        return k_signing


if __name__ == "__main__":
    # 示例：生成 S3 GET 对象请求的签名
    ACCESS_KEY = "your_access_key_here"  # 替换为你的 Access Key
    SECRET_KEY = "your_secret_key_here"  # 替换为你的 Secret Key
    REGION = "us-east-1"  # 替换为你的区域

    # 创建签名生成器
    generator = SignatureGenerator(
        access_key=ACCESS_KEY,
        secret_key=SECRET_KEY,
        region=REGION
    )

    # 设置请求参数
    method = "GET"
    host = "your-bucket.s3.us-east-1.amazonaws.com"
    path = "/test-object.txt"
    query_params = {}
    headers = {
        "Content-Type": "application/octet-stream"
    }
    payload = b""

    # 生成签名
    auth_header, final_headers = generator.generate_aws_sigv4(
        method=method,
        host=host,
        path=path,
        query_params=query_params,
        headers=headers,
        payload=payload
    )

    # 打印结果
    print("生成的 Authorization 头部:")
    print(auth_header)
    print("\n完整请求头:")
    for key, value in final_headers.items():
        print(f"{key}: {value}")

    # 打印完整的 curl 命令示例
    print("\n\n完整的 curl 命令示例:")
    curl_cmd = f"curl -X {method} \\\n"
    for key, value in final_headers.items():
        curl_cmd += f'  -H "{key}: {value}" \\\n'
    curl_cmd += f"  https://{host}{path}"
    print(curl_cmd)