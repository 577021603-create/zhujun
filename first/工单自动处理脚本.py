from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# ==========配置区============
URL = "https://css.cloud.inspur.com/platform/dashboard#state=23f2201d-512b-4708-a3af-1b5e6cf0a00f&session_state=c324da4b-ef55-4a39-a020-a1e3c2a0379d&code=eyJhbGciOiJkaXIiLCJlbmMiOiJBMTI4Q0JDLUhTMjU2In0..z5Xd8P0hdLasvHrm7mI1Zg.aY1Sj6Ia3QkJka1WAAxwt7mktKNeOIMU43P923MYd1nKZbU2m2bw40KRfRA-JsREF8xborIUgnNdwrpDmOpfRbnoxXrF-CuHPaG4UpZMdvwN-jwUqtXK6-aJxbR-l78aTTb0eqCOPT9oqv6Cm1viFLius-XDzvO-nvCW8S3vB5NyigKEys_3q_zLmY9rNQlZy8kiQGG4YUwcZ46--1unCnSCfEPW-pibIXhtNZ0ElPpDAyrwq_VmTfxv99HDN59Q4WzL6L9ru6XMrijKQRP8VsmQx2jN9CCCWomBHpmXERWYAZsUrPeCqoX7aaL55kq0ubunEU0L_9sdSGFssoE_5w.tuhAB8palmEoV48Dn8yAwA"
USERNAME = "ccsss-zhujun"
PASSWORD = "Zscvh456873691!"
DRIVER_PATH = r"D:\python project\chromedriver-win64\chromedriver-win64\chromedriver.exe"
# ============================

def main():
    service = Service(executable_path=DRIVER_PATH)
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless=new")  # 需要无头模式取消注释
    driver = webdriver.Chrome(service=service, options=options)
    driver.maximize_window()

    try:
        print(f"正在打开网页：{URL}")
        driver.get(URL)

        wait = WebDriverWait(driver, 20)

        # keycloak账号密码输入框
        username_input = wait.until(EC.element_to_be_clickable((By.NAME, "username")))
        password_input = wait.until(EC.element_to_be_clickable((By.NAME, "password")))

        username_input.clear()
        username_input.send_keys(USERNAME)
        password_input.clear()
        password_input.send_keys(PASSWORD)

        # 登录按钮 xpath //*[@id="kc-login"]
        login_btn = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="kc-login"]')))
        login_btn.click()

        print("已点击登录，等待页面跳转...")
        time.sleep(10)
        print(f"跳转后URL: {driver.current_url}")
        time.sleep(600)
        input("执行完毕，按回车关闭浏览器...")

    except Exception as e:
        print(f"程序异常：{e}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
