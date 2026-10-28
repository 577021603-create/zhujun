from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException, StaleElementReferenceException
from selenium.webdriver.common.keys import Keys
import time
import random
import re
import os
import sys
from datetime import datetime, timedelta

# ==========配置区============
URL = "https://css.cloud.inspur.com/platform/dashboard#state=23f2201d-512b-4708-a3af-1b5e6cf0a00f&session_state=c324da4b-ef55-4a39-a020-a1e3c2a0379d&code=eyJhbGciOiJkaXIiLCJlbmMiOiJBMTI4Q0JDLUhTMjU2In0..z5Xd8P0hdLasvHrm7mI1Zg.aY1Sj6Ia3QkJka1WAAxwt7mktKNeOIMU43P923MYd1nKZbU2m2bw40KRfRA-JsREF8xborIUgnNdwrpDmOpfRbnoxXrF-CuHPaG4UpZMdvwN-jwUqtXK6-aJxbR-l78aTTb0eqCOPT9oqv6Cm1viFLius-XDzvO-nvCW8S3vB5NyigKEys_3q_zLmY9rNQlZy8kiQGG4YUwcZ46--1unCnSCfEPW-pibIXhtNZ0ElPpDAyrwq_VmTfxv99HDN59Q4WzL6L9ru6XMrijKQRP8VsmQx2jN9CCCWomBHpmXERWYAZsUrPeCqoX7aaL55kq0ubunEU0L_9sdSGFssoE_5w.tuhAB8palmEoV48Dn8yAwA"
USERNAME = "ccsss-zhujun"
PASSWORD = "Zscvh456873691!"
DRIVER_PATH = r"D:\python project\chromedriver-win64\chromedriver-win64\chromedriver.exe"
# 8分钟超时(单位秒)，正式启用计时逻辑
TIMEOUT_SEC = 8 * 60

# =====测试开关=====
# True：仅测试挂起流程（进入【我的经手工单】找可挂起工单执行一次后退出，不执行任何关单动作）
SUSPEND_TEST_MODE = False
# True：编辑框8秒内找不到就跳过填理由直接挂起（容错）；False：保持原逻辑等25秒，等不到则中止
SKIP_EDITOR_IF_MISSING = True

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
    "[NetDeviceAlert]": """1.登录交换机查看日志，发现交换机正常运行
2.查看SNMP配置正常 
3.zabbix查看正常显示交换机状态 
4.已咨询相关设备厂商，为设备固有bug
结论:本次告警为误告警，因交换机无法ping通产生的告警，交换机正常运行，关单"""
}
KEY_WORDS = list(CONTENT_MAP.keys())

# 富文本输入框
EDITOR_XPATH = '//*[@id="Watermark"]/div[2]/app-tab/div/app-deal-workorder/form/div[1]/div/div[1]/div[3]/nz-tabset/div[2]/div[1]/div[1]/div[2]/div/div/app-edit/quill-editor/div[2]/div[1]'
# 关单按钮：button[8]下的span
BUTTON_BAR_XPATH = '//*[@id="Watermark"]/div[2]/app-tab/div/app-deal-workorder/form/div[2]'
CLOSE_BTN_XPATH = BUTTON_BAR_XPATH + '//button[contains(normalize-space(.),"关单")]'
# 挂起按钮 button[7]
SUSPEND_BTN_XPATH = BUTTON_BAR_XPATH + '//button[contains(normalize-space(.),"挂起")]'

# NetDeviceAlert需要校验的原始描述框xpath
DESC_CHECK_XPATH = '//*[@id="Watermark"]/div[2]/app-tab/div/app-deal-workorder/form/div[1]/div/div[2]/div[2]/div/nz-tabset/div[2]/div[1]/div/div/div/div/div[2]'

# =========xpath更新=========
# 可见的挂起弹窗（跳过页面里隐藏的历史弹窗，如“添加关联工单”）
SUSPEND_MODAL_XPATH = '(//div[contains(@class,"ant-modal-wrap") and not(contains(@style,"visibility: hidden"))])[last()]'
# 弹窗内挂起分类下拉框（老版ng-zorro: ant-select-selection；新版antd: ant-select-selector，双兼容）
SUSPEND_MODAL_SELECT_XPATH = SUSPEND_MODAL_XPATH + '//div[contains(@class,"ant-select-selection")][1] | ' + SUSPEND_MODAL_XPATH + '//div[contains(@class,"ant-select-selector")][1]'
# 选中“其他”选项：兼容多种下拉结构（ant-select-dropdown、旧ul/li、新版item-option、cdk浮层内ul/li）
SUSPEND_MODAL_OPTION_OTHER_XPATH = '(//div[contains(@class,"ant-select-dropdown")]//li[contains(normalize-space(.),"其他")])[last()] | (//ul[contains(@class,"ant-select-dropdown-menu")]//li[contains(normalize-space(.),"其他")])[last()] | (//div[contains(@class,"ant-select-item-option") and contains(normalize-space(.),"其他")])[last()] | (//div[contains(@class,"cdk-overlay-container")]//ul)[last()]//li[contains(normalize-space(.),"其他")]'
# 弹窗内日期输入框（老版ng-zorro: input.ant-calendar-picker-input readonly，点击唤起日历弹窗）
SUSPEND_MODAL_DATE_INPUT_XPATH = SUSPEND_MODAL_XPATH + '//input[contains(@class,"ant-calendar-picker-input")] | ' + SUSPEND_MODAL_XPATH + '//nz-date-picker//input'
# 弹窗确认按钮（按文字定位，优先“含挂起分类/预计解决时间”的可见弹窗，兜底最后可见弹窗）
SUSPEND_MODAL_CONFIRM_BTN_XPATH = '(//div[contains(@class,"ant-modal-wrap") and not(contains(@style,"visibility: hidden")) and (contains(.,"挂起分类") or contains(.,"预计解决时间"))][last()]//div[contains(@class,"ant-modal-footer")]//button[contains(normalize-space(.),"确定")]) | (//div[contains(@class,"ant-modal-wrap") and not(contains(@style,"visibility: hidden"))][last()]//div[contains(@class,"ant-modal-footer")]//button[contains(normalize-space(.),"确定")])'
# 工单详情页返回按钮（测试模式返回列表用，优先button后尝试a）
BACK_BTN_XPATH = '//*[@id="Watermark"]/div[2]/app-tab/div/app-deal-workorder//button[contains(normalize-space(.),"返回")] | //*[@id="Watermark"]/div[2]/app-tab/div/app-deal-workorder//a[contains(normalize-space(.),"返回")]'

# tab xpath
QUERY_TAB_XPATH = '/html/body/app-root/default/div[1]/nav/div/ul/li[8]'
PENDING_TAB_XPATH = '//*[@id="Watermark"]/div[2]/app-tab/div/app-workorder/div/div[1]/div[2]/div[1]'
PROCESSING_TAB_XPATH = '//*[@id="Watermark"]/div[2]/app-tab/div/app-workorder/div/div[1]/div[2]/div[2]'
# 【我的经手工单】tab（测试挂起流程用，div[3]）
HANDLED_TAB_XPATH = '//*[@id="Watermark"]/div[2]/app-tab/div/app-workorder/div/div[1]/div[2]/div[3]'
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
    """执行工单挂起完整流程：填暂时挂起。，弹窗选其他，设置延后2天日期，点确认；成功返回True，失败返回False"""
    try:
        print("📝尝试填入【暂时挂起。】")
        try:
            editor = WebDriverWait(driver, 8).until(EC.element_to_be_clickable((By.XPATH, EDITOR_XPATH)))
            editor.click()
            time.sleep(1.5)
            editor.clear()
            editor.send_keys("暂时挂起。")
            time.sleep(3)
            print("✅理由已填入")
        except TimeoutException:
            if SKIP_EDITOR_IF_MISSING:
                print("⚠编辑框8秒内不可用（只读或表单不同），跳过填理由，直接尝试挂起")
            else:
                raise

        print("🖱️点击挂起按钮(button[7])")
        suspend_btn = wait.until(EC.element_to_be_clickable((By.XPATH, SUSPEND_BTN_XPATH)))
        safe_click(driver, suspend_btn)
        time.sleep(4)

        print("⏱等待挂起弹窗DOM渲染完成")
        wait.until(EC.presence_of_element_located((By.XPATH, SUSPEND_MODAL_XPATH)))
        time.sleep(3)

        print("🖱️检查挂起分类下拉框（默认已选“其他”则跳过）")
        modal_select = wait.until(EC.presence_of_element_located((By.XPATH, SUSPEND_MODAL_SELECT_XPATH)))
        current_text = (modal_select.text or '').strip()
        if '其他' in current_text:
            print(f"✅挂起分类已是【其他】（当前显示: {current_text}），跳过选择")
        else:
            print(f"🖱️挂起分类当前为【{current_text}】，点开下拉选择【其他】")
            safe_click(driver, modal_select)
            time.sleep(2)
            # 若下拉未展开，改点 nz-select 根节点再试一次
            try:
                vis_dd = driver.find_elements(By.XPATH, '//div[contains(@class,"ant-select-dropdown")][not(ancestor::*[contains(@style,"display: none") or contains(@style,"visibility: hidden")])]')
                if not vis_dd:
                    print("⚠下拉未展开，改点nz-select根节点重试")
                    nz_sel = driver.find_element(By.XPATH, SUSPEND_MODAL_XPATH + '//nz-select[1]')
                    driver.execute_script("arguments[0].click();", nz_sel)
                    time.sleep(2)
            except Exception:
                pass
            try:
                option_other = wait.until(EC.element_to_be_clickable((By.XPATH, SUSPEND_MODAL_OPTION_OTHER_XPATH)))
                safe_click(driver, option_other)
                time.sleep(3)
            except TimeoutException:
                # 证据采集：找不到选项时导出页面HTML与截图，便于定位真实结构
                try:
                    driver.save_screenshot(r'D:\python project\first\option_fail_screen.png')
                    with open(r'D:\python project\first\option_fail_dump.html', 'w', encoding='utf-8') as f:
                        f.write(driver.execute_script("return document.body.innerHTML"))
                    print("📄下拉选项失败证据已导出: D:\\python project\\first\\option_fail_dump.html")
                except Exception:
                    pass
                raise

        print("🖱️点击日期输入框打开日历，点选日期（延后2天）")
        date_input = wait.until(EC.element_to_be_clickable((By.XPATH, SUSPEND_MODAL_DATE_INPUT_XPATH)))
        safe_click(driver, date_input)
        time.sleep(2)
        target_day = datetime.now() + timedelta(days=2)
        target_date_str = target_day.strftime("%Y-%m-%d")
        day_num = str(target_day.day)
        print(f"📅 目标日期：{target_date_str}，日历中点选第{day_num}天")
        date_picked = False
        try:
            # 日历浮层（ng-zorro: <date-range-popup>）
            cal_dd = wait.until(EC.visibility_of_element_located((By.XPATH, '//date-range-popup')))
            title_str = f"{target_day.year}年{target_day.month}月{target_day.day}日"
            # 面板月份若不是目标月份，点“下月”箭头切换（最多3次）
            for _ in range(3):
                try:
                    ym_txt = cal_dd.find_element(By.XPATH, './/span[contains(@class,"ant-calendar-ym-select")]').text
                except Exception:
                    ym_txt = ''
                if f"{target_day.year}年" in ym_txt and f"{target_day.month}月" in ym_txt:
                    break
                try:
                    next_btn = cal_dd.find_element(By.XPATH, './/a[contains(@class,"ant-calendar-next-month-btn")]')
                    safe_click(driver, next_btn)
                    time.sleep(1.2)
                except Exception:
                    break
            # 直接按单元格 title 属性点选（如 title="2026年9月22日"），最稳
            cell = cal_dd.find_element(By.XPATH, f'.//td[@title="{title_str}"]//div[contains(@class,"ant-calendar-date")]')
            safe_click(driver, cell)
            time.sleep(2)
            cur_val = (date_input.get_attribute('value') or '').strip()
            if target_date_str in cur_val:
                print(f"✅日历点选成功，日期输入框当前值: {cur_val}")
                date_picked = True
            else:
                print(f"⚠点选后输入框值不对（当前: {cur_val!r}，目标: {target_date_str}），改直接输入兜底")
        except Exception as e:
            print(f"⚠日历点选异常（{e}），改直接输入兜底")
            # 证据：日历结构不符预期时导出，便于定位真实DOM
            try:
                driver.save_screenshot(r'D:\python project\first\calendar_fail_screen.png')
                with open(r'D:\python project\first\calendar_fail_dump.html', 'w', encoding='utf-8') as f:
                    f.write(driver.execute_script("return document.body.innerHTML"))
                print("📄日历结构证据已导出: D:\\python project\\first\\calendar_fail_dump.html")
            except Exception:
                pass
        if not date_picked:
            # 兜底：直接输入（部分旧版组件可生效）
            try:
                driver.execute_script("arguments[0].removeAttribute('readonly');", date_input)
                date_input.clear()
                date_input.send_keys(target_date_str)
                time.sleep(1)
                date_input.send_keys(Keys.ENTER)
                time.sleep(1)
                driver.execute_script("arguments[0].blur();", date_input)
                time.sleep(1)
            except Exception:
                pass
            print(f"⌨直接输入兜底完成（输入框当前值: {date_input.get_attribute('value')}）")
        # 若日历浮层仍残留，按ESC关闭（避免遮挡确定按钮）；不影响挂起弹窗
        try:
            leftovers = driver.find_elements(By.XPATH, '//date-range-popup')
            if leftovers:
                date_input.send_keys(Keys.ESCAPE)
                time.sleep(1)
        except Exception:
            pass
        print(f"⌨日期处理完成（输入框当前值: {date_input.get_attribute('value')}）")

        print("🖱️点击挂起弹窗确认按钮")
        confirmed = False
        for attempt in range(1, 4):
            try:
                confirm_btn = wait.until(EC.element_to_be_clickable((By.XPATH, SUSPEND_MODAL_CONFIRM_BTN_XPATH)))
            except TimeoutException:
                print(f"⚠第{attempt}次未找到确定按钮，检查弹窗是否已关闭")
                if not driver.find_elements(By.XPATH, SUSPEND_MODAL_XPATH):
                    print("✅挂起弹窗已不在页面，视为已确认")
                    confirmed = True
                    break
                time.sleep(2)
                continue
            try:
                confirm_btn.click()
            except ElementClickInterceptedException:
                print(f"⚠第{attempt}次点击被拦截，JS兜底点击")
                driver.execute_script("arguments[0].click();", confirm_btn)
            except Exception as e:
                print(f"⚠第{attempt}次点击异常：{e}，JS兜底点击")
                driver.execute_script("arguments[0].click();", confirm_btn)
            print(f"✅第{attempt}次点击确定，等待弹窗关闭...")
            try:
                WebDriverWait(driver, 10).until(EC.invisibility_of_element_located((By.XPATH, SUSPEND_MODAL_XPATH)))
                print("✅挂起弹窗已关闭")
                confirmed = True
                break
            except TimeoutException:
                print(f"⚠第{attempt}次点击后弹窗未关闭，重试...")
                time.sleep(2)
        if not confirmed:
            # 留证据：确定点不下去时导出页面HTML与截图
            try:
                driver.save_screenshot(r'D:\python project\first\confirm_fail_screen.png')
                with open(r'D:\python project\first\confirm_fail_dump.html', 'w', encoding='utf-8') as f:
                    f.write(driver.execute_script("return document.body.innerHTML"))
                print("📄确认失败证据已导出: D:\\python project\\first\\confirm_fail_dump.html")
            except Exception:
                pass
            raise TimeoutException("点击确定后挂起弹窗未关闭，可能表单校验未通过")
        print("✅挂起操作全部执行完成，等待页面跳转回待处理列表")
        time.sleep(8)
        return True
    except Exception as e:
        import traceback
        print(f"❌挂起流程内部异常：{e}")
        print("异常堆栈:\n", traceback.format_exc())
        return False

def back_to_list(driver, wait, tab_xpath=None):
    """从工单详情页返回列表：优先点应用内tab条上的【工单查询】；其次浏览器后退；最后刷新并重新导航（查询→目标tab）"""
    target_tab = tab_xpath or (HANDLED_TAB_XPATH if SUSPEND_TEST_MODE else PENDING_TAB_XPATH)
    # 1) 点应用内 tab 条上的【工单查询】（详情页在应用内tab打开，此方式最可靠，不触发整页刷新）
    try:
        list_tab = wait.until(EC.element_to_be_clickable((
            By.XPATH, '//*[@id="Watermark"]/div[2]/app-tab/div//*[self::span or self::div or self::a][contains(normalize-space(.),"工单查询")][1]')))
        safe_click(driver, list_tab)
        time.sleep(4)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, PENDING_TABLE_CONTAINER_XPATH)))
        try:
            h_tab = wait.until(EC.element_to_be_clickable((By.XPATH, target_tab)))
            safe_click(driver, h_tab)
            time.sleep(3)
        except Exception:
            pass
        print("↩已通过应用内【工单查询】tab返回列表")
        return True
    except Exception:
        pass
    # 2) 浏览器后退（SPA路由不整页刷新）
    try:
        driver.back()
        time.sleep(4)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, PENDING_TABLE_CONTAINER_XPATH)))
        try:
            h_tab = wait.until(EC.element_to_be_clickable((By.XPATH, target_tab)))
            safe_click(driver, h_tab)
            time.sleep(3)
        except Exception:
            pass
        print("↩已通过浏览器后退返回列表")
        return True
    except Exception:
        pass
    # 3) 刷新并重新导航
    try:
        driver.refresh()
        time.sleep(6)
        q_tab = wait.until(EC.element_to_be_clickable((By.XPATH, QUERY_TAB_XPATH)))
        q_tab.click()
        time.sleep(5)
        h_tab2 = wait.until(EC.element_to_be_clickable((By.XPATH, target_tab)))
        safe_click(driver, h_tab2)
        time.sleep(5)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, PENDING_TABLE_CONTAINER_XPATH)))
        print("↩已通过刷新+重新导航返回列表")
        return True
    except Exception:
        print("❌刷新后仍未回到列表")
        return False

def test_suspend_flow_once(driver, wait):
    """仅测试挂起流程：在【我的经手工单】逐行点处理，找到详情页有【挂起】按钮的行执行一次挂起流程，跳过所有关单动作"""
    print("\n====开始【我的经手工单】挂起流程测试====")
    row_idx = 0
    attempted = 0
    try:
        while True:
            try:
                table_container = WebDriverWait(driver, 8).until(
                    EC.presence_of_element_located((By.XPATH, PENDING_TABLE_CONTAINER_XPATH))
                )
                all_tr = table_container.find_elements(By.XPATH, './/tbody/tr')
                total = len(all_tr)
                if total == 0:
                    print("⏳表格行异步加载中，轮询等待最多30秒")
                    for _ in range(15):
                        time.sleep(2)
                        all_tr = table_container.find_elements(By.XPATH, './/tbody/tr')
                        total = len(all_tr)
                        if total > 0:
                            break
                print(f"📋当前列表行数：{total}")
                total = len(all_tr)
                if total == 0:
                    print("⚠首次0行，可能是tab点击未生效，重新点击tab再等一次")
                    try:
                        tab_el = driver.find_element(By.XPATH, HANDLED_TAB_XPATH)
                        safe_click(driver, tab_el)
                        time.sleep(5)
                    except Exception as ex:
                        print("重新点击tab失败：" + str(ex))
                    for _ in range(10):
                        all_tr = table_container.find_elements(By.XPATH, './/tbody/tr')
                        total = len(all_tr)
                        if total > 0:
                            break
                        time.sleep(2)
                    print(f"重新点击后行数：{total}")
                    if total == 0:
                        print("当前URL=" + str(driver.current_url))
                        try:
                            tab_el2 = driver.find_element(By.XPATH, HANDLED_TAB_XPATH)
                            print("HANDLED_TAB class=" + str(tab_el2.get_attribute("class")) + " aria-selected=" + str(tab_el2.get_attribute("aria-selected")))
                        except Exception as ex:
                            print("读取tab属性失败 " + str(ex))
                        try:
                            driver.save_screenshot(r"D:\python project\first\test_0rows.png")
                            print("已保存截图 test_0rows.png")
                        except Exception as ex:
                            print("截图失败 " + str(ex))
                if row_idx >= total:
                    print(f"❌测试结束：共 {total} 行，尝试了 {attempted} 行，未找到可挂起的工单")
                    return False
                tr = all_tr[row_idx]
                try:
                    wo_id = tr.find_element(By.XPATH, WORK_ORDER_ID_XPATH).text.strip()
                except NoSuchElementException:
                    wo_id = "UNKNOWN_ID"
                try:
                    deal_btn = tr.find_element(By.XPATH, './/td[30]/div/button[1]')
                except NoSuchElementException:
                    print(f"行{row_idx + 1} | {wo_id} 无处理按钮，跳过")
                    row_idx += 1
                    continue
                print(f"行{row_idx + 1} | {wo_id} 有处理按钮，直接执行挂起流程")
                safe_click(driver, deal_btn)
                time.sleep(6)
                # 不判断是否符合条件，直接执行挂起流程
                suspend_workorder_flow(driver, wait)
                # 判断是否已回到列表（挂起成功会自动跳转）
                try:
                    WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.XPATH, PENDING_TABLE_CONTAINER_XPATH)))
                    print(f"✅测试完成：工单 {wo_id} 挂起流程已执行并返回列表，结果见上方日志")
                    return True
                except TimeoutException:
                    attempted += 1
                    print(f"行{row_idx + 1} | {wo_id} 挂起流程未生效（仍停留在详情页），返回列表继续")
                    if not back_to_list(driver, wait):
                        print("❌返回列表失败，放弃本次测试")
                        return False
                    row_idx += 1
                    continue
            except StaleElementReferenceException:
                # 返回列表后表格重新渲染，重新获取行
                continue
    except Exception as e:
        print(f"测试流程异常：{e}")
        import traceback
        print(traceback.format_exc())
        return False

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

def elapsed_since_create(create_time_str):
    """解析工单创建时间 'YYYY-MM-DD HH:MM:SS'，返回距现在的秒数；解析失败返回None。"""
    try:
        ct = datetime.strptime(create_time_str.strip(), "%Y-%m-%d %H:%M:%S")
        return (datetime.now() - ct).total_seconds()
    except Exception:
        return None


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
            create_time_str = ""
            try:
                create_time_str = tr.find_element(By.XPATH, './/td[8]').text.strip()
            except NoSuchElementException:
                pass
            try:
                tr.find_element(By.XPATH, './/td[30]/div/button[1]')
                has_deal_button = True
            except NoSuchElementException:
                pass
            print(f"行{row_no:2d} | ID:{wo_id:<14} | 创建时间：{create_time_str} | 原始级别：【{level_text:<12}】 | 标题：{title_text[:50]:<50} | 是否有处理按钮：{has_deal_button}")
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

        row_no = 0
        while True:
            row_no += 1
            try:
                # 每行重新定位表格与行元素：详情页导航后列表会重新渲染，缓存的行会过期（stale）
                table_container = driver.find_element(By.XPATH, PENDING_TABLE_CONTAINER_XPATH)
                all_tr = table_container.find_elements(By.XPATH, './/tbody/tr')
                if row_no > len(all_tr):
                    break
                tr = all_tr[row_no - 1]
                print(f"------开始处理第{row_no}行工单------")
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
                try:
                    create_time_str = tr.find_element(By.XPATH, './/td[8]').text.strip()
                except NoSuchElementException:
                    create_time_str = ""

                hit_key = None
                for kw in KEY_WORDS:
                    if kw in title_text:
                        hit_key = kw
                        break
                print(f"第{row_no}行 | ID【{wo_id}】| 创建时间：{create_time_str} | 原始级别：【{level_text}】 | 标题：{title_text} | hit_key={hit_key}")

                # ========= M1逻辑：识别到直接挂起，无需等待 =========
                if "M1" in level_text:
                    print(f"🔥M1工单 ID【{wo_id}】直接执行挂起！")
                    deal_btn = tr.find_element(By.XPATH, './/td[30]/div/button[1]')
                    safe_click(driver, deal_btn)
                    time.sleep(6)
                    if not suspend_workorder_flow(driver, wait):
                        print(f"⚠M1工单【{wo_id}】挂起流程失败，返回列表继续")
                        back_to_list(driver, wait, PENDING_TAB_XPATH)
                    if wo_id in workorder_timer_dict:
                        del workorder_timer_dict[wo_id]
                    hit_any_workorder = True
                    return hit_any_workorder

                # ========= M2 / M3逻辑 =========
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
                            try:
                                desc_elem = wait.until(EC.visibility_of_element_located((By.XPATH, DESC_CHECK_XPATH)))
                            except TimeoutException:
                                print("⚠固定路径描述框未找到，尝试按内容定位")
                                desc_elem = wait.until(EC.visibility_of_element_located((
                                    By.XPATH, '//*[self::div or self::span or self::pre][contains(.,"OSS 告警工单")][contains(.,"告警汇总信息")]')))
                            desc_text = desc_elem.text
                            print("========原始描述框内容开始========")
                            print(desc_text)
                            print("========原始描述框内容结束========\n")
                            if "ICMP ping" not in desc_text and "SNMP data collection" not in desc_text:
                                # 不可关单：按工单创建时间算8分钟计时，满8分钟才挂起
                                elapsed = elapsed_since_create(create_time_str)
                                if elapsed is None:
                                    print(f"⚠NetDeviceAlert工单【{wo_id}】创建时间解析失败（{create_time_str!r}），本轮跳过")
                                    back_to_list(driver, wait, PENDING_TAB_XPATH)
                                    continue
                                if elapsed < TIMEOUT_SEC:
                                    print(f"⏳NetDeviceAlert描述不满足条件，工单创建于{create_time_str}，已过{elapsed:.0f}秒/{TIMEOUT_SEC}秒，继续计时")
                                    back_to_list(driver, wait, PENDING_TAB_XPATH)
                                    continue
                                print(f"✅NetDeviceAlert描述不满足条件，工单创建于{create_time_str}，已过{elapsed:.0f}秒 >= {TIMEOUT_SEC}秒，执行挂起！")
                                if not suspend_workorder_flow(driver, wait):
                                    print(f"⚠NetDeviceAlert工单【{wo_id}】挂起流程失败，返回列表继续")
                                    back_to_list(driver, wait, PENDING_TAB_XPATH)
                                if wo_id in workorder_timer_dict:
                                    del workorder_timer_dict[wo_id]
                                hit_any_workorder = True
                                return hit_any_workorder
                        close_workorder_flow(driver, wait, hit_key)
                        hit_any_workorder = True
                        return hit_any_workorder
                    else:
                        # M2/M3未命中关键字：按工单创建时间算8分钟计时，满8分钟才挂起
                        elapsed = elapsed_since_create(create_time_str)
                        if elapsed is None:
                            print(f"⚠{real_level}工单【{wo_id}】创建时间解析失败（{create_time_str!r}），本轮跳过")
                            continue
                        if elapsed < TIMEOUT_SEC:
                            print(f"⏳{real_level}工单【{wo_id}】未命中关键字，创建于{create_time_str}，已过{elapsed:.0f}秒/{TIMEOUT_SEC}秒，继续计时")
                            continue
                        print(f"✅{real_level}工单【{wo_id}】未命中关键字，创建于{create_time_str}，已过{elapsed:.0f}秒 >= {TIMEOUT_SEC}秒，执行挂起！")
                        deal_btn = tr.find_element(By.XPATH, './/td[30]/div/button[1]')
                        safe_click(driver, deal_btn)
                        time.sleep(6)
                        if not suspend_workorder_flow(driver, wait):
                            print(f"⚠{real_level}工单【{wo_id}】挂起流程失败，返回列表继续")
                            back_to_list(driver, wait, PENDING_TAB_XPATH)
                        if wo_id in workorder_timer_dict:
                            del workorder_timer_dict[wo_id]
                        hit_any_workorder = True
                        return hit_any_workorder
                else:
                    print(f"ℹ第{row_no}行 ID【{wo_id}】原始级别文本【{level_text}】，不属于M1/M2/M3，跳过")
                    continue

            except StaleElementReferenceException:
                # 表格重新渲染导致行过期：重新定位该行再处理一次
                print(f"ℹ第{row_no}行表格重新渲染（stale），重新定位后重试")
                try:
                    time.sleep(2)
                    table_container = driver.find_element(By.XPATH, PENDING_TABLE_CONTAINER_XPATH)
                    all_tr = table_container.find_elements(By.XPATH, './/tbody/tr')
                    if row_no <= len(all_tr):
                        print(f"✅第{row_no}行重定位成功，重新处理该行")
                        row_no -= 1
                        continue
                except Exception:
                    pass
                print(f"ℹ第{row_no}行重试仍失败，跳过该行")
                continue
            except NoSuchElementException:
                print(f"ℹ第{row_no}行缺少ID/级别/标题/处理按钮元素，跳过该行")
                continue
        return hit_any_workorder
    except Exception as e:
        print(f"处理待处理工单列表异常：{e}")
        return False

def bring_chrome_to_front():
    """把自动化 Chrome 窗口置顶，避免用户错过谷歌验证码"""
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        found = []
        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def _cb(hwnd, lparam):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buf, length + 1)
                    title = buf.value
                    if 'Google' in title or 'css.cloud' in title or 'inspur' in title.lower():
                        found.append(hwnd)
            return True
        user32.EnumWindows(_cb, 0)
        if found:
            user32.ShowWindow(found[0], 5)
            user32.SetForegroundWindow(found[0])
            return True
    except Exception:
        pass
    return False


def recover_to_pending(driver, wait):
    """确保回到【我的待处理】：先关闭残留弹窗，再依次尝试 ①直接找PENDING_TAB ②点导航【工单查询】 ③刷新+重新导航；失败返回None"""
    # 0) 若页面有残留可见弹窗（如挂起弹窗未关闭），先按ESC关闭，避免遮挡导航
    try:
        for _ in range(3):
            wraps = driver.find_elements(By.XPATH, '(//div[contains(@class,"ant-modal-wrap") and not(contains(@style,"visibility: hidden"))])')
            if wraps:
                print("⚠检测到残留弹窗，按ESC关闭")
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                time.sleep(2)
            else:
                break
    except Exception:
        pass
    for attempt in range(2):
        try:
            tab = wait.until(EC.element_to_be_clickable((By.XPATH, PENDING_TAB_XPATH)))
            return tab
        except TimeoutException:
            pass
        # 尝试点导航【工单查询】（刷新后应用回到默认首页，必须先导航回工单查询模块）
        try:
            q_tab = wait.until(EC.element_to_be_clickable((By.XPATH, QUERY_TAB_XPATH)))
            q_tab.click()
            time.sleep(5)
        except TimeoutException:
            pass
        # 刷新后重新导航
        try:
            driver.refresh()
            time.sleep(6)
        except Exception:
            pass
    return None

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
        # 登录后等待页面加载（含人工输入谷歌验证码的时间），最多轮询180秒；每轮把Chrome窗口置顶提醒用户
        login_poll_start = time.time()
        while time.time() - login_poll_start < 180:
            bring_chrome_to_front()
            try:
                WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, QUERY_TAB_XPATH)))
                break
            except TimeoutException:
                print("⏳仍在等待登录/谷歌验证码，继续等待...（Chrome窗口已置顶，请检查验证码）")
        else:
            raise TimeoutException("等待登录完成超时180秒，请检查谷歌验证码是否已输入")
        #初始进入工单查询
        work_order_query = wait.until(EC.element_to_be_clickable((By.XPATH, QUERY_TAB_XPATH)))
        work_order_query.click()
        time.sleep(5)
        if SUSPEND_TEST_MODE:
            print("进入【我的经手工单】挂起测试模式")
            my_handled = wait.until(EC.element_to_be_clickable((By.XPATH, HANDLED_TAB_XPATH)))
            my_handled.click()
            time.sleep(5)
            test_suspend_flow_once(driver, wait)
            print("测试结束，关闭浏览器")
            driver.quit()
            return
        time.sleep(5)
        print("✅已点击【工单查询】")
        time.sleep(5)
        # ==========大循环 持续轮询==========
        while True:
            my_pending = recover_to_pending(driver, wait)
            if my_pending is None:
                print("⚠⚠页面状态异常：可能已掉登录或被弹窗遮挡，Chrome窗口已置顶，请人工检查（如有验证码请完成）")
                bring_chrome_to_front()
                time.sleep(60)
                my_pending = recover_to_pending(driver, wait)
                if my_pending is None:
                    raise TimeoutException("连续两次无法回到【我的待处理】，请检查页面登录状态")
            my_pending.click()
            print("✅切换到【我的待处理】")
            time.sleep(5)
            has_processed = process_workorder_list(driver, wait, workorder_timer)
            if has_processed:
                print("🔔本次循环成功处理工单，继续下一轮循环")
                continue
            else:
                random_sleep_sec = random.randint(30, 420)
                print(f"⚠【我的待处理】无满足条件工单，随机等待 {random_sleep_sec} 秒后继续轮询")
                time.sleep(random_sleep_sec)
    except Exception as e:
        print(f"主循环异常：{e}")
        import traceback
        print(traceback.format_exc())
        # 保存现场证据，便于定位崩溃原因
        try:
            driver.save_screenshot(r'D:\python project\first\crash_screen.png')
            with open(r'D:\python project\first\crash_dump.html', 'w', encoding='utf-8') as f:
                f.write(driver.execute_script("return document.body.innerHTML"))
            print("📄崩溃现场已导出: D:\\python project\\first\\crash_screen.png / crash_dump.html")
        except Exception:
            pass
        try:
            driver.quit()
        except Exception:
            pass
        print("程序异常，10秒后自动重启（请准备再次输入谷歌验证码）...")
        time.sleep(10)
        try:
            # 带 -X utf8 重启，避免Windows控制台中文编码问题
            os.execv(sys.executable, [sys.executable, '-X', 'utf8'] + sys.argv[1:])
        except Exception:
            pass

if __name__ == "__main__":
    main()
