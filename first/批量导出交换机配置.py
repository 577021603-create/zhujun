import paramiko
import time
from datetime import datetime
import os
import re


class SwitchConfigExporter:
    def __init__(self, host, username, password, port=22, timeout=30, vendor='cisco'):
        """初始化交换机连接参数"""
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.timeout = timeout
        self.vendor = vendor
        self.ssh = None
        self.channel = None

    def connect(self):
        """建立SSH连接"""
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(
                self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=self.timeout
            )
            self.channel = self.ssh.invoke_shell()
            self.channel.resize_pty(width=1000, height=1000)
            time.sleep(1)
            self._read_output()
            return True
        except Exception as e:
            print(f"连接交换机 {self.host} 失败: {str(e)}")
            return False

    def _read_output(self, timeout=1.0):
        """读取通道输出，带超时处理"""
        output = b''
        start_time = time.time()
        while time.time() - start_time < timeout or self.channel.recv_ready():
            if self.channel.recv_ready():
                output += self.channel.recv(65535)
                start_time = time.time()
            else:
                time.sleep(0.1)
        return output.decode('utf-8', errors='ignore')

    def send_command(self, command, delay=1, expect_paging=True):
        """发送命令到交换机并处理分页返回结果"""
        try:
            self.channel.send(command + '\n')
            time.sleep(delay)

            output = ""

            while True:
                page_output = self._read_output()
                output += page_output

                if expect_paging and (
                        "---- More ----" in page_output or
                        "--More--" in page_output or
                        "按空格键继续" in page_output
                ):
                    self.channel.send(' ')
                    time.sleep(0.5)
                else:
                    break

            output = output.replace(command, '', 1).strip()
            output = re.sub(r'---- More ----\s*', '', output)
            output = re.sub(r'--More--\s*', '', output)
            output = re.sub(r'按空格键继续.*?\s*', '', output)

            return output
        except Exception as e:
            print(f"发送命令失败: {str(e)}")
            return None

    def get_config(self):
        """获取交换机配置，处理分页情况"""
        if not self.channel:
            print("未建立连接，请先调用connect()方法")
            return None

#       if self.vendor in ['huawei', 'hc']:
#            self.send_command('system-view', delay=1, expect_paging=False)

        config = self.send_command('dis cu', delay=2, expect_paging=True)
        return config

    def clean_config(self, config):
        """清理配置内容，移除多余的空白行"""
        if not config:
            return ""

        # 按行分割配置
        lines = config.split('\n')

        # 处理每行，移除首尾空白并过滤空行
        cleaned_lines = []
        for line in lines:
            stripped_line = line.strip()
            # 只保留非空行
            if stripped_line:
                cleaned_lines.append(stripped_line)

        # 用单个换行符连接所有行
        return '\n'.join(cleaned_lines)

    def save_config_to_file(self, config, directory='switch_configs'):
        """将配置保存到文件，保存前先清理多余空白行"""
        if not config:
            print("没有配置内容可保存")
            return False

        try:
            # 清理配置内容
            cleaned_config = self.clean_config(config)

            if not os.path.exists(directory):
                os.makedirs(directory)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.host}_{timestamp}.txt"
            filepath = os.path.join(directory, filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(cleaned_config)

            print(f"配置已成功保存到: {filepath}")
            return True
        except Exception as e:
            print(f"保存配置失败: {str(e)}")
            return False

    def disconnect(self):
        """断开SSH连接"""
        if self.ssh:
            self.ssh.close()
            print(f"已断开与 {self.host} 的连接")

    def export_config(self):
        """一键导出配置主方法"""
        if not self.connect():
            return False

        try:
            config = self.get_config()
            if config:
                return self.save_config_to_file(config)
            return False
        finally:
            self.disconnect()

def load_switch_list(filename):
    """从TXT文件加载交换机列表，每行格式：用户名 IP地址 端口号 厂商 密码"""
    switches = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                parts = line.split()

                if len(parts) < 5:
                    print(f"警告: 第 {line_num} 行格式不正确，需要至少5个字段")
                    continue

                try:
                    switch_info = {
                        'user': parts[0],
                        'ip': parts[1],
                        'port': int(parts[2]),
                        'vendor': parts[3].lower(),
                        'password': parts[4]
                    }
                    switches.append(switch_info)
                except ValueError:
                    print(f"警告: 第 {line_num} 行端口号必须是数字")
                    continue

        return switches if switches else None
    except FileNotFoundError:
        print(f"错误: 文件 {filename} 未找到")
        return None
    except Exception as e:
        print(f"加载交换机列表时出错: {str(e)}")
        return None


def main():
    print("===== 批量交换机配置导出工具 =====")
    print("TXT文件格式：用户名 IP地址 端口号 厂商 密码")

    txt_file =  "switches.txt"

    switches = load_switch_list(txt_file)
    if not switches:
        print("没有有效的交换机信息可处理")
        return


    for i, switch in enumerate(switches, 1):
        print(f"\n===== 处理第 {i}/{len(switches)} 台交换机: {switch.get('ip')} =====")

        host = switch.get('ip')
        username = switch.get('user')
        port = switch.get('port')
        vendor = switch.get('vendor')
        password = switch.get('password')

        print(f"用户名: {username}, IP: {host}, 端口: {port}, 厂商: {vendor}")

        exporter = SwitchConfigExporter(
            host=host,
            username=username,
            password=password,
            port=port,
            vendor=vendor
        )
        exporter.export_config()

    print("\n===== 批量处理完成 =====")


if __name__ == "__main__":
    main()
