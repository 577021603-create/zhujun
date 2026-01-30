import pygame
import sys
import math
import random
import time

# ===================== 初始化配置 =====================
# 初始化pygame所有模块
pygame.init()
pygame.mixer.init()  # 初始化音频模块

# 窗口配置
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("浪漫爱心特效 | 自定义交互版")
clock = pygame.time.Clock()

# 颜色定义（RGB）
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
PINK = (255, 192, 203)
PURPLE = (138, 43, 226)
ORANGE = (255, 165, 0)
BLUE = (0, 191, 255)

# 全局变量
running = True
fps = 60  # 帧率
heart_list = []  # 存储爱心对象
particle_list = []  # 存储粒子对象
custom_text = "I ❤️ You"  # 自定义文字
text_size = 30  # 文字大小
text_color = WHITE  # 文字颜色
music_playing = False  # 背景音乐状态


# ===================== 粒子类（爱心周围特效） =====================
class Particle:
    def __init__(self, x, y):
        # 粒子初始位置（爱心中心偏移）
        self.x = x + random.randint(-30, 30)
        self.y = y + random.randint(-30, 30)
        # 粒子大小（随机）
        self.size = random.uniform(1, 3)
        # 粒子移动速度（随机方向）
        self.vx = random.uniform(-1, 1)
        self.vy = random.uniform(-1, 1)
        # 粒子颜色（渐变粉色系）
        self.color = (
            255,
            random.randint(150, 255),
            random.randint(180, 255)
        )
        # 粒子生命周期（帧数）
        self.life = random.randint(60, 120)
        self.alive = True

    def update(self):
        """更新粒子状态"""
        # 移动粒子
        self.x += self.vx
        self.y += self.vy
        # 生命周期减少
        self.life -= 1
        # 生命周期结束则标记为死亡
        if self.life <= 0:
            self.alive = False
        # 粒子慢慢变小
        self.size *= 0.98

    def draw(self):
        """绘制粒子"""
        if self.alive:
            pygame.draw.circle(
                screen,
                self.color,
                (int(self.x), int(self.y)),
                int(self.size)
            )


# ===================== 爱心类（核心交互对象） =====================
class Heart:
    def __init__(self, x, y):
        # 爱心初始位置
        self.x = x
        self.y = y
        # 爱心基础大小
        self.base_size = 12
        self.size = self.base_size
        # 跳动速度和方向
        self.speed = 0.3
        self.grow = True
        # 爱心颜色（渐变）
        self.color_r = 255
        self.color_g = 192
        self.color_b = 203
        self.color_speed = 1  # 颜色渐变速度
        # 鼠标交互相关
        self.is_hover = False  # 是否鼠标悬浮
        self.is_clicked = False  # 是否被点击
        # 振动效果（点击后）
        self.shake = False
        self.shake_angle = 0
        self.shake_speed = 5

    def update(self, mouse_pos):
        """更新爱心状态（包含交互）"""
        # 1. 爱心跳动逻辑
        if self.grow:
            self.size += self.speed
            if self.size >= self.base_size + 3:
                self.grow = False
        else:
            self.size -= self.speed
            if self.size <= self.base_size - 2:
                self.grow = True

        # 2. 颜色渐变（粉色→红色→粉色）
        self.color_g -= self.color_speed
        if self.color_g <= 100 or self.color_g >= 200:
            self.color_speed *= -1  # 反向渐变

        # 3. 鼠标悬浮检测
        dx = mouse_pos[0] - self.x
        dy = mouse_pos[1] - self.y
        distance = math.hypot(dx, dy)
        self.is_hover = distance < 50  # 50像素内为悬浮

        # 4. 点击振动效果
        if self.shake:
            self.shake_angle += self.shake_speed
            if self.shake_angle >= 360:
                self.shake = False
                self.shake_angle = 0

    def draw(self):
        """绘制爱心（包含旋转/振动效果）"""
        # 保存当前绘图状态
        pygame.save()

        # 振动效果（旋转）
        if self.shake:
            pygame.transform.rotate(screen, math.sin(math.radians(self.shake_angle)) * 2)

        # 计算爱心坐标点（基于笛卡尔心形公式）
        points = []
        for angle in range(0, 360):
            rad = math.radians(angle)
            x = self.size * 16 * (math.sin(rad)) ** 3
            y = self.size * (13 * math.cos(rad) - 5 * math.cos(2 * rad) - 2 * math.cos(3 * rad) - math.cos(4 * rad))
            points.append((self.x + x, self.y - y))

        # 绘制爱心（填充+描边）
        fill_color = (self.color_r, self.color_g, self.color_b)
        pygame.draw.polygon(screen, fill_color, points)
        pygame.draw.polygon(screen, RED, points, 2)  # 红色描边

        # 鼠标悬浮时添加光晕
        if self.is_hover:
            # 绘制半透明光晕
            halo_surface = pygame.Surface((100, 100), pygame.SRCALPHA)
            pygame.draw.circle(halo_surface, (255, 255, 255, 50), (50, 50), 40)
            screen.blit(halo_surface, (self.x - 50, self.y - 50))

        # 恢复绘图状态
        pygame.restore()

    def on_click(self):
        """点击爱心触发的效果"""
        self.shake = True  # 启动振动
        # 生成粒子特效
        for _ in range(20):
            particle = Particle(self.x, self.y)
            particle_list.append(particle)


# ===================== 工具函数 =====================
def play_background_music():
    """播放背景音乐（需提前准备mp3文件，也可注释掉）"""
    global music_playing
    if not music_playing:
        try:
            # 替换为你的背景音乐路径（可选，无则注释）
            # pygame.mixer.music.load("love_music.mp3")
            # pygame.mixer.music.set_volume(0.5)
            # pygame.mixer.music.play(-1)  # 循环播放
            music_playing = True
            print("背景音乐启动成功（若无声音请检查文件路径）")
        except:
            print("未找到背景音乐文件，跳过播放")


def draw_custom_text():
    """绘制自定义文字"""
    font = pygame.font.SysFont("Arial", text_size, bold=True)
    text_surface = font.render(custom_text, True, text_color)
    # 文字位置（爱心下方）
    text_rect = text_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 80))
    screen.blit(text_surface, text_rect)

    # 绘制文字阴影（增强视觉效果）
    shadow_surface = font.render(custom_text, True, (50, 50, 50))
    screen.blit(shadow_surface, (text_rect.x + 2, text_rect.y + 2))


def handle_events(heart):
    """处理所有事件（鼠标、键盘、关闭）"""
    global running, custom_text, text_size, text_color
    mouse_pos = pygame.mouse.get_pos()

    for event in pygame.event.get():
        # 关闭窗口
        if event.type == pygame.QUIT:
            running = False

        # 键盘事件
        elif event.type == pygame.KEYDOWN:
            # 退出程序
            if event.key == pygame.K_ESCAPE:
                running = False
            # 增大文字
            elif event.key == pygame.K_UP:
                text_size = min(text_size + 2, 50)
            # 减小文字
            elif event.key == pygame.K_DOWN:
                text_size = max(text_size - 2, 10)
            # 切换文字颜色
            elif event.key == pygame.K_c:
                color_list = [WHITE, PINK, RED, PURPLE, ORANGE, BLUE]
                current_idx = color_list.index(text_color)
                text_color = color_list[(current_idx + 1) % len(color_list)]
            # 自定义文字（按回车确认）
            elif event.key == pygame.K_RETURN:
                custom_text = input("请输入自定义文字：")

        # 鼠标点击事件
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # 左键点击
                if heart.is_hover:
                    heart.on_click()

    return mouse_pos


# ===================== 初始化核心对象 =====================
# 创建主爱心（屏幕中心）
main_heart = Heart(WIDTH // 2, HEIGHT // 2)
# 播放背景音乐（可选）
play_background_music()

# ===================== 主循环 =====================
print("程序启动成功！操作说明：")
print("1. 鼠标悬浮在爱心上：显示光晕")
print("2. 点击爱心：触发振动+粒子特效")
print("3. 按↑/↓键：调整文字大小")
print("4. 按C键：切换文字颜色")
print("5. 按回车：自定义文字")
print("6. 按ESC：退出程序")

while running:
    # 1. 清空屏幕（黑色背景）
    screen.fill(BLACK)

    # 2. 获取鼠标位置
    mouse_pos = handle_events(main_heart)

    # 3. 更新爱心状态
    main_heart.update(mouse_pos)

    # 4. 更新粒子（移除死亡粒子）
    for particle in particle_list[:]:
        particle.update()
        if not particle.alive:
            particle_list.remove(particle)

    # 5. 绘制所有元素
    # 绘制粒子
    for particle in particle_list:
        particle.draw()
    # 绘制爱心
    main_heart.draw()
    # 绘制文字
    draw_custom_text()

    # 6. 更新屏幕
    pygame.display.flip()

    # 7. 控制帧率
    clock.tick(fps)

# ===================== 程序结束 =====================
pygame.mixer.music.stop()
pygame.quit()
sys.exit()