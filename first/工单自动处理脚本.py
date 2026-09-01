from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
import time

# 配置信息
DRIVER_PATH = "D:\\python project\\chromedriver-win64\\chromedriver-win64\\chromedriver.exe"


def main():
    """主函数 - 百度填充测试"""
    driver = None
    try:
        print("=" * 60)
        print("工单自动处理脚本 - 百度填充测试")
        print("=" * 60)

        # 初始化浏览器选项
        print("\n[1] 正在启动浏览器...")
        options = webdriver.ChromeOptions()
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1920,1080")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        
        # 尝试使用自动ChromeDriver管理（Selenium 4.6+）
        try:
            print("  尝试使用自动ChromeDriver管理...")
            driver = webdriver.Chrome(options=options)
            print("  ✓ 自动ChromeDriver管理成功")
        except Exception as e:
            print(f"  自动管理失败: {str(e)}")
            print("  尝试使用手动指定的ChromeDriver...")
            
            # 检查手动指定的驱动是否存在
            import os
            if os.path.exists(DRIVER_PATH):
                service = Service(executable_path=DRIVER_PATH)
                driver = webdriver.Chrome(service=service, options=options)
                print(f"  ✓ 使用手动驱动: {DRIVER_PATH}")
            else:
                print("  ✗ 手动驱动也不存在，请安装匹配的ChromeDriver")
                return

        # 访问百度
        print("\n[2] 正在访问百度...")
        driver.get("https://www.baidu.com")
        time.sleep(3)
        
        current_url = driver.current_url
        print(f"  当前URL: {current_url}")
        print(f"  页面标题: {driver.title}")

        # 在百度搜索框输入内容
        print("\n[3] 正在搜索框输入内容...")
        
        # 方式1: 通过id查找搜索框
        try:
            search_box = driver.find_element(By.ID, "kw")
            print("  ✓ 通过ID找到搜索框 (id='kw')")
        except:
            # 方式2: 通过name查找
            search_box = driver.find_element(By.NAME, "wd")
            print("  ✓ 通过Name找到搜索框 (name='wd')")
        
        # 清空并输入
        search_box.clear()
        time.sleep(0.5)
        search_box.send_keys("工单自动处理")
        print("  ✓ 已输入: '工单自动处理'")
        time.sleep(1)

        # 点击搜索按钮
        print("\n[4] 正在点击搜索按钮...")
        search_button = driver.find_element(By.ID, "su")
        search_button.click()
        print("  ✓ 已点击搜索按钮")
        time.sleep(3)

        # 保存结果截图
        print("\n[5] 保存搜索结果截图...")
        driver.save_screenshot("baidu_search_result.png")
        print("  ✓ 截图已保存: baidu_search_result.png")

        # 等待用户查看
        print("\n" + "=" * 60)
        print("测试完成！")
        print("请查看：")
        print("  - 浏览器窗口中的搜索结果")
        print("  - 截图: baidu_search_result.png")
        print("=" * 60)
        
        print("\n按回车键关闭浏览器...")
        input()

    except Exception as e:
        print(f"\n✗ 发生错误: {str(e)}")
        if driver:
            driver.save_screenshot("search_error.png")
            print("错误截图已保存: search_error.png")
    finally:
        if driver:
            driver.quit()
            print("✓ 浏览器已关闭")


if __name__ == "__main__":
    main()
