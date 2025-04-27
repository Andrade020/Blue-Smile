import pygame
import sys
import math
import random

# --- Configurações de janela e resolução ---
pygame.init()
WIDTH, HEIGHT = 1920, 1080
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Asteroids com Disco de Acreção Relativístico (1920×1080)")
clock = pygame.time.Clock()
FPS = 60
CENTER = pygame.Vector2(WIDTH/2, HEIGHT/2)

# --- Constantes de Relatividade Especial ---
C = 800.0   # velocidade-limite (unidades/frame)

# --- Cores ---
WHITE   = (255, 255, 255)
GRAY    = (100, 100, 100)
YELLOW  = (255, 255,   0)
BH_INF  = ( 50,  50,  50)  # contorno da zona de influência
BH_KILL = (255,   0,   0)  # contorno da zona de captura
BLACK   = (  0,   0,   0)

# --- Geração procedural em setores de asteroides grandes ---
SECTOR_SIZE = 800
LOAD_RADIUS = 2
sectors = {}

def get_sector(pos):
    return (int(pos.x // SECTOR_SIZE), int(pos.y // SECTOR_SIZE))

def generate_sector(sx, sy):
    random.seed(sx * 73856093 ^ sy * 19349663)
    asts = []
    for _ in range(random.randint(5, 12)):
        x = sx * SECTOR_SIZE + random.uniform(0, SECTOR_SIZE)
        y = sy * SECTOR_SIZE + random.uniform(0, SECTOR_SIZE)
        asts.append(Asteroid(initial_pos=pygame.Vector2(x, y)))
    return asts

def update_sectors(ship_pos):
    csx, csy = get_sector(ship_pos)
    for dx in range(-LOAD_RADIUS, LOAD_RADIUS+1):
        for dy in range(-LOAD_RADIUS, LOAD_RADIUS+1):
            key = (csx+dx, csy+dy)
            if key not in sectors:
                sectors[key] = generate_sector(*key)
    for key in list(sectors):
        if abs(key[0]-csx)>LOAD_RADIUS or abs(key[1]-csy)>LOAD_RADIUS:
            del sectors[key]

# --- Classe Buraco Negro ---
class BlackHole:
    def __init__(self, pos, radius, gm, kill_factor=0.3):
        self.pos         = pygame.Vector2(pos)
        self.radius      = radius                  # zona de influência
        self.GM          = gm                      # constante G·massa
        self.kill_radius = radius * kill_factor    # zona de captura

    def attract(self, obj):
        r_vec = self.pos - obj.pos
        r = r_vec.length()
        if r <= self.kill_radius:
            obj.trapped = True
            return
        # atração newtoniana
        a = self.GM / (r*r)
        obj.vel += r_vec.normalize() * a

    def time_dilation(self, world_pos):
        r = (world_pos - self.pos).length()
        if r <= self.kill_radius:
            return 0.0
        if r <= self.radius:
            return math.sqrt(max(0.0, 1 - (self.radius / r)))
        return 1.0

    def draw(self, ship_pos):
        rel = self.pos - ship_pos + CENTER
        # contorno da zona de influência
        pygame.draw.circle(screen, BH_INF,
                           (int(rel.x), int(rel.y)),
                           int(self.radius), 1)
        # contorno da zona de captura
        pygame.draw.circle(screen, BH_KILL,
                           (int(rel.x), int(rel.y)),
                           int(self.kill_radius), 1)

# --- Classe Nave ---
class Ship:
    def __init__(self):
        self.pos      = pygame.Vector2(0,0)
        self.vel      = pygame.Vector2(0,0)
        self.angle    = 0
        self.thrust   = 0.2
        self.turn_spd = 5
        self.size     = 20
        self.trapped  = False

    def update(self, black_holes):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            self.angle += self.turn_spd
        if keys[pygame.K_RIGHT]:
            self.angle -= self.turn_spd
        if keys[pygame.K_UP]:
            rad     = math.radians(self.angle)
            impulso = pygame.Vector2(math.cos(rad), -math.sin(rad)) * self.thrust
            self.vel += impulso

        for bh in black_holes:
            bh.attract(self)

        if self.vel.length() > C:
            self.vel.scale_to_length(C)

        factor = min(bh.time_dilation(self.pos) for bh in black_holes)
        self.pos += self.vel * factor

    def draw(self):
        rad = math.radians(self.angle)
        dir_vec = pygame.Vector2(math.cos(rad), -math.sin(rad))
        p1 = CENTER + dir_vec * self.size
        p2 = CENTER + dir_vec.rotate(140) * self.size
        p3 = CENTER + dir_vec.rotate(-140) * self.size
        pygame.draw.polygon(screen, WHITE, (p1, p2, p3), 2)

# --- Classe Asteroide Grande ---
class Asteroid:
    def __init__(self, initial_pos=None):
        self.pos     = pygame.Vector2(initial_pos) if initial_pos else \
                       pygame.Vector2(random.uniform(0,WIDTH),
                                      random.uniform(0,HEIGHT))
        ang       = random.uniform(0,360)
        spd       = random.uniform(1,3)
        self.vel   = pygame.Vector2(math.cos(math.radians(ang)),
                                   math.sin(math.radians(ang))) * spd
        self.radius  = random.randint(15,40)
        self.trapped = False

    def update(self, ship_pos, black_holes):
        for bh in black_holes:
            bh.attract(self)
        factor = min(bh.time_dilation(self.pos) for bh in black_holes)
        self.pos += self.vel * factor

    def draw(self, ship_pos, ship_vel):
        v_ship = ship_vel.length()
        beta   = min(v_ship/C, 0.999)
        gamma  = 1/math.sqrt(1 - beta**2)
        dir_s  = ship_vel.normalize() if v_ship>0 else pygame.Vector2(1,0)

        rel    = self.pos - ship_pos
        x_par  = rel.dot(dir_s)
        x_perp = rel - x_par*dir_s
        contracted = (x_par/gamma)*dir_s + x_perp
        screen_pos = CENTER + contracted

        if contracted.length()>0:
            los     = contracted.normalize()
            v_rad   = -ship_vel.dot(los)
            b_rad   = max(-0.999, min(0.999, v_rad/C))
            doppler = math.sqrt((1+b_rad)/(1-b_rad))
        else:
            doppler = 1.0
        shade = max(0, min(255, int(GRAY[0] * doppler)))
        color = (shade, shade, shade)

        w = max(1, int(self.radius*2/gamma))
        h = self.radius*2
        rect = pygame.Rect(0,0, w, h)
        rect.center = (int(screen_pos.x), int(screen_pos.y))
        if -self.radius<=screen_pos.x<=WIDTH+self.radius and \
           -self.radius<=screen_pos.y<=HEIGHT+self.radius:
            pygame.draw.ellipse(screen, color, rect, 2)

# --- Classe Tiro Relativístico ---
class Bullet:
    def __init__(self, pos, angle, ship_vel):
        self.pos = pygame.Vector2(pos)
        rad     = math.radians(angle)
        dir_v   = pygame.Vector2(math.cos(rad), -math.sin(rad))
        u       = 6.0
        u_vec   = dir_v * u
        v_vec   = pygame.Vector2(ship_vel)

        v2    = v_vec.length_squared()
        β2    = v2/(C*C)
        γ     = 1/math.sqrt(1-β2) if β2<1 else float('inf')
        v_hat = v_vec.normalize() if v2>0 else pygame.Vector2(1,0)
        u_para= v_hat*(u_vec.dot(v_hat))
        u_perp= u_vec - u_para
        denom = 1 + (v_vec.dot(u_vec))/(C*C)
        w_para= (u_para + v_vec)/denom
        w_perp= u_perp/(γ*denom)
        self.vel   = w_para + w_perp

        self.radius  = 3
        self.trapped = False

    def update(self, ship_pos, black_holes):
        for bh in black_holes:
            bh.attract(self)
        factor = min(bh.time_dilation(self.pos) for bh in black_holes)
        self.pos += self.vel * factor

    def draw(self, ship_pos, ship_vel):
        v_ship = ship_vel.length()
        beta   = min(v_ship/C, 0.999)
        gamma  = 1/math.sqrt(1-beta**2)
        dir_s  = ship_vel.normalize() if v_ship>0 else pygame.Vector2(1,0)
        rel    = self.pos - ship_pos
        x_par  = rel.dot(dir_s)
        x_perp = rel - x_par*dir_s
        contracted = (x_par/gamma)*dir_s + x_perp
        screen_pos = CENTER + contracted

        if -self.radius<=screen_pos.x<=WIDTH+self.radius and \
           -self.radius<=screen_pos.y<=HEIGHT+self.radius:
            pygame.draw.circle(screen, YELLOW,
                               (int(screen_pos.x), int(screen_pos.y)),
                               self.radius)

# --- Classe PixelAsteroid (Disco de Acreção) ---
class PixelAsteroid:
    def __init__(self, bh, min_r, max_r):
        theta = random.uniform(0, 2*math.pi)
        r     = random.uniform(min_r, max_r)
        self.pos = pygame.Vector2(math.cos(theta), math.sin(theta)) * r + bh.pos
        v_mag = math.sqrt(bh.GM / r)
        tang  = pygame.Vector2(-math.sin(theta), math.cos(theta))
        self.vel = tang * v_mag * random.uniform(0.8, 1.2)
        self.radius = 1
        self.trapped = False

    def update(self, ship_pos, black_holes):
        for bh in black_holes:
            bh.attract(self)
        factor = min(bh.time_dilation(self.pos) for bh in black_holes)
        self.pos += self.vel * factor

    def draw(self, ship_pos, ship_vel):
        rel = self.pos - ship_pos + CENTER
        if 0 <= rel.x < WIDTH and 0 <= rel.y < HEIGHT:
            screen.set_at((int(rel.x), int(rel.y)), GRAY)

# --- Função Principal ---
def main():
    ship        = Ship()
    bullets     = []
    black_holes = [BlackHole(pos=(1600,0), radius=200, gm=5e4, kill_factor=0.3)]
    update_sectors(ship.pos)

    # gera disco de acreção
    disk_particles = []
    for bh in black_holes:
        for _ in range(2000):
            disk_particles.append(PixelAsteroid(bh,
                                bh.radius * 1.1,
                                bh.radius * 3.0))

    while True:
        # eventos
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif e.type==pygame.KEYDOWN and e.key==pygame.K_SPACE:
                bullets.append(Bullet(ship.pos, ship.angle, ship.vel))

        # atualizações
        ship.update(black_holes)
        if ship.trapped:
            print("Game Over: engolido pelo buraco negro.")
            pygame.quit()
            sys.exit()

        update_sectors(ship.pos)

        # asteroides grandes
        all_asts = [a for sec in sectors.values() for a in sec]
        for a in all_asts:
            a.update(ship.pos, black_holes)
        # tiros
        for b in bullets:
            b.update(ship.pos, black_holes)
        # partículas do disco
        for p in disk_particles:
            p.update(ship.pos, black_holes)

        # limpa objetos capturados
        all_asts      = [a for a in all_asts      if not a.trapped]
        bullets       = [b for b in bullets       if not b.trapped]
        disk_particles = [p for p in disk_particles if not p.trapped]

        # desenho
        screen.fill(BLACK)
        for bh in black_holes:
            bh.draw(ship.pos)
        for p in disk_particles:
            p.draw(ship.pos, ship.vel)
        ship.draw()
        for a in all_asts:
            a.draw(ship.pos, ship.vel)
        for b in bullets:
            b.draw(ship.pos, ship.vel)

        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    main()
