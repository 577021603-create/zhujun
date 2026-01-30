from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
import time
import traceback
import os


def auto_login_and_operate():
    # 1. 谷歌浏览器核心配置
    driver_path = r"D:\python project\chromedriver-win64\chromedriver-win64\chromedriver.exe"
    options = webdriver.ChromeOptions()

    # 验证码加载核心配置
    options.add_argument("--disable-features=BlockInsecurePrivateNetworkRequests")
    options.add_argument("--allow-running-insecure-content")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--enable-javascript")
    options.add_argument("--enable-images")
    options.add_experimental_option("prefs", {
        "profile.managed_default_content_settings.images": 1,
        "profile.managed_default_content_settings.javascript": 1,
        "profile.content_settings.exceptions.images.*.setting": 1,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False
    })

    # 基础稳定性配置
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-features=VizDisplayCompositor")

    # 网络/证书兼容配置
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors")
    options.add_argument("--allow-insecure-localhost")
    options.add_argument("--ignore-certificate-errors-spki-list")
    options.add_argument("--disable-web-security")

    # 反爬/特征隐藏配置
    options.add_argument("--incognito")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")

    # 2. 启动浏览器（保留兜底逻辑）
    driver = None
    try:
        service = Service(driver_path)
        service.log_path = os.devnull
        service.creationflags = 0x08000000

        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
        })
        driver.implicitly_wait(15)
        print("✅ 谷歌浏览器启动成功")
    except Exception as e:
        print(f"❌ 浏览器启动失败（指定路径）：{str(e)}")
        # 兜底方案：自动下载匹配版本的ChromeDriver
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
            service.log_path = os.devnull
            driver = webdriver.Chrome(service=service, options=options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            driver.implicitly_wait(15)
            print("✅ 自动适配ChromeDriver版本并启动成功")
        except Exception as e2:
            print(f"❌ 自动适配也失败：{str(e2)}")
            return

    try:
        # 3. 访问目标网站
        login_url = "https://console.gz-cloud.cn/region/gzy-zwww/console/tenant/compute/cbr/backup/ecs?tab=copy&type=list"
        print(f"🔍 正在访问目标网站：{login_url}")

        driver.delete_all_cookies()
        driver.set_page_load_timeout(60)
        driver.get(login_url)

        WebDriverWait(driver, 30).until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )
        time.sleep(5)
        print(f"✅ 网站访问成功，当前URL：{driver.current_url}")

        # 4. 登录操作
        try:
            # 定位并输入用户名
            username_elem = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[@id="ce_app"]/section/main/div/div/div[2]/form/div[1]/div/div[2]/input'))
            )
            username_elem.clear()
            username_elem.send_keys("朱军")
            print("✅ 用户名输入完成")

            # 定位并输入密码
            password_elem = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[@id="ce_app"]/section/main/div/div/div[2]/form/div[2]/div/div/input'))
            )
            password_elem.clear()
            password_elem.send_keys("Zscvh456873691@")
            print("✅ 密码输入完成")

            # 验证码加载检测
            try:
                captcha_elem = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//img[contains(@src, "captcha") or contains(@alt, "验证码")]'))
                )
                print("✅ 验证码图片加载完成")
            except:
                print("ℹ️ 未检测到验证码图片，继续执行登录流程")

            time.sleep(10)

            # 点击登录按钮
            login_btn = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="ce_app"]/section/main/div/div/div[2]/form/button'))
            )
            login_btn.click()
            print("✅ 登录按钮点击完成")
            time.sleep(5)

        except Exception as e:
            print(f"❌ 登录操作失败：{str(e)}")
            driver.quit()
            return

        # 5. 登录状态验证
        print(f"📌 当前页面标题：{driver.title}")
        print(f"📌 当前页面URL：{driver.current_url}")
        cloud_service_exists = False
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="app-content"]/div/div/div/div[2]/div/div[2]'))
            )
            cloud_service_exists = True
        except:
            cloud_service_exists = False

        if "管理平台" in driver.title or "compute/cbr" in driver.current_url or cloud_service_exists:
            print("🎉 登录成功，开始执行后续操作...")

            # ========== 核心操作序列 ==========
            # 步骤1：点击云服务基础入口
            print("🔹 准备点击云服务基础入口")
            try:
                cloud_service_elem = WebDriverWait(driver, 20).until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="app-content"]/div/div/div/div[2]/div/div[2]'))
                )
                cloud_service_elem.click()
                print("✅ 云服务基础入口点击完成")
                time.sleep(3)
            except Exception as e:
                print(f"❌ 云服务基础入口点击失败：{str(e)}")
                driver.quit()
                return

            # 步骤2：点击第2个目标元素 + 切换新窗口（核心修复）
            print("🔹 准备点击第2个元素")
            # 先记录原始窗口句柄
            original_window = driver.current_window_handle
            print(f"🔍 原始窗口句柄：{original_window}")

            # 等待抽屉菜单展开
            try:
                WebDriverWait(driver, 15).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, "div.arco-drawer.product-drawer"))
                )
                print("✅ 第2个元素所在的抽屉菜单已展开")
            except Exception as e:
                print(f"❌ 抽屉菜单未展开：{str(e)}")
                driver.quit()
                return

            # 定位并点击第2个元素
            try:
                elem2_css = "body > div.arco-drawer-wrapper.plugin__topbar-product-drawer-warp > div.arco-drawer.product-drawer.slideLeft-appear-done.slideLeft-enter-done > div > span > div > div > div.serch-drawer > div.product-warp > div:nth-child(2) > ul > li:nth-child(4) > div"
                elem2 = WebDriverWait(driver, 20).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, elem2_css))
                )

                # 点击元素（触发新窗口打开）
                driver.execute_script("arguments[0].click();", elem2)
                print("✅ 第2个元素点击完成，等待新窗口打开...")

                # 核心：等待新窗口出现并切换
                WebDriverWait(driver, 30).until(
                    lambda d: len(d.window_handles) > 1
                )
                # 遍历所有窗口，切换到新窗口
                new_window = None
                for handle in driver.window_handles:
                    if handle != original_window:
                        new_window = handle
                        driver.switch_to.window(new_window)
                        break
                print(f"✅ 切换到新窗口，句柄：{new_window}")
                print(f"✅ 新窗口URL：{driver.current_url}")

                # 验证新窗口是否是目标URL
                target_url_feature = "/compute/cbr/backup/volume"
                if target_url_feature not in driver.current_url:
                    # 等待新窗口加载目标URL
                    WebDriverWait(driver, 20).until(
                        lambda d: target_url_feature in d.current_url
                    )
                print(f"✅ 新窗口已加载目标URL：{driver.current_url}")

            except Exception as e:
                print(f"❌ 第2个元素点击/新窗口切换失败：{str(e)}")
                driver.quit()
                return

            # 等待新窗口页面完全加载
            WebDriverWait(driver, 20).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            time.sleep(8)
            print("✅ 新窗口页面已完全加载")

            # 步骤3：定位并点击第三个元素（使用指定XPATH）
            print("🔹 准备点击第3个元素（指定XPATH）")
            click_success = False

            # 移除原iframe相关逻辑（适配新XPATH）
            try:
                # 你指定的第三个元素XPATH
                target_xpath = '//*[@id="app-content"]/div/div[2]/aside/div/div[2]/div[2]/div/div[2]/div/div[2]'
                target_elem = WebDriverWait(driver, 25).until(
                    EC.element_to_be_clickable((By.XPATH, target_xpath))
                )
                # 滚动+强制可见
                driver.execute_script("""
                    arguments[0].scrollIntoView({block: 'center', inline: 'center', behavior: 'smooth'});
                    arguments[0].style.visibility = 'visible';
                    arguments[0].style.display = 'block';
                """, target_elem)
                time.sleep(2)
                # JS点击
                driver.execute_script("arguments[0].click();", target_elem)
                click_success = True
                print("✅ 第3个元素点击完成")

            except Exception as e:
                print(f"❌ 第3个元素主定位失败：{str(e)}")
                # 兜底：坐标点击
                try:
                    target_elem = driver.find_element(By.XPATH, target_xpath)
                    ActionChains(driver).move_to_element(target_elem).click().perform()
                    click_success = True
                    print("✅ 第3个元素兜底方案生效：坐标点击成功")
                except Exception as e2:
                    print(f"❌ 第3个元素所有方案失败：{str(e2)}")

            time.sleep(10)

            # 步骤4：定位并点击第四个元素（使用指定XPATH）
            print("🔹 准备点击第4个元素（指定XPATH）")
            try:
                # 你指定的第四个元素XPATH（修正笔误xpanth→xpath）
                elem4_xpath = '//*[@id="arco-tabs-2-tab-1"]'
                elem4 = WebDriverWait(driver, 20).until(
                    EC.element_to_be_clickable((By.XPATH, elem4_xpath))
                )
                # JS点击避免交互限制
                driver.execute_script("arguments[0].click();", elem4)
                print("✅ 第4个元素点击完成")
                time.sleep(30)
            except Exception as e:
                print(f"❌ 第4个元素点击失败：{str(e)}")
                try:
                    elem4 = driver.find_element(By.XPATH, elem4_xpath)
                    ActionChains(driver).move_to_element(elem4).click().perform()
                    print("✅ 第4个元素兜底方案生效：坐标点击成功")
                    time.sleep(30)
                except:
                    print("❌ 第4个元素兜底方案也失败")

            # ========== 关键配置：初始化第六元素XPATH基础索引 ==========
            base_div_index = 4  # 第一轮的X值，可根据你的实际场景调整
            # 第六元素固定JS路径（仅第一轮尝试使用）
            elem6_js_selector = "body > div:nth-child(25) > div.arco-modal-wrapper.arco-modal-wrapper-align-center > div > div:nth-child(2) > div.arco-modal-footer > button.arco-btn.arco-btn-primary.arco-btn-size-default.arco-btn-shape-square.arco-btn-loading-fixed-width"

            # ========== 封装第五、第六元素操作函数（优化执行时间+按需跳过JS定位） ==========
            def execute_fifth_sixth(is_first_loop):
                """
                执行第五、第六元素点击操作（优化执行时间）
                is_first_loop: 是否是第一轮循环（True=第一轮，False=第二轮及以后）
                返回操作是否成功
                """
                # 步骤5：点击第5个元素（保留原有CSS定位和逻辑）
                print("🔹 准备点击第5个元素")
                try:
                    elem5_css = "#arco-tabs-2-panel-1 > div > div > div.arco-table.arco-table-size-default.arco-table-hover.arco-table-layout-fixed.arco-table-fixed-column.arco-table-has-fixed-col-left.arco-table-has-fixed-col-right > div > div > div.arco-table-container > div > div > div.arco-table-body > table > tbody > tr:nth-child(1) > td.arco-table-td.arco-table-col-fixed-right.arco-table-col-fixed-right-first > div > span > div > div > div > div:nth-child(3) > span"
                    elem5 = WebDriverWait(driver, 20).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, elem5_css))
                    )
                    elem5.click()
                    print("✅ 第5个元素点击完成")
                    time.sleep(5)  # 优化：仅等待2秒即可执行元素6操作，大幅缩短执行时间
                except Exception as e:
                    print(f"❌ 第5个元素点击失败：{str(e)}")
                    return False

                # 步骤6：点击第6个元素（按需跳过JS定位，优化执行效率）
                print("🔹 准备点击第6个元素")
                # 1. 仅第一轮尝试JS定位，第二轮及以后直接跳过，使用XPATH兜底
                if is_first_loop:
                    try:
                        # 先检测JS元素是否存在
                        check_js_elem = f"return document.querySelector('{elem6_js_selector}');"
                        WebDriverWait(driver, 15).until(
                            lambda d: d.execute_script(check_js_elem) is not None
                        )
                        # 执行JS点击
                        click_js_elem = f"""
                        var elem = document.querySelector('{elem6_js_selector}');
                        if(elem) {{
                            elem.dispatchEvent(new MouseEvent('click', {{bubbles: true, cancelable: true}}));
                            return true;
                        }}
                        return false;
                        """
                        js_click_success = driver.execute_script(click_js_elem)
                        if js_click_success:
                            print("✅ 第6个元素（第一轮）JS定位点击完成")
                            time.sleep(5)
                            return True
                    except Exception as e:
                        print(f"ℹ️ 第6个元素（第一轮）JS定位失败，切换XPATH定位：{str(e)}")

                # 2. 第二轮及以后直接进入XPATH定位（跳过JS检测），第一轮JS失败后也进入此处
                try:
                    # 计算当前轮次的div索引：仅递增一次，后续保持不变
                    if is_first_loop:
                        current_div_index = base_div_index
                    else:
                        current_div_index = base_div_index + 1  # 仅递增一次，第二轮及以后固定使用该值
                    # 动态拼接XPATH
                    dynamic_elem6_xpath = f"/html/body/div[{current_div_index}]/div[2]/div/div[2]/div[3]/button[2]"
                    print(f"🔍 生成第六元素XPATH：{dynamic_elem6_xpath}（{'第一轮原始索引' if is_first_loop else '第二轮及以后固定索引'}）")
                    # 等待元素可点击并点击
                    elem6 = WebDriverWait(driver, 15).until(
                        EC.element_to_be_clickable((By.XPATH, dynamic_elem6_xpath))
                    )
                    elem6.click()
                    print("✅ 第6个元素XPATH定位点击完成")
                    time.sleep(5)
                    return True
                except Exception as e:
                    print(f"❌ 第6个元素XPATH定位点击失败：{str(e)}")
                    return False

            # ========== 封装状态检测函数（检测删除中→不可用） ==========
            def check_status_until_unavailable():
                """检测指定元素文本，直到出现“不可用”，返回是否检测成功"""
                status_xpath = '//*[@id="arco-tabs-2-panel-1"]/div/div/div[2]/div/div/div[1]/div/div/div[2]/table/tbody/tr[1]/td[3]/div/span/span/span[2]'
                max_check_times = 100  # 最大检测次数，防止无限循环
                check_count = 0

                while check_count < max_check_times:
                    try:
                        # 等待状态元素加载
                        status_elem = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, status_xpath))
                        )
                        current_text = status_elem.text.strip()
                        print(f"🔍 第{check_count+1}次检测状态：{current_text}")

                        # 判断状态
                        if "不可用" in current_text:
                            print("✅ 检测到状态变为'不可用'，停止等待")
                            return True
                        elif "可用" in current_text:
                            print("✅ 检测到状态变为'可用'，停止等待")
                            return True
                        elif "删除中" in current_text:
                            print("⏳ 检测到'删除中'，等待2秒后再次检测...")
                            time.sleep(2)
                            check_count += 1
                        else:
                            print(f"ℹ️ 当前状态为'{current_text}'，非目标状态，等待10秒后再次检测...")
                            time.sleep(10)
                            check_count += 1
                    except Exception as e:
                        print(f"❌ 状态检测异常：{str(e)}，等待10秒后重试...")
                        time.sleep(10)
                        check_count += 1

                print("❌ 达到最大检测次数，状态仍未变为'不可用'")
                return False

            # ========== 封装主循环逻辑 ==========
            def main_loop():
                """主循环：执行第五、第六元素 + 状态检测，循环指定次数"""
                max_loop_times = 9999  # 最大循环次数，可自定义调整
                current_loop = 0  # 循环计数器（从0开始）

                while current_loop < max_loop_times:
                    print(f"\n========== 开始执行第{current_loop+1}轮操作 ==========")
                    # 判断是否是第一轮循环（current_loop=0 即为第一轮）
                    is_first_loop = (current_loop == 0)
                    # 1. 执行第五、第六元素操作（传入是否第一轮标识）
                    operate_success = execute_fifth_sixth(is_first_loop)
                    if not operate_success:
                        print(f"❌ 第{current_loop+1}轮第五、第六元素操作失败，终止循环")
                        break

                    # 2. 检测状态直到变为“不可用”
                    status_success = check_status_until_unavailable()
                    if not status_success:
                        print(f"❌ 第{current_loop+1}轮状态检测超时，终止循环")
                        break

                    # 3. 轮次完成，准备下一轮
                    current_loop += 1
                    print(f"✅ 第{current_loop}轮操作完成，等待5秒后开始下一轮...\n")
                    time.sleep(5)

                if current_loop >= max_loop_times:
                    print(f"✅ 已完成{max_loop_times}轮操作，达到最大循环次数")

            # 启动主循环
            main_loop()

        else:
            print("❌ 登录验证失败，页面未跳转至目标系统")

    except Exception as e:
        print(f"❌ 核心操作流程异常：{str(e)}")
        print(f"📝 异常详情：{traceback.format_exc()}")
    finally:
        print("\n🎉 操作流程执行完毕，浏览器将保持打开状态...")
        time.sleep(30)
        # driver.quit()


if __name__ == "__main__":
    auto_login_and_operate()