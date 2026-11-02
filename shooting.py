"""종스크롤 슈팅 게임 (pygame)

조작법:
  방향키 / WASD : 이동
  Space / Z    : 발사 (누르고 있으면 연사)
  P            : 일시정지
  R            : 게임 오버 후 다시 시작
  ESC          : 종료

모든 그래픽과 효과음은 코드로 직접 만들므로 이미지/사운드 파일이 필요 없습니다.
아이템(P)을 먹을 때마다 총알 수가 2 → 4 → 8 → 16발로 늘어납니다.
"""

import math
from array import array
import random
import sys

import pygame

# ---------------------------------------------------------------- 설정
WIDTH, HEIGHT = 480, 720
FPS = 60
SCROLL_SPEED = 2
PLAYER_SPEED = 5
FIRE_DELAY = 8          # 프레임 단위 연사 간격
BOSS_EVERY = 2000       # 이 점수마다 보스 등장

BG_GRASS = (34, 90, 48)
BG_GRASS2 = (40, 104, 56)
RIVER = (40, 90, 160)
WHITE = (255, 255, 255)
YELLOW = (255, 220, 60)
RED = (230, 60, 60)
ORANGE = (255, 150, 40)
CYAN = (90, 220, 255)
GRAY = (130, 130, 140)


def load_font(size):
    """한글이 보이는 폰트를 우선 사용"""
    for name in ("malgungothic", "applegothic", "nanumgothic"):
        path = pygame.font.match_font(name)
        if path:
            return pygame.font.Font(path, size)
    return pygame.font.Font(None, size)


# ---------------------------------------------------------------- 효과음
class Sounds:
    """효과음을 코드로 합성 (사운드 장치가 없으면 소리 없이 진행)"""

    def __init__(self):
        self.enabled = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 512)
            self.rate, _, self.channels = pygame.mixer.get_init()
        except (pygame.error, TypeError):
            return
        self.enabled = True

        def noise(smooth):
            state = [0.0]

            def f():
                state[0] += smooth * (random.uniform(-1, 1) - state[0])
                return state[0]
            return f

        def square(freq, t):
            return 1.0 if math.sin(2 * math.pi * freq * t) > 0 else -1.0

        n1, n2, n3 = noise(0.3), noise(0.12), noise(0.2)
        notes = [523, 659, 784, 1047]
        self.sounds = {
            "shoot": self.make(0.07, lambda t, p: square(1400 - 700 * p, t) * 0.25 * (1 - p)),
            "explode": self.make(0.35, lambda t, p: n1() * 2.5 * (1 - p) ** 2),
            "big_explode": self.make(1.2, lambda t, p: n2() * 4.0 * (1 - p) ** 1.5),
            "hit": self.make(0.7, lambda t, p: (n3() * 2.5 + 0.5 * math.sin(2 * math.pi * (220 - 160 * p) * t)) * (1 - p) ** 1.5),
            "powerup": self.make(0.32, lambda t, p: math.sin(2 * math.pi * notes[min(3, int(p * 4))] * t) * 0.6),
            "warning": self.make(1.4, lambda t, p: square(880 if int(t * 6) % 2 == 0 else 660, t) * 0.3),
            "gameover": self.make(1.2, lambda t, p: math.sin(2 * math.pi * (440 - 330 * p) * t) * 0.6 * (1 - p)),
        }
        self.sounds["shoot"].set_volume(0.35)
        pygame.mixer.set_reserved(1)
        self.shot_channel = pygame.mixer.Channel(0)  # 연사음은 전용 채널에서 끊어 재생

    def make(self, duration, fn):
        buf = array("h")
        n = int(self.rate * duration)
        for i in range(n):
            v = max(-1.0, min(1.0, fn(i / self.rate, i / n)))
            buf.extend([int(v * 32767 * 0.6)] * self.channels)
        return pygame.mixer.Sound(buffer=buf.tobytes())

    def play(self, name):
        if not self.enabled:
            return
        if name == "shoot":
            self.shot_channel.play(self.sounds[name])
        else:
            self.sounds[name].play()


# ---------------------------------------------------------------- 배경
class Background:
    """세로로 끝없이 흐르는 지형 (풀밭 + 구불구불한 강)"""

    TILE = 40

    def __init__(self):
        self.offset = 0.0
        self.row_index = 0
        rows = HEIGHT // self.TILE + 2
        self.rows = [self.make_row() for _ in range(rows)]

    def make_row(self):
        self.row_index += 1
        center = WIDTH / 2 + math.sin(self.row_index * 0.12) * 140
        width = 70 + math.sin(self.row_index * 0.05) * 30
        trees = [random.randrange(0, WIDTH) for _ in range(random.randint(0, 2))]
        return center, width, trees

    def update(self):
        self.offset += SCROLL_SPEED
        if self.offset >= self.TILE:
            self.offset -= self.TILE
            self.rows.pop()
            self.rows.insert(0, self.make_row())

    def draw(self, surf):
        for i, (center, width, trees) in enumerate(self.rows):
            y = (i - 1) * self.TILE + self.offset
            color = BG_GRASS if (i + self.row_index) % 2 else BG_GRASS2
            pygame.draw.rect(surf, color, (0, y, WIDTH, self.TILE + 1))
            pygame.draw.rect(surf, RIVER, (center - width / 2, y, width, self.TILE + 1))
            for tx in trees:
                if abs(tx - center) > width / 2 + 12:
                    pygame.draw.circle(surf, (20, 60, 30), (tx, int(y + 20)), 9)


# ---------------------------------------------------------------- 오브젝트
class Bullet:
    def __init__(self, x, y, vx, vy, friendly, radius=4):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.friendly = friendly
        self.radius = radius
        self.alive = True

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if not (-20 < self.x < WIDTH + 20 and -20 < self.y < HEIGHT + 20):
            self.alive = False

    def draw(self, surf):
        if self.friendly:
            pygame.draw.rect(surf, YELLOW, (self.x - 2, self.y - 8, 4, 14))
        else:
            pygame.draw.circle(surf, RED, (int(self.x), int(self.y)), self.radius)
            pygame.draw.circle(surf, WHITE, (int(self.x), int(self.y)), self.radius - 2)


class Player:
    def __init__(self):
        self.x, self.y = WIDTH / 2, HEIGHT - 100
        self.radius = 10
        self.cooldown = 0
        self.power = 1
        self.invincible = 120

    def update(self, keys):
        dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
        dy = (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w])
        if dx and dy:
            dx *= 0.7071
            dy *= 0.7071
        self.x = max(30, min(WIDTH - 30, self.x + dx * PLAYER_SPEED))
        self.y = max(30, min(HEIGHT - 35, self.y + dy * PLAYER_SPEED))
        self.cooldown = max(0, self.cooldown - 1)
        self.invincible = max(0, self.invincible - 1)

    def shoot(self):
        if self.cooldown:
            return []
        self.cooldown = FIRE_DELAY
        count = self.shot_count()
        spread = {2: 0.0, 4: 0.35, 8: 0.7, 16: 1.1}[count]  # 전체 부채꼴 각도(라디안)
        shots = []
        for i in range(count):
            offset = i - (count - 1) / 2
            angle = offset * spread / (count - 1)
            x = self.x + offset * (12 if count == 2 else 3)
            shots.append(Bullet(x, self.y - 26, math.sin(angle) * 12, -math.cos(angle) * 12, True))
        return shots

    def shot_count(self):
        return 2 ** self.power  # 파워 1~4 → 2, 4, 8, 16발

    def draw(self, surf, frame):
        """대한항공 도장을 본뜬 여객기 (위에서 본 모습, 기수가 위쪽)"""
        if self.invincible and frame % 6 < 3:
            return
        x, y = self.x, self.y
        sky_blue = (120, 190, 232)
        silver = (205, 210, 220)
        navy = (25, 45, 95)

        # 엔진 배기 불꽃
        flame = 5 + (frame % 4) * 2
        for ex in (-14, 14):
            pygame.draw.polygon(surf, ORANGE, [(x + ex - 3, y + 11), (x + ex + 3, y + 11), (x + ex, y + 11 + flame)])
        # 주날개 (후퇴익)
        for s in (-1, 1):
            pygame.draw.polygon(surf, silver, [(x + 4 * s, y - 6), (x + 29 * s, y + 11),
                                               (x + 29 * s, y + 16), (x + 4 * s, y + 8)])
        # 날개 밑 엔진 2기
        for ex in (-14, 14):
            pygame.draw.rect(surf, (165, 170, 182), (x + ex - 3, y - 2, 6, 13), border_radius=2)
            pygame.draw.rect(surf, (60, 60, 70), (x + ex - 3, y - 2, 6, 3))
        # 수평 꼬리날개
        for s in (-1, 1):
            pygame.draw.polygon(surf, silver, [(x + 3 * s, y + 19), (x + 13 * s, y + 27),
                                               (x + 13 * s, y + 30), (x + 3 * s, y + 26)])
        # 동체 (하늘색 상부 도장)
        pygame.draw.ellipse(surf, sky_blue, (x - 6, y - 30, 12, 62))
        pygame.draw.line(surf, (235, 245, 252), (x, y - 20), (x, y + 26), 2)  # 은색 경계선 느낌
        # 조종석 창
        pygame.draw.polygon(surf, navy, [(x - 4, y - 23), (x + 4, y - 23), (x + 3, y - 20), (x - 3, y - 20)])
        # 꼬리 쪽 태극 문양 (단순화한 빨강/파랑 원)
        cx, cy, r = int(x), int(y + 14), 5
        pygame.draw.circle(surf, WHITE, (cx, cy), r + 1)
        pygame.draw.circle(surf, (205, 30, 50), (cx, cy), r, draw_top_left=True, draw_top_right=True)
        pygame.draw.circle(surf, (20, 70, 160), (cx, cy), r, draw_bottom_left=True, draw_bottom_right=True)
        pygame.draw.circle(surf, (205, 30, 50), (cx - 2, cy), 2)
        pygame.draw.circle(surf, (20, 70, 160), (cx + 2, cy), 2)


class Enemy:
    """kind: drone(직진), weaver(지그재그), gunner(조준 사격), turret(지상 포대)"""

    STATS = {
        "drone":  dict(hp=1, radius=14, score=100, color=(220, 80, 80)),
        "weaver": dict(hp=2, radius=14, score=150, color=(200, 90, 220)),
        "gunner": dict(hp=4, radius=18, score=300, color=(240, 160, 40)),
        "turret": dict(hp=3, radius=16, score=200, color=GRAY),
    }

    def __init__(self, kind, x, y):
        self.kind = kind
        s = self.STATS[kind]
        self.hp, self.radius, self.score, self.color = s["hp"], s["radius"], s["score"], s["color"]
        self.x, self.y = x, y
        self.base_x = x
        self.t = 0
        self.alive = True
        self.flash = 0
        self.fire_timer = random.randint(40, 100)

    def update(self, player, bullets):
        self.t += 1
        if self.kind == "drone":
            self.y += 4
        elif self.kind == "weaver":
            self.y += 2.5
            self.x = self.base_x + math.sin(self.t * 0.06) * 80
        elif self.kind == "gunner":
            self.y += 1.5 if self.y < 180 else 0.4
        elif self.kind == "turret":
            self.y += SCROLL_SPEED  # 지형과 함께 흘러감

        if self.kind in ("gunner", "turret") and self.y > 0:
            self.fire_timer -= 1
            if self.fire_timer <= 0:
                self.fire_timer = 90 if self.kind == "gunner" else 120
                angle = math.atan2(player.y - self.y, player.x - self.x)
                bullets.append(Bullet(self.x, self.y, math.cos(angle) * 4, math.sin(angle) * 4, False))

        self.flash = max(0, self.flash - 1)
        if self.y > HEIGHT + 40:
            self.alive = False

    def hit(self, dmg=1):
        self.hp -= dmg
        self.flash = 4
        if self.hp <= 0:
            self.alive = False
            return True
        return False

    def draw(self, surf):
        x, y, r = int(self.x), int(self.y), self.radius
        color = WHITE if self.flash else self.color
        if self.kind == "turret":
            pygame.draw.rect(surf, (70, 70, 80), (x - r, y - r, r * 2, r * 2))
            pygame.draw.circle(surf, color, (x, y), r - 4)
            pygame.draw.line(surf, (40, 40, 40), (x, y), (x, y + r + 4), 5)
        elif self.kind == "gunner":
            pygame.draw.polygon(surf, color, [(x - r, y - 8), (x + r, y - 8), (x + 8, y + r), (x - 8, y + r)])
            pygame.draw.circle(surf, (60, 30, 10), (x, y), 6)
        else:
            pygame.draw.polygon(surf, color, [(x, y + r), (x - r, y - r), (x, y - r // 2), (x + r, y - r)])


class Boss:
    def __init__(self, level):
        self.x, self.y = WIDTH / 2, -80
        self.radius = 50
        self.max_hp = 60 + level * 30
        self.hp = self.max_hp
        self.t = 0
        self.alive = True
        self.flash = 0
        self.score = 3000 + level * 1000
        self.level = level

    def update(self, player, bullets):
        self.t += 1
        if self.y < 130:
            self.y += 1.5
            return
        self.x = WIDTH / 2 + math.sin(self.t * 0.015) * 150
        # 원형 탄막
        if self.t % 70 == 0:
            n = 12 + self.level * 2
            for i in range(n):
                a = 2 * math.pi * i / n + self.t * 0.05
                bullets.append(Bullet(self.x, self.y, math.cos(a) * 3, math.sin(a) * 3, False, 5))
        # 조준 3연발
        if self.t % 45 == 20:
            base = math.atan2(player.y - self.y, player.x - self.x)
            for d in (-0.2, 0, 0.2):
                bullets.append(Bullet(self.x, self.y + 30, math.cos(base + d) * 5, math.sin(base + d) * 5, False))
        self.flash = max(0, self.flash - 1)

    def hit(self, dmg=1):
        if self.y < 130:
            return False  # 등장 중에는 무적
        self.hp -= dmg
        self.flash = 3
        if self.hp <= 0:
            self.alive = False
            return True
        return False

    def draw(self, surf):
        x, y = int(self.x), int(self.y)
        body = WHITE if self.flash else (110, 110, 150)
        pygame.draw.polygon(surf, (70, 70, 100), [(x - 90, y - 10), (x + 90, y - 10), (x + 60, y + 25), (x - 60, y + 25)])
        pygame.draw.circle(surf, body, (x, y), 50)
        pygame.draw.circle(surf, (60, 60, 90), (x, y), 34)
        core = RED if self.t % 20 < 10 else ORANGE
        pygame.draw.circle(surf, core, (x, y), 16)
        for side in (-70, 70):
            pygame.draw.circle(surf, body, (x + side, y + 5), 14)


class PowerUp:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.radius = 12
        self.alive = True
        self.t = 0

    def update(self):
        self.t += 1
        self.y += 1.5
        if self.y > HEIGHT + 20:
            self.alive = False

    def draw(self, surf, font):
        c = CYAN if self.t % 20 < 10 else WHITE
        pygame.draw.circle(surf, c, (int(self.x), int(self.y)), self.radius, 3)
        txt = font.render("P", True, c)
        surf.blit(txt, txt.get_rect(center=(self.x, self.y)))


class Explosion:
    def __init__(self, x, y, size=1.0):
        self.particles = []
        for _ in range(int(18 * size)):
            a = random.uniform(0, 2 * math.pi)
            sp = random.uniform(1, 5) * size
            self.particles.append([x, y, math.cos(a) * sp, math.sin(a) * sp, random.randint(20, 40)])
        self.alive = True

    def update(self):
        for p in self.particles:
            p[0] += p[2]
            p[1] += p[3]
            p[4] -= 1
        self.particles = [p for p in self.particles if p[4] > 0]
        self.alive = bool(self.particles)

    def draw(self, surf):
        for x, y, _, _, life in self.particles:
            color = YELLOW if life > 25 else ORANGE if life > 12 else RED
            pygame.draw.circle(surf, color, (int(x), int(y)), max(1, life // 8))


def collide(a, b):
    return (a.x - b.x) ** 2 + (a.y - b.y) ** 2 < (a.radius + b.radius) ** 2


# ---------------------------------------------------------------- 게임
class Game:
    def __init__(self):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        self.sfx = Sounds()
        pygame.display.set_caption("Sky Patrol - 종스크롤 슈팅")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = load_font(22)
        self.small = load_font(16)
        self.big = load_font(44)
        self.high_score = 0
        self.reset()

    def reset(self):
        self.bg = Background()
        self.player = Player()
        self.bullets = []
        self.enemies = []
        self.powerups = []
        self.explosions = []
        self.boss = None
        self.boss_level = 0
        self.next_boss = BOSS_EVERY
        self.score = 0
        self.lives = 3
        self.frame = 0
        self.spawn_timer = 60
        self.paused = False
        self.game_over = False
        self.message = ("STAGE START", 120)

    # ---- 적 생성
    def spawn(self):
        if self.boss:
            return
        self.spawn_timer -= 1
        if self.spawn_timer > 0:
            return
        difficulty = min(1.0, self.score / 15000)
        self.spawn_timer = int(70 - 40 * difficulty) + random.randint(0, 30)

        roll = random.random()
        if roll < 0.35:  # 드론 편대
            x = random.randint(40, WIDTH - 40)
            for i in range(random.randint(3, 5)):
                self.enemies.append(Enemy("drone", x, -30 - i * 40))
        elif roll < 0.6:
            x = random.randint(100, WIDTH - 100)
            for i in range(3):
                self.enemies.append(Enemy("weaver", x, -30 - i * 50))
        elif roll < 0.8:
            self.enemies.append(Enemy("gunner", random.randint(40, WIDTH - 40), -30))
        else:
            self.enemies.append(Enemy("turret", random.randint(30, WIDTH - 30), -30))

        if self.score >= self.next_boss:
            self.boss_level += 1
            self.next_boss += BOSS_EVERY + self.boss_level * 1000
            self.boss = Boss(self.boss_level)
            self.message = ("WARNING!  BOSS", 150)
            self.sfx.play("warning")

    # ---- 피격 처리
    def player_hit(self):
        if self.player.invincible:
            return
        self.explosions.append(Explosion(self.player.x, self.player.y, 1.5))
        self.lives -= 1
        self.sfx.play("hit")
        if self.lives <= 0:
            self.game_over = True
            self.sfx.play("gameover")
            self.high_score = max(self.high_score, self.score)
            return
        self.player = Player()  # 재출격 시 파워는 1로 초기화
        self.bullets = [b for b in self.bullets if b.friendly]

    def kill_enemy(self, e):
        self.score += e.score
        self.explosions.append(Explosion(e.x, e.y))
        self.sfx.play("explode")
        if random.random() < 0.08 or e.kind == "gunner" and random.random() < 0.3:
            self.powerups.append(PowerUp(e.x, e.y))

    def update(self):
        keys = pygame.key.get_pressed()
        self.frame += 1
        self.bg.update()

        if not self.game_over:
            self.player.update(keys)
            if keys[pygame.K_SPACE] or keys[pygame.K_z]:
                shots = self.player.shoot()
                if shots:
                    self.bullets += shots
                    self.sfx.play("shoot")
            self.spawn()

        for b in self.bullets:
            b.update()
        for e in self.enemies:
            e.update(self.player, self.bullets)
        if self.boss:
            self.boss.update(self.player, self.bullets)
        for p in self.powerups:
            p.update()
        for ex in self.explosions:
            ex.update()

        # 아군 탄 vs 적 / 보스
        for b in self.bullets:
            if not b.friendly or not b.alive:
                continue
            for e in self.enemies:
                if e.alive and collide(b, e):
                    b.alive = False
                    if e.hit():
                        self.kill_enemy(e)
                    break
            else:
                if self.boss and collide(b, self.boss):
                    b.alive = False
                    if self.boss.hit():
                        self.score += self.boss.score
                        self.sfx.play("big_explode")
                        for _ in range(5):
                            self.explosions.append(Explosion(
                                self.boss.x + random.randint(-60, 60),
                                self.boss.y + random.randint(-40, 40), 2.0))
                        self.powerups.append(PowerUp(self.boss.x, self.boss.y))
                        self.boss = None
                        self.bullets = [x for x in self.bullets if x.friendly]
                        self.message = ("BOSS CLEAR!", 120)

        # 적 / 적 탄 / 아이템 vs 플레이어
        if not self.game_over:
            pl = self.player
            for b in self.bullets:
                if not b.friendly and b.alive and collide(b, pl):
                    b.alive = False
                    self.player_hit()
                    break
            for e in self.enemies:
                if e.alive and e.kind != "turret" and collide(e, pl):
                    e.alive = False
                    self.explosions.append(Explosion(e.x, e.y))
                    self.player_hit()
                    break
            if self.boss and collide(self.boss, self.player):
                self.player_hit()
            for p in self.powerups:
                if p.alive and collide(p, self.player):
                    p.alive = False
                    self.sfx.play("powerup")
                    if self.player.power < 4:
                        self.player.power += 1
                    else:
                        self.score += 500

        self.bullets = [b for b in self.bullets if b.alive]
        self.enemies = [e for e in self.enemies if e.alive]
        self.powerups = [p for p in self.powerups if p.alive]
        self.explosions = [e for e in self.explosions if e.alive]

        if self.message:
            text, t = self.message
            self.message = (text, t - 1) if t > 1 else None

    # ---- 그리기
    def draw_text(self, text, font, color, center):
        img = font.render(text, True, color)
        shadow = font.render(text, True, (0, 0, 0))
        rect = img.get_rect(center=center)
        self.screen.blit(shadow, rect.move(2, 2))
        self.screen.blit(img, rect)

    def draw(self):
        s = self.screen
        self.bg.draw(s)
        # 지상 포대는 비행체 아래에 그림
        for e in self.enemies:
            if e.kind == "turret":
                e.draw(s)
        for p in self.powerups:
            p.draw(s, self.small)
        for e in self.enemies:
            if e.kind != "turret":
                e.draw(s)
        if self.boss:
            self.boss.draw(s)
        if not self.game_over:
            self.player.draw(s, self.frame)
        for b in self.bullets:
            b.draw(s)
        for ex in self.explosions:
            ex.draw(s)

        # HUD
        s.blit(self.font.render(f"SCORE {self.score:07d}", True, WHITE), (10, 8))
        s.blit(self.small.render(f"HI {max(self.high_score, self.score):07d}", True, WHITE), (10, 34))
        for i in range(self.lives):
            x = WIDTH - 24 - i * 22
            pygame.draw.polygon(s, WHITE, [(x, 12), (x - 8, 28), (x + 8, 28)])
        s.blit(self.small.render(f"SHOT x{self.player.shot_count()}", True, CYAN), (WIDTH - 90, 34))

        if self.boss:
            w = WIDTH - 40
            pygame.draw.rect(s, (60, 0, 0), (20, HEIGHT - 20, w, 8))
            pygame.draw.rect(s, RED, (20, HEIGHT - 20, w * self.boss.hp / self.boss.max_hp, 8))

        if self.message:
            self.draw_text(self.message[0], self.big, YELLOW, (WIDTH / 2, HEIGHT / 2 - 60))
        if self.paused:
            self.draw_text("일시정지 (P)", self.big, WHITE, (WIDTH / 2, HEIGHT / 2))
        if self.game_over:
            self.draw_text("GAME OVER", self.big, RED, (WIDTH / 2, HEIGHT / 2 - 20))
            self.draw_text("R: 다시 시작   ESC: 종료", self.font, WHITE, (WIDTH / 2, HEIGHT / 2 + 30))

        pygame.display.flip()

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return
                    if event.key == pygame.K_p and not self.game_over:
                        self.paused = not self.paused
                    if event.key == pygame.K_r and self.game_over:
                        self.reset()
            if not self.paused:
                self.update()
            self.draw()
            self.clock.tick(FPS)


if __name__ == "__main__":
    Game().run()
    pygame.quit()
    sys.exit()
