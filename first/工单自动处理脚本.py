from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.common.keys import Keys
import time
import random
from datetime import datetime, timedelta

# ==========配置区============
URL = "https://css.cloud.inspur.com/platform/dashboard#state=23f2201d-512b-4708-a3af-1b5e6cf0a00f&session_state=c324da4b-ef55-4a39-a020-a1e3c2a0379d&code=eyJhbGciOiJkaXIiLCJlbmMiOiJBMTI4Q0JDLUhTMjU2In0..z5Xd8P0hdLasvHrm7mI1Zg.aY1Sj6Ia3QkJka1WAAxwt7mktKNeOIMU43P923MYd1nKZbU2m2bw40KRfRA-JsREF8xborIUgnNdwrpDmOpfRbnoxXrF-CuHPaG4UpZMdvwN-jwUqtXK6-aJxbR-l78aTTb0eqCOPT9oqv6Cm1viFLius-XDzvO-nvCW8S3vB5NyigKEys_3q_zLmY9rNQlZy8kiQGG4YUwcZ46--1unCnSCfEPW-pibIXhtNZ0ElPpDAyrwq_VmTfxv99HDN59Q4WzL6L9ru6XMrijKQRP8VsmQx2jN9CCCWomBHpmXERWYAZsUrPeCqoX7aaL55kq0ubunEU0L_9sdSGFssoE_5w.tuhAB8palmEoV48Dn8yAwA"
USERNAME = "ccsss-zhujun"
PASSWORD = "Zscvh456873691!"
DRIVER_PATH = r"D:\python project\chromedriver-win64\chromedriver-win64\chromedriver.exe"
# 8分钟超时(单位秒)，正式启用计时逻辑
TIMEOUT_SEC = 8 * 60

# 告警关键字与对应关单处理话术映射
CONTENT_MAP = {
    "[VMCpuHighMajor]": """1.告警内容以及告警虚机IP已告知客户，客户自行操作降低cpu使用，决策是否需求增加资源
2.眉山以项目形式交付，浪潮只负责运维
3.登录rbss检查cpu使用超过90%。cpu使用超过90%对业务无影响""",
    "[VMMemHighMajor]": """1.告警内容以及告警虚机IP已告知客户，客户自行操作降低内存使用，决策是否需求增加资源。
2.眉山以项目形式交付，浪潮只负责运维。
3.登录rbss检查内存使用超过90%。内存使用超过90%对业务无影响。""",
    "[VMDiskFullMajor]": """1.告警内容以及告警虚机IP已告知客户，客户自行操作降低存储使用，决策是否需求增加资源。
2.眉山以项目形式交付，浪潮只负责运维。
3.登录rbss检查存储使用超过90%。存储使用超过90%对业务无影响。""",
    "[VMAllDisksFullMajor]": """1.告警内容以及告警虚机IP已告知客户，客户自行操作降低存储使用，决策是否需求增加资源。
2.眉山以项目形式交付，浪潮只负责运维。
3.登录rbss检查存储使用超过90%。存储使用超过90%对业务无影响。""",
    "[HighBandwidthUsage]": """1、收到一条关于交换机的告警。该交换机在过去时间内使用率持续超过90%。
2、这种持续高负载可能会影响服务器上运行的应用性能。立即登录交换机排查原因。
3、分析系统负载：通过 使用 内存和cpu 查看命令整体负载情况。
4、核查近期变更：查看流量主要来自哪些IP，以及流量类型、出入方向、通知客户核实。
5、监控关联指标：经排查、和客户核对，带宽开销和实际使用需求场景匹配。
6、处理结果：使用率已恢复正常情况，工单关闭""",
    "[NetDeviceAlert]": """1、收到一条关于交换机的告警。该交换机在过去时间内使用率持续超过90%。
2、这种持续高负载可能会影响服务器上运行的应用性能。立即登录交换机排查原因。
3、分析系统负载：通过 使用 内存和cpu 查看命令整体负载情况。
4、核查近期变更：查看流量主要来自哪些IP，以及流量类型、出入方向、通知客户核实。
5、监控关联指标：经排查、和客户核对，带宽开销和实际使用需求场景匹配。
6、处理结果：使用率已恢复正常情况，工单关闭"""
}
KEY_WORDS = list(CONTENT_MAP.keys())

# 富文本输入框
EDITOR_XPATH = '//*[@id="Watermark"]/div[2]/app-tab/div/app-deal-workorder/form/div[1]/div/div[1]/div[3]/nz-tabset/div[2]/div[1]/div[1]/div[2]/div/div/app-edit/quill-editor/div[2]/div[1]'
# 关单按钮：button[8]下的span
CLOSE_BTN_XPATH = '//*[@id="Watermark"]/div[2]/app-tab/div/app-deal-workorder/form/div[2]/button[8]/span'
# 挂起按钮 button[7]
SUSPEND_BTN_XPATH = '//*[@id="Watermark"]/div[2]/app-tab/div/app-deal-workorder/form/div[2]/button[7]'

# NetDeviceAlert需要校验的原始描述框xpath
DESC_CHECK_XPATH = '//*[@id="Watermark"]/div[2]/app-tab/div/app-deal-workorder/form/div[1]/div/div[2]/div[2]/div/nz-tabset/div[2]/div[1]/div/div/div/div/div[2]'

# =========xpath更新=========
SUSPEND_MODAL_SELECT_XPATH = '//*[@id="cdk-overlay-9"]/nz-modal/div/div[2]/div/div/div[2]/div[1]/div/div[2]/nz-select/div/span/i'
# 选中“其他”li元素，去掉/text()，selenium不能定位text()文本节点
SUSPEND_MODAL_OPTION_OTHER_XPATH = '//*[@id="cdk-overlay-17"]/div/div/ul/li[4]'
# 挂起弹窗外层日期输入框
SUSPEND_MODAL_DATE_INPUT_XPATH = '//*[@id="cdk-overlay-9"]/nz-modal/div/div[2]/div/div/div[2]/div[2]/div/div[2]/nz-date-picker/nz-picker/span/input'
# 日历弹窗内输入框（新）
POPUP_DATE_INPUT_XPATH = '//*[@id="cdk-overlay-18"]/div/date-range-popup/div/div/div/calendar-input/div/div/input'
SUSPEND_MODAL_CONFIRM_BTN_XPATH = '//*[@id="cdk-overlay-9"]/nz-modal/div/div[2]/div/div/div[3]/button[2]'

# tab xpath
QUERY_TAB_XPATH = '/html/body/app-root/default/div[1]/nav/div/ul/li[8]'
PENDING_TAB_XPATH = '//*[@id="Watermark"]/div[2]/app-tab/div/app-workorder/div/div[1]/div[2]/div[1]'
PROCESSING_TAB_XPATH = '//*[@id="Watermark"]/div[2]/app-tab/div/app-workorder/div/div[1]/div[2]/div[2]'
# 【我的待处理】表格容器xpath
PENDING_TABLE_CONTAINER_XPATH = '//*[@id="Watermark"]/div[2]/app-tab/div/app-workorder/div/div[2]/div[2]'

# 工单编号：表头th[3]，对应数据行 td[3]
WORK_ORDER_ID_XPATH = './/td[3]'
# ============================

def safe_click(driver, element):
    """安全点击：优先普通click，被拦截时使用JS执行点击兜底"""
    try:
        element.click()
    except ElementClickInterceptedException:
        print("⚠普通click被拦截，使用JS执行点击")
        driver.execute_script("arguments[0].click();", element)

def suspend_workorder_flow(driver, wait):
    """执行工单挂起完整流程：填暂时挂起，弹窗选其他，设置延后2天日期，ESC关闭日历，等待2秒后点确认"""
    try:
        print("📝富文本填入【暂时挂起】")
        editor = wait.until(EC.element_to_be_clickable((By.XPATH, EDITOR_XPATH)))
        editor.click()
        time.sleep(1.5)
        editor.clear()
        editor.send_keys("暂时挂起")
        time.sleep(3)

        print("🖱️点击挂起按钮(button[7])")
        suspend_btn = wait.until(EC.element_to_be_clickable((By.XPATH, SUSPEND_BTN_XPATH)))
        safe_click(driver, suspend_btn)
        time.sleep(2)
        print("⏱等待挂起弹窗DOM渲染完成")
        time.sleep(3)

        print("🖱️弹窗点开原因下拉框(i图标)")
        modal_select = wait.until(EC.element_to_be_clickable((By.XPATH, SUSPEND_MODAL_SELECT_XPATH)))
        safe_click(driver, modal_select)
        time.sleep(3)

        print("🖱️选择下拉选项【其他】")
        option_other = wait.until(EC.element_to_be_clickable((By.XPATH, SUSPEND_MODAL_OPTION_OTHER_XPATH)))
        safe_click(driver, option_other)
        time.sleep(3)

        print("🖱️点开日期输入框，唤起日历弹窗")
        date_input = wait.until(EC.element_to_be_clickable((By.XPATH, SUSPEND_MODAL_DATE_INPUT_XPATH)))
        safe_click(driver, date_input)
        time.sleep(3)

        # ========== 新逻辑：日历弹窗内部input输入，延后2天 ==========
        popup_input = wait.until(EC.element_to_be_clickable((By.XPATH, POPUP_DATE_INPUT_XPATH)))
        target_day = datetime.now() + timedelta(days=2)
        target_date_str = target_day.strftime("%Y-%m-%d")
        print(f"📅 设置挂起到期日期：{target_date_str}")

        # JS清空输入框，赋值并触发前端事件
        driver.execute_script("arguments[0].value = '';", popup_input)
        time.sleep(0.5)
        driver.execute_script(f'arguments[0].value="{target_date_str}";arguments[0].dispatchEvent(new Event("input"));arguments[0].dispatchEvent(new Event("change"));', popup_input)
        time.sleep(2)

        # 按下ESC关闭日历弹窗
        popup_input.send_keys(Keys.ESCAPE)
        print("⌨按下ESC关闭日历弹窗")
        time.sleep(2)

        print("🖱️点击挂起弹窗确认按钮")
        confirm_btn = wait.until(EC.element_to_be_clickable((By.XPATH, SUSPEND_MODAL_CONFIRM_BTN_XPATH)))
        safe_click(driver, confirm_btn)
        print("✅挂起操作全部执行完成，等待页面跳转回待处理列表")
        time.sleep(8)
    except Exception as e:
        import traceback
        print(f"❌挂起流程内部异常：{e}")
        print("异常堆栈:\n", traceback.format_exc())

def close_workorder_flow(driver, wait, hit_key):
    """执行关单流程，填入对应话术；NetDeviceAlert已提前做完描述校验"""
    print("等待富文本编辑框加载")
    editor = wait.until(EC.element_to_be_clickable((By.XPATH, EDITOR_XPATH)))
    editor.click()
    time.sleep(1)
    fill_text = CONTENT_MAP[hit_key]
    editor.clear()
    editor.send_keys(fill_text)
    print(f"✅已填入处理话术")
    time.sleep(5)
    #点击关单 button[8]/span
    close_btn = wait.until(EC.element_to_be_clickable((By.XPATH, CLOSE_BTN_XPATH)))
    safe_click(driver, close_btn)
    print("✅已点击关单按钮(button[8]/span)，等待页面自动跳转回【我的待处理】")
    time.sleep(10)

def process_workorder_list(driver, wait, workorder_timer_dict):
    """
    在【我的待处理】页面处理工单列表
    workorder_timer_dict: {工单ID:第一次发现时间戳}
    正式启用8分钟计时：M2/M3未命中关键字，需要等待满8分钟才执行挂起
    return True:处理到符合条件工单；return False:没有找到可处理工单
    """
    print("\n====开始遍历【我的待处理】表格判断工单====")
    try:
        table_container = WebDriverWait(driver,8).until(
            EC.presence_of_element_located((By.XPATH, PENDING_TABLE_CONTAINER_XPATH))
        )
        all_tr = table_container.find_elements(By.XPATH, './/tbody/tr')
        print(f"\n📋待处理表格总行数：{len(all_tr)}")
        print("-"*120)
        current_id_set = set()
        hit_any_workorder = False

        #打印表格信息
        for idx, tr in enumerate(all_tr):
            row_no = idx +1
            wo_id = "UNKNOWN_ID"
            level_text = "无级别标签"
            title_text = "无标题"
            has_deal_button = False
            try:
                id_elem = tr.find_element(By.XPATH, WORK_ORDER_ID_XPATH)
                raw_id = id_elem.text.strip()
                if raw_id:
                    wo_id = raw_id
            except NoSuchElementException:
                pass
            try:
                level_elem = tr.find_element(By.XPATH, './/td[6]/div/app-workorder-status-label')
                level_text = level_elem.text.strip()
            except NoSuchElementException:
                pass
            try:
                title_elem = tr.find_element(By.XPATH, './/td[2]')
                title_text = title_elem.text.strip()
            except NoSuchElementException:
                pass
            try:
                tr.find_element(By.XPATH, './/td[30]/div/button[1]')
                has_deal_button = True
            except NoSuchElementException:
                pass
            print(f"行{row_no:2d} | ID:{wo_id:<14} | 原始级别：【{level_text:<12}】 | 标题：{title_text[:55]:<55} | 是否有处理按钮：{has_deal_button}")
            current_id_set.add(wo_id)
        print("-"*120,"\n")

        # 清理已经消失的工单计时
        remove_keys = []
        for saved_wo_id in workorder_timer_dict:
            if saved_wo_id not in current_id_set:
                remove_keys.append(saved_wo_id)
        for wo_id in remove_keys:
            print(f"ℹ工单ID【{wo_id}】已经不在待处理列表，清除计时标记")
            del workorder_timer_dict[wo_id]

        for idx, tr in enumerate(all_tr):
            row_no = idx +1
            print(f"------开始处理第{row_no}行工单------")
            try:
                wo_id = "UNKNOWN_ID"
                try:
                    id_elem = tr.find_element(By.XPATH, WORK_ORDER_ID_XPATH)
                    raw_id = id_elem.text.strip()
                    if raw_id:
                        wo_id = raw_id
                except NoSuchElementException:
                    pass

                level_elem = tr.find_element(By.XPATH, './/td[6]/div/app-workorder-status-label')
                level_text = level_elem.text.strip()
                title_elem = tr.find_element(By.XPATH, './/td[2]')
                title_text = title_elem.text.strip()

                hit_key = None
                for kw in KEY_WORDS:
                    if kw in title_text:
                        hit_key = kw
                        break
                print(f"第{row_no}行 | ID【{wo_id}】| 原始级别：【{level_text}】 | 标题：{title_text} | hit_key={hit_key}")

                # ========= M1逻辑：识别到直接挂起，无需等待 =========
                if "M1" in level_text:
                    print(f"🔥M1工单 ID【{wo_id}】直接执行挂起！")
                    deal_btn = tr.find_element(By.XPATH, './/td[30]/div/button[1]')
                    safe_click(driver, deal_btn)
                    time.sleep(6)
                    suspend_workorder_flow(driver, wait)
                    if wo_id in workorder_timer_dict:
                        del workorder_timer_dict[wo_id]
                    hit_any_workorder = True
                    return hit_any_workorder

                # ========= M2 / M3逻辑：启用8分钟计时 =========
                elif "M2" in level_text or "M3" in level_text:
                    real_level = "M2" if "M2" in level_text else "M3"
                    if hit_key is not None:
                        # M2/M3命中关键字：直接关单，不受计时限制
                        print(f"✅{real_level}工单 ID【{wo_id}】命中关键字 {hit_key}，准备点击工单处理按钮执行关单")
                        deal_btn = tr.find_element(By.XPATH, './/td[30]/div/button[1]')
                        safe_click(driver, deal_btn)
                        time.sleep(5)
                        if hit_key == "[NetDeviceAlert]":
                            print("🔍NetDeviceAlert工单，读取并校验原始描述框")
                            desc_elem = wait.until(EC.visibility_of_element_located((By.XPATH, DESC_CHECK_XPATH)))
                            desc_text = desc_elem.text
                            print("========原始描述框内容开始========")
                            print(desc_text)
                            print("========原始描述框内容结束========\n")
                            if "ICMP ping" not in desc_text and "SNMP data collection" not in desc_text:
                                print("⚠原始描述不满足条件，跳过该工单，继续扫描下一行")
                                continue
                        close_workorder_flow(driver, wait, hit_key)
                        hit_any_workorder = True
                        return hit_any_workorder
                    else:
                        # M2/M3未命中关键字：判断计时
                        now_ts = time.time()
                        if wo_id not in workorder_timer_dict:
                            #首次发现，记录当前时间戳
                            workorder_timer_dict[wo_id] = now_ts
                            print(f"⏱首次发现{real_level}工单【{wo_id}】，开始8分钟计时，暂不处理")
                            continue
                        else:
                            #已经存在计时记录，计算已等待时长
                            elapsed = now_ts - workorder_timer_dict[wo_id]
                            if elapsed >= TIMEOUT_SEC:
                                print(f"✅{real_level}工单【{wo_id}】计时已达到{elapsed:.1f}秒 >= {TIMEOUT_SEC}秒，执行挂起！")
                                deal_btn = tr.find_element(By.XPATH, './/td[30]/div/button[1]')
                                safe_click(driver, deal_btn)
                                time.sleep(6)
                                suspend_workorder_flow(driver, wait)
                                del workorder_timer_dict[wo_id]
                                hit_any_workorder = True
                                return hit_any_workorder
                            else:
                                remain = TIMEOUT_SEC - elapsed
                                print(f"⌛{real_level}工单【{wo_id}】已等待{elapsed:.1f}秒，还需等待{remain:.1f}秒，暂跳过")
                                continue
                else:
                    print(f"ℹ第{row_no}行 ID【{wo_id}】原始级别文本【{level_text}】，不属于M1/M2/M3，跳过")
                    continue

            except NoSuchElementException:
                print(f"ℹ第{row_no}行缺少ID/级别/标题/处理按钮元素，跳过该行")
                continue
        return hit_any_workorder
    except Exception as e:
        print(f"处理待处理工单列表异常：{e}")
        return False

def main():
    service = Service(executable_path=DRIVER_PATH)
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless=new")
    driver = webdriver.Chrome(service=service, options=options)
    driver.maximize_window()
    wait = WebDriverWait(driver,25)
    workorder_timer = dict()
    try:
        print(f"正在打开网页：{URL}")
        driver.get(URL)
        #登录
        username_input = wait.until(EC.element_to_be_clickable((By.NAME, "username")))
        password_input = wait.until(EC.element_to_be_clickable((By.NAME, "password")))
        username_input.clear()
        username_input.send_keys(USERNAME)
        password_input.clear()
        password_input.send_keys(PASSWORD)
        login_btn = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="kc-login"]')))
        time.sleep(5)
        print("等待登录页面加载完成")
        login_btn.click()
        print("已点击登录，等待输入谷歌验证码，等待页面加载完成")
        time.sleep(15)
        #初始进入工单查询
        work_order_query = wait.until(EC.element_to_be_clickable((By.XPATH, QUERY_TAB_XPATH)))
        work_order_query.click()
        print("✅已点击【工单查询】")
        time.sleep(5)
        # ==========大循环 持续轮询==========
        while True:
            my_pending = wait.until(EC.element_to_be_clickable((By.XPATH, PENDING_TAB_XPATH)))
            my_pending.click()
            print("✅切换到【我的待处理】")
            time.sleep(5)
            has_processed = process_workorder_list(driver, wait, workorder_timer)
            if has_processed:
                print("🔔本次循环成功处理工单，继续下一轮循环")
                continue
            else:
                random_sleep_sec = random.randint(30, 420)
                print(f"⚠【我的待处理】无满足条件工单，随机等待 {random_sleep_sec} 秒后刷新")
                time.sleep(random_sleep_sec)
    except Exception as e:
        print(f"主循环异常：{e}")
        import traceback
        print(traceback.format_exc())
        input("程序异常，按回车键关闭浏览器：")
        driver.quit()

if __name__ == "__main__":
    main()
