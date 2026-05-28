"""Hardcoded constants for M2: ATB battle, Attack + Magic (Fire), + game feel."""

# Display
SCREEN_W = 640
SCREEN_H = 480
FPS = 60
TITLE = "Magitek — M2"

# Colors (R, G, B)
BG = (24, 24, 32)  # retained for reference; M2 draws a gradient instead
TEXT = (235, 235, 240)
TEXT_DIM = (130, 130, 145)
HERO = (90, 160, 230)
ENEMY = (200, 90, 90)
HP_FILL = (90, 200, 110)
HP_EMPTY = (60, 40, 40)
MP_FILL = (110, 150, 230)
MP_EMPTY = (40, 40, 60)
ATB_FILL = (230, 200, 90)
ATB_EMPTY = (40, 40, 60)
MENU_BG = (40, 40, 56)
MENU_BORDER = (120, 120, 140)
CURSOR = (235, 235, 240)

# Battle
ATB_MAX = 100.0
DAMAGE_VARIANCE = (0.8, 1.2)

# --- M2: animation / game feel ----------------------------------------

# Action lunge (seconds). Damage resolves at the start of LUNGE_HOLD.
LUNGE_OUT = 0.15
LUNGE_HOLD = 0.05
LUNGE_BACK = 0.15
LUNGE_DISTANCE_RATIO = 0.6  # 0..1 of the distance to the target's center

# Hit reaction (seconds). Lengths can exceed the lunge; the scene stays in
# ACTION until the longest of action + hit-reaction has finished.
HIT_FLASH_DURATION = 0.15
HIT_FLASH_COLOR = (255, 255, 255)
HIT_SHAKE_DURATION = 0.25
HIT_SHAKE_AMPLITUDE = 4  # pixels at start; decays linearly to 0

# Floating damage numbers.
DAMAGE_NUMBER_DURATION = 0.7
DAMAGE_NUMBER_RISE = 30  # pixels traveled upward over the lifetime
DAMAGE_COLOR_ATTACK = (235, 235, 240)
DAMAGE_COLOR_FIRE = (240, 160, 70)

# Idle bob — subtle vertical sway for living combatants.
IDLE_BOB_HZ = 1.5
IDLE_BOB_AMP = 2

# Death fade — alpha goes to 0 and the body sinks downward.
DEATH_FADE_DURATION = 0.6
DEATH_SINK = 20

# Smooth bars — exponential decay rate. Higher = snappier.
BAR_INTERP_RATE = 10.0

# Background — vertical gradient with a darker floor band.
BG_TOP = (28, 26, 44)
BG_BOTTOM = (52, 32, 56)
BG_FLOOR = (28, 22, 36)
BG_HORIZON = int(SCREEN_H * 0.66)

# Stats: (HP, MP, attack, defense, speed). MP optional; absent = 0.
HERO_STATS = {
    "name": "Hero",
    "hp": 100,
    "mp": 30,
    "attack": 20,
    "defense": 5,
    "speed": 12,
}

ENEMY_STATS = {
    "name": "Enemy",
    "hp": 60,
    "attack": 12,
    "defense": 3,
    "speed": 9,
}

# Spells: plain data so M2+ can extend the list without code changes.
SPELLS = [
    {"name": "Fire", "mp_cost": 10, "power": 25, "ignores_defense": True},
]
