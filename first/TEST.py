import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
import urllib3

# 忽略 SSL 警告（因 verify=False）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ====== Ceph S3 配置 ======
CEPH_ENDPOINT = "http://10.1.26.236:20003"
CEPH_ACCESS_KEY = "31qfugp5qGDyjlBbuIf6"
CEPH_SECRET_KEY = "Pd0T7I4BwucrX0peXP6cTCMCU9jpPZNWNJWxQOO7"
CEPH_REGION = "default-region"


def create_ceph_s3_client():
    """创建 Ceph S3 客户端（强制 path-style）"""
    try:
        s3_client = boto3.client(
            "s3",
            endpoint_url=CEPH_ENDPOINT,
            aws_access_key_id=CEPH_ACCESS_KEY,
            aws_secret_access_key=CEPH_SECRET_KEY,
            region_name=CEPH_REGION,
            verify=False,
            config=Config(
                signature_version="s3v4",
                retries={"max_attempts": 3},
                s3={"addressing_style": "path"}  # 关键：避免虚拟主机式解析
            )
        )
        # 简单测试：尝试列出桶（不报错即连通）
        s3_client.list_buckets()
        print("✅ Ceph S3 客户端连接成功")
        return s3_client
    except Exception as e:
        print(f"❌ 无法连接 Ceph S3: {e}")
        return None


def create_bucket_indirectly(s3_client, bucket_name):
    """
    通过上传一个临时对象间接创建桶（绕过 CreateBucket 的 InvalidRange Bug）
    """
    temp_key = ".bucket-init-marker"
    try:
        # 上传一个空对象 → 自动创建桶（如果允许）
        s3_client.put_object(Bucket=bucket_name, Key=temp_key, Body=b"")
        print(f"✅ 桶 '{bucket_name}' 创建成功（通过 put_object）")
        # 清理临时对象
        s3_client.delete_object(Bucket=bucket_name, Key=temp_key)
        return True
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'BucketAlreadyOwnedByYou':
            print(f"ℹ️  桶 '{bucket_name}' 已存在且属于你")
            return True
        elif error_code == 'NoSuchBucket':
            # 理论上不会出现，因为 put_object 会自动建桶
            print(f"❌ 桶创建失败：RGW 可能禁止用户自动创建桶")
            return False
        elif 'AccessDenied' in str(e):
            print(f"❌ 权限不足：无法创建桶或上传对象")
            return False
        else:
            print(f"❌ 创建桶时发生未知错误: {e}")
            return False
    except Exception as e:
        print(f"❌ 创建桶异常: {e}")
        return False


def verify_bucket_exists(s3_client, bucket_name):
    """验证桶是否在用户桶列表中"""
    try:
        buckets = s3_client.list_buckets().get('Buckets', [])
        bucket_names = [b['Name'] for b in buckets]
        if bucket_name in bucket_names:
            print(f"✅ 验证成功：桶 '{bucket_name}' 存在于你的账户中")
        else:
            print(f"⚠️  验证失败：桶 '{bucket_name}' 不在列表中（可能权限隔离）")
    except Exception as e:
        print(f"❌ 验证桶失败: {e}")


if __name__ == "__main__":
    # 修改为你自己的唯一桶名（避免冲突）
    BUCKET_NAME = "test-20260211-004"

    print(f"🔧 尝试创建桶: {BUCKET_NAME}")

    # 1. 创建客户端
    client = create_ceph_s3_client()
    if not client:
        exit(1)

    # 2. 间接创建桶（核心 workaround）
    success = create_bucket_indirectly(client, BUCKET_NAME)

    # 3. 验证
    if success:
        verify_bucket_exists(client, BUCKET_NAME)
    else:
        print("🛑 桶创建失败，退出。")
        exit(1)