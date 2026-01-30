import tkinter as tk
import random
import time
import sys

# 50条温柔祈愿语气提示语（移除“希望你”，保留核心语义）
TIPS = (
    "开心一点✨", "好好吃饭", "别熬夜啦",
    "多喝温水", "慢慢来不急", "笑口常开",
    "别太累咯", "记得添衣", "早点休息",
    "永远很棒", "吃点甜的", "别生气啦",
    "歇会儿再忙", "抬头看云", "出门带伞",
    "睡个好觉", "善待自己", "别想太多",
    "别急慢慢来", "多走动走", "吃热乎饭",
    "别委屈自己", "放轻松点", "记得喝水",
    "抱抱自己", "别硬撑呀", "今天超棒",
    "随手存档", "慢慢吃饭", "记得吃水果",
    "伸个懒腰", "按时洗头", "换双干净袜",
    "整理桌面", "常联系爸妈", "开窗透气",
    "调小音量", "放下手机", "享受发呆",
    "喝口快乐水", "系紧鞋带", "别丢东西",
    "心情放晴", "胃口好好", "步子慢些",
    "别皱眉头", "晒晒阳光", "看好钱包",
    "收好钥匙", "别贪凉哦"
)

# 柔和日常背景色
COLORS = (
    "lightpink", "skyblue", "lightgreen", "lavender",
    "lightyellow", "plum", "coral", "bisque", "aquamarine"
)

# 全局存储所有弹窗（防止被回收）
all_popups = []
# 目标弹窗数（固定50个）
TARGET_COUNT =100

def create_single_popup(popup_id):
    """创建单个弹窗（默认尺寸+快速弹出）"""
    # 1. 创建窗口并加入全局列表
    win = tk.Tk()
    all_popups.append(win)

    # 2. 还原默认尺寸：200宽 × 70高
    win_width = 200
    win_height = 70

    # 3. 精准屏幕适配（预留20px边距）
    screen_w = win.winfo_screenwidth()
    screen_h = win.winfo_screenheight()
    x = random.randint(20, screen_w - win_width - 20)
    y = random.randint(20, screen_h - win_height - 20)

    # 4. 窗口核心设置
    win.geometry(f"{win_width}x{win_height}+{x}+{y}")
    win.resizable(False, False)
    win.title("温柔小提醒")
    win.attributes("-topmost", True)    # 置顶显示
    win.attributes("-alpha", 0.95)      # 轻微透明

    # 5. 文字配置（无“希望你”，保留祈愿语气）
    tip = random.choice(TIPS)
    bg_color = random.choice(COLORS)
    label = tk.Label(
        win, text=tip, bg=bg_color,
        font=("微软雅黑", 12, "normal"),
        wraplength=180,
        justify="center",
        padx=10, pady=10,
        fg="#333333"
    )
    label.pack(fill="both", expand=True)

    # 6. 强制刷新（确保立即显示）
    win.update_idletasks()
    win.update()

    # 7. 打印进度
    print(f"✅ 已弹出弹窗 {popup_id}/{TARGET_COUNT}", end="\r")

def start_all_popups():
    """快速串行创建50个弹窗（0.1秒/个，100%稳定）"""
    # 缩短间隔至0.1秒，加快弹出速度
    for i in range(TARGET_COUNT):
        create_single_popup(i + 1)
        time.sleep(0.1)

    # 全部完成提示
    print(f"\n🎉 全部{TARGET_COUNT}个弹窗已100%弹出！")
    print("✨ 愿这些温柔的小提醒，能给你带来温暖 ✨")

if __name__ == "__main__":
    # 初始化tk主窗口（隐藏）
    root = tk.Tk()
    root.withdraw()

    # 启动弹窗创建
    start_all_popups()

    # 维持运行
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\n🛑 程序已手动终止")
        root.quit()
        sys.exit(0)