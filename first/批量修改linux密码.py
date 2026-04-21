import paramiko
from paramiko.ssh_exception import NoValidConnectionsError, AuthenticationException


def change_ccadmin_password_with_key(
        host: str,
        port: int = 22,
        username: str = "ccadmin",  # 登录用户（可以是非ccadmin，脚本会自动sudo）
        private_key_path: str = "C:\\Users\\23325\\Desktop\\TEST\\圣洁云创\\平台技术资料\\软件脚本工具\\服务器私钥\\private-key",  # 你的私钥路径
        new_ccadmin_password: str = "Cestc@2026!"
):
    """
    使用SSH密钥登录Linux，修改ccadmin密码
    :param host: 服务器IP
    :param port: SSH端口
    :param username: 密钥登录的用户名
    :param private_key_path: 私钥文件路径
    :param new_ccadmin_password: 要设置的新ccadmin密码
    """
    # 加载私钥
    try:
        private_key = paramiko.RSAKey.from_private_key_file(private_key_path)
    except Exception as e:
        print(f"私钥加载失败：{str(e)}")
        return False

    # 创建SSH客户端
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # 密钥登录服务器
        print(f"正在连接 {host}，密钥登录中...")
        ssh.connect(
            hostname=host,
            port=port,
            username=username,
            pkey=private_key,
            timeout=10
        )
        print("登录成功！")

        # 执行修改ccadmin密码命令
        # echo 'ccadmin:新密码' | chpasswd 是Linux标准改密命令
        command = f"echo 'ccadmin:{new_ccadmin_password}' | sudo chpasswd"
        print(command)
        stdin, stdout, stderr = ssh.exec_command(command, get_pty=True)

        # 获取输出
        error = stderr.read().decode("utf-8")
        output = stdout.read().decode("utf-8")

        if error:
            print(f"执行失败：{error}")
            return False
        else:
            print(f"ccadmin 密码修改成功！新密码：{new_ccadmin_password}")
            return True

    except AuthenticationException:
        print("认证失败：密钥错误或无权限")
    except NoValidConnectionsError:
        print("连接失败：IP/端口不通或服务器不可达")
    except Exception as e:
        print(f"未知错误：{str(e)}")
    finally:
        ssh.close()


# ===================== 使用示例 =====================
if __name__ == "__main__":
    change_ccadmin_password_with_key(
        host="10.1.1.29",  # 你的服务器IP
        port=22,  # SSH端口
        username="ccadmin",  # 密钥登录的用户名
        private_key_path="C:\\Users\\23325\\Desktop\\TEST\\圣洁云创\\平台技术资料\\软件脚本工具\\服务器私钥\\private-key", # 本地私钥路径
        new_ccadmin_password="Cestc@2026!"  # 新ccadmin密码
    )