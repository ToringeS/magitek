"""Hardcoded constants for M0: one ATB battle, attack only."""

# Display
SCREEN_W = 640
SCREEN_H = 480
FPS = 60
TITLE = "Magitek — M0"

# Colors (R, G, B)
BG = (24, 24, 32)
TEXT = (235, 235, 240)
HERO = (90, 160, 230)
ENEMY = (200, 90, 90)
HP_FILL = (90, 200, 110)
HP_EMPTY = (60, 40, 40)
ATB_FILL = (230, 200, 90)
ATB_EMPTY = (40, 40, 60)
MENU_BG = (40, 40, 56)
MENU_BORDER = (120, 120, 140)
CURSOR = (235, 235, 240)

# Battle
ATB_MAX = 100.0
DAMAGE_VARIANCE = (0.8, 1.2)

# Stats: (HP, attack, defense, speed)
HERO_STATS = {
    "name": "Hero",
    "hp": 100,
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
