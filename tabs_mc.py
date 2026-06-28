"""
MINECRAFT TABS  --  Totally Accurate Battle Simulator, Minecraft edition!
By Toby | Built with Ursina (real 3D)

* Place two armies of blocky Minecraft mobs on a voxel battlefield
* Newest mobs: Warden, Breeze, Camel, Sniffer, Allay, Armadillo, Creaking, Bogged
* Classics: Zombie, Skeleton, Creeper, Iron Golem, Piglin Brute, Wolf, Pillager
* Hit SPACE to start the battle and watch the chaos!
* Real 3D camera, structures, and an epic (non-chiptune) procedural soundtrack.

CONTROLS
  Left click ............ place selected unit on YOUR half
  1-8 / click buttons ... pick a unit
  TAB ................... switch team you are placing (Red / Blue)
  SPACE ................. START the battle
  R ..................... reset back to setup
  Right-mouse drag ...... orbit camera   |   scroll = zoom   |   middle-drag = pan
  C ..................... clear your placed units
"""
import os
import sys
import math
import random

from pathlib import Path

from ursina import *

import mc_audio

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(APP_DIR, 'assets')

# Generate all audio files (cached after first run). Ursina resolves audio by
# name relative to application.asset_folder (set in boot), so we reference the
# clips by stem -- this works no matter what directory the game is launched from.
mc_audio.generate_all(ASSETS)
AUDIO = {
    'menu': 'menu_theme', 'battle': 'battle_theme',
    'hit': 'sfx_hit', 'death': 'sfx_death', 'explode': 'sfx_explode',
    'bow': 'sfx_bow', 'sonic': 'sfx_sonic', 'win': 'sfx_win',
    'place': 'sfx_place', 'start': 'sfx_start',
}


def play_sfx(name, volume=0.4):
    # One-shot SFX must auto-destroy or Audio entities pile up over a battle.
    if MUTED:
        return
    Audio(AUDIO[name], autoplay=True, volume=volume, auto_destroy=True)


# Set to True by the M key to silence all music and sound effects.
MUTED = False


# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------
FIELD_W = 34          # x extent (blocks)
FIELD_D = 26          # z extent (blocks)
START_GOLD = 1400
RED = 'red'
BLUE = 'blue'


def mc(r, g, b):
    return color.rgb(r / 255, g / 255, b / 255)


def mca(r, g, b, a):
    return color.rgba(r / 255, g / 255, b / 255, a)


TEAM_COLOR = {RED: mc(225, 65, 60), BLUE: mc(70, 120, 235)}
TEAM_NAME = {RED: 'RED', BLUE: 'BLUE'}

HELP_TEXT = """HOW TO PLAY  -  MINECRAFT TABS

GOAL: build an army, then watch it fight the enemy.
The last side with a unit standing WINS!

1.  You control RED. Your half is the FRONT (red) zone.
2.  Click a mob button at the bottom to pick a unit (it costs gold).
3.  Left-click your RED zone to place it. You have 1400 gold.
4.  Press TAB to switch to BLUE and build the enemy army.
5.  Press SPACE (or the START BATTLE button) to fight!

CONTROLS
   Left-click ....  place the selected unit on your half
   TAB ..........  switch side (RED / BLUE)
   C ............  clear your side        R ....  reset / new battle
   Right-drag ...  turn camera            Scroll ..  zoom in / out
   M ............  mute / unmute music
   H ............  show / hide this help

Click anywhere  -  or press H  -  to begin!"""


# ----------------------------------------------------------------------------
# Mob roster
# parts: list of (px, py, pz, sx, sy, sz, (r,g,b))  -- feet at y=0
# ----------------------------------------------------------------------------
def humanoid(skin, shirt, legs, head=None, arm_fwd=False, arm=None):
    head = head or skin
    arm = arm or shirt
    az = 0.28 if arm_fwd else 0.0
    ay = 0.95 if arm_fwd else 0.9
    return [
        (-0.13, 0.3, 0, 0.22, 0.6, 0.24, legs),
        (0.13, 0.3, 0, 0.22, 0.6, 0.24, legs),
        (0, 0.9, 0, 0.5, 0.66, 0.27, shirt),
        (-0.34, ay, az, 0.18, 0.62, 0.2, arm),
        (0.34, ay, az, 0.18, 0.62, 0.2, arm),
        (0, 1.45, 0, 0.5, 0.5, 0.5, head),
    ]


MOBS = {
    # ---------------- classics ----------------
    'zombie': dict(
        name='Zombie', cost=70, hp=120, dmg=14, rng=1.3, speed=2.0, cd=0.9,
        ranged=False, special=None, band_y=0.9, key='1',
        desc='Cheap melee horde',
        parts=humanoid(mc(110, 150, 95), mc(60, 110, 130), mc(60, 70, 130),
                       head=mc(95, 140, 80), arm_fwd=True)),
    'skeleton': dict(
        name='Skeleton', cost=110, hp=80, dmg=16, rng=12, speed=1.9, cd=1.3,
        ranged=True, proj='arrow', special=None, band_y=0.9, key='2',
        desc='Bow archer',
        parts=humanoid(mc(225, 225, 225), mc(200, 200, 200), mc(180, 180, 180))
        + [(0.42, 0.95, 0.1, 0.08, 0.9, 0.08, mc(120, 90, 50))]),
    'creeper': dict(
        name='Creeper', cost=130, hp=90, dmg=120, rng=1.6, speed=2.3, cd=1.0,
        ranged=False, special='explode', band_y=0.8, key='3',
        desc='Rushes in and EXPLODES',
        parts=[
            (-0.15, 0.2, 0.15, 0.22, 0.4, 0.22, mc(70, 150, 70)),
            (0.15, 0.2, 0.15, 0.22, 0.4, 0.22, mc(70, 150, 70)),
            (-0.15, 0.2, -0.15, 0.22, 0.4, 0.22, mc(70, 150, 70)),
            (0.15, 0.2, -0.15, 0.22, 0.4, 0.22, mc(70, 150, 70)),
            (0, 0.95, 0, 0.5, 0.9, 0.4, mc(85, 170, 80)),
            (0, 1.6, 0, 0.52, 0.52, 0.52, mc(90, 175, 85)),
            (-0.12, 1.62, 0.27, 0.12, 0.14, 0.04, mc(20, 30, 20)),
            (0.12, 1.62, 0.27, 0.12, 0.14, 0.04, mc(20, 30, 20)),
            (0, 1.45, 0.27, 0.14, 0.22, 0.04, mc(20, 30, 20)),
        ]),
    'iron_golem': dict(
        name='Iron Golem', cost=300, hp=600, dmg=55, rng=1.8, speed=1.2, cd=1.4,
        ranged=False, special='knockback', band_y=1.4, key='4', kb=3.2,
        desc='Tanky bruiser, huge knockback', scale=1.0,
        parts=[
            (-0.32, 0.55, 0, 0.34, 1.1, 0.4, mc(190, 195, 185)),
            (0.32, 0.55, 0, 0.34, 1.1, 0.4, mc(190, 195, 185)),
            (0, 1.55, 0, 0.85, 1.0, 0.6, mc(205, 208, 198)),
            (0, 1.45, 0.0, 0.7, 0.5, 0.62, mc(120, 165, 95)),
            (-0.7, 1.5, 0, 0.3, 1.3, 0.34, mc(185, 190, 180)),
            (0.7, 1.5, 0, 0.3, 1.3, 0.34, mc(185, 190, 180)),
            (0, 2.4, 0, 0.55, 0.6, 0.62, mc(200, 203, 193)),
            (0, 2.45, 0.3, 0.5, 0.16, 0.06, mc(150, 80, 90)),
        ]),
    'piglin': dict(
        name='Piglin Brute', cost=160, hp=180, dmg=34, rng=1.4, speed=2.6, cd=0.8,
        ranged=False, special=None, band_y=0.9, key='5',
        desc='Fast aggressive melee',
        parts=humanoid(mc(225, 150, 150), mc(90, 70, 60), mc(70, 55, 45),
                       head=mc(230, 160, 155), arm_fwd=True)
        + [(0.42, 1.2, 0.2, 0.1, 0.5, 0.1, mc(225, 200, 90)),
           (0.42, 1.45, 0.2, 0.3, 0.12, 0.3, mc(225, 200, 90))]),
    'wolf': dict(
        name='Wolf', cost=60, hp=70, dmg=18, rng=1.2, speed=4.2, cd=0.6,
        ranged=False, special=None, band_y=0.55, key='6',
        desc='Very fast, glass cannon pack',
        parts=[
            (0, 0.45, 0.1, 0.34, 0.4, 0.8, mc(210, 210, 215)),
            (0, 0.6, 0.55, 0.34, 0.36, 0.34, mc(225, 225, 230)),
            (0, 0.78, 0.62, 0.12, 0.18, 0.1, mc(210, 210, 215)),
            (-0.13, 0.78, 0.62, 0.1, 0.16, 0.08, mc(225, 225, 230)),
            (0.13, 0.78, 0.62, 0.1, 0.16, 0.08, mc(225, 225, 230)),
            (0, 0.4, -0.4, 0.1, 0.1, 0.4, mc(200, 200, 205)),
            (-0.12, 0.18, 0.35, 0.1, 0.36, 0.1, mc(180, 180, 185)),
            (0.12, 0.18, 0.35, 0.1, 0.36, 0.1, mc(180, 180, 185)),
            (-0.12, 0.18, -0.2, 0.1, 0.36, 0.1, mc(180, 180, 185)),
            (0.12, 0.18, -0.2, 0.1, 0.36, 0.1, mc(180, 180, 185)),
        ]),
    'pillager': dict(
        name='Pillager', cost=140, hp=110, dmg=22, rng=11, speed=2.0, cd=1.6,
        ranged=True, proj='arrow', special=None, band_y=0.9, key='7',
        desc='Crossbow ranged',
        parts=humanoid(mc(150, 160, 150), mc(75, 85, 80), mc(60, 65, 60),
                       head=mc(150, 160, 150), arm_fwd=True)
        + [(0, 1.0, 0.42, 0.5, 0.16, 0.1, mc(90, 65, 45)),
           (0, 1.0, 0.5, 0.1, 0.4, 0.08, mc(90, 65, 45))]),

    # ---------------- newest mobs ----------------
    'warden': dict(
        name='Warden', cost=550, hp=1400, dmg=110, rng=14, speed=1.1, cd=2.2,
        ranged=True, proj='sonic', special='boss', band_y=1.6, key='8',
        desc='NEWEST: sonic boom boss, monstrous HP', scale=1.0,
        parts=[
            (-0.4, 0.7, 0, 0.42, 1.4, 0.5, mc(20, 45, 50)),
            (0.4, 0.7, 0, 0.42, 1.4, 0.5, mc(20, 45, 50)),
            (0, 2.1, 0, 1.0, 1.5, 0.7, mc(25, 55, 60)),
            (0, 2.2, 0.34, 0.7, 0.9, 0.06, mc(40, 220, 210)),
            (-0.85, 2.2, 0, 0.35, 1.7, 0.42, mc(22, 50, 55)),
            (0.85, 2.2, 0, 0.35, 1.7, 0.42, mc(22, 50, 55)),
            (0, 3.2, 0, 0.78, 0.7, 0.7, mc(18, 40, 45)),
            (-0.18, 3.3, 0.36, 0.14, 0.1, 0.04, mc(60, 230, 220)),
            (0.18, 3.3, 0.36, 0.14, 0.1, 0.04, mc(60, 230, 220)),
            (0, 3.6, 0, 0.5, 0.18, 0.5, mc(45, 210, 200)),
        ]),
    'breeze': dict(
        name='Breeze', cost=150, hp=90, dmg=20, rng=10, speed=3.4, cd=1.1,
        ranged=True, proj='wind', special='hop', band_y=1.0, key='9',
        desc='NEWEST: wind charges + huge knockback', kb=3.5,
        parts=[
            (0, 0.7, 0, 0.5, 0.9, 0.5, mca(150, 210, 235, 0.85)),
            (0, 1.35, 0, 0.55, 0.5, 0.55, mca(180, 230, 245, 0.9)),
            (0, 0.5, 0, 0.7, 0.16, 0.7, mca(120, 190, 225, 0.7)),
            (0, 1.05, 0, 0.64, 0.16, 0.64, mca(135, 200, 230, 0.7)),
            (-0.12, 1.4, 0.27, 0.1, 0.12, 0.04, mc(40, 90, 130)),
            (0.12, 1.4, 0.27, 0.1, 0.12, 0.04, mc(40, 90, 130)),
        ]),
    'camel': dict(
        name='Camel', cost=240, hp=420, dmg=40, rng=1.8, speed=2.2, cd=1.3,
        ranged=False, special='dash', band_y=1.3, key='Q', kb=2.6,
        desc='NEWEST: tanky, dashes with knockback',
        parts=[
            (-0.3, 0.75, 0.35, 0.22, 1.5, 0.22, mc(225, 200, 140)),
            (0.3, 0.75, 0.35, 0.22, 1.5, 0.22, mc(225, 200, 140)),
            (-0.3, 0.75, -0.35, 0.22, 1.5, 0.22, mc(225, 200, 140)),
            (0.3, 0.75, -0.35, 0.22, 1.5, 0.22, mc(225, 200, 140)),
            (0, 1.7, 0, 0.7, 0.7, 1.5, mc(235, 210, 150)),
            (0, 2.15, 0.35, 0.4, 0.4, 0.3, mc(220, 195, 135)),
            (0, 2.2, -0.05, 0.4, 0.4, 0.3, mc(220, 195, 135)),
            (0, 2.1, 0.85, 0.32, 0.7, 0.34, mc(235, 210, 150)),
            (0, 2.5, 1.0, 0.34, 0.34, 0.36, mc(240, 215, 155)),
        ]),
    'sniffer': dict(
        name='Sniffer', cost=320, hp=750, dmg=42, rng=1.9, speed=1.0, cd=1.6,
        ranged=False, special='knockback', band_y=1.2, key='W', kb=2.4,
        desc='NEWEST: enormous HP wall',
        parts=[
            (0, 1.0, 0, 1.3, 1.4, 2.0, mc(190, 95, 110)),
            (0, 1.7, 1.0, 0.9, 1.0, 0.7, mc(205, 110, 120)),
            (0, 2.25, 1.1, 0.3, 0.4, 0.3, mc(120, 200, 130)),
            (-0.45, 0.4, 0.9, 0.3, 0.8, 0.4, mc(170, 85, 100)),
            (0.45, 0.4, 0.9, 0.3, 0.8, 0.4, mc(170, 85, 100)),
            (-0.45, 0.4, -0.8, 0.3, 0.8, 0.4, mc(170, 85, 100)),
            (0.45, 0.4, -0.8, 0.3, 0.8, 0.4, mc(170, 85, 100)),
        ]),
    'allay': dict(
        name='Allay', cost=180, hp=60, dmg=0, rng=8, speed=3.0, cd=1.0,
        ranged=False, special='heal', band_y=1.4, key='E', fly=1.4, heal=18,
        desc='NEWEST: flying healer, buffs allies',
        parts=[
            (0, 1.0, 0, 0.34, 0.5, 0.28, mc(70, 150, 230)),
            (0, 1.4, 0, 0.34, 0.34, 0.34, mc(95, 175, 245)),
            (-0.12, 1.45, 0.18, 0.07, 0.08, 0.03, mc(20, 30, 60)),
            (0.12, 1.45, 0.18, 0.07, 0.08, 0.03, mc(20, 30, 60)),
            (-0.34, 1.05, -0.1, 0.06, 0.5, 0.34, mca(180, 220, 255, 0.6)),
            (0.34, 1.05, -0.1, 0.06, 0.5, 0.34, mca(180, 220, 255, 0.6)),
        ]),
    'armadillo': dict(
        name='Armadillo', cost=150, hp=260, dmg=26, rng=1.3, speed=2.4, cd=0.9,
        ranged=False, special='roll', band_y=0.6, key='A', armor=0.45,
        desc='NEWEST: rolls in, 45% armor',
        parts=[
            (0, 0.5, 0, 0.6, 0.55, 0.85, mc(120, 90, 70)),
            (0, 0.78, 0, 0.5, 0.3, 0.7, mc(95, 70, 55)),
            (0, 0.4, 0.55, 0.3, 0.3, 0.3, mc(180, 150, 130)),
            (-0.18, 0.15, 0.4, 0.1, 0.3, 0.1, mc(140, 110, 90)),
            (0.18, 0.15, 0.4, 0.1, 0.3, 0.1, mc(140, 110, 90)),
            (-0.18, 0.15, -0.3, 0.1, 0.3, 0.1, mc(140, 110, 90)),
            (0.18, 0.15, -0.3, 0.1, 0.3, 0.1, mc(140, 110, 90)),
        ]),
    'creaking': dict(
        name='Creaking', cost=260, hp=200, dmg=38, rng=1.5, speed=2.4, cd=1.0,
        ranged=False, special='revive', band_y=1.4, key='T',
        desc='NEWEST: revives ONCE, hard to kill',
        parts=[
            (-0.2, 0.6, 0, 0.18, 1.2, 0.2, mc(75, 60, 50)),
            (0.2, 0.6, 0, 0.18, 1.2, 0.2, mc(75, 60, 50)),
            (0, 1.5, 0, 0.5, 0.7, 0.35, mc(90, 72, 58)),
            (-0.5, 1.6, 0, 0.16, 1.0, 0.18, mc(70, 56, 46)),
            (0.5, 1.6, 0, 0.16, 1.0, 0.18, mc(70, 56, 46)),
            (0, 2.2, 0, 0.5, 0.5, 0.5, mc(80, 64, 52)),
            (-0.12, 2.25, 0.27, 0.1, 0.12, 0.05, mc(255, 140, 30)),
            (0.12, 2.25, 0.27, 0.1, 0.12, 0.05, mc(255, 140, 30)),
            (0, 2.7, 0, 0.3, 0.4, 0.3, mc(60, 90, 55)),
        ]),
    'bogged': dict(
        name='Bogged', cost=170, hp=95, dmg=14, rng=12, speed=1.9, cd=1.5,
        ranged=True, proj='poison', special='poison', band_y=0.9, key='Y',
        desc='NEWEST: poison arrows (damage over time)',
        parts=humanoid(mc(180, 200, 175), mc(150, 180, 150), mc(120, 150, 120),
                       head=mc(160, 190, 160))
        + [(0, 1.7, 0, 0.5, 0.2, 0.5, mc(90, 150, 90)),
           (-0.18, 1.78, 0.1, 0.12, 0.2, 0.12, mc(110, 170, 110)),
           (0.2, 1.75, -0.1, 0.1, 0.18, 0.1, mc(110, 170, 110)),
           (0.42, 0.95, 0.1, 0.08, 0.9, 0.08, mc(120, 90, 50))]),
}

ROSTER = list(MOBS.keys())


# ----------------------------------------------------------------------------
# Particles
# ----------------------------------------------------------------------------
particles = []


class Particle(Entity):
    def __init__(self, pos, col, vel, life=0.6, scl=0.16, grav=-9):
        super().__init__(model='cube', color=col, position=pos,
                         scale=scl, shader=None)
        self.vel = Vec3(*vel)
        self.life = life
        self.max_life = life
        self.grav = grav
        particles.append(self)

    def step(self, dt):
        self.vel.y += self.grav * dt
        self.position += self.vel * dt
        if self.y < 0.05:
            self.y = 0.05
            self.vel *= 0.4
            self.vel.y = abs(self.vel.y) * 0.3
        self.life -= dt
        self.scale *= (1 - dt * 1.2)
        if self.life <= 0:
            if self in particles:
                particles.remove(self)
            destroy(self)


def burst(pos, col, n=10, power=4, life=0.6, scl=0.16):
    for _ in range(n):
        ang = random.uniform(0, math.tau)
        sp = random.uniform(0.3, 1) * power
        vel = (math.cos(ang) * sp, random.uniform(2, 5), math.sin(ang) * sp)
        Particle(Vec3(pos[0], pos[1], pos[2]), col, vel, life, scl)


# ----------------------------------------------------------------------------
# Projectiles
# ----------------------------------------------------------------------------
projectiles = []


class Projectile(Entity):
    def __init__(self, owner, target, kind):
        self.kind = kind
        self.owner = owner
        self.target = target
        self.dmg = owner.dmg
        start = owner.world_position + Vec3(0, owner.proj_h, 0)
        cfg = {
            'arrow': dict(m='cube', c=mc(200, 200, 200), s=(0.08, 0.08, 0.5), spd=22, kb=0.4),
            'poison': dict(m='cube', c=mc(120, 200, 110), s=(0.1, 0.1, 0.5), spd=20, kb=0.3),
            'wind': dict(m='sphere', c=mca(220, 240, 255, 0.8), s=0.4, spd=16, kb=owner.kb),
            'sonic': dict(m='cube', c=mc(60, 230, 220), s=(0.7, 0.7, 0.7), spd=26, kb=1.6),
        }[kind]
        super().__init__(model=cfg['m'], color=cfg['c'], position=start,
                         scale=cfg['s'])
        self.speed = cfg['spd']
        self.kb = cfg['kb']
        projectiles.append(self)

    def step(self, dt):
        if not self.target or not getattr(self.target, 'alive', False):
            self._die()
            return
        tgt = self.target.world_position + Vec3(0, self.target.proj_h, 0)
        to = tgt - self.world_position
        d = to.length()
        if d < 0.6:
            self.target.take_damage(self.dmg, self.owner)
            dirv = Vec3(to.x, 0, to.z)
            if dirv.length() > 0.01 and self.kb > 0:
                self.target.knockback(dirv.normalized(), self.kb)
            if self.kind == 'poison':
                self.target.apply_poison(6, 4)
                burst((tgt.x, tgt.y, tgt.z), mc(120, 200, 110), 6, 2, 0.4, 0.1)
            elif self.kind == 'sonic':
                burst((tgt.x, tgt.y, tgt.z), mc(60, 230, 220), 14, 5, 0.4)
                play_sfx('sonic', 0.4)
            elif self.kind == 'wind':
                burst((tgt.x, tgt.y, tgt.z), mc(220, 240, 255), 10, 4, 0.4)
            else:
                burst((tgt.x, tgt.y, tgt.z), self.color, 5, 2, 0.3, 0.1)
            self._die()
            return
        self.look_at(tgt)
        self.position += to.normalized() * self.speed * dt

    def _die(self):
        if self in projectiles:
            projectiles.remove(self)
        destroy(self)


# ----------------------------------------------------------------------------
# Unit
# ----------------------------------------------------------------------------
units = []
corpses = []        # dead units still fading out (so reset can clean them)


class Unit(Entity):
    def __init__(self, kind, team, pos):
        super().__init__(position=(pos[0], 0, pos[2]))
        self.kind = kind
        self.team = team
        cfg = MOBS[kind]
        self.cfg = cfg
        self.max_hp = cfg['hp']
        self.hp = cfg['hp']
        self.dmg = cfg['dmg']
        self.rng = cfg['rng']
        self.base_speed = cfg['speed']
        self.cd = cfg['cd']
        self.ranged = cfg['ranged']
        self.special = cfg.get('special')
        self.kb = cfg.get('kb', 0.8)
        self.armor = cfg.get('armor', 0.0)
        self.fly = cfg.get('fly', 0.0)
        self.proj_kind = cfg.get('proj')
        self.heal_amt = cfg.get('heal', 0)
        self.scale_mul = cfg.get('scale', 1.0)

        self.alive = True
        self.atk_timer = random.uniform(0, 0.4)
        self.target = None
        self.retarget = 0
        self.fuse = -1
        self.poison_t = 0
        self.poison_dps = 0
        self.stun_t = 0
        self.revived = False
        self.proj_h = cfg['band_y']

        self.model_root = Entity(parent=self)
        self.model_root.scale = self.scale_mul
        self._build_model()
        self.y = self.fly

        # health bar
        self.bar_bg = Entity(model='cube', color=color.rgb(0, 0, 0),
                             scale=(1.1, 0.16, 0.05))
        self.bar = Entity(model='cube', color=color.lime,
                          scale=(1.05, 0.12, 0.06))
        self.bar_h = cfg['band_y'] * self.scale_mul + 1.0 + self.fly
        units.append(self)

    def _build_model(self):
        for p in self.cfg['parts']:
            Entity(parent=self.model_root, model='cube', color=p[6],
                   position=(p[0], p[1], p[2]), scale=(p[3], p[4], p[5]))
        # team band around chest
        by = self.cfg['band_y']
        Entity(parent=self.model_root, model='cube', color=TEAM_COLOR[self.team],
               position=(0, by, 0), scale=(0.62, 0.16, 0.3))
        # banner pole
        Entity(parent=self.model_root, model='cube', color=mc(90, 70, 50),
               position=(0, by + 1.2, -0.3), scale=(0.05, 1.4, 0.05))
        Entity(parent=self.model_root, model='cube', color=TEAM_COLOR[self.team],
               position=(0.18, by + 1.6, -0.3), scale=(0.4, 0.5, 0.04))

    # -------- combat helpers --------
    def take_damage(self, amount, source=None):
        if not self.alive:
            return
        amount *= (1 - self.armor)
        self.hp -= amount
        self.model_root.blink(color.red, duration=0.12)
        if self.hp <= 0:
            self.die()

    def apply_poison(self, dps, dur):
        self.poison_t = max(self.poison_t, dur)
        self.poison_dps = dps

    def knockback(self, dirv, amount):
        if not self.alive or self.special == 'boss':
            return
        np_ = self.position + dirv * amount
        np_.x = clamp(np_.x, -FIELD_W / 2 + 1, FIELD_W / 2 - 1)
        np_.z = clamp(np_.z, -FIELD_D / 2 + 1, FIELD_D / 2 - 1)
        self.animate_position(Vec3(np_.x, self.fly, np_.z), duration=0.18,
                              curve=curve.out_expo)
        # Brief stun so AI movement doesn't fight the knockback tween.
        self.stun_t = max(self.stun_t, 0.18)

    def _final_destroy(self):
        if self in corpses:
            corpses.remove(self)
            destroy(self)

    def die(self):
        if self.special == 'revive' and not self.revived:
            self.revived = True
            self.hp = self.max_hp
            self.poison_t = 0
            self.poison_dps = 0
            burst((self.x, 1, self.z), mc(255, 140, 30), 18, 4)
            self.model_root.blink(mc(255, 140, 30), duration=0.3)
            return
        self.alive = False
        burst((self.x, 1, self.z), self.cfg['parts'][0][6], 16, 4)
        play_sfx('death', 0.3)
        destroy(self.bar_bg)
        destroy(self.bar)
        self.model_root.animate_rotation((90, self.model_root.rotation_y, 0),
                                         duration=0.4, curve=curve.out_bounce)
        for c in self.model_root.children:
            c.fade_out(duration=1.0, delay=0.4)
        if self in units:
            units.remove(self)
        corpses.append(self)
        invoke(self._final_destroy, delay=1.6)

    def explode_now(self):
        play_sfx('explode', 0.5)
        burst((self.x, 1, self.z), mc(255, 200, 80), 26, 7, 0.7, 0.25)
        for u in list(units):
            if u.team != self.team and u.alive:
                d = (u.position - self.position).length()
                if d < 4.5:
                    u.take_damage(self.dmg * (1 - d / 4.5))
                    dirv = Vec3(u.x - self.x, 0, u.z - self.z)
                    if dirv.length() > 0.01:
                        u.knockback(dirv.normalized(), 3.0)
        self.alive = False
        destroy(self.bar_bg)
        destroy(self.bar)
        if self in units:
            units.remove(self)
        corpses.append(self)
        invoke(self._final_destroy, delay=0.05)

    # -------- per-frame AI --------
    def nearest_enemy(self):
        best, bd = None, 1e9
        for u in units:
            if u.team != self.team and u.alive:
                d = (u.position - self.position).length_squared()
                if d < bd:
                    bd, best = d, u
        return best

    def nearest_wounded_ally(self):
        best, bd = None, 1e9
        for u in units:
            if (u.team == self.team and u.alive and u is not self
                    and u.hp < u.max_hp):
                d = (u.position - self.position).length_squared()
                if d < bd:
                    bd, best = d, u
        return best

    def think(self, dt):
        if not self.alive:
            return
        if self.poison_t > 0:
            self.poison_t -= dt
            self.hp -= self.poison_dps * dt
            if random.random() < 0.1:
                burst((self.x, 1, self.z), mc(120, 200, 110), 1, 1, 0.3, 0.08)
            if self.hp <= 0:
                self.die()
                return

        if self.stun_t > 0:
            # Being knocked back: let the tween move us, skip AI this frame.
            self.stun_t -= dt
            return

        self.atk_timer -= dt
        self.retarget -= dt
        if self.retarget <= 0 or not self.target or not self.target.alive:
            self.target = self.nearest_enemy()
            self.retarget = 0.3

        # Allay = support healer
        if self.special == 'heal':
            self._support(dt)
            return

        tgt = self.target
        if not tgt:
            return
        to = Vec3(tgt.x - self.x, 0, tgt.z - self.z)
        dist = to.length()
        if dist > 0.01:
            self.model_root.rotation_y = math.degrees(math.atan2(to.x, to.z))

        speed = self.base_speed
        if self.special == 'roll' and dist > 4:
            speed *= 2.0
            self.model_root.rotation_x = (time.time() * 600) % 360
        elif self.special == 'dash' and dist > 5:
            speed *= 1.8

        if dist > self.rng:
            # separation from close allies to avoid clumping
            sep = self._separation()
            move = to.normalized() * speed + sep
            step = move.normalized() * speed * dt
            nx = clamp(self.x + step.x, -FIELD_W / 2 + 1, FIELD_W / 2 - 1)
            nz = clamp(self.z + step.z, -FIELD_D / 2 + 1, FIELD_D / 2 - 1)
            self.x, self.z = nx, nz
            # walk bob
            self.model_root.y = abs(math.sin(time.time() * speed * 3)) * 0.08
            if self.special == 'hop':
                self.model_root.y += abs(math.sin(time.time() * 4)) * 0.2
        else:
            if self.special == 'explode':
                if self.fuse < 0:
                    self.fuse = 0.7
                self.fuse -= dt
                f = 1 + (0.7 - self.fuse) * 0.6
                self.model_root.scale = self.scale_mul * f
                self.model_root.blink(color.white, duration=0.15)
                if self.fuse <= 0:
                    self.explode_now()
                return
            if self.atk_timer <= 0:
                self._attack(tgt, to)
                self.atk_timer = self.cd

    def _separation(self):
        push = Vec3(0, 0, 0)
        for u in units:
            if u is self or not u.alive or u.team != self.team:
                continue
            d = self.position - u.position
            dl = d.length()
            if 0.01 < dl < 1.1:
                push += Vec3(d.x, 0, d.z).normalized() * (1.1 - dl)
        return push * 1.5

    def _attack(self, tgt, to):
        # lunge
        self.model_root.animate_position(
            Vec3(0, self.model_root.y, 0.25), duration=0.08,
            curve=curve.out_expo)
        self.model_root.animate_position(
            Vec3(0, self.model_root.y, 0), duration=0.12, delay=0.08)
        if self.ranged:
            Projectile(self, tgt, self.proj_kind)
            snd = 'sonic' if self.proj_kind == 'sonic' else 'bow'
            if self.proj_kind != 'sonic':
                play_sfx('bow', 0.25)
        else:
            tgt.take_damage(self.dmg, self)
            play_sfx('hit', 0.25)
            if self.kb > 1.2 or self.special in ('knockback', 'dash'):
                if to.length() > 0.01:
                    tgt.knockback(to.normalized(), self.kb)
            burst((tgt.x, tgt.proj_h, tgt.z), color.white, 4, 2, 0.25, 0.1)

    def _support(self, dt):
        ally = self.nearest_wounded_ally()
        # gentle hovering
        self.model_root.y = math.sin(time.time() * 3) * 0.15
        if not ally:
            # drift toward team's center mass
            cx = sum(u.x for u in units if u.team == self.team and u.alive)
            cnt = sum(1 for u in units if u.team == self.team and u.alive)
            if cnt:
                tx = cx / cnt
                self.x = lerp(self.x, clamp(tx, -FIELD_W / 2 + 1, FIELD_W / 2 - 1),
                              dt * 0.6)
            return
        to = Vec3(ally.x - self.x, 0, ally.z - self.z)
        d = to.length()
        if d > self.rng:
            step = to.normalized() * self.base_speed * dt
            self.x = clamp(self.x + step.x, -FIELD_W / 2 + 1, FIELD_W / 2 - 1)
            self.z = clamp(self.z + step.z, -FIELD_D / 2 + 1, FIELD_D / 2 - 1)
        elif self.atk_timer <= 0:
            ally.hp = min(ally.max_hp, ally.hp + self.heal_amt)
            ally.model_root.blink(mc(120, 230, 160), duration=0.2)
            burst((ally.x, ally.proj_h, ally.z), mc(150, 240, 180), 5, 2, 0.4, 0.1)
            self.atk_timer = self.cd

    def update_bar(self):
        if not self.alive:
            return
        frac = clamp(self.hp / self.max_hp, 0, 1)
        self.bar_bg.world_position = self.world_position + Vec3(0, self.bar_h, 0)
        self.bar.world_position = self.bar_bg.world_position + Vec3(0, 0, -0.01)
        self.bar.scale_x = 1.05 * frac
        self.bar.x = self.bar_bg.world_position.x  # keep centered-left handled below
        self.bar.color = mc(int(255 * (1 - frac)), int(220 * frac + 30), 40)
        # billboard toward camera
        self.bar_bg.look_at(camera.world_position)
        self.bar.look_at(camera.world_position)


# ----------------------------------------------------------------------------
# World / structures
# ----------------------------------------------------------------------------
def build_block(x, y, z, col, s=1.0):
    return Entity(model='cube', color=col, position=(x, y, z), scale=s)


def build_world():
    # voxel ground
    gx = FIELD_W // 2 + 3
    gz = FIELD_D // 2 + 3
    grass1 = mc(78, 150, 44)
    grass2 = mc(122, 188, 72)
    dirt = mc(134, 96, 67)
    parent = Entity()
    for x in range(-gx, gx + 1):
        for z in range(-gz, gz + 1):
            top = grass1 if (x + z) % 2 == 0 else grass2
            edge = abs(x) > FIELD_W // 2 or abs(z) > FIELD_D // 2
            c = mc(120, 110, 95) if edge else top
            Entity(parent=parent, model='cube', color=c,
                   position=(x, -0.5, z), scale=(1, 1, 1))
    # dirt underlayer
    Entity(model='cube', color=dirt, position=(0, -1.5, 0),
           scale=(2 * gx + 1, 1, 2 * gz + 1))

    # center divider line (bright, so each side is obvious)
    Entity(model='cube', color=mca(255, 240, 150, 0.95),
           position=(0, 0.04, 0), scale=(FIELD_W, 0.08, 0.45))

    # invisible picker plane
    global ground_picker
    ground_picker = Entity(model='plane', scale=(FIELD_W, 1, FIELD_D),
                           position=(0, 0.01, 0), collider='box', visible=False)

    _trees()
    _trial_chamber(-FIELD_W / 2 - 1, -FIELD_D / 2 - 1)
    _trial_chamber(FIELD_W / 2 + 1, FIELD_D / 2 + 1)
    _ancient_city(FIELD_W / 2 + 1.5, -FIELD_D / 2 - 1.5)
    _village_house(-FIELD_W / 2 - 2.5, FIELD_D / 2 + 1.5)


def _trees():
    spots = [(-FIELD_W / 2 - 1, -3), (-FIELD_W / 2 - 1, 5),
             (FIELD_W / 2 + 1, -5), (FIELD_W / 2 + 1, 3)]
    for (x, z) in spots:
        for y in range(4):
            build_block(x, 0.5 + y, z, mc(102, 76, 48), 0.7)
        leaf = mc(60, 130, 50)
        for lx in (-1, 0, 1):
            for lz in (-1, 0, 1):
                build_block(x + lx, 4.2, z + lz, leaf, 1.0)
        for lx in (-1, 0, 1):
            build_block(x + lx, 5.0, z, leaf, 0.9)
            build_block(x, 5.0, z + lx, leaf, 0.9)
        build_block(x, 5.7, z, leaf, 0.9)


def _trial_chamber(cx, cz):
    tuff = mc(108, 108, 112)
    copper = mc(190, 120, 90)
    for dx in (-1, 1):
        for dz in (-1, 1):
            for y in range(3):
                build_block(cx + dx, 0.5 + y, cz + dz, tuff, 0.9)
            build_block(cx + dx, 3.3, cz + dz, copper, 0.95)
    build_block(cx, 0.6, cz, mc(40, 60, 70), 1.2)
    build_block(cx, 1.2, cz, mc(90, 200, 210), 0.5)


def _ancient_city(cx, cz):
    deep = mc(55, 58, 66)
    sculk = mc(20, 40, 55)
    for y in range(5):
        build_block(cx, 0.5 + y, cz, deep, 1.0)
    build_block(cx, 5.5, cz, sculk, 1.3)
    build_block(cx, 6.2, cz, mc(40, 200, 190), 0.4)
    for dx in (-1.4, 1.4):
        build_block(cx + dx, 0.5, cz, sculk, 0.9)
        build_block(cx + dx, 0.9, cz, mc(40, 180, 175), 0.25)


def _village_house(cx, cz):
    plank = mc(160, 120, 75)
    log = mc(110, 82, 52)
    roof = mc(140, 70, 55)
    for dx in range(-2, 3):
        for dz in range(-2, 3):
            edge = abs(dx) == 2 or abs(dz) == 2
            if edge:
                for y in range(3):
                    build_block(cx + dx, 0.5 + y, cz + dz, plank, 1.0)
    for (dx, dz) in [(-2, -2), (2, -2), (-2, 2), (2, 2)]:
        for y in range(3):
            build_block(cx + dx, 0.5 + y, cz + dz, log, 1.0)
    for i, w in enumerate(range(5, 0, -1)):
        build_block(cx, 3.2 + i * 0.5, cz, roof, w)


# ----------------------------------------------------------------------------
# Game manager
# ----------------------------------------------------------------------------
class Game:
    def __init__(self):
        self.phase = 'setup'
        self.gold = {RED: START_GOLD, BLUE: START_GOLD}
        self.team = RED
        self.selected = ROSTER[0]
        self.winner = None
        self.music = None
        self._build_ui()
        self.play_music('menu')
        self.refresh_hud()

    # ---- music ----
    def play_music(self, which):
        if self.music:
            self.music.stop()
            destroy(self.music)
        self.music = Audio(AUDIO[which], loop=True, autoplay=True,
                           volume=0.0 if MUTED else 0.55)

    # ---- ui ----
    def _build_ui(self):
        self.title = Text('MINECRAFT  TABS', origin=(0, 0), x=0, y=0.46,
                          scale=1.6, color=color.rgb(1, 1, 1))
        # Top-left gold/turn readout (left-aligned so it never clips off-screen).
        self.hud = Text('', origin=(-0.5, 0), x=-0.82, y=0.46, scale=1.0)
        # Top-right music indicator.
        self.audio_lbl = Text('', origin=(0.5, 0), x=0.82, y=0.46, scale=0.9,
                              color=mc(190, 230, 190))
        # One short instruction line, centred just above the unit buttons.
        self.hint = Text('', origin=(0, 0), x=0, y=-0.235, scale=0.85,
                         color=mc(235, 235, 215))

        # Big labels so it's obvious which half belongs to whom.
        self.lbl_blue = Text('ENEMY  -  BLUE', origin=(0, 0), x=0, y=0.34,
                             scale=1.4, color=mc(95, 175, 255))
        self.lbl_red = Text('YOUR SIDE  -  RED  (place units in front of the line)',
                            origin=(0, 0), x=0, y=-0.12, scale=1.0,
                            color=mc(255, 110, 110))

        # Translucent coloured zones painted on each half (setup phase only).
        self.zone_red = Entity(model='plane', color=mca(255, 60, 60, 0.26),
                               position=(0, 0.05, -FIELD_D / 4),
                               scale=(FIELD_W, 1, FIELD_D / 2), double_sided=True)
        self.zone_blue = Entity(model='plane', color=mca(70, 120, 255, 0.26),
                                position=(0, 0.05, FIELD_D / 4),
                                scale=(FIELD_W, 1, FIELD_D / 2), double_sided=True)

        self.banner = Text('', origin=(0, 0), x=0, y=0.1, scale=3,
                           color=color.yellow, enabled=False)

        # unit buttons along the bottom (two rows)
        self.buttons = {}
        per_row = 8
        for i, kind in enumerate(ROSTER):
            cfg = MOBS[kind]
            row = i // per_row
            col_i = i % per_row
            bx = -0.78 + col_i * 0.222
            by = -0.30 - row * 0.085
            b = Button(parent=camera.ui, text=f"{cfg['name']}\n{cfg['cost']}g",
                       color=mc(60, 60, 70), scale=(0.2, 0.075),
                       position=(bx, by), text_size=0.5)
            b.kind = kind
            b.on_click = Func(self.select, kind)
            self.buttons[kind] = b
        self.start_btn = Button(parent=camera.ui, text='START  BATTLE  (Space)',
                                color=mc(70, 160, 70), scale=(0.34, 0.07),
                                position=(0, -0.47),
                                on_click=Func(self.start_battle))

        self._build_help()
        self._update_audio_label()

    def _build_help(self):
        # Full-screen dark panel (a Button so it also captures the dismiss click).
        self.help_bg = Button(parent=camera.ui, model='quad',
                              color=mca(8, 10, 18, 0.93),
                              highlight_color=mca(8, 10, 18, 0.93),
                              pressed_color=mca(8, 10, 18, 0.93),
                              scale=(2.2, 1.3), z=-1,
                              on_click=Func(self.toggle_help))
        self.help_text = Text(parent=camera.ui, text=HELP_TEXT, origin=(0, 0),
                              x=0, y=0, scale=0.95, z=-1.1,
                              color=color.white, line_height=1.15)
        self.help_items = [self.help_bg, self.help_text]
        self.help_open = True

    def _update_audio_label(self):
        self.audio_lbl.text = 'Music: OFF  (M)' if MUTED else 'Music: ON  (M)'

    def _set_setup_markers(self, visible):
        for e in (self.zone_red, self.zone_blue, self.lbl_red, self.lbl_blue):
            e.enabled = visible

    def toggle_help(self):
        self.help_open = not self.help_open
        for e in self.help_items:
            e.enabled = self.help_open

    def toggle_mute(self):
        global MUTED
        MUTED = not MUTED
        if self.music:
            self.music.volume = 0.0 if MUTED else 0.55
        self._update_audio_label()

    def select(self, kind):
        self.selected = kind
        self.refresh_hud()

    def refresh_hud(self):
        for kind, b in self.buttons.items():
            b.color = mc(120, 100, 40) if kind == self.selected else mc(60, 60, 70)
        tc = TEAM_NAME[self.team]
        self.hud.text = (f"Placing: <{'red' if self.team==RED else 'azure'}>{tc}</>  "
                         f"<white>Gold  R:{self.gold[RED]}  B:{self.gold[BLUE]}")
        self.hud.color = TEAM_COLOR[self.team]
        if self.phase == 'setup':
            sel = MOBS[self.selected]
            side = 'RED (front)' if self.team == RED else 'BLUE (back)'
            self.hint.text = (f"Selected: {sel['name']} ({sel['cost']}g) - {sel['desc']}    "
                              f"Click your {side} half to place.   "
                              f"[TAB] switch  [C] clear  [H] help")
        elif self.phase == 'battle':
            r = sum(1 for u in units if u.team == RED and u.alive)
            b = sum(1 for u in units if u.team == BLUE and u.alive)
            self.hint.text = f"BATTLE!   Red: {r}    Blue: {b}     [R] reset   [M] music"
        else:
            self.hint.text = "Press R to play again!     [H] help"

    # ---- placement ----
    def try_place(self, point=None):
        if self.phase != 'setup':
            return
        if point is None:
            if mouse.hovered_entity != ground_picker or mouse.world_point is None:
                return
            point = mouse.world_point
        p = point
        # team halves: RED z<0, BLUE z>0
        valid = (p.z < -0.5) if self.team == RED else (p.z > 0.5)
        if not valid:
            self.flash_hint("Place on YOUR half!")
            return
        cost = MOBS[self.selected]['cost']
        if self.gold[self.team] < cost:
            self.flash_hint("Not enough gold!")
            return
        if abs(p.x) > FIELD_W / 2 - 1 or abs(p.z) > FIELD_D / 2 - 1:
            return
        Unit(self.selected, self.team, (p.x, 0, p.z))
        self.gold[self.team] -= cost
        play_sfx('place', 0.4)
        self.refresh_hud()

    def flash_hint(self, msg):
        self.hint.text = msg
        self.hint.color = color.orange
        invoke(self.refresh_hud, delay=1.0)
        invoke(setattr, self.hint, 'color', mc(230, 230, 210), delay=1.0)

    def clear_team(self):
        if self.phase != 'setup':
            return
        for u in list(units):
            if u.team == self.team:
                self.gold[self.team] += MOBS[u.kind]['cost']
                destroy(u.bar_bg)
                destroy(u.bar)
                units.remove(u)
                destroy(u)
        self.refresh_hud()

    # ---- phases ----
    def start_battle(self):
        if self.phase != 'setup':
            return
        if not any(u.team == RED for u in units) or \
           not any(u.team == BLUE for u in units):
            self.flash_hint("Both teams need at least one unit!")
            return
        self.phase = 'battle'
        for kind, b in self.buttons.items():
            b.enabled = False
        self.start_btn.enabled = False
        self.title.enabled = False
        self._set_setup_markers(False)
        play_sfx('start', 0.6)
        self.play_music('battle')
        self.refresh_hud()

    def reset(self):
        for u in list(units):
            destroy(u.bar_bg)
            destroy(u.bar)
            destroy(u)
        units.clear()
        for c in list(corpses):
            corpses.remove(c)
            destroy(c)
        for p in list(projectiles):
            destroy(p)
        projectiles.clear()
        for p in list(particles):
            destroy(p)
        particles.clear()
        self.phase = 'setup'
        self.gold = {RED: START_GOLD, BLUE: START_GOLD}
        self.winner = None
        self.banner.enabled = False
        self.title.enabled = True
        self._set_setup_markers(True)
        for b in self.buttons.values():
            b.enabled = True
        self.start_btn.enabled = True
        self.play_music('menu')
        self.refresh_hud()

    def check_winner(self):
        if self.phase != 'battle':
            return
        r = any(u.team == RED and u.alive for u in units)
        b = any(u.team == BLUE and u.alive for u in units)
        if r and b:
            # Stalemate guard: if neither side has a unit that can deal
            # damage (e.g. Allay-only teams), the fight can never resolve.
            r_dmg = any(u.team == RED and u.alive and u.dmg > 0 for u in units)
            b_dmg = any(u.team == BLUE and u.alive and u.dmg > 0 for u in units)
            if not r_dmg and not b_dmg:
                r = b = False
        if not r or not b:
            self.phase = 'over'
            if r and not b:
                self.winner = RED
            elif b and not r:
                self.winner = BLUE
            else:
                self.winner = None
            if self.winner:
                self.banner.text = f"{TEAM_NAME[self.winner]}  WINS!"
                self.banner.color = TEAM_COLOR[self.winner]
            else:
                self.banner.text = "DRAW!"
                self.banner.color = color.white
            self.banner.enabled = True
            play_sfx('win', 0.6)
            self.refresh_hud()

    # ---- main loop ----
    def update(self, dt):
        for p in list(particles):
            p.step(dt)
        if self.phase == 'battle':
            for u in list(units):
                u.think(dt)
            for pr in list(projectiles):
                pr.step(dt)
            self.check_winner()
            self.refresh_hud()
        for u in units:
            u.update_bar()

    def input(self, key):
        # While the help overlay is open, keys just close it (clicks are
        # handled by the overlay button itself).
        if self.help_open:
            if key in ('space', 'enter', 'escape', 'h'):
                self.toggle_help()
            return
        if key == 'h':
            self.toggle_help()
        elif key == 'm':
            self.toggle_mute()
        elif key == 'tab':
            self.team = BLUE if self.team == RED else RED
            self.refresh_hud()
        elif key == 'space':
            self.start_battle()
        elif key == 'r':
            self.reset()
        elif key == 'c':
            self.clear_team()
        elif key == 'left mouse down':
            self.try_place()
        else:
            for kind, cfg in MOBS.items():
                if key == cfg['key'].lower():
                    self.select(kind)
                    break


# ----------------------------------------------------------------------------
# Boot
# ----------------------------------------------------------------------------
# Panda3D's audio library defaults to 'null' (completely silent). We must
# pick a real audio backend BEFORE Ursina starts, or no sound is ever heard.
from panda3d.core import loadPrcFileData  # noqa: E402
loadPrcFileData('', 'audio-library-name p3openal_audio')

app = Ursina(title='Minecraft TABS', borderless=False, fullscreen=False,
             size=(1280, 760), vsync=True)
application.asset_folder = Path(APP_DIR)
window.color = mc(135, 200, 245)
# Hide Ursina's developer overlays (fps / entity / collider counters).
for _counter in ('fps_counter', 'entity_counter', 'collider_counter'):
    _ovl = getattr(window, _counter, None)
    if _ovl is not None:
        _ovl.enabled = False
window.exit_button.visible = False

Sky(color=mc(140, 200, 245))
DirectionalLight(y=3, rotation=(45, -45, 0))
AmbientLight(color=color.rgba(180, 180, 190, 255))

build_world()

# camera
ed = EditorCamera(rotation=(38, 0, 0))
camera.world_position = (0, 24, -30)
camera.fov = 55
ed.target_z = 0

GAME = Game()


def update():
    GAME.update(time.dt)


def input(key):
    GAME.input(key)


if __name__ == '__main__':
    app.run()
