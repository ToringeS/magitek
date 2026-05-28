"""Hardcoded constants for M3: 2v2 ATB battle, single-target Attack + Fire."""

# Display
SCREEN_W = 640
SCREEN_H = 480
FPS = 60
TITLE = "Magitek — M3"

# Music
MUSIC_FILE = "Tales from Southern Realms.mp3"
MUSIC_VOLUME = 0.4  # 0.0 to 1.0

# Colors (R, G, B)
BG = (24, 24, 32)  # retained for reference; the scene draws a gradient instead
TEXT = (235, 235, 240)
TEXT_DIM = (130, 130, 145)
HERO_COLORS = [
    (90, 160, 230),   # Hero 1 — blue
    (140, 200, 110),  # Hero 2 — green
]
ENEMY_COLORS = [
    (200, 90, 90),    # Enemy 1 — red
    (180, 100, 180),  # Enemy 2 — purple
]
# Legacy aliases (kept so anything still importing HERO/ENEMY keeps building).
HERO = HERO_COLORS[0]
ENEMY = ENEMY_COLORS[0]
HP_FILL = (90, 200, 110)
HP_EMPTY = (60, 40, 40)
MP_FILL = (110, 150, 230)
MP_EMPTY = (40, 40, 60)
ATB_FILL = (230, 200, 90)
ATB_EMPTY = (40, 40, 60)
MENU_BG = (40, 40, 56)
MENU_BORDER = (120, 120, 140)
CURSOR = (235, 235, 240)
TARGET_CURSOR = (240, 200, 80)
ACTIVE_HERO_MARKER = (235, 235, 240)

# Battle
ATB_MAX = 100.0
DAMAGE_VARIANCE = (0.8, 1.2)

# --- Layout (4 slots, two columns) ------------------------------------

# Bodies are smaller than M2 to fit four combatants on a 640x480 screen
# with HP/MP/ATB bars under each.
BODY_W = 140
BODY_H = 90
SLOT_TOP_Y = 40
SLOT_BOTTOM_Y = 250
ENEMY_COL_X = 50
HERO_COL_X = SCREEN_W - 50 - BODY_W

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

# Background — forest night scene.
BG_TOP           = (4,   7,  18)
BG_BOTTOM        = (14,  12, 36)
BG_FLOOR         = (12,  22, 14)
BG_HORIZON       = int(SCREEN_H * 0.60)
BG_STAR          = (210, 220, 255)
BG_MOON          = (245, 242, 210)
BG_MOON_SHADOW   = (10,   8,  22)
BG_MTN_FAR       = (18,  24, 36)
BG_MTN_MID       = (14,  28, 18)
BG_TREE_FAR      = (10,  20, 14)
BG_TREE_MID      = (8,   16, 10)
BG_TREE_NEAR     = (6,   12,  8)
BG_STAR_SPEED    = 1.5   # pixels per second downward
BG_STAR_COUNT    = 80

# Stats: (HP, MP, attack, defense, speed). MP optional; absent = 0.
HERO_STATS_LIST = [
    {
        "name": "Hero 1",
        "hp": 100,
        "mp": 30,
        "attack": 20,
        "defense": 5,
        "speed": 12,
    },
    {
        "name": "Hero 2",
        "hp": 70,
        "mp": 50,
        "attack": 12,
        "defense": 3,
        "speed": 14,
    },
]

ENEMY_STATS_LIST = [
    {
        "name": "Enemy 1",
        "hp": 60,
        "attack": 12,
        "defense": 3,
        "speed": 9,
    },
    {
        "name": "Enemy 2",
        "hp": 50,
        "attack": 10,
        "defense": 2,
        "speed": 11,
    },
]

# Spells: plain data so future milestones can extend the list without code changes.
SPELLS = [
    {"name": "Fire", "mp_cost": 10, "power": 25, "ignores_defense": True},
]
