import pygame
import math
import random
import sys

pygame.init()
pygame.mixer.init()

sound_shoot     = pygame.mixer.Sound("assets/shoot.wav")
sound_hit       = pygame.mixer.Sound("assets/hit.wav")
sound_explosion = pygame.mixer.Sound("assets/explosion.wav")
sound_levelup   = pygame.mixer.Sound("assets/levelup.wav")
sound_xp        = pygame.mixer.Sound("assets/xp.wav")
sound_shoot.set_volume(0.3)
sound_hit.set_volume(0.4)
sound_explosion.set_volume(0.5)
sound_levelup.set_volume(0.6)
sound_xp.set_volume(0.4)

W, H = 1024, 768
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("SURVIVOR GAME")
clock = pygame.time.Clock()

font_huge  = pygame.font.SysFont("consolas", 80, bold=True)
font_big   = pygame.font.SysFont("consolas", 40, bold=True)
font_med   = pygame.font.SysFont("consolas", 28, bold=True)
font_small = pygame.font.SysFont("consolas", 20)

C_BG        = (10,  12,  20)
C_GRID      = (20,  25,  40)
C_PLAYER    = (100, 220, 255)
C_PLAYER_HL = (200, 240, 255)
C_BULLET    = (255, 240,  80)
C_ENEMY_1   = (220,  60,  60)
C_ENEMY_2   = (220, 120,  40)
C_ENEMY_3   = (180,  40, 220)
C_XP        = ( 80, 255, 140)
C_WHITE     = (255, 255, 255)
C_GREY      = (140, 150, 170)
C_HP_RED    = (220,  50,  50)
C_HP_GREEN  = ( 60, 220, 100)
C_GOLD      = (255, 200,  40)
C_DARK      = ( 15,  18,  30)

ENEMY_COLORS = [C_ENEMY_1, C_ENEMY_2, C_ENEMY_3]

class Particle:
    def __init__(self, x, y, color, vx, vy, life=40, size=4):
        self.x, self.y = x, y
        self.color = color
        self.vx, self.vy = vx, vy
        self.life = self.max_life = life
        self.size = size

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.15
        self.vx *= 0.96
        self.life -= 1

    def draw(self, surf):
        alpha = self.life / self.max_life
        r = max(1, int(self.size * alpha))
        col = tuple(int(c * alpha) for c in self.color)
        pygame.draw.circle(surf, col, (int(self.x), int(self.y)), r)

particles: list[Particle] = []

def spawn_particles(x, y, color, n=12, speed=3, life=40, size=4):
    for _ in range(n):
        angle = random.uniform(0, 2 * math.pi)
        v = random.uniform(0.5, speed)
        particles.append(Particle(x, y, color, math.cos(angle)*v, math.sin(angle)*v, life, size))

class Bullet:
    def __init__(self, x, y, dx, dy, dmg=20, color=C_BULLET, size=5, speed=12):
        self.x, self.y = float(x), float(y)
        length = math.hypot(dx, dy) or 1
        self.vx = dx / length * speed
        self.vy = dy / length * speed
        self.dmg   = dmg
        self.color = color
        self.size  = size
        self.alive = True
        self.trail: list[tuple] = []
        self.pierce = 1

    def update(self):
        self.trail.append((int(self.x), int(self.y)))
        if len(self.trail) > 6:
            self.trail.pop(0)
        self.x += self.vx
        self.y += self.vy
        if not (-50 < self.x < W+50 and -50 < self.y < H+50):
            self.alive = False

    def draw(self, surf):
        for i, pos in enumerate(self.trail):
            alpha = (i + 1) / len(self.trail)
            col = tuple(int(c * alpha) for c in self.color)
            r = max(1, int(self.size * alpha * 0.7))
            pygame.draw.circle(surf, col, pos, r)
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), self.size)

class XP:
    def __init__(self, x, y, value=10):
        self.x, self.y = float(x), float(y)
        self.value = value
        self.alive = True
        self.bob = random.uniform(0, math.pi * 2)
        self.radius = 6 + value // 10

    def draw(self, surf, tick):
        bob_y = math.sin(tick * 0.05 + self.bob) * 3
        cx, cy = int(self.x), int(self.y + bob_y)
        glow = max(0, int(60 + 40 * math.sin(tick * 0.08 + self.bob)))
        glow_col = (0, glow, int(glow * 0.6))
        pygame.draw.circle(surf, glow_col, (cx, cy), self.radius + 5)
        pygame.draw.circle(surf, C_XP, (cx, cy), self.radius)
        pygame.draw.circle(surf, C_WHITE, (cx, cy), self.radius // 2)

class Enemy:
    def __init__(self, x, y, kind=0):
        self.x, self.y = float(x), float(y)
        self.kind = kind
        self.alive = True
        self.tick  = random.randint(0, 60)
        configs = [
            dict(hp=40,  speed=1.2, size=14, dmg=8,  xp=10, color=C_ENEMY_1),
            dict(hp=100, speed=0.7, size=22, dmg=18, xp=25, color=C_ENEMY_2),
            dict(hp=20,  speed=2.2, size=10, dmg=5,  xp=8,  color=C_ENEMY_3),
        ]
        cfg = configs[kind % len(configs)]
        self.hp    = self.max_hp = cfg["hp"]
        self.speed = cfg["speed"]
        self.size  = cfg["size"]
        self.dmg   = cfg["dmg"]
        self.xp    = cfg["xp"]
        self.color = cfg["color"]
        self.flash = 0

    def move_toward(self, px, py):
        dx, dy = px - self.x, py - self.y
        d = math.hypot(dx, dy) or 1
        self.x += dx / d * self.speed
        self.y += dy / d * self.speed
        self.tick += 1

    def hit(self, dmg):
        self.hp -= dmg
        self.flash = 8
        if self.hp <= 0:
            self.alive = False
            return True
        return False

    def draw(self, surf):
        col = C_WHITE if self.flash > 0 else self.color
        if self.flash > 0:
            self.flash -= 1
        wiggle_x = math.sin(self.tick * 0.18) * 2
        cx, cy = int(self.x + wiggle_x), int(self.y)
        pygame.draw.circle(surf, col, (cx, cy), self.size)
        pygame.draw.circle(surf, (30, 30, 30), (cx, cy), self.size, 2)
        eye_off = self.size // 3
        pygame.draw.circle(surf, C_WHITE, (cx - eye_off, cy - eye_off//2), 3)
        pygame.draw.circle(surf, C_WHITE, (cx + eye_off, cy - eye_off//2), 3)
        pygame.draw.circle(surf, (20, 20, 20), (cx - eye_off, cy - eye_off//2), 1)
        pygame.draw.circle(surf, (20, 20, 20), (cx + eye_off, cy - eye_off//2), 1)
        bar_w = self.size * 2
        bar_h = 4
        bx, by = cx - self.size, cy - self.size - 10
        pygame.draw.rect(surf, (60, 20, 20), (bx, by, bar_w, bar_h))
        fill = int(bar_w * self.hp / self.max_hp)
        pygame.draw.rect(surf, C_HP_GREEN, (bx, by, fill, bar_h))

class Player:
    def __init__(self):
        self.x, self.y = W // 2, H // 2
        self.hp = self.max_hp = 100
        self.speed = 3.5
        self.size  = 16
        self.alive = True
        self.iframes = 0
        self.shoot_cd = 0
        self.shoot_rate = 25      
        self.bullet_dmg   = 20
        self.bullet_speed = 12
        self.bullet_count = 1      
        self.xp  = 0
        self.xp_to_level = 50
        self.regen_rate = 0       
        self.regen_cd = 0  
        self.level = 1
        self.kills = 0
        self.score = 0
        self.angle = 0
        self.orbit_bullets = []

    def move(self, keys):
        dx = dy = 0
        if keys[pygame.K_w] or keys[pygame.K_UP]:    dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:  dy += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:  dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx += 1
        if dx or dy:
            d = math.hypot(dx, dy)
            self.x = max(self.size, min(W - self.size, self.x + dx/d*self.speed))
            self.y = max(self.size, min(H - self.size, self.y + dy/d*self.speed))
            self.angle = math.atan2(dy, dx)

    def take_damage(self, dmg):
        if self.iframes > 0:
            return
        self.hp -= dmg
        self.iframes = 45
        spawn_particles(self.x, self.y, C_HP_RED, 10, 3)
        if self.hp <= 0:
            self.alive = False

    def gain_xp(self, amount):
        self.xp += amount
        if self.xp >= self.xp_to_level:
            self.xp -= self.xp_to_level
            self.xp_to_level = int(self.xp_to_level * 1.4)
            self.level += 1
            return True  
        return False

    def draw(self, surf, tick):
        if self.iframes > 0 and (tick // 4) % 2 == 0:
            return
        glow_r = self.size + 8 + int(3 * math.sin(tick * 0.1))
        pygame.draw.circle(surf, (20, 60, 90), (int(self.x), int(self.y)), glow_r)
        pygame.draw.circle(surf, C_PLAYER, (int(self.x), int(self.y)), self.size)
        pygame.draw.circle(surf, C_PLAYER_HL, (int(self.x), int(self.y)), self.size - 4)
        ex = self.x + math.cos(self.angle) * (self.size + 8)
        ey = self.y + math.sin(self.angle) * (self.size + 8)
        pygame.draw.line(surf, C_WHITE, (int(self.x), int(self.y)), (int(ex), int(ey)), 4)

UPGRADES = [
    {"name": "⚡ Speed Boost",     "desc": "Move faster",             "key": "speed"},
    {"name": "🔫 Rapid Fire",      "desc": "Shoot faster",            "key": "firerate"},
    {"name": "💥 Power Shot",      "desc": "+20 bullet damage",       "key": "damage"},
    {"name": "❤️  Vitality",       "desc": "+30 max HP & heal",       "key": "hp"},
    {"name": "🎯 Multishot",       "desc": "Fire one extra bullet",   "key": "multi"},
    {"name": "💚 Regeneration",    "desc": "Heal every second",       "key": "regen"},
    {"name": "🗡 Piercing Shot",    "desc": "Bullet piercing enemy",   "key": "pierce"},
]

def pick_upgrades():
    return random.sample(UPGRADES, min(3, len(UPGRADES)))

def apply_upgrade(player, key):
    if key == "speed":
        player.speed    += 0.5
    elif key == "firerate":
        player.shoot_rate = max(8, player.shoot_rate - 4)
    elif key == "damage":
        player.bullet_dmg += 20
    elif key == "hp":
        player.max_hp += 30
        player.hp = min(player.max_hp, player.hp + 30)
    elif key == "multi":
        player.bullet_count += 1
    elif key == "regen":
        player.regen_rate += 2
    elif key == "pierce":
        player.bullet_count += 0  
        player.pierce = getattr(player, "pierce", 1) + 1

def draw_bar(surf, x, y, w, h, val, mx, fg, bg=(40,20,20), label=""):
    pygame.draw.rect(surf, bg, (x, y, w, h), border_radius=4)
    fill = int(w * val / mx)
    if fill > 0:
        pygame.draw.rect(surf, fg, (x, y, fill, h), border_radius=4)
    pygame.draw.rect(surf, C_GREY, (x, y, w, h), 1, border_radius=4)
    if label:
        txt = font_small.render(label, True, C_WHITE)
        surf.blit(txt, (x + 4, y + h//2 - txt.get_height()//2))

def draw_hud(surf, player, wave, tick, enemy_count):
    draw_bar(surf, 16, 16, 220, 22, player.hp, player.max_hp, C_HP_GREEN, label=f"HP  {player.hp}/{player.max_hp}")
    draw_bar(surf, 16, 44, 220, 14, player.xp, player.xp_to_level, C_XP, bg=(10,30,20), label=f"LV{player.level}")
    wave_txt  = font_med.render(f"WAVE {wave}", True, C_GOLD)
    score_txt = font_small.render(f"Score: {player.score}   Kills: {player.kills}", True, C_GREY)
    surf.blit(wave_txt,  (W // 2 - wave_txt.get_width() // 2, 10))
    surf.blit(score_txt, (W // 2 - score_txt.get_width() // 2, 44))
    ec = font_small.render(f"Enemies: {enemy_count}", True, C_GREY)
    surf.blit(ec, (W - ec.get_width() - 16, 16))

def draw_grid(surf, tick):
    surf.fill(C_BG)
    offset = tick % 40
    for x in range(-40, W + 40, 40):
        pygame.draw.line(surf, C_GRID, (x + offset, 0), (x + offset, H))
    for y in range(-40, H + 40, 40):
        pygame.draw.line(surf, C_GRID, (0, y + offset), (W, y + offset))

def spawn_enemy(wave):
    side = random.randint(0, 3)
    if side == 0:
        x, y = random.randint(0, W), -30
    elif side == 1:
        x, y = W + 30, random.randint(0, H)
    elif side == 2:
        x, y = random.randint(0, W), H + 30
    else:
        x, y = -30, random.randint(0, H)
    max_kind = min(2, wave // 3)
    kind = random.randint(0, max_kind)
    return Enemy(x, y, kind)

def draw_menu(surf, tick):
    draw_grid(surf, tick)
    title = font_huge.render("SURVIVOR", True, C_PLAYER)
    shadow = font_huge.render("SURVIVOR", True, (20, 80, 120))
    surf.blit(shadow, (W//2 - title.get_width()//2 + 4, H//2 - 160 + 4))
    surf.blit(title,  (W//2 - title.get_width()//2,     H//2 - 160))
    sub   = font_med.render("Bertahan Hiduplah dari Serangan Musuh!", True, C_GREY)
    start = font_big.render("[ PRESS ENTER TO START ]", True, C_GOLD if (tick // 30) % 2 == 0 else C_GREY)
    ctrl  = font_small.render("WASD for Move   |   Auto-aim & Auto-fire", True, C_GREY)
    surf.blit(sub,   (W//2 - sub.get_width()//2,   H//2 - 80))
    surf.blit(start, (W//2 - start.get_width()//2, H//2 + 10))
    surf.blit(ctrl,  (W//2 - ctrl.get_width()//2,  H//2 + 80))

def draw_levelup(surf, choices):
    overlay = pygame.Surface((W, H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    surf.blit(overlay, (0, 0))
    title = font_big.render("⬆  LEVEL UP  ⬆", True, C_GOLD)
    surf.blit(title, (W//2 - title.get_width()//2, 180))
    sub = font_small.render("Choose an upgrade:", True, C_GREY)
    surf.blit(sub, (W//2 - sub.get_width()//2, 230))
    bw, bh = 340, 90
    total_w = bw * len(choices) + 30 * (len(choices) - 1)
    start_x = W//2 - total_w // 2
    for i, ch in enumerate(choices):
        bx = start_x + i * (bw + 30)
        by = H // 2 - bh // 2
        pygame.draw.rect(surf, (20, 40, 70), (bx, by, bw, bh), border_radius=10)
        pygame.draw.rect(surf, C_GOLD, (bx, by, bw, bh), 2, border_radius=10)
        key_lbl = font_small.render(f"[{i+1}]", True, C_GOLD)
        name_lbl = font_med.render(ch["name"], True, C_WHITE)
        desc_lbl = font_small.render(ch["desc"], True, C_GREY)
        surf.blit(key_lbl,  (bx + 14, by + 10))
        surf.blit(name_lbl, (bx + bw//2 - name_lbl.get_width()//2, by + 28))
        surf.blit(desc_lbl, (bx + bw//2 - desc_lbl.get_width()//2, by + 60))

def draw_gameover(surf, player, wave, tick):
    draw_grid(surf, tick)
    over  = font_huge.render("GAME OVER", True, C_HP_RED)
    surf.blit(over, (W//2 - over.get_width()//2, H//2 - 160))
    lines = [
        f"Wave reached : {wave}",
        f"Level        : {player.level}",
        f"Kills        : {player.kills}",
        f"Score        : {player.score}",
    ]
    for i, ln in enumerate(lines):
        t = font_med.render(ln, True, C_WHITE)
        surf.blit(t, (W//2 - t.get_width()//2, H//2 - 60 + i * 40))
    restart = font_med.render("[ ENTER ] Play Again    [ ESC ] Quit", True, C_GOLD if (tick // 30) % 2 == 0 else C_GREY)
    surf.blit(restart, (W//2 - restart.get_width()//2, H//2 + 120))

def game_loop():
    player   = Player()
    bullets: list[Bullet] = []
    enemies: list[Enemy]  = []
    xp_orbs: list[XP] = []

    tick  = 0
    wave  = 1
    wave_timer   = 0
    wave_interval = 420         
    enemies_per_wave = 6

    levelup_mode   = False
    levelup_choices: list[dict] = []

    while True:
        dt = clock.tick(60)
        tick += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if levelup_mode:
                    idx = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2}.get(event.key)
                    if idx is not None and idx < len(levelup_choices):
                        apply_upgrade(player, levelup_choices[idx]["key"])
                        spawn_particles(player.x, player.y, C_GOLD, 20, 5)
                        levelup_mode = False
                else:
                    if event.key == pygame.K_ESCAPE:
                        return "menu"

        if levelup_mode:
            draw_grid(screen, tick)
            for e in enemies:  e.draw(screen)
            for o in xp_orbs:  o.draw(screen, tick)
            for b in bullets:  b.draw(screen)
            player.draw(screen, tick)
            draw_hud(screen, player, wave, tick, len(enemies))
            draw_levelup(screen, levelup_choices)
            pygame.display.flip()
            continue

        keys = pygame.key.get_pressed()
        player.move(keys)

        player.shoot_cd -= 1
        if player.shoot_cd <= 0 and enemies:
            nearest = min(enemies, key=lambda e: math.hypot(e.x-player.x, e.y-player.y))
            dx = nearest.x - player.x
            dy = nearest.y - player.y
            player.angle = math.atan2(dy, dx)
            spread = 0.18
            for i in range(player.bullet_count):
                offset = (i - (player.bullet_count - 1) / 2) * spread
                a = player.angle + offset
                b = Bullet(player.x, player.y,
                            math.cos(a), math.sin(a),
                            dmg=player.bullet_dmg,
                            speed=player.bullet_speed)

                b.pierce = getattr(player, "pierce", 1)
                bullets.append(b)
                sound_shoot.play()
            player.shoot_cd = player.shoot_rate

        wave_timer += 1
        if wave_timer >= wave_interval:
            wave_timer = 0
            wave += 1
            count = enemies_per_wave + wave * 2
            for _ in range(count):
                enemies.append(spawn_enemy(wave))

        for e in enemies:
            e.move_toward(player.x, player.y)
            if math.hypot(e.x - player.x, e.y - player.y) < e.size + player.size:
                player.take_damage(e.dmg)

        for b in bullets:
            b.update()
            if not b.alive:
                continue
            for e in enemies:
                if not e.alive:
                    continue
                if math.hypot(b.x - e.x, b.y - e.y) < b.size + e.size:
                    killed = e.hit(b.dmg)
                    sound_hit.play()
                    b.pierce -= 1
                    if b.pierce <= 0:
                        b.alive = False
                    spawn_particles(b.x, b.y, e.color, 8, 2.5, 25, 3)
                    if killed:
                        player.kills += 1
                        player.hp = min(player.max_hp, player.hp + 3)
                        player.score += e.xp * wave
                        sound_explosion.play()
                        spawn_particles(e.x, e.y, e.color, 18, 3.5)
                        xp_orbs.append(XP(e.x, e.y, e.xp))
                    break

        for ob in player.orbit_bullets:
            for e in enemies:
                if not e.alive:
                    continue

                if math.hypot(ob.x - e.x, ob.y - e.y) < ob.size + e.size:
                    killed = e.hit(ob.dmg)
                    sound_hit.play()

                    spawn_particles(ob.x, ob.y, e.color, 6, 2)

                    if killed:
                        player.kills += 1
                        player.score += e.xp * wave
                        sound_explosion.play()
                        spawn_particles(e.x, e.y, e.color, 15, 3)
                        xp_orbs.append(XP(e.x, e.y, e.xp))

        for o in xp_orbs:
            if math.hypot(o.x - player.x, o.y - player.y) < 30:
                o.alive = False
                sound_xp.play()
                levelled = player.gain_xp(o.value)
                if levelled:
                    levelup_mode = True
                    sound_levelup.play()
                    levelup_choices = pick_upgrades()
                    spawn_particles(player.x, player.y, C_GOLD, 30, 4)

        bullets   = [b for b in bullets   if b.alive]
        enemies   = [e for e in enemies   if e.alive]
        xp_orbs   = [o for o in xp_orbs   if o.alive]
        for p in particles: p.update()
        particles[:] = [p for p in particles if p.life > 0]

        if player.iframes > 0:
            player.iframes -= 1

        if player.regen_rate > 0:
            player.regen_cd -= 1
            if player.regen_cd <= 0:
                player.hp = min(player.max_hp, player.hp + player.regen_rate)
                player.regen_cd = 60

        if not player.alive:
            return ("gameover", player, wave)

        draw_grid(screen, tick)
        for o in xp_orbs:  o.draw(screen, tick)
        for ob in player.orbit_bullets:  ob.draw(screen)
        for e in enemies:  e.draw(screen)
        for b in bullets:  b.draw(screen)
        for p in particles: p.draw(screen)
        player.draw(screen, tick)
        draw_hud(screen, player, wave, tick, len(enemies))
        pygame.display.flip()

def main():
    tick = 0
    state = "menu"
    gameover_data = None

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if state == "menu" and event.key == pygame.K_RETURN:
                    state = "game"
                elif state == "gameover":
                    if event.key == pygame.K_RETURN:
                        state = "game"
                    elif event.key == pygame.K_ESCAPE:
                        state = "menu"

        if state == "menu":
            draw_menu(screen, tick)
            pygame.display.flip()
            clock.tick(60)
            tick += 1

        elif state == "game":
            result = game_loop()
            if result == "menu":
                state = "menu"
                tick = 0
            elif isinstance(result, tuple) and result[0] == "gameover":
                _, player, wave = result
                gameover_data = (player, wave)
                state = "gameover"
                tick = 0

        elif state == "gameover":
            player, wave = gameover_data
            draw_gameover(screen, player, wave, tick)
            pygame.display.flip()
            clock.tick(60)
            tick += 1

if __name__ == "__main__":
    main()