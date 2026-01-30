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
from bs4 import BeautifulSoup

# ==================== 配置区 ====================
# 公共配置
DRIVER_PATH = "D:\\python project\\chromedriver-win64\\chromedriver-win64\\chromedriver.exe"
CAPTCHA_SAVE_PATH = "D:\\check\\png\\captCHA.png"
WAIT_TIMEOUT = 20

# 原有系统配置
LOGIN_URL = "https://ops.gz-cloud.cn/login"
TARGET_URL = "https://ops.gz-cloud.cn/console/om/capacity/service?regionId=-1"
VCPU_TEXT_XPATH = "//p[@class='list_hover' and text()='vCPU']"
VCPU_POPUP_TABLE_XPATH = "//div[contains(@class, 'arco-modal-content')]//div[contains(@class, 'arco-table-scroll-position-left')]//table"
MEMORY_TEXT_XPATH = "//p[@class='list_hover' and text()='内存']"
MEMORY_POPUP_TABLE_XPATH = "//div[contains(@class, 'arco-modal-content')]//div[contains(@class, 'arco-table-scroll-scroll-position-left')]//table"

# 政务网块存储配置（新增SSD）
STORAGE_URL = "http://10.0.21.37:8056/dashboard/clusters/1/pools"
STORAGE_USERNAME = "admin"
STORAGE_PASSWORD = "Cestc@1234!@"
HDD_USAGE_XPATH = "//div[@class='UsageBar__footer']//div[@class='UsageBar__footer--right' and contains(text(),'/ 81.24 TB')]"  # HDD定位
SSD_USAGE_XPATH = "//div[@class='UsageBar__footer']//div[@class='UsageBar__footer--right' and contains(text(),'/ 118.5 TB')]"  # 新增SSD定位

# 登录相关XPath
CAPTCHA_IMG_XPATH = "//div[@class='captcha-wrap el-col el-col-6']/img[@id='captchaRef']"
USERNAME_XPATH = "//div[contains(@class, 'login-form-item') and contains(@class, 'el-input')]//input[@name='username']"
PASSWORD_XPATH = "//div[contains(@class, 'login-form-item') and contains(@class, 'el-input')]//input[@name='password']"
CAPTCHA_INPUT_XPATH = "//div[@class='el-input']/input[@name='captcha']"
LOGIN_BUTTON_XPATH = "//button[@type='button']"
REFRESH_CAPTCHA_XPATH = "//div[@class='captcha-refresh']"
LOGIN_SUCCESS_XPATH = "//div[@class='arco-menu-item arco-menu-selected menu' and @tabindex='0' and @role='menuitem']"


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

        captcha_elem = WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.XPATH, CAPTCHA_IMG_XPATH))
        )

        src = captcha_elem.get_attribute("src")
        print(f"验证码图片地址: {src[:50]}...")

        if src.startswith("data:image"):
            base64_data = src.split(",")[1]
            with open(CAPTCHA_SAVE_PATH, "wb") as f:
                f.write(base64.b64decode(base64_data))
        else:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            response = requests.get(src, headers=headers, timeout=10, verify=False)
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


def login_original_system(driver: webdriver.Chrome, username: str, password: str) -> bool:
    """登录原有系统"""
    try:
        driver.get(LOGIN_URL)
        driver.maximize_window()
        print(f"已打开原有系统登录页面: {LOGIN_URL}")
        time.sleep(2)

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

        captcha_code = recognize_captcha()
        if not captcha_code:
            print("验证码识别失败，登录终止")
            return False
        print(f"识别到验证码: {captcha_code}")

        WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, USERNAME_XPATH))
        ).send_keys(username)

        WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, PASSWORD_XPATH))
        ).send_keys(password)

        WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, CAPTCHA_INPUT_XPATH))
        ).send_keys(captcha_code)

        WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, LOGIN_BUTTON_XPATH))
        ).click()
        print("已提交登录请求")
        time.sleep(3)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, LOGIN_SUCCESS_XPATH))
        )
        print("原有系统登录成功")
        return True
    except TimeoutException:
        print("登录超时或登录失败")
        return False
    except Exception as e:
        print(f"登录过程出错: {str(e)}")
        return False


def login_storage_system(driver: webdriver.Chrome) -> bool:
    """登录政务网块存储系统"""
    try:
        driver.get(STORAGE_URL)
        print(f"已打开政务网块存储系统页面: {STORAGE_URL}")
        time.sleep(2)

        # 尝试定位并填写用户名密码（根据实际登录页调整XPath）
        try:
            # 用户名输入框（尝试多种定位方式）
            username_input = WebDriverWait(driver, WAIT_TIMEOUT).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//input[@name='name' and @placeholder='请输入用户名或邮箱地址']"))
            )
            username_input.clear()
            username_input.send_keys(STORAGE_USERNAME)

            # 密码输入框（尝试多种定位方式）
            password_input = WebDriverWait(driver, WAIT_TIMEOUT).until(
                EC.element_to_be_clickable((By.XPATH, "//input[contains(@name, 'password')]"))
            )
            password_input.clear()
            password_input.send_keys(STORAGE_PASSWORD)

            # 登录按钮（尝试多种定位方式）
            login_btn = WebDriverWait(driver, WAIT_TIMEOUT).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@class='btn btn-primary btn-block' and text()='登录']"))
            )
            login_btn.click()
            print("政务网块存储系统登录请求已提交")
            time.sleep(3)

            # 验证登录成功（根据实际页面调整）
            #            WebDriverWait(driver, WAIT_TIMEOUT).until(
            #                EC.presence_of_element_located(
            #                   (By.XPATH, "//*[contains(text(), '存储统计') or contains(text(), 'Dashboard')]"))
            #           )
            print("政务网块存储系统登录成功")
            return True
        except Exception as e:
            print(f"登录表单元素定位失败: {str(e)}")
            # 截图保存当前页面以便调试
            driver.save_screenshot("storage_login_page.png")
            print("已保存登录页面截图: storage_login_page.png")
            return False
    except Exception as e:
        print(f"政务网块存储系统登录失败: {str(e)}")
        return False


def navigate_to_target(driver: webdriver.Chrome) -> bool:
    """跳转至原有系统目标页面"""
    try:
        driver.get(TARGET_URL)
        print(f"已跳转至目标页面: {TARGET_URL}")

        WebDriverWait(driver, WAIT_TIMEOUT).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        time.sleep(3)
        print("目标页面加载完成")
        return True
    except TimeoutException:
        print(f"目标页面加载超时（{WAIT_TIMEOUT}秒）")
        return False
    except Exception as e:
        print(f"跳转目标页面失败: {str(e)}")
        return False


def click_element(driver: webdriver.Chrome, xpath: str, desc: str) -> bool:
    """通用点击函数"""
    try:
        elem = WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )

        driver.execute_script("arguments[0].scrollIntoView();", elem)
        time.sleep(1)

        elem.click()
        print(f"成功点击【{desc}】，弹出数据框")
        return True
    except TimeoutException:
        print(f"超时错误：{WAIT_TIMEOUT}秒内未找到可点击的【{desc}】元素")
        return False
    except ElementClickInterceptedException:
        print(f"【{desc}】元素被遮挡，尝试通过JS点击")
        try:
            elem = driver.find_element(By.XPATH, xpath)
            driver.execute_script("arguments[0].click();", elem)
            return True
        except Exception as e:
            print(f"JS点击【{desc}】失败: {str(e)}")
            return False
    except Exception as e:
        print(f"点击【{desc}】失败: {str(e)}")
        return False


def extract_table(driver: webdriver.Chrome, table_xpath: str, desc: str) -> pd.DataFrame:
    """通用表格提取函数"""
    try:
        table_elem = WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.XPATH, table_xpath))
        )

        soup = BeautifulSoup(table_elem.get_attribute('outerHTML'), 'html.parser')
        rows = soup.find_all('tr')

        headers = [th.text.strip() for th in rows[0].find_all(['th', 'td'])]
        if not headers:
            raise ValueError(f"【{desc}】表格表头为空")

        data = []
        for row in rows[1:]:
            cells = [td.text.strip() for td in row.find_all(['th', 'td'])]
            if len(cells) == len(headers):
                data.append(cells)
            else:
                print(f"警告：【{desc}】行数据长度与表头不匹配，跳过该行：{cells}")

        df = pd.DataFrame(data, columns=headers)

        required_columns = ["区域名称", "可用区名称", "集群名称"]
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            print(f"警告：【{desc}】表格缺失关键列 {missing_cols}")

        print(f"【{desc}】表格数据提取完成：")
        print(df)
        return df
    except TimeoutException:
        print(f"超时错误：{WAIT_TIMEOUT}秒内未找到【{desc}】弹出框表格")
        return pd.DataFrame()
    except Exception as e:
        print(f"提取【{desc}】表格数据失败: {str(e)}")
        return pd.DataFrame()


def extract_storage_usage(driver: webdriver.Chrome, xpath: str, storage_type: str) -> str:
    """通用存储使用情况提取函数（同时支持HDD和SSD）"""
    try:
        # 使用指定XPath定位元素（不刷新浏览器）
        storage_elem = WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )

        # 提取文本值并清理
        usage_text = storage_elem.text.strip()
        print(f"成功提取{storage_type}使用情况文本: {usage_text}")

        # 解析使用量和总量
        if '/' in usage_text:
            used, total = [item.strip() for item in usage_text.split('/')]
            print(f"解析结果 - {storage_type}已使用: {used}, 总量: {total}")

        return usage_text
    except TimeoutException:
        print(f"超时错误：{WAIT_TIMEOUT}秒内未找到{storage_type}元素（XPath: {xpath}）")
        driver.save_screenshot(f"{storage_type.lower()}_element_not_found.png")
        print(f"已保存{storage_type}元素定位失败截图: {storage_type.lower()}_element_not_found.png")
        return ""
    except Exception as e:
        print(f"提取{storage_type}使用情况失败: {str(e)}")
        return ""


def main():
    # 初始化浏览器（全程复用一个实例，不刷新）
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--ignore-certificate-errors")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])

    driver = None
    try:
        driver = webdriver.Chrome(
            service=Service(executable_path=DRIVER_PATH),
            options=options
        )

        # 1. 处理原有系统数据
        print("\n===== 开始处理原有系统数据 =====")
        if login_original_system(driver, "朱军", "Zscvh456873691#"):
            if navigate_to_target(driver):
                # 提取vCPU数据
                if click_element(driver, VCPU_TEXT_XPATH, "vCPU"):
                    vcpu_df = extract_table(driver, VCPU_POPUP_TABLE_XPATH, "vCPU")
                    if not vcpu_df.empty:
                        vcpu_df.to_csv("vcpu_data.csv", index=False)
                        print("vCPU数据已保存至vcpu_data.csv")

                # 提取内存数据
                if click_element(driver, MEMORY_TEXT_XPATH, "内存"):
                    memory_df = extract_table(driver, MEMORY_POPUP_TABLE_XPATH, "内存")
                    if not memory_df.empty:
                        memory_df.to_csv("memory_data.csv", index=False)
                        print("内存数据已保存至memory_data.csv")

        # 2. 处理政务网块存储数据（共享浏览器实例）
        print("\n===== 开始处理政务网块存储数据 =====")
        if login_storage_system(driver):
            # 提取HDD数据
            hdd_usage = extract_storage_usage(driver, HDD_USAGE_XPATH, "HDD")
            if hdd_usage:
                with open("hdd_usage.txt", "w", encoding="utf-8") as f:
                    f.write(hdd_usage)
                print("HDD使用情况已保存至hdd_usage.txt")

            # 提取SSD数据（不刷新浏览器，直接使用新XPath定位）
            ssd_usage = extract_storage_usage(driver, SSD_USAGE_XPATH, "SSD")
            if ssd_usage:
                with open("ssd_usage.txt", "w", encoding="utf-8") as f:
                    f.write(ssd_usage)
                print("SSD使用情况已保存至ssd_usage.txt")

        # 操作完成后停留
        print("\n所有操作完成，将停留60秒后关闭浏览器")
        time.sleep(60)

    except Exception as e:
        print(f"主流程出错: {str(e)}")
        if driver:
            error_screenshot = os.path.join(os.path.dirname(CAPTCHA_SAVE_PATH), "error.png")
            driver.save_screenshot(error_screenshot)
            print(f"错误截图已保存至: {error_screenshot}")
    finally:
        if driver:
            driver.quit()
            print("浏览器已关闭")


if __name__ == "__main__":
    main()
