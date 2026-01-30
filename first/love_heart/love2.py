import os
import subprocess
import sys

def open_borderless_browser(html_filename):
    """
    用无边框模式打开浏览器，加载本地HTML文件
    :param html_filename: 本地HTML文件名（如love.html）
    """
    # 1. 获取本地HTML文件的绝对URL路径
    html_path = os.path.abspath(html_filename)
    if not os.path.exists(html_path):
        print(f"❌ 错误：未找到文件 {html_filename}，请确认文件在当前目录！")
        return
    # 转换为浏览器可识别的file:// URL
    html_url = f"file:///{html_path.replace(os.sep, '/')}"

    # 2. 定义浏览器路径（优先Chrome，其次Edge）
    browser_paths = []
    if sys.platform == "win32":  # Windows系统
        # Chrome常见路径
        chrome_paths = [
            os.path.join(os.environ.get("PROGRAMFILES", ""), "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Google", "Chrome", "Application", "chrome.exe")
        ]
        # Edge常见路径
        edge_path = os.path.join(os.environ.get("PROGRAMFILES", ""), "Microsoft", "Edge", "Application", "msedge.exe")
        browser_paths = chrome_paths + [edge_path]
    elif sys.platform == "darwin":  # MacOS系统
        browser_paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"
        ]
    else:  # Linux系统
        browser_paths = ["google-chrome", "chromium", "microsoft-edge"]

    # 3. 查找可用的浏览器
    browser_exe = None
    for path in browser_paths:
        if os.path.exists(path) or (sys.platform != "win32" and subprocess.call(["which", path], stdout=subprocess.PIPE) == 0):
            browser_exe = path
            break
    if not browser_exe:
        print("❌ 错误：未找到Chrome/Edge浏览器，请先安装！")
        return

    # 4. 构造浏览器启动参数（核心：无边框模式）
    # --app=URL：应用模式（无边框、无地址栏、无菜单）
    # --kiosk=URL：自助服务终端模式（全屏无边框，按ESC退出）
    # 优先用--app模式（非全屏，更灵活）
    args = [
        browser_exe,
        "--app=" + html_url,  # 应用模式（无边框核心参数）
        "--window-size=1000,700",  # 窗口大小（宽,高）
        "--window-position=100,100",  # 窗口位置（x,y）
        "--no-first-run",  # 跳过首次运行提示
        "--no-default-browser-check"  # 跳过默认浏览器检查
    ]

    # 5. 启动无边框浏览器
    try:
        print(f"✅ 正在用无边框模式打开 {html_filename}...")
        print(f"浏览器路径：{browser_exe}")
        print(f"加载的文件：{html_url}")
        # 启动浏览器（不阻塞Python进程）
        subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as e:
        print(f"❌ 启动浏览器失败：{e}")

# 运行：打开无边框浏览器加载love.html
if __name__ == "__main__":
    open_borderless_browser("love.html")