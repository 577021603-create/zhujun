import requests
import re
import socket
import time
import concurrent.futures
from urllib.parse import urljoin


class NginxDetection:
    def __init__(self, target_url, timeout=5, print_headers=False):
        self.target_url = target_url
        self.timeout = timeout
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.nginx_version = None
        self.print_headers = print_headers  # 新增：是否打印响应头

    def detect_nginx(self):
        """检测目标是否运行Nginx服务器"""
        try:
            response = requests.get(self.target_url, headers=self.headers, timeout=self.timeout)

            # 新增：打印响应头
            if self.print_headers:
                self._print_response_headers(response)

            # 检查响应头中的Server字段
            server_header = response.headers.get('Server', '')
            if 'nginx' in server_header.lower():
                self.nginx_version = self._extract_version(server_header)
                print(f"检测到Nginx服务器，版本: {self.nginx_version or '未知'}")
                return True

            # 检查特定的Nginx错误页面
            error_response = requests.get(urljoin(self.target_url, '/nonexistentpage'), timeout=self.timeout)
            if 'nginx' in error_response.text.lower():
                print("检测到Nginx服务器(通过错误页面识别)")
                return True

            return False
        except Exception as e:
            print(f"检测Nginx服务器时出错: {e}")
            return False

    def _extract_version(self, server_header):
        """从Server头中提取Nginx版本号"""
        match = re.search(r'nginx/([\d.]+)', server_header)
        if match:
            return match.group(1)
        return None

    # 新增：打印响应头的方法
    def _print_response_headers(self, response):
        """打印HTTP响应头"""
        print("\n响应头信息:")
        for header, value in response.headers.items():
            print(f"{header}: {value}")
        print()

    def check_version_information_disclosure(self):
        """检查Nginx版本信息泄露"""
        if self.nginx_version:
            return f"警告: Nginx版本信息通过Server头泄露 ({self.nginx_version})"
        return None

    def check_secure_headers(self):
        """检查安全相关HTTP头是否缺失"""
        missing_headers = []

        try:
            response = requests.get(self.target_url, headers=self.headers, timeout=self.timeout)

            required_headers = {
                'X-Frame-Options': '防止点击劫持',
                'X-Content-Type-Options': '防止MIME类型嗅探',
                'Content-Security-Policy': '防止XSS攻击',
                'Strict-Transport-Security': '强制HTTPS连接'
            }

            for header, description in required_headers.items():
                if header not in response.headers:
                    missing_headers.append(f"{header} ({description})")

            if missing_headers:
                return f"缺失安全头: {', '.join(missing_headers)}"
            return None
        except Exception as e:
            print(f"检查安全头时出错: {e}")
            return None

    def check_nginx_status_page(self):
        """检查Nginx状态页面是否暴露"""
        status_endpoints = ['/nginx_status', '/status']

        for endpoint in status_endpoints:
            try:
                url = urljoin(self.target_url, endpoint)
                response = requests.get(url, headers=self.headers, timeout=self.timeout)

                # 新增：打印状态页面的响应头
                if self.print_headers:
                    print(f"\n{url} 的响应头信息:")
                    for header, value in response.headers.items():
                        print(f"{header}: {value}")
                    print()

                if response.status_code == 200:
                    # 检查典型的Nginx状态页面内容
                    if 'Active connections' in response.text or 'server accepts handled requests' in response.text:
                        return f"警告: Nginx状态页面暴露 - {url}"
            except Exception as e:
                print(f"检查状态页面 {endpoint} 时出错: {e}")
        return None

    def check_buffer_overflow_cve_2017_7529(self):
        """检查CVE-2017-7529缓冲区溢出漏洞 (Nginx 0.5.6 - 1.13.2)"""
        if not self.nginx_version:
            return None

        try:
            # 解析版本号
            major, minor, patch = map(int, self.nginx_version.split('.')[:3])

            # 检查受影响的版本范围
            if (major == 0 and minor >= 5 and minor <= 99) or \
                    (major == 1 and minor == 0) or \
                    (major == 1 and minor == 1 and patch <= 10) or \
                    (major == 1 and minor >= 2 and minor <= 12) or \
                    (major == 1 and minor == 13 and patch <= 2):
                return f"警告: 可能存在CVE-2017-7529缓冲区溢出漏洞 (受影响版本: {self.nginx_version})"
            return None
        except (ValueError, IndexError):
            print(f"无法解析Nginx版本号: {self.nginx_version}")
            return None

    def check_http_splitting_cve_2019_9511(self):
        """检查CVE-2019-9511 HTTP请求拆分漏洞 (Nginx < 1.15.9)"""
        if not self.nginx_version:
            return None

        try:
            major, minor, patch = map(int, self.nginx_version.split('.')[:3])

            # 检查受影响的版本范围
            if major < 1 or (major == 1 and minor < 15) or (major == 1 and minor == 15 and patch < 9):
                return f"警告: 可能存在CVE-2019-9511 HTTP请求拆分漏洞 (受影响版本: {self.nginx_version})"
            return None
        except (ValueError, IndexError):
            print(f"无法解析Nginx版本号: {self.nginx_version}")
            return None

    def check_ssrf_cve_2019_20372(self):
        """检查CVE-2019-20372 SSRF漏洞 (Nginx < 1.17.8)"""
        if not self.nginx_version:
            return None

        try:
            major, minor, patch = map(int, self.nginx_version.split('.')[:3])

            # 检查受影响的版本范围
            if major < 1 or (major == 1 and minor < 17) or (major == 1 and minor == 17 and patch < 8):
                return f"警告: 可能存在CVE-2019-20372 SSRF漏洞 (受影响版本: {self.nginx_version})"
            return None
        except (ValueError, IndexError):
            print(f"无法解析Nginx版本号: {self.nginx_version}")
            return None

    def check_underscore_in_uri(self):
        """检查Nginx对包含下划线的URI的处理问题"""
        try:
            # 检查包含下划线的URI是否被正确处理
            test_url = urljoin(self.target_url, '/test_underscore')
            response = requests.get(test_url, headers=self.headers, timeout=self.timeout)

            # 新增：打印测试URL的响应头
            if self.print_headers:
                print(f"\n{test_url} 的响应头信息:")
                for header, value in response.headers.items():
                    print(f"{header}: {value}")
                print()

            # 如果返回404，可能存在配置问题
            if response.status_code == 404:
                # 检查正常URI是否返回不同结果
                normal_url = urljoin(self.target_url, '/testunderscore')
                normal_response = requests.get(normal_url, headers=self.headers, timeout=self.timeout)

                if normal_response.status_code != 404:
                    return "警告: Nginx可能配置为忽略包含下划线的URI"
            return None
        except Exception as e:
            print(f"检查下划线URI处理时出错: {e}")
            return None

    def scan(self):
        """执行完整的Nginx扫描"""
        print(f"开始扫描Nginx服务器: {self.target_url}")
        start_time = time.time()
        results = []

        # 首先检测是否为Nginx服务器
        if not self.detect_nginx():
            print("未检测到Nginx服务器，扫描终止")
            return []

        # 定义要执行的检查函数
        checks = [
            self.check_version_information_disclosure,
            self.check_secure_headers,
            self.check_nginx_status_page,
            self.check_buffer_overflow_cve_2017_7529,
            self.check_http_splitting_cve_2019_9511,
            self.check_ssrf_cve_2019_20372,
            self.check_underscore_in_uri
        ]

        # 执行所有检查
        for check in checks:
            result = check()
            if result:
                results.append(result)

        elapsed_time = time.time() - start_time
        print(f"扫描完成，耗时 {elapsed_time:.2f} 秒")

        if results:
            print("\n发现以下潜在问题:")
            for i, result in enumerate(results, 1):
                print(f"{i}. {result}")
        else:
            print("\n未发现明显问题")

        return results


# 使用示例
if __name__ == "__main__":
    target = "http://10.1.26.249"  # 替换为实际目标URL
    print_headers = True  # 设置为True以打印请求头

    scanner = NginxDetection(target, print_headers=print_headers)
    scanner.scan()