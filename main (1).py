"""
ROCKET TREE: SUNLIGHT THIEF  -  pixel edition
=============================================

You are a flying rocket-ship tree. Steal every raindrop and sunbeam from the
other trees (1 point each) while they hurl apples at you. Your rocket burns
fuel whenever you fly, so catch the flying fuel cans!

Controls
--------
    Arrow keys / WASD ... fly (uses fuel)
    P ................... pause
    ESC ................. quit
    SPACE / ENTER ....... start / restart

Requires: Python 3.8+ and pygame (pip install -r requirements.txt)
"""

import math
import random
import sys

import pygame

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
# The game is drawn at a tiny "pixel art" resolution and scaled up, which is
# what gives it the chunky pixelated look.
LW, LH = 320, 224
SCALE = 3
WIN_W, WIN_H = LW * SCALE, LH * SCALE
FPS = 60

GROUND_Y = LH - 26
FLY_FLOOR = GROUND_Y - 32      # lowest point you can fly while you have fuel
CRASH_Y = GROUND_Y - 20        # where you land when you run out of fuel
GRAVITY = 300.0               # for apples

START_LIVES = 3
HURT_SECONDS = 1.5
INVINCIBLE_SECONDS = 10.0

MAX_SPEED = 125.0
ACCEL = 620.0
DRAG = 3.0
FALL_GRAVITY = 170.0           # pulls you down when the tank is empty

FUEL_MAX = 100.0
FUEL_DRAIN = 4.0               # fuel lost per second while flying
FUEL_CAN_AMOUNT = 40.0
GOOD_SCORE = 50                # this many points or more earns a compliment
BAD_SCORE = 25                 # fewer than this earns an insult

GAME_OVER_COMMENTS = [
    (10, [
        "Did you even leave the ground? The seeds are laughing.",
        "Even a tree stump would have lasted longer.",
        "That was a seedling-level performance.",
        "The rocket was fine. The pilot was photosynthesizing.",
    ]),
    (25, [
        "Not bad, sapling. Your roots are showing.",
        "A promising start. The apples were just warming up.",
        "Running on fumes already? Watch that fuel gauge!",
        "Respectable. The other trees are only mildly annoyed.",
    ]),
    (50, [
        "Now that's some serious branch work!",
        "The forest is starting to sweat.",
        "Sunlight stolen, apples dodged. Solid run!",
        "You flew like a tree with a deadline.",
    ]),
    (90, [
        "The other trees are filing a formal complaint.",
        "Absolute canopy-level menace. The forest fears you.",
        "Sunlight: stolen. Rain: stolen. Dignity: intact.",
        "The apples are scared of YOU now.",
    ]),
    (float("inf"), [
        "LEGENDARY! The forest named a hurricane after you.",
        "Ancient Redwood of the Sky. Bow before your own shadow.",
        "You didn't dodge apples, you rewrote botany.",
        "The other trees have unionized. They still can't hit you.",
    ]),
]


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def clamp(value, low, high):
    return max(low, min(high, value))


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))


def pick_comment(points):
    for limit, lines in GAME_OVER_COMMENTS:
        if points < limit:
            return random.choice(lines)
    return ""


INSULTS = [
    "Pathetic. Even the apples felt bad for you.",
    "A bonsai could fly better than you.",
    "Were you trying to lose, or is it natural talent?",
    "You're not a rocket tree, you're a falling log.",
    "The whole forest is laughing at you. Loudly.",
    "Weak. A houseplant would have lasted longer.",
    "Did the apples get lucky, or are you just that slow?",
]
FUEL_INSULTS = [
    "You forgot to refuel. A TREE. With a ROCKET.",
    "The fuel cans were literally flying at you!",
    "Congrats on discovering gravity the hard way.",
    "The fuel gauge was RIGHT THERE. You ignored it.",
]
COMPLIMENTS = [
    "Incredible flying! The forest bows to you.",
    "What a legend! Those apples never stood a chance.",
    "Pure skill. You're the best rocket tree around.",
    "Flawless sap-powered flying. Absolutely elite.",
    "The other trees are jealous. You earned it.",
    "Wow! That was a masterclass in sun stealing.",
]
DEATH_TEXT = {
    "fuel": "YOU CRASHED: OUT OF FUEL!",
    "apple": "KNOCKED OUT BY AN APPLE",
    "acorn": "BONKED BY AN ACORN",
    "pinecone": "SPEARED BY A PINECONE",
}


def pick_verdict(points, cause=None):
    """An insult for a bad score, a compliment for a good one, else nothing."""
    if points < BAD_SCORE:
        pool = INSULTS + (FUEL_INSULTS * 2 if cause == "fuel" else [])
        return random.choice(pool), (255, 100, 90)
    if points >= GOOD_SCORE:
        return random.choice(COMPLIMENTS), (120, 255, 140)
    return None


def draw_text(surf, font, text, pos, color=(255, 255, 255),
              anchor="topleft", shadow=True):
    """Un-antialiased text so it stays crisp and pixelated."""
    img = font.render(text, False, color)
    w, h = img.get_size()
    if w > LW - 6:  # never let text run off the tiny screen
        img = pygame.transform.scale(img, (LW - 6, max(1, int(h * (LW - 6) / w))))
    rect = img.get_rect(**{anchor: pos})
    if shadow:
        sh = font.render(text, False, (0, 0, 0))
        if sh.get_width() != img.get_width():
            sh = pygame.transform.scale(sh, img.get_size())
        surf.blit(sh, rect.move(1, 1))
    surf.blit(img, rect)


def wrap_text(font, text, max_w):
    lines, cur = [], ""
    for word in text.split():
        test = (cur + " " + word).strip()
        if font.size(test)[0] <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def blit_center(dst, spr, cx, cy):
    dst.blit(spr, (int(cx - spr.get_width() // 2), int(cy - spr.get_height() // 2)))


def make_sprite(rows, palette):
    """Build a pixel sprite from rows of characters ('.' = transparent)."""
    surf = pygame.Surface((len(rows[0]), len(rows)), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            col = palette.get(ch)
            if col is not None:
                surf.set_at((x, y), col)
    return surf


def make_glow(radius, color, peak=110):
    """Banded radial glow (the bands suit the pixel look)."""
    surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for r in range(radius, 0, -2):
        alpha = int(peak * (1 - r / radius) ** 1.5)
        pygame.draw.circle(surf, (*color, alpha), (radius, radius), r)
    return surf


# ---------------------------------------------------------------------------
# Pixel sprites
# ---------------------------------------------------------------------------
APPLE_ROWS = [
    "...sgg.",
    "...sg..",
    ".rrrrr.",
    "rhrrrrR",
    "rhrrrrR",
    "rrrrrrR",
    ".rrrrR.",
    "..RRR..",
]
APPLE_PAL = {"r": (205, 30, 45), "R": (140, 15, 35), "h": (255, 150, 160),
             "s": (100, 60, 30), "g": (70, 200, 80)}

RAIN_ROWS = [
    "..b..",
    "..b..",
    ".bbb.",
    "bbbbb",
    "bwbbB",
    "bbbBB",
    ".BBB.",
]
RAIN_PAL = {"b": (70, 150, 255), "B": (35, 90, 215), "w": (215, 238, 255)}

HEART_ROWS = [
    ".kkk.kkk.",
    "kRRRkRRRk",
    "kRwRRRRRk",
    "kRRRRRRRk",
    ".kRRRRRk.",
    "..kRRRk..",
    "...kRk...",
    "....k....",
]
HEART_PAL = {"k": (70, 0, 20), "R": (235, 45, 75), "w": (255, 170, 190)}
HEART_EMPTY_PAL = {"k": (40, 25, 35), "R": (70, 55, 65), "w": (70, 55, 65)}

ACORN_ROWS = [
    "...s...",
    ".ccccc.",
    "CCCCCCC",
    ".AAAAa.",
    ".AAAAa.",
    ".AAAaa.",
    "..AAa..",
    "...a...",
]
ACORN_PAL = {"s": (80, 50, 25), "c": (150, 105, 55), "C": (110, 70, 35),
             "A": (195, 135, 65), "a": (150, 95, 40)}

CONE_ROWS = [
    "...pPpP....",
    "..PpPpPpP..",
    ".PpPpPpPpP.",
    "PpPpPpPpPpP",
    ".PpPpPpPpP.",
    "..PpPpPpP..",
    "...pPpP....",
]
CONE_PAL = {"P": (125, 78, 36), "p": (80, 45, 20)}

FUEL_ROWS = [
    "...gggg.kk",
    "...g..g.k.",
    "RRRRRRRRRR",
    "RwRRRRRRRD",
    "RwRyyyyRRD",
    "RRRyDDyRRD",
    "RRRyyyyRRD",
    "RRRRRRRRRD",
    "RRRRRRRRRD",
    "DDDDDDDDDD",
]
FUEL_PAL = {"k": (35, 35, 40), "g": (175, 175, 185), "R": (215, 55, 40),
            "D": (140, 30, 30), "w": (255, 150, 130), "y": (250, 215, 70)}

BAG_ROWS = [
    "...kkkkkk...",
    "....tttt....",
    "..kTTTTTTk..",
    ".kTTTTTTTTk.",
    "kTTTGGGGTTTk",
    "kTTGGWWGGTTk",
    "kTTWWWWWWTTk",
    "kTTWWWWWWTTk",
    "kTTGGWWGGTTk",
    "kTTTGGGGTTTk",
    ".kTTTTTTTTk.",
    "..kkkkkkkk..",
]
BAG_PAL = {"k": (90, 60, 30), "t": (150, 110, 60), "T": (212, 172, 112),
           "G": (60, 190, 80), "W": (255, 255, 255)}

ANGER_ROWS = [
    "RR.RR",
    "R...R",
    ".....",
    "R...R",
    "RR.RR",
]
ANGER_PAL = {"R": (255, 50, 40)}


def make_sun_sprite(frame):
    s = pygame.Surface((13, 13), pygame.SRCALPHA)
    pygame.draw.circle(s, (255, 236, 90), (6, 6), 3)
    s.set_at((5, 5), (255, 255, 200))
    if frame == 0:
        pts = [(6, 0), (6, 1), (6, 11), (6, 12), (0, 6), (1, 6), (11, 6), (12, 6)]
    else:
        pts = [(2, 2), (1, 1), (10, 2), (11, 1), (2, 10), (1, 11), (10, 10), (11, 11)]
    for p in pts:
        s.set_at(p, (255, 205, 60))
    return s


class Sprites:
    def __init__(self):
        apple = make_sprite(APPLE_ROWS, APPLE_PAL)
        self.apple_frames = [apple] + [pygame.transform.rotate(apple, a) for a in (90, 180, 270)]
        self.rain = make_sprite(RAIN_ROWS, RAIN_PAL)
        self.sun = [make_sun_sprite(0), make_sun_sprite(1)]
        self.heart = make_sprite(HEART_ROWS, HEART_PAL)
        self.heart_empty = make_sprite(HEART_ROWS, HEART_EMPTY_PAL)
        self.acorn = make_sprite(ACORN_ROWS, ACORN_PAL)
        self.cone = make_sprite(CONE_ROWS, CONE_PAL)
        self.fuel = make_sprite(FUEL_ROWS, FUEL_PAL)
        self.bag = make_sprite(BAG_ROWS, BAG_PAL)
        self.anger = make_sprite(ANGER_ROWS, ANGER_PAL)


# ---------------------------------------------------------------------------
# Particles and pop-up text
# ---------------------------------------------------------------------------
class Particle:
    def __init__(self, x, y, vx, vy, life, color, size=1,
                 gravity=0.0, streak=False, drag=0.0):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = self.max_life = life
        self.color = color
        self.size = size
        self.gravity = gravity
        self.streak = streak
        self.drag = drag

    def update(self, dt):
        self.life -= dt
        if self.drag:
            k = max(0.0, 1.0 - self.drag * dt)
            self.vx *= k
            self.vy *= k
        self.vy += self.gravity * dt
        self.x += self.vx * dt
        self.y += self.vy * dt

    def draw(self, surf):
        frac = max(0.0, self.life / self.max_life)
        if self.streak:
            pygame.draw.line(
                surf, self.color, (int(self.x), int(self.y)),
                (int(self.x - self.vx * 0.04), int(self.y - self.vy * 0.04)))
        else:
            s = max(1, int(round(self.size * frac)))
            pygame.draw.rect(surf, self.color, (int(self.x), int(self.y), s, s))


class Popup:
    def __init__(self, x, y, text, color):
        self.x, self.y = x, y
        self.text = text
        self.color = color
        self.life = 0.9

    def update(self, dt):
        self.life -= dt
        self.y -= 16 * dt


# ---------------------------------------------------------------------------
# Hazards (apples, acorns, pinecones)
# ---------------------------------------------------------------------------
class Hazard:
    RADII = {"apple": 4, "acorn": 4, "pinecone": 6}

    def __init__(self, kind, x, y, vx=0.0, vy=0.0):
        self.kind = kind
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.base_x, self.base_y = x, y
        self.r = self.RADII[kind]
        self.age = 0.0
        self.dead = False

    def update(self, dt):
        self.age += dt
        if self.kind == "apple":
            self.vy += GRAVITY * dt
            self.x += self.vx * dt
            self.y += self.vy * dt
            if self.x < -20 or self.x > LW + 20:
                self.dead = True
        elif self.kind == "acorn":
            self.y += self.vy * dt
            self.x = self.base_x + math.sin(self.age * 4) * 6
        else:  # pinecone
            self.x += self.vx * dt
            self.y = self.base_y + math.sin(self.age * 3) * 15
            if self.x < -20:
                self.dead = True

    def hit_ground(self):
        return self.kind in ("apple", "acorn") and self.y > GROUND_Y + 1

    def draw(self, surf, spr):
        if self.kind == "apple":
            blit_center(surf, spr.apple_frames[int(self.age * 12) % 4], self.x, self.y)
        elif self.kind == "acorn":
            blit_center(surf, spr.acorn, self.x, self.y)
        else:
            blit_center(surf, spr.cone, self.x, self.y)


# ---------------------------------------------------------------------------
# Collectibles (raindrops, sunbeams, fertilizer, flying fuel cans)
# ---------------------------------------------------------------------------
class Item:
    PICK = {"rain": 12, "sun": 12, "fert": 15, "fuel": 15}

    def __init__(self, kind, x, y, vx=0.0, vy=0.0):
        self.kind = kind
        self.x, self.y = x, y
        self.base_x, self.base_y = x, y
        self.vx, self.vy = vx, vy
        self.age = random.random() * 6
        self.dead = False

    @property
    def pick_radius(self):
        return self.PICK[self.kind]

    def update(self, dt, px, py):
        self.age += dt
        if self.kind == "fuel":
            # fuel cans flap sideways across the sky
            self.base_x += self.vx * dt
            self.x = self.base_x
            self.y = self.base_y + math.sin(self.age * 3) * 8
            if self.x < -24 or self.x > LW + 24:
                self.dead = True
            return
        self.base_y += self.vy * dt
        self.y = self.base_y
        self.x = self.base_x + math.sin(self.age * 2) * 4
        if self.kind in ("rain", "sun"):
            # the rocket tree sucks up nearby water and light
            d = math.hypot(px - self.x, py - self.y)
            if 0 < d < 50:
                pull = 90 * (1 - d / 50) * dt
                self.base_x += (px - self.x) / d * pull
                self.base_y += (py - self.y) / d * pull
        if self.base_y > LH + 10:
            self.dead = True

    def draw(self, surf, spr, glows, t):
        x, y = int(self.x), int(self.y)
        if self.kind == "rain":
            blit_center(surf, spr.rain, x, y)
        elif self.kind == "sun":
            blit_center(surf, spr.sun[int(self.age * 4) % 2], x, y)
        elif self.kind == "fert":
            blit_center(surf, glows[int(t * 8) % len(glows)], x, y)
            blit_center(surf, spr.bag, x, y)
        else:  # fuel can with flapping wings and a spinning propeller
            flap = int(self.age * 14) % 2
            wy = y - 3 + (-2 if flap else 2)
            pygame.draw.rect(surf, (235, 240, 255), (x - 10, wy, 4, 2))
            pygame.draw.rect(surf, (235, 240, 255), (x + 7, wy, 4, 2))
            blit_center(surf, spr.fuel, x, y)
            pw = 9 if flap else 5
            pygame.draw.rect(surf, (210, 210, 220), (x - pw // 2, y - 9, pw, 1))
            pygame.draw.rect(surf, (90, 90, 100), (x - 1, y - 8, 2, 2))


# ---------------------------------------------------------------------------
# Enemy trees (angry apple throwers)
# ---------------------------------------------------------------------------
class EnemyTree:
    ARM_LEN = 15

    def __init__(self, x):
        self.x = x
        self.height = random.randint(38, 50)
        self.sway_phase = random.random() * 6.28
        self.reset()

    def reset(self):
        self.cooldown = random.uniform(1.0, 2.5)
        self.throw_t = None      # None = idle, 0..1 = wind-up progress
        self.dir = 1
        self.awake = False
        self.recoil = 0.0

    @property
    def sway(self):
        return math.sin(self.sway_phase) * 1.5

    def lean(self):
        """Leans back while winding up, then lunges forward."""
        if self.throw_t is not None:
            p = self.throw_t
            if p < 0.65:
                q = p / 0.65
                return -self.dir * 3.0 * (q * q * (3 - 2 * q))
            q = (p - 0.65) / 0.35
            return self.dir * lerp(-3.0, 3.0, q)
        return self.dir * 3.0 * (self.recoil / 0.25)

    def top_x(self):
        return self.x + self.sway + self.lean()

    def shoulder(self):
        return self.x + self.sway * 0.5 + self.lean() * 0.5, GROUND_Y - self.height * 0.45

    def arm_phi(self):
        if self.throw_t is None:
            return math.radians(-50)
        p = self.throw_t
        if p < 0.65:
            q = p / 0.65
            ease = q * q * (3 - 2 * q)
            return math.radians(lerp(-50, 165, ease))   # wind back
        q = (p - 0.65) / 0.35
        return math.radians(lerp(165, 35, q))           # whip forward

    def hand_pos(self):
        sx, sy = self.shoulder()
        phi = self.arm_phi()
        return (sx + self.dir * math.cos(phi) * self.ARM_LEN,
                sy - math.sin(phi) * self.ARM_LEN)

    def update(self, dt, game):
        self.sway_phase += dt * 1.5
        self.recoil = max(0.0, self.recoil - dt)

        # angry steam puffing out of the canopy
        if self.awake:
            rate = 2.0 + 6.0 * game.anger + (8.0 if self.throw_t is not None else 0.0)
            if random.random() < rate * dt:
                side = random.choice((-1, 1))
                game.particles.append(Particle(
                    self.top_x() + side * 12, GROUND_Y - self.height - 6,
                    side * random.uniform(5, 20), -random.uniform(18, 40),
                    random.uniform(0.5, 0.9),
                    random.choice([(245, 245, 245), (215, 215, 225)]), 3, drag=1.0))

        if self.throw_t is None:
            if self.awake:
                self.cooldown -= dt
                if self.cooldown <= 0:
                    self.throw_t = 0.0
                    self.dir = 1 if game.px > self.x else -1
        else:
            self.dir = 1 if game.px > self.x else -1
            self.throw_t += dt / game.windup_time
            if self.throw_t >= 1.0:
                hx, hy = self.hand_pos()
                self.throw_t = None
                self.recoil = 0.25
                game.spawn_apple(hx, hy)
                game.burst(hx, hy, (255, 255, 255), 5, 40, 0)
                self.cooldown = game.throw_interval()

    def draw(self, surf, spr, health, anger, clock):
        throwing = self.throw_t is not None
        fury = 0.0
        if self.awake:
            fury = 0.2 + 0.25 * anger
        if throwing:
            fury = min(1.0, fury + 0.35 + 0.3 * self.throw_t)

        tx = int(round(self.top_x()))
        if throwing:
            tx += random.choice((-1, 0, 1))      # shaking with rage
        cy = int(GROUND_Y - self.height)
        rx = int(self.x)

        # trunk
        pygame.draw.polygon(surf, (110, 70, 35), [
            (rx - 5, GROUND_Y + 1), (rx + 5, GROUND_Y + 1), (tx + 3, cy), (tx - 3, cy)])
        pygame.draw.polygon(surf, (80, 50, 25), [
            (rx + 1, GROUND_Y + 1), (rx + 5, GROUND_Y + 1), (tx + 3, cy), (tx + 1, cy)])

        # canopy - turns brown as you steal their food, red when furious
        base = lerp_color((150, 125, 55), (62, 172, 72), health)
        leaf = lerp_color(base, (205, 55, 40), fury * 0.8)
        dark = lerp_color(lerp_color((105, 88, 38), (30, 110, 48), health),
                          (110, 20, 20), fury * 0.8)
        light = lerp_color(leaf, (255, 255, 255), 0.25)
        blobs = ((-12, 5, 10), (12, 5, 10), (0, -3, 14), (0, -16, 10))
        for ox, oy, r in blobs:
            pygame.draw.circle(surf, dark, (tx + ox, cy + oy), r + 1)
        for ox, oy, r in blobs:
            pygame.draw.circle(surf, leaf, (tx + ox, cy + oy), r)
        pygame.draw.rect(surf, light, (tx - 6, cy - 19, 4, 2))
        pygame.draw.rect(surf, light, (tx - 11, cy - 5, 3, 2))
        pygame.draw.rect(surf, light, (tx + 6, cy - 10, 3, 2))

        # angry face
        ey = cy - 4
        for s in (-1, 1):
            ex = tx + s * 5
            pygame.draw.rect(surf, (255, 255, 255), (ex - 2, ey - 1, 4, 4))
            pupil = (235, 20, 20) if self.awake else (30, 15, 10)
            pygame.draw.rect(surf, pupil, (ex - 2 + (2 if self.dir > 0 else 0), ey, 2, 2))
        brow_w = 3 if fury > 0.5 else 2
        pygame.draw.line(surf, (35, 12, 8), (tx - 10, ey - 5), (tx - 2, ey), brow_w)
        pygame.draw.line(surf, (35, 12, 8), (tx + 10, ey - 5), (tx + 2, ey), brow_w)
        my = cy + 5
        if throwing:                                   # full roar
            pygame.draw.rect(surf, (25, 5, 5), (tx - 4, my, 9, 6))
            pygame.draw.rect(surf, (200, 45, 55), (tx - 2, my + 4, 5, 2))
            pygame.draw.rect(surf, (255, 255, 255), (tx - 4, my, 2, 2))
            pygame.draw.rect(surf, (255, 255, 255), (tx + 3, my, 2, 2))
        elif self.awake:                               # gritted teeth
            pygame.draw.rect(surf, (25, 5, 5), (tx - 5, my, 11, 4))
            for dx in (-4, -1, 2):
                pygame.draw.rect(surf, (255, 255, 255), (tx + dx, my, 2, 2))
            for dx in (-3, 0, 3):
                pygame.draw.rect(surf, (255, 255, 255), (tx + dx, my + 2, 2, 2))
        else:                                          # deep frown
            pygame.draw.rect(surf, (40, 20, 10), (tx - 3, my + 1, 7, 1))
            pygame.draw.rect(surf, (40, 20, 10), (tx - 4, my + 2, 1, 1))
            pygame.draw.rect(surf, (40, 20, 10), (tx + 4, my + 2, 1, 1))
        if fury > 0.5:                                 # forehead vein
            pygame.draw.rect(surf, (255, 60, 50), (tx + 4, cy - 12, 1, 3))
            pygame.draw.rect(surf, (255, 60, 50), (tx + 5, cy - 12, 2, 1))
        if self.awake and (throwing or int(clock * 4) % 2 == 0):
            surf.blit(spr.anger, (tx + 9, cy - 28))

        # throwing arm (with a clenched fist) and a fist-shaking arm
        sx, sy = self.shoulder()
        hx, hy = self.hand_pos()
        pygame.draw.line(surf, (92, 60, 30), (int(sx), int(sy)), (int(hx), int(hy)), 3)
        pygame.draw.circle(surf, (125, 82, 42), (int(hx), int(hy)), 3)
        pygame.draw.rect(surf, (80, 50, 25), (int(hx) - 1, int(hy), 3, 1))
        if throwing:
            blit_center(surf, spr.apple_frames[0], hx, hy - 4)
        if self.awake or throwing:
            shake = math.sin(clock * 14 + self.x) * 1.5
            fx = int(sx - self.dir * 8)
            fy = int(sy - 12 + shake)
            pygame.draw.line(surf, (92, 60, 30), (int(sx - self.dir * 2), int(sy)), (fx, fy), 3)
            pygame.draw.circle(surf, (125, 82, 42), (fx, fy), 3)


# ---------------------------------------------------------------------------
# The game
# ---------------------------------------------------------------------------
GREENS = [(90, 255, 110), (150, 255, 160), (40, 220, 90)]
CLOUD_BLOBS = ((-12, 2, 7), (0, -3, 10), (13, 2, 8), (5, 5, 7), (-6, 5, 6))


class Game:
    TREE_XS = (30, 82, 134, 186, 238, 290)
    WAKE_ORDER = (3, 1, 5, 0, 4, 2)

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Rocket Tree: Sunlight Thief")
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        self.canvas = pygame.Surface((LW, LH))
        self.clock = pygame.time.Clock()
        self.f_tiny = pygame.font.Font(None, 14)
        self.f_small = pygame.font.Font(None, 18)
        self.f_med = pygame.font.Font(None, 26)
        self.f_big = pygame.font.Font(None, 40)
        self.f_huge = pygame.font.Font(None, 52)
        self.spr = Sprites()
        self.sky = self.build_sky()
        self.hill_far, self.hill_near = self.build_hills()
        self.ground = self.build_ground()
        self.glow_sun = make_glow(28, (255, 230, 120), 150)
        self.glow_aura = [make_glow(r, (60, 255, 90), 120) for r in (24, 28, 32)]
        self.glow_item = [make_glow(r, (60, 255, 90), 110) for r in (12, 15, 18)]
        self.overlays = {}
        self.clouds = [[random.uniform(0, LW + 120), random.uniform(14, 70),
                        random.uniform(0.8, 1.3), random.uniform(4, 10),
                        random.choice((0.15, 0.3))] for _ in range(6)]
        self.trees = [EnemyTree(x) for x in self.TREE_XS]
        self.best = 0
        self.anim_t = 0.0
        self.state = "title"
        self.comment_lines = []
        self.reset()

    # ----- setup -----------------------------------------------------------
    def build_sky(self):
        sky = pygame.Surface((LW, LH))
        top, bottom = (88, 160, 230), (200, 230, 250)
        bands = 14
        for i in range(bands):
            y0 = i * LH // bands
            y1 = (i + 1) * LH // bands
            pygame.draw.rect(sky, lerp_color(top, bottom, i / (bands - 1)),
                             (0, y0, LW, y1 - y0))
        return sky

    def build_hills(self):
        far = pygame.Surface((LW + 80, LH), pygame.SRCALPHA)
        near = pygame.Surface((LW + 80, LH), pygame.SRCALPHA)
        for cx, dy, r in ((20, 30, 55), (110, 38, 70), (200, 28, 52), (290, 40, 75), (360, 30, 55)):
            pygame.draw.circle(far, (128, 185, 170), (cx, GROUND_Y + dy), r)
        for cx, dy, r in ((60, 26, 45), (150, 22, 40), (250, 30, 50), (340, 24, 42)):
            pygame.draw.circle(near, (108, 176, 120), (cx, GROUND_Y + dy), r)
        return far, near

    def build_ground(self):
        rnd = random.Random(7)
        h = LH - GROUND_Y
        g = pygame.Surface((LW, h))
        g.fill((105, 72, 42))
        pygame.draw.rect(g, (70, 150, 58), (0, 0, LW, 6))
        pygame.draw.rect(g, (104, 190, 80), (0, 0, LW, 2))
        for _ in range(140):
            g.set_at((rnd.randrange(LW), rnd.randrange(8, h)),
                     rnd.choice([(88, 58, 33), (125, 90, 55)]))
        for x in range(0, LW, 4):
            g.set_at((x + rnd.randrange(4), 6), (70, 150, 58))
        return g

    def reset(self):
        self.elapsed = 0.0
        self.lives = START_LIVES
        self.px, self.py = LW / 2.0, GROUND_Y - 90.0
        self.vx = self.vy = 0.0
        self.fuel = FUEL_MAX
        self.thrusting = False
        self.hurt_timer = 0.0
        self.invincible_timer = 0.0
        self.stolen_rain = 0
        self.stolen_sun = 0
        self.hazards = []
        self.items = []
        self.particles = []
        self.popups = []
        self.shake = 0.0
        self.t_rain = 0.4
        self.t_sun = 0.9
        self.t_acorn = 2.0
        self.t_cone = 2.0
        self.t_fert = random.uniform(10, 16)
        self.t_fuel = 5.0
        self.exhaust_t = 0.0
        self.death_cause = None
        self.last_hit = None
        self.verdict_lines = []
        self.verdict_color = (255, 255, 255)
        for t in self.trees:
            t.reset()

    def start_game(self):
        self.reset()
        self.state = "play"

    # ----- difficulty ------------------------------------------------------
    @property
    def level(self):
        return 1 + int(self.elapsed // 12)

    @property
    def speed_mult(self):
        return min(3.0, 1.0 + self.elapsed / 150.0)

    @property
    def windup_time(self):
        return max(0.38, 0.8 - 0.004 * self.elapsed)

    def throw_interval(self):
        base = max(0.7, 2.8 - 0.035 * self.elapsed)
        return base * random.uniform(0.7, 1.4)

    @property
    def points(self):
        return self.stolen_rain + self.stolen_sun

    @property
    def health(self):
        return max(0.2, 1.0 - self.points / 120.0)

    @property
    def anger(self):
        return min(1.0, self.points / 80.0)

    # ----- spawning --------------------------------------------------------
    def popup(self, x, y, text, color):
        self.popups.append(Popup(x, y, text, color))

    def spawn_apple(self, x, y):
        dist = math.hypot(self.px - x, self.py - y)
        t = clamp(dist / (127 * self.speed_mult), 0.45, 1.6)
        jitter = max(5.0, 23.0 - self.elapsed * 0.2)
        tx = self.px + self.vx * t * 0.4 + random.uniform(-jitter, jitter)
        ty = self.py + self.vy * t * 0.4 + random.uniform(-jitter, jitter)
        vx = (tx - x) / t
        vy = (ty - y) / t - 0.5 * GRAVITY * t
        self.hazards.append(Hazard("apple", x, y, vx, vy))

    def burst(self, x, y, color, n=12, speed=70, gravity=100):
        for _ in range(n):
            a = random.random() * math.tau
            s = random.uniform(15, speed)
            self.particles.append(Particle(
                x, y, math.cos(a) * s, math.sin(a) * s,
                random.uniform(0.3, 0.7), color, random.randint(1, 3), gravity))

    def update_spawns(self, dt):
        sm = self.speed_mult
        self.t_rain -= dt
        if self.t_rain <= 0:
            self.items.append(Item("rain", random.uniform(8, LW - 8), -8,
                                   vy=random.uniform(30, 47) * sm))
            self.t_rain = random.uniform(0.6, 1.2)
        self.t_sun -= dt
        if self.t_sun <= 0:
            self.items.append(Item("sun", random.uniform(8, LW - 8), -8,
                                   vy=random.uniform(27, 43) * sm))
            self.t_sun = random.uniform(0.9, 1.6)
        self.t_fert -= dt
        if self.t_fert <= 0:
            self.items.append(Item("fert", random.uniform(20, LW - 20), -12, vy=47))
            self.t_fert = random.uniform(18, 28)

        # flying fuel cans come more often when your tank is low
        self.t_fuel -= dt
        if self.t_fuel <= 0:
            from_left = random.random() < 0.5
            speed = random.uniform(30, 45)
            self.items.append(Item("fuel", -14 if from_left else LW + 14,
                                   random.uniform(30, GROUND_Y - 40),
                                   vx=speed if from_left else -speed))
            self.t_fuel = random.uniform(8, 13) if self.fuel > 50 else random.uniform(4, 7)

        if self.elapsed >= 18:  # falling acorns
            self.t_acorn -= dt
            if self.t_acorn <= 0:
                self.hazards.append(Hazard("acorn", random.uniform(8, LW - 8), -8,
                                           0, random.uniform(67, 87) * sm))
                self.t_acorn = max(0.5, 2.2 - self.elapsed * 0.012)
        if self.elapsed >= 36:  # sine-wave pinecones from the right
            self.t_cone -= dt
            if self.t_cone <= 0:
                self.hazards.append(Hazard("pinecone", LW + 14,
                                           random.uniform(35, GROUND_Y - 30),
                                           -random.uniform(77, 100) * sm, 0))
                self.t_cone = max(0.8, 3.5 - self.elapsed * 0.02)

    # ----- collisions ------------------------------------------------------
    def player_hit(self, hz):
        c1 = math.hypot(hz.x - self.px, hz.y - (self.py - 11))
        c2 = math.hypot(hz.x - self.px, hz.y - (self.py + 7))
        return c1 < 10 + hz.r * 0.8 or c2 < 6 + hz.r * 0.8

    def hurt(self):
        self.lives -= 1
        self.hurt_timer = HURT_SECONDS
        self.shake = 0.35
        self.burst(self.px, self.py, (255, 120, 40), 22, 90)

    def crash(self):
        """Ran out of fuel and hit the ground: instant game over."""
        self.py = float(CRASH_Y)
        self.vx = self.vy = 0.0
        self.lives = 0
        self.death_cause = "fuel"
        self.shake = 0.5
        self.burst(self.px, GROUND_Y - 2, (150, 110, 60), 24, 80, 200)
        self.burst(self.px, GROUND_Y - 8, (255, 140, 40), 24, 110)

    # ----- update ----------------------------------------------------------
    def update_sky(self, dt):
        for c in self.clouds:
            c[0] += c[3] * dt * (1 + self.elapsed / 100)

    def update_player(self, dt):
        keys = pygame.key.get_pressed()
        ix = int(bool(keys[pygame.K_RIGHT] or keys[pygame.K_d])) - \
            int(bool(keys[pygame.K_LEFT] or keys[pygame.K_a]))
        iy = int(bool(keys[pygame.K_DOWN] or keys[pygame.K_s])) - \
            int(bool(keys[pygame.K_UP] or keys[pygame.K_w]))
        powered = self.fuel > 0
        ax = ay = 0.0
        self.thrusting = False
        if ix or iy:
            n = math.hypot(ix, iy)
            if powered:
                ax, ay = ix / n * ACCEL, iy / n * ACCEL
                self.fuel = max(0.0, self.fuel - FUEL_DRAIN * dt)
                self.thrusting = True
                if self.fuel <= 0:
                    self.popup(self.px, self.py - 34, "OUT OF FUEL!", (255, 80, 60))
            else:
                ax = ix / n * ACCEL * 0.35   # glide steering only
        if not powered:
            ay += FALL_GRAVITY

        # momentum: accelerate, then air drag, so the tree glides smoothly
        self.vx += ax * dt
        self.vy += ay * dt
        k = max(0.0, 1.0 - DRAG * dt)
        self.vx *= k
        self.vy *= k
        sp = math.hypot(self.vx, self.vy)
        if sp > MAX_SPEED:
            self.vx *= MAX_SPEED / sp
            self.vy *= MAX_SPEED / sp
        self.px += self.vx * dt
        self.py += self.vy * dt

        if self.px < 14:
            self.px, self.vx = 14.0, max(0.0, self.vx)
        elif self.px > LW - 14:
            self.px, self.vx = LW - 14.0, min(0.0, self.vx)
        if self.py < 30:
            self.py, self.vy = 30.0, max(0.0, self.vy)
        if self.fuel > 0:
            if self.py > FLY_FLOOR:
                self.py, self.vy = float(FLY_FLOOR), min(0.0, self.vy)
        elif self.py >= CRASH_Y:
            self.crash()

    def emit_flight_particles(self, dt):
        inv = self.invincible_timer > 0
        powered = self.fuel > 0
        self.exhaust_t -= dt
        if self.exhaust_t <= 0:
            ex = self.px + random.uniform(-2, 2)
            ey = self.py + 20
            if powered:
                self.exhaust_t = 0.025 if self.thrusting else 0.08
                col = random.choice(GREENS if inv else [(255, 170, 40), (255, 110, 30), (255, 235, 110)])
                self.particles.append(Particle(
                    ex, ey, -self.vx * 0.3 + random.uniform(-6, 6),
                    30 + random.uniform(0, 30) + (40 if self.thrusting else 0), 0.25, col, 2))
                self.particles.append(Particle(
                    ex, ey + 3, -self.vx * 0.15 + random.uniform(-5, 5),
                    14 + random.uniform(0, 16), 0.8,
                    (170, 240, 185) if inv else (205, 205, 215), 3, drag=1.2))
            else:  # sputtering engine
                self.exhaust_t = 0.12
                self.particles.append(Particle(
                    ex, ey, random.uniform(-5, 5), random.uniform(8, 20),
                    0.7, (90, 90, 100), 3, drag=1.0))

        if inv:  # green fertilizer blast through the air
            for _ in range(3):
                a = random.uniform(-0.5, 0.5)
                sp = random.uniform(90, 170)
                self.particles.append(Particle(
                    self.px + random.uniform(-10, 10), self.py + random.uniform(-14, 12),
                    math.sin(a) * sp * 0.5 - self.vx * 0.5, math.cos(a) * sp - self.vy * 0.5,
                    0.4, random.choice(GREENS), 2, streak=random.random() < 0.6))

        # wind streaks and leaves make the flying feel fast
        speed = math.hypot(self.vx, self.vy)
        if speed > 18 and random.random() < min(1.0, speed / MAX_SPEED * 1.2):
            self.particles.append(Particle(
                random.uniform(0, LW), random.uniform(10, GROUND_Y - 5),
                -self.vx * 1.5, -self.vy * 1.5, 0.22,
                (170, 255, 190) if inv else (235, 245, 255), 1, streak=True))
        if speed > 40 and random.random() < 0.25:
            self.particles.append(Particle(
                self.px + random.uniform(-8, 8), self.py - 14 + random.uniform(-8, 8),
                -self.vx * 0.4 + random.uniform(-10, 10), -self.vy * 0.4 + random.uniform(-10, 10),
                0.5, random.choice([(60, 170, 70), (100, 210, 90)]), 2))

    def update_play(self, dt):
        self.elapsed += dt
        self.update_sky(dt)
        self.update_player(dt)
        if self.lives <= 0:          # crashed out of fuel
            self.end_game()
            return

        self.hurt_timer = max(0.0, self.hurt_timer - dt)
        self.invincible_timer = max(0.0, self.invincible_timer - dt)
        self.shake = max(0.0, self.shake - dt)

        # more trees wake up and get furious as time passes
        awake_count = min(len(self.trees), 2 + int(self.elapsed // 12))
        for i, idx in enumerate(self.WAKE_ORDER):
            self.trees[idx].awake = i < awake_count
        for t in self.trees:
            t.update(dt, self)

        self.update_spawns(dt)
        self.emit_flight_particles(dt)

        # hazards
        for hz in self.hazards:
            hz.update(dt)
            if hz.kind == "apple" and random.random() < 0.35:
                self.particles.append(Particle(hz.x, hz.y, 0, 0, 0.25, (255, 120, 120), 1))
            if hz.hit_ground():
                self.burst(hz.x, GROUND_Y,
                           (220, 60, 60) if hz.kind == "apple" else (150, 110, 60), 6, 40)
                hz.dead = True
            elif self.player_hit(hz):
                hz.dead = True
                if self.invincible_timer > 0:
                    self.burst(hz.x, hz.y, (90, 255, 120), 14, 80, 0)
                elif self.hurt_timer <= 0:
                    self.last_hit = hz.kind
                    self.hurt()
                else:
                    self.burst(hz.x, hz.y, (255, 255, 255), 6, 40)
        self.hazards = [h for h in self.hazards if not h.dead]

        # items
        for it in self.items:
            it.update(dt, self.px, self.py)
            if math.hypot(it.x - self.px, it.y - (self.py - 2)) < it.pick_radius:
                it.dead = True
                if it.kind == "rain":
                    self.stolen_rain += 1
                    self.burst(it.x, it.y, (90, 160, 255), 6, 50, 0)
                    self.popup(it.x, it.y - 6, "+1", (150, 200, 255))
                elif it.kind == "sun":
                    self.stolen_sun += 1
                    self.burst(it.x, it.y, (255, 225, 80), 6, 50, 0)
                    self.popup(it.x, it.y - 6, "+1", (255, 235, 120))
                elif it.kind == "fert":
                    self.invincible_timer = INVINCIBLE_SECONDS
                    self.burst(it.x, it.y, (90, 255, 110), 30, 120, 0)
                    self.popup(self.px, self.py - 34, "INVINCIBLE!", (120, 255, 140))
                else:
                    self.fuel = min(FUEL_MAX, self.fuel + FUEL_CAN_AMOUNT)
                    self.burst(it.x, it.y, (255, 170, 40), 14, 70, 0)
                    self.popup(self.px, self.py - 34, "+FUEL", (255, 210, 90))
        self.items = [i for i in self.items if not i.dead]

        self.update_particles(dt)

        if self.lives <= 0:
            self.end_game()

    def update_particles(self, dt):
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]
        for p in self.popups:
            p.update(dt)
        self.popups = [p for p in self.popups if p.life > 0]

    def end_game(self):
        self.state = "over"
        self.best = max(self.best, self.points)
        if self.death_cause is None:
            self.death_cause = self.last_hit
        self.comment_lines = wrap_text(self.f_small, pick_comment(self.points), LW - 30)
        verdict = pick_verdict(self.points, self.death_cause)
        if verdict:
            text, self.verdict_color = verdict
            self.verdict_lines = wrap_text(self.f_small, text, LW - 30)
        else:
            self.verdict_lines = []
        self.burst(self.px, self.py, (255, 140, 40), 40, 110)

    # ----- drawing ---------------------------------------------------------
    def draw_player(self, surf):
        inv = self.invincible_timer > 0
        powered = self.fuel > 0
        O = 32
        pic = pygame.Surface((64, 64), pygame.SRCALPHA)

        # rocket flame (bigger when thrusting, green when invincible)
        if powered:
            L = 6 + random.randint(0, 4) + (9 if self.thrusting else 0)
            if inv:
                L = int(L * 1.6) + 4
            outer = (50, 240, 130) if inv else (255, 140, 30)
            inner = (215, 255, 225) if inv else (255, 235, 110)
            pygame.draw.polygon(pic, outer, [(O - 3, O + 19), (O + 3, O + 19), (O, O + 19 + L)])
            pygame.draw.polygon(pic, inner, [(O - 1, O + 19), (O + 1, O + 19), (O, O + 19 + max(2, L // 2))])
        elif int(self.anim_t * 10) % 5 == 0:
            pygame.draw.polygon(pic, (70, 70, 80), [(O - 2, O + 19), (O + 2, O + 19), (O, O + 22)])

        # fins, trunk body, window
        fin, fin_dark = (210, 50, 50), (150, 30, 40)
        pygame.draw.polygon(pic, fin, [(O - 4, O + 6), (O - 11, O + 19), (O - 4, O + 17)])
        pygame.draw.polygon(pic, fin, [(O + 4, O + 6), (O + 11, O + 19), (O + 4, O + 17)])
        pygame.draw.line(pic, fin_dark, (O - 4, O + 8), (O - 4, O + 17))
        pygame.draw.line(pic, fin_dark, (O + 3, O + 8), (O + 3, O + 17))
        pygame.draw.rect(pic, (125, 82, 42), (O - 4, O - 3, 8, 20))
        pygame.draw.rect(pic, (95, 60, 30), (O + 2, O - 3, 2, 20))
        pygame.draw.rect(pic, (190, 195, 205), (O - 4, O + 11, 8, 2))
        pygame.draw.rect(pic, (60, 60, 70), (O - 3, O + 17, 6, 2))
        pygame.draw.circle(pic, (80, 55, 28), (O, O + 5), 3)
        pygame.draw.circle(pic, (150, 220, 255), (O, O + 5), 2)
        pic.set_at((O - 1, O + 4), (255, 255, 255))

        # leafy nose cone
        blobs = ((0, -12, 9), (-7, -6, 6), (7, -6, 6), (0, -21, 6))
        for ox, oy, r in blobs:
            pygame.draw.circle(pic, (28, 100, 45), (O + ox, O + oy), r + 1)
        for ox, oy, r in blobs:
            pygame.draw.circle(pic, (50, 175, 70), (O + ox, O + oy), r)
        pygame.draw.rect(pic, (110, 225, 115), (O - 5, O - 19, 3, 2))
        pygame.draw.rect(pic, (110, 225, 115), (O - 9, O - 8, 2, 2))
        # determined face
        pygame.draw.rect(pic, (255, 255, 255), (O - 4, O - 14, 3, 3))
        pygame.draw.rect(pic, (255, 255, 255), (O + 1, O - 14, 3, 3))
        pygame.draw.rect(pic, (0, 0, 0), (O - 3, O - 13, 1, 2))
        pygame.draw.rect(pic, (0, 0, 0), (O + 2, O - 13, 1, 2))
        pygame.draw.line(pic, (20, 60, 25), (O - 6, O - 17), (O - 1, O - 14))
        pygame.draw.line(pic, (20, 60, 25), (O + 5, O - 17), (O, O - 14))
        pygame.draw.rect(pic, (20, 60, 25), (O - 2, O - 8, 5, 1))
        pygame.draw.rect(pic, (20, 60, 25), (O + 3, O - 9, 1, 1))

        # lean into the direction of travel (in chunky 3 degree steps)
        angle = clamp(-self.vx / MAX_SPEED * 14.0, -14.0, 14.0)
        angle = int(round(angle / 3.0)) * 3
        if angle:
            pic = pygame.transform.rotate(pic, angle)
        bob = 0 if self.thrusting else int(round(math.sin(self.anim_t * 4) * 1.5))
        surf.blit(pic, pic.get_rect(center=(int(self.px), int(self.py) + bob)))

    def draw_world(self, surf):
        surf.blit(self.sky, (0, 0))
        shift = self.px - LW / 2.0
        surf.blit(self.hill_far, (int(-40 - shift * 0.06), 0))
        surf.blit(self.hill_near, (int(-40 - shift * 0.12), 0))

        # the sun dims as you steal its light
        strength = max(0.15, 1.0 - self.stolen_sun / 80.0)
        self.glow_sun.set_alpha(int(255 * strength))
        sun_x, sun_y = LW // 2 + 30, 40
        blit_center(surf, self.glow_sun, sun_x, sun_y)
        pygame.draw.circle(surf, lerp_color((150, 130, 85), (255, 235, 95), strength),
                           (sun_x, sun_y), 11)

        # clouds shrink as you steal their rain
        rain_scale = max(0.3, 1.0 - self.stolen_rain / 90.0)
        shade = lerp_color((170, 175, 195), (255, 255, 255), rain_scale)
        under = lerp_color((140, 150, 175), (215, 225, 242), rain_scale)
        for cx0, cy, s, _spd, f in self.clouds:
            cx = (cx0 - shift * f) % (LW + 120) - 60
            s2 = s * rain_scale
            for ox, oy, r in CLOUD_BLOBS:
                pygame.draw.circle(surf, under, (int(cx + ox * s2), int(cy + oy * s2) + 2), max(2, int(r * s2)))
            for ox, oy, r in CLOUD_BLOBS:
                pygame.draw.circle(surf, shade, (int(cx + ox * s2), int(cy + oy * s2)), max(2, int(r * s2)))

        surf.blit(self.ground, (0, GROUND_Y))
        for t in self.trees:
            t.draw(surf, self.spr, max(0.2, 1.0 - self.points / 120.0), self.anger, self.anim_t)

        for it in self.items:
            it.draw(surf, self.spr, self.glow_item, self.anim_t)
        for hz in self.hazards:
            hz.draw(surf, self.spr)

        if self.state in ("play", "paused"):
            if self.invincible_timer > 0:
                flicker = self.invincible_timer < 2 and int(self.invincible_timer * 8) % 2 == 0
                if not flicker:
                    blit_center(surf, self.glow_aura[int(self.anim_t * 10) % 3],
                                int(self.px), int(self.py) - 4)
                    pygame.draw.circle(surf, (130, 255, 150), (int(self.px), int(self.py) - 4),
                                       21 + int(self.anim_t * 10) % 3, 1)
        if self.state != "over":
            blink = self.hurt_timer > 0 and int(self.hurt_timer * 12) % 2 == 0
            if not blink:
                self.draw_player(surf)

        for p in self.particles:
            p.draw(surf)
        for p in self.popups:
            draw_text(surf, self.f_tiny, p.text, (int(p.x), int(p.y)), p.color, anchor="center")

    def draw_hud(self, surf):
        for i in range(START_LIVES):
            surf.blit(self.spr.heart if i < self.lives else self.spr.heart_empty, (4 + i * 11, 4))

        # fuel bar
        frac = clamp(self.fuel / FUEL_MAX, 0.0, 1.0)
        low = frac < 0.25
        blink = int(self.anim_t * 6) % 2 == 0
        draw_text(surf, self.f_tiny, "FUEL", (4, 16), (255, 225, 140))
        bx, by, bw, bh = 28, 17, 72, 7
        pygame.draw.rect(surf, (20, 20, 30), (bx - 1, by - 1, bw + 2, bh + 2))
        col = (80, 220, 90) if frac > 0.5 else (250, 210, 60) if frac > 0.25 else (240, 60, 50)
        if not (low and blink) and frac > 0:
            pygame.draw.rect(surf, col, (bx, by, max(1, int(bw * frac)), bh))
        for i in range(1, 10):
            pygame.draw.line(surf, (20, 20, 30), (bx + bw * i // 10, by), (bx + bw * i // 10, by + bh - 1))
        pygame.draw.rect(surf, (255, 255, 255), (bx - 1, by - 1, bw + 2, bh + 2), 1)
        if low and blink:
            draw_text(surf, self.f_tiny, "OUT OF FUEL!" if self.fuel <= 0 else "LOW FUEL!",
                      (bx + bw + 5, 16), (255, 80, 70))

        # fertilizer power bar
        if self.invincible_timer > 0:
            f2 = self.invincible_timer / INVINCIBLE_SECONDS
            draw_text(surf, self.f_tiny, "POWER", (4, 28), (150, 255, 170))
            pygame.draw.rect(surf, (20, 60, 25), (28, 29, 72, 6))
            pygame.draw.rect(surf, (80, 255, 110), (28, 29, max(1, int(72 * f2)), 6))
            pygame.draw.rect(surf, (255, 255, 255), (27, 28, 74, 8), 1)

        draw_text(surf, self.f_tiny, "POINTS", (LW - 6, 3), (255, 235, 120), "topright")
        draw_text(surf, self.f_med, "%d" % self.points, (LW - 6, 11), anchor="topright")

        # bottom strip over the ground
        surf.blit(self.spr.rain, (6, GROUND_Y + 8))
        draw_text(surf, self.f_tiny, "RAIN %d" % self.stolen_rain, (16, GROUND_Y + 10), (200, 225, 255))
        surf.blit(self.spr.sun[0], (80, GROUND_Y + 6))
        draw_text(surf, self.f_tiny, "SUN %d" % self.stolen_sun, (96, GROUND_Y + 10), (255, 235, 140))
        draw_text(surf, self.f_tiny, "LV %d  SPEED x%.1f  TIME %ds" % (self.level, self.speed_mult, int(self.elapsed)),
                  (LW - 6, GROUND_Y + 10), anchor="topright")

    def overlay(self, surf, alpha):
        ov = self.overlays.get(alpha)
        if ov is None:
            ov = pygame.Surface((LW, LH), pygame.SRCALPHA)
            ov.fill((0, 0, 0, alpha))
            self.overlays[alpha] = ov
        surf.blit(ov, (0, 0))

    def draw(self):
        c = self.canvas
        self.draw_world(c)
        cx = LW // 2
        if self.state in ("play", "paused"):
            self.draw_hud(c)
        if self.state == "paused":
            self.overlay(c, 110)
            draw_text(c, self.f_big, "PAUSED", (cx, 95), anchor="center")
            draw_text(c, self.f_small, "PRESS P TO RESUME", (cx, 120), anchor="center")
        elif self.state == "title":
            self.overlay(c, 100)
            draw_text(c, self.f_huge, "ROCKET TREE", (cx, 42), (120, 255, 140), "center")
            draw_text(c, self.f_med, "SUNLIGHT THIEF", (cx, 70), (255, 235, 120), "center")
            lines = ["STEAL RAIN AND SUNLIGHT: 1 POINT EACH",
                     "DODGE THE ANGRY TREES' APPLES - 3 LIVES",
                     "FLYING USES FUEL - CATCH THE FUEL CANS!",
                     "FERTILIZER = 10 SECONDS INVINCIBLE",
                     "WASD / ARROWS: FLY    P: PAUSE    ESC: QUIT"]
            for i, line in enumerate(lines):
                draw_text(c, self.f_small, line, (cx, 100 + i * 14), anchor="center")
            if int(self.anim_t * 2) % 2 == 0:
                draw_text(c, self.f_med, "PRESS SPACE OR ENTER", (cx, 186), (255, 255, 255), "center")
        elif self.state == "over":
            self.overlay(c, 175)
            draw_text(c, self.f_huge, "GAME OVER", (cx, 32), (255, 80, 80), "center")
            for i in range(START_LIVES):
                c.blit(self.spr.heart_empty, (cx - 17 + i * 12, 54))
            draw_text(c, self.f_big, "POINTS: %d" % self.points, (cx, 80), (255, 235, 120), "center")
            cause = DEATH_TEXT.get(self.death_cause)
            if cause:
                draw_text(c, self.f_tiny, cause, (cx, 98), (255, 120, 100), "center")
            y = 112
            for line in self.comment_lines:
                draw_text(c, self.f_small, line, (cx, y), anchor="center")
                y += 12
            y += 4
            for line in self.verdict_lines:
                draw_text(c, self.f_small, line, (cx, y), self.verdict_color, "center")
                y += 12
            draw_text(c, self.f_tiny,
                      "RAIN %d   SUN %d   SURVIVED %ds   BEST %d" %
                      (self.stolen_rain, self.stolen_sun, int(self.elapsed), self.best),
                      (cx, y + 8), (200, 220, 255), "center")
            if int(self.anim_t * 2) % 2 == 0:
                draw_text(c, self.f_small, "PRESS R OR ENTER TO PLAY AGAIN", (cx, 186), anchor="center")
            draw_text(c, self.f_tiny, "ESC TO QUIT", (cx, 202), (180, 180, 190), "center")

        # scale the tiny canvas up with hard pixel edges
        scaled = pygame.transform.scale(c, (WIN_W, WIN_H))
        self.screen.fill((0, 0, 0))
        ox = oy = 0
        if self.shake > 0:
            ox = random.randint(-2, 2) * SCALE
            oy = random.randint(-2, 2) * SCALE
        self.screen.blit(scaled, (ox, oy))
        pygame.display.flip()

    # ----- loop ------------------------------------------------------------
    def quit(self):
        pygame.quit()
        sys.exit()

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.quit()
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self.quit()
        if self.state == "title" and event.key in (pygame.K_SPACE, pygame.K_RETURN):
            self.start_game()
        elif self.state == "over" and event.key in (pygame.K_r, pygame.K_RETURN, pygame.K_SPACE):
            self.start_game()
        elif self.state == "play" and event.key == pygame.K_p:
            self.state = "paused"
        elif self.state == "paused" and event.key == pygame.K_p:
            self.state = "play"

    def update(self, dt):
        if self.state != "paused":
            self.anim_t += dt
        if self.state == "play":
            self.update_play(dt)
        elif self.state in ("title", "over"):
            self.update_sky(dt)
            for t in self.trees:
                t.sway_phase += dt * 1.5
            self.update_particles(dt)

    def run(self):
        while True:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            for event in pygame.event.get():
                self.handle_event(event)
            self.update(dt)
            self.draw()


def main():
    Game().run()


if __name__ == "__main__":
    main()
