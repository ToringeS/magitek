"""Hardcoded constants for M1: ATB battle, Attack + Magic (Fire)."""

# Display
SCREEN_W = 640
SCREEN_H = 480
FPS = 60
TITLE = "Magitek — M1"

# Colors (R, G, B)
BG = (24, 24, 32)
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
