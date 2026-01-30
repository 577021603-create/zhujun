import os
import time
import base64
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (TimeoutException,
                                        ElementClickInterceptedException)
import pandas as pd
from bs4 import BeautifulSoup  # 新增HTML解析库

# ==================== 配置区 ====================
DRIVER_PATH = "D:\\python project\\chromedriver-win64\\chromedriver-win64\\chromedriver.exe"
LOGIN_URL = "https://ops.gz-cloud.cn/login"
CAPTCHA_SAVE_PATH = "D:\\check\\png\\captcha.png"
TARGET_URL = "https://ops.gz-cloud.cn/console/om/capacity/service?regionId=-1"  # 需先跳转的目标页面

# 元素定位XPath
# 登录相关
CAPTCHA_IMG_XPATH = "//div[@class='captcha-wrap el-col el-col-6']/img[@id='captchaRef']"
USERNAME_XPATH = "//div[contains(@class, 'login-form-item') and contains(@class, 'el-input')]//input[@name='username']"
PASSWORD_XPATH = "//div[contains(@class, 'login-form-item') and contains(@class, 'el-input')]//input[@name='password']"
CAPTCHA_INPUT_XPATH = "//div[@class='el-input']/input[@name='captcha']"
LOGIN_BUTTON_XPATH = "//button[@type='button']"
REFRESH_CAPTCHA_XPATH = "//div[@class='captcha-refresh']"
LOGIN_SUCCESS_XPATH = "//div[@class='arco-menu-item arco-menu-selected menu' and @tabindex='0' and @role='menuitem']"

# 目标页面操作相关
VCPU_TEXT_XPATH = "//p[@class='list_hover' and text()='vCPU']"  # vCPU文字定位
POPUP_TABLE_XPATH = "//div[contains(@class, 'arco-modal-content')]//div[contains(@class, 'arco-table-scroll-position-left')]//table"  # 弹出框表格

WAIT_TIMEOUT = 20  # 等待超时时间（秒）


# ==================== 配置区结束 ====================

def recognize_captcha() -> str:
    """调用打码平台识别验证码"""
    try:
        with open(CAPTCHA_SAVE_PATH, 'rb') as f:
            b64_data = base64.b64encode(f.read()).decode()

        response = requests.post(
            "http://api.jfbym.com/api/YmServer/customApi",
            json={
                "token": "d-JSx6o9vsIlN8ydkeR2MQOP7pILwHOULjNQkKLNGOA",
                "type": "10103",
                "image": b64_data
            },
            headers={"Content-Type": "application/json"}
        ).json()

        print("打码平台响应:", response)
        return response.get('data', {}).get('data', '')
    except Exception as e:
        print(f"验证码识别失败: {str(e)}")
        return ""


def download_captcha(driver: webdriver.Chrome) -> bool:
    """下载验证码图片到本地"""
    try:
        os.makedirs(os.path.dirname(CAPTCHA_SAVE_PATH), exist_ok=True)

        # 等待验证码元素加载
        captcha_elem = WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.XPATH, CAPTCHA_IMG_XPATH))
        )

        src = captcha_elem.get_attribute("src")
        print(f"验证码图片地址: {src[:50]}...")

        # 处理Base64格式图片
        if src.startswith("data:image"):
            base64_data = src.split(",")[1]
            with open(CAPTCHA_SAVE_PATH, "wb") as f:
                f.write(base64.b64decode(base64_data))
        # 处理普通URL图片
        else:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            response = requests.get(src, headers=headers, timeout=10)
            with open(CAPTCHA_SAVE_PATH, "wb") as f:
                f.write(response.content)

        print(f"验证码已保存至: {CAPTCHA_SAVE_PATH}")
        return True
    except TimeoutException:
        print(f"超时错误：{WAIT_TIMEOUT}秒内未找到验证码元素")
        return False
    except Exception as e:
        print(f"下载验证码失败: {str(e)}")
        return False


def login(driver: webdriver.Chrome, username: str, password: str) -> bool:
    """执行登录操作并返回登录结果"""
    try:
        driver.get(LOGIN_URL)
        driver.maximize_window()
        print(f"已打开登录页面: {LOGIN_URL}")
        time.sleep(2)  # 等待页面加载

        # 下载验证码
        if not download_captcha(driver):
            print("尝试刷新验证码并重试")
            refresh_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, REFRESH_CAPTCHA_XPATH))
            )
            refresh_btn.click()
            time.sleep(1)
            if not download_captcha(driver):
                print("验证码下载失败，登录终止")
                return False

        # 识别验证码
        captcha_code = recognize_captcha()
        if not captcha_code:
            print("验证码识别失败，登录终止")
            return False
        print(f"识别到验证码: {captcha_code}")

        # 填写用户名
        WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, USERNAME_XPATH))
        ).send_keys(username)

        # 填写密码
        WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, PASSWORD_XPATH))
        ).send_keys(password)

        # 填写验证码
        WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, CAPTCHA_INPUT_XPATH))
        ).send_keys(captcha_code)

        # 点击登录按钮
        WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, LOGIN_BUTTON_XPATH))
        ).click()
        print("已提交登录请求")
        time.sleep(3)

        # 验证登录成功
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, LOGIN_SUCCESS_XPATH))
        )
        print("登录成功")
        return True
    except TimeoutException:
        print("登录超时或登录失败")
        return False
    except Exception as e:
        print(f"登录过程出错: {str(e)}")
        return False


def navigate_to_target(driver: webdriver.Chrome) -> bool:
    """跳转至目标页面并验证加载成功"""
    try:
        driver.get(TARGET_URL)
        print(f"已跳转至目标页面: {TARGET_URL}")

        # 等待页面完全加载（可根据实际页面特征调整）
        WebDriverWait(driver, WAIT_TIMEOUT).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        time.sleep(3)  # 额外等待动态内容加载
        print("目标页面加载完成")
        return True
    except TimeoutException:
        print(f"目标页面加载超时（{WAIT_TIMEOUT}秒）")
        return False
    except Exception as e:
        print(f"跳转目标页面失败: {str(e)}")
        return False


def click_vcpu_element(driver: webdriver.Chrome) -> bool:
    """在目标页面点击vCPU文字元素"""
    try:
        # 等待vCPU元素可点击
        vcpu_elem = WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, VCPU_TEXT_XPATH))
        )

        # 确保元素在可视区域内
        driver.execute_script("arguments[0].scrollIntoView();", vcpu_elem)
        time.sleep(1)

        vcpu_elem.click()
        print("成功点击vCPU文字，弹出数据框")
        return True
    except TimeoutException:
        print(f"超时错误：{WAIT_TIMEOUT}秒内未找到可点击的vCPU元素")
        return False
    except ElementClickInterceptedException:
        print("vCPU元素被遮挡，尝试通过JS点击")
        try:
            vcpu_elem = driver.find_element(By.XPATH, VCPU_TEXT_XPATH)
            driver.execute_script("arguments[0].click();", vcpu_elem)
            return True
        except Exception as e:
            print(f"JS点击vCPU失败: {str(e)}")
            return False
    except Exception as e:
        print(f"点击vCPU失败: {str(e)}")
        return False


def extract_table_with_html(driver: webdriver.Chrome) -> pd.DataFrame:
    """通过解析HTML的tr/td修复格式，精准提取表格数据"""
    try:
        # 等待弹出框表格加载
        table_elem = WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.XPATH, POPUP_TABLE_XPATH))
        )
        print("已找到弹出框表格，开始解析HTML结构")

        # 使用BeautifulSoup解析表格
        soup = BeautifulSoup(table_elem.get_attribute('outerHTML'), 'html.parser')
        rows = soup.find_all('tr')

        # 提取表头（第一行th/td）
        headers = [th.text.strip() for th in rows[0].find_all(['th', 'td'])]
        if not headers:
            raise ValueError("表头为空")

        # 提取数据行（第二行及以后）
        data = []
        for row in rows[1:]:
            cells = [td.text.strip() for td in row.find_all(['th', 'td'])]
            if len(cells) == len(headers):
                data.append(cells)
            else:
                print(f"警告：行数据长度与表头不匹配，跳过该行：{cells}")

        # 构建DataFrame
        df = pd.DataFrame(data, columns=headers)

        # 格式校验示例（可扩展）
        required_columns = ["区域名称", "可用区名称", "集群名称"]
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            print(f"警告：缺失关键列 {missing_cols}")

        print("表格数据提取完成（通过HTML解析修复格式）：")
        print(df)
        return df
    except TimeoutException:
        print(f"超时错误：{WAIT_TIMEOUT}秒内未找到弹出框表格")
        return pd.DataFrame()
    except Exception as e:
        print(f"提取表格数据失败: {str(e)}")
        return pd.DataFrame()


def main():
    # 初始化浏览器
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])

    driver = None
    try:
        driver = webdriver.Chrome(
            service=Service(executable_path=DRIVER_PATH),
            options=options
        )

        # 1. 执行登录
        if not login(driver, "朱军", "Zscvh456873691#"):
            return

        # 2. 跳转至目标页面（关键步骤：确保先跳转）
        if not navigate_to_target(driver):
            return

        # 3. 在目标页面点击vCPU
        if not click_vcpu_element(driver):
            return

        # 4. 提取并校验表格数据（通过HTML解析修复格式）
        table_data = extract_table_with_html(driver)
        if not table_data.empty:
            # 保存结果
            output_path = os.path.join(os.path.dirname(CAPTCHA_SAVE_PATH), "vcpu_data_fixed.csv")
            table_data.to_csv(output_path, index=False)
            print(f"数据已保存至: {output_path}（格式已修复）")

        # 操作完成后停留
        print("所有操作完成，将停留60秒后关闭浏览器")
        time.sleep(60)

    except Exception as e:
        print(f"主流程出错: {str(e)}")
        if driver:
            # 保存错误截图
            error_screenshot = os.path.join(os.path.dirname(CAPTCHA_SAVE_PATH), "error.png")
            driver.save_screenshot(error_screenshot)
            print(f"错误截图已保存至: {error_screenshot}")
    finally:
        if driver:
            driver.quit()
            print("浏览器已关闭")


if __name__ == "__main__":
    main()