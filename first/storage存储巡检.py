import paramiko
import os
from tqdm import tqdm


class storagexunjian():
    def __init__(self, SSH_HOST: str):
        # 1. 写死SSH连接参数（无需手动输入）
        self.SSH_HOST = SSH_HOST  # 远程服务器IP/域名
        self.SSH_USER = "root"  # SSH用户名
        self.SSH_PWD = "Cestc@1234!@"  # SSH密码
        self.SSH_PORT = 22  # SSH端口
        self.SCRIPT_PATH = "/root/CECTC-inspect-1.0.9/CECTC-inspect"  # 远程脚本路径
        self.SCRIPT_USER = "admin"  # 传给脚本的用户名
        self.SCRIPT_PASSWORD = "Cestc@1234!@"
        self.REMOTE_DIR = "/root/CECTC-inspect-1.0.9"
        self.LOCAL_DIR = "C:\\"

        # 确保本地目录存在
        os.makedirs(self.LOCAL_DIR, exist_ok=True)

    def ssh(self):
        ssh_client = paramiko.SSHClient()
        try:
            # 自动接受未知主机密钥
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh_client.connect(
                hostname=self.SSH_HOST,
                port=self.SSH_PORT,
                username=self.SSH_USER,
                password=self.SSH_PWD
            )

            # 定义要执行的多条命令
            commands = f"cd {os.path.dirname(self.SCRIPT_PATH)} && bash {self.SCRIPT_PATH}"
#                "cd /root/CECTC-inspect-1.0.9 && ls -l"



            # 依次执行多条命令
#            for cmd in commands:
#                stdin, stdout, stderr = ssh_client.exec_command(cmd)
#                err_msg = stderr.read().decode("utf-8")
 #               if err_msg:
#                    print("命令错误：", err_msg)

            # 执行脚本并传入参数
#            stdin, stdout, stderr = ssh_client.exec_command(f"bash {self.SCRIPT_PATH}")
            stdin, stdout, stderr = ssh_client.exec_command(commands)
            stdin.write(f"{self.SCRIPT_USER}\n")
            stdin.write(f"{self.SCRIPT_PASSWORD}\n")
            stdin.flush()

            # 打印脚本执行结果
            print("脚本输出：", stdout.read().decode("utf-8"))
            script_err = stderr.read().decode("utf-8")
            if script_err:
                print("脚本错误：", script_err)

            # 查找最新的docx文件
            stdin, stdout, stderr = ssh_client.exec_command(
                f"ls -lt {self.REMOTE_DIR}/*.docx 2>/dev/null | grep -v '^total' | head -n 1"
            )
            latest_file_info = stdout.read().decode("utf-8").strip()
            err_msg = stderr.read().decode("utf-8")

            if err_msg:
                print("查找文件错误：", err_msg)
                return

            if not latest_file_info:
                print("未找到任何.docx文件")
                return

            # 提取文件名
            latest_filename = latest_file_info.split()[-1]
            if '/' in latest_filename:
                latest_filename = latest_filename.split('/')[-1]

            remote_file_path = f"{self.REMOTE_DIR}/{latest_filename}"
            local_file_path = os.path.join(self.LOCAL_DIR, latest_filename)

            # 下载文件
            sftp = ssh_client.open_sftp()
            sftp.get(remote_file_path, local_file_path)
            print("docx文件下载完成")
            sftp.close()

        except Exception as e:
            print(f"操作失败：{str(e)}")
        finally:
            ssh_client.close()


def main():
    servers = {
        "hlw_oss": "10.0.21.37",
        "hlw_ebs": "10.0.22.45",
        "zww_oss": "10.1.22.41",
        "zww_ebs": "10.1.21.1"
    }

    # 设置动画进度条，使用动态填充字符
    with tqdm(total=len(servers),
              desc="服务器巡检中",
              unit="台",
              bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
              ascii=" =",  # 动画填充字符
              miniters=1,
              dynamic_ncols=True) as pbar:
        for i, (name, ip) in enumerate(servers.items(), 1):
            # 显示当前正在处理的服务器，增加动画感
            pbar.set_postfix_str(f"正在处理: {name} 🔍", refresh=True)
            print(f"\n===== 开始处理第 {i}/{len(servers)} 台: {name} ({ip}) =====")

            # 执行巡检
            inspector = storagexunjian(ip)
            inspector.ssh()

            # 更新进度，触发动画效果
            pbar.update(1)

        # 完成后显示成功图标
        pbar.set_postfix_str("所有服务器处理完成 ✅")


if __name__ == "__main__":
    main()
