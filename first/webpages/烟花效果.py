import pygame
import random
import math

# 初始化pygame
pygame.init()

# 设置窗口参数
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("原谅帽 + 烟花背景")
clock = pygame.time.Clock()

# 定义颜色列表（烟花配色）
COLORS = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

# ---------------------- 加载原谅帽图片 ----------------------
# 图片路径（注意：Windows路径用双反斜杠或原始字符串）
HAT_IMAGE_PATH = r"C:\1.png"  # r前缀避免转义，等价于 "C:\\1.png"
try:
    # 加载图片并缩放（适配窗口大小，可调整缩放比例）
    hat_img = pygame.image.load(HAT_IMAGE_PATH).convert_alpha()  # 保留透明通道
    # 缩放帽子尺寸（宽高可自定义，示例：缩放到200x200）
    hat_img = pygame.transform.scale(hat_img, (200, 200))
    # 获取帽子图片的矩形区域（用于居中显示）
    hat_rect = hat_img.get_rect(center=(WIDTH//2, HEIGHT//2))
except Exception as e:
    # 图片加载失败时的容错提示
    print(f"加载帽子图片失败：{e}")
    print("请检查图片路径是否正确（C:\\1.png），或图片是否存在")
    pygame.quit()
    exit()

# ---------------------- 烟花类（保留原有逻辑） ----------------------
class Firework:
    def __init__(self):
        self.x = random.randint(0, WIDTH)
        self.y = HEIGHT
        self.color = random.choice(COLORS)
        self.exploded = False
        self.particles = []
        self.speed = random.randint(8, 12)  # 烟花上升速度

    def explode(self):
        if not self.exploded:
            num_particles = random.randint(50, 100)
            for _ in range(num_particles):
                angle = random.uniform(0, 2 * math.pi)
                speed = random.uniform(2, 5)
                self.particles.append(Particle(self.x, self.y, self.color, angle, speed))
            self.exploded = True

    def update(self):
        if not self.exploded:
            self.y -= self.speed
            if self.y < HEIGHT / 2:
                self.explode()
        else:
            for particle in self.particles:
                particle.update()

class Particle:
    def __init__(self, x, y, color, angle, speed):
        self.x = x
        self.y = y
        self.color = color
        self.angle = angle
        self.speed = speed
        self.lifetime = random.uniform(50, 100)

    def update(self):
        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed + 0.1  # 重力影响
        self.lifetime -= 1

# ---------------------- 主循环（整合烟花+帽子显示） ----------------------
fireworks = []
running = True
while running:
    # 1. 填充黑色背景（烟花更醒目）
    screen.fill((0, 0, 0))

    # 2. 处理退出事件
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # 3. 生成新烟花（保留原有频率）
    if random.random() < 0.05:
        fireworks.append(Firework())

    # 4. 更新并绘制所有烟花
    for firework in fireworks:
        firework.update()
        # 绘制未爆炸的烟花（上升的光点）
        if not firework.exploded:
            pygame.draw.circle(screen, firework.color, (int(firework.x), int(firework.y)), 5)
        # 绘制爆炸后的烟花粒子
        else:
            for particle in firework.particles:
                if particle.lifetime > 0:
                    pygame.draw.circle(screen, particle.color, (int(particle.x), int(particle.y)), 2)

    # 5. 绘制原谅帽（叠加在烟花上层）
    screen.blit(hat_img, hat_rect)  # 将帽子画在窗口正中央

    # 6. 刷新屏幕+控制帧率
    pygame.display.flip()
    clock.tick(60)

# 退出程序
pygame.quit()