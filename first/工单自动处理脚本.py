from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
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
        # 登录按钮
        login_btn = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="kc-login"]')))
        time.sleep(5)
        print("等待登录页面加载完成")
        login_btn.click()
        print("已点击登录，等待输入谷歌验证码，等待页面加载完成")
        time.sleep(15)

        # =========元素命名========
        # 第一个元素：工单查询
        work_order_query = wait.until(EC.element_to_be_clickable((By.XPATH, '/html/body/app-root/default/div[1]/nav/div/ul/li[8]')))
        print("尝试点击【工单查询】")
        work_order_query.click()
        print("✅已点击【工单查询】")
        time.sleep(5) #动作后等待5秒

        # 第二个元素：我的待处理
        my_pending = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="Watermark"]/div[2]/app-tab/div/app-workorder/div/div[1]/div[2]/div[1]')))
        print("准备点击【我的待处理】")
        my_pending.click()
        print("✅已点击【我的待处理】")
        time.sleep(5) #动作后等待5秒

        # 第三个元素：我的处理中
        my_processing = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="Watermark"]/div[2]/app-tab/div/app-workorder/div/div[1]/div[2]/div[2]')))
        print("准备点击【我的处理中】")
        my_processing.click()
        print("✅已点击【我的处理中】")
        time.sleep(5) #动作后等待5秒

        print("====开始遍历表格判断工单====")
        # 表单容器
        table_container_xpath = '//*[@id="Watermark"]/div[2]/app-tab/div/app-workorder/div/div[2]/div[2]'
        # 等待表格容器
        table_container = WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.XPATH, table_container_xpath))
        )
        # 在容器内部查找所有tbody行
        all_tr = table_container.find_elements(By.XPATH, './/tbody/tr')
        print(f"表格一共检测到 {len(all_tr)} 条工单行")

        hit = False
        # 循环遍历每一行
        for idx, tr in enumerate(all_tr):
            try:
                # 当前行内：级别标签
                level_elem = tr.find_element(By.XPATH, './/td[6]/div/app-workorder-status-label')
                level_text = level_elem.text.strip()
                # 当前行内：工单处理按钮
                deal_btn = tr.find_element(By.XPATH, './/td[30]/div/button[1]')
                print(f"第{idx+1}行｜级别文本：【{level_text}】")

                # 判断是否M2/M3
                if "M2" in level_text or "M3" in level_text:
                    print(f"✅第{idx+1}行匹配M2/M3，点击该行工单处理按钮")
                    deal_btn.click()
                    time.sleep(5) #点击工单处理按钮后等待5秒
                    hit = True
                    break
            except NoSuchElementException:
                # 当前行缺少按钮/级别标签，跳过该行
                print(f"ℹ第{idx+1}行：没有处理按钮或者级别标签，跳过")
                continue

        if not hit:
            print("❌全部工单没有M2/M3级别，点击【工单查询】")
            work_order_query.click()
            time.sleep(5) #点击工单查询后等待5秒

        print("业务逻辑执行结束")

    except Exception as e:
        print(f"程序异常：{e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
