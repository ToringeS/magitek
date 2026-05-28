"""BattleScene: ATB timing, single-option menu, damage, win/lose.

Three sub-states:
- RUNNING: ATB bars fill. Enemy acts the moment its bar fills; if the hero's
  bar fills we switch to HERO_MENU.
- HERO_MENU: both bars paused (Wait mode). Player confirms Attack.
- OVER: battle resolved; show Win/Lose. Any keydown signals exit.
"""

import random

import pygame

import config
from entities import Combatant, make_enemy, make_hero


# Sub-states
RUNNING = "running"
HERO_MENU = "hero_menu"
OVER = "over"


def _roll_damage(attacker: Combatant, defender: Combatant) -> int:
    variance = random.uniform(*config.DAMAGE_VARIANCE)
    return max(1, round((attacker.attack - defender.defense) * variance))


class BattleScene:
    def __init__(self) -> None:
        self.hero = make_hero()
        self.enemy = make_enemy()
        self.state = RUNNING
        self.outcome: str | None = None  # "win" or "lose" once OVER

        # Whether the user has requested to leave the OVER screen.
        self.done = False

        # Fonts initialized lazily so tests / headless imports don't need a display.
        self._font_small: pygame.font.Font | None = None
        self._font_large: pygame.font.Font | None = None

    # ---- input ---------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return

        if self.state == HERO_MENU:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                self._hero_attack()
        elif self.state == OVER:
            # Any key quits.
            self.done = True

    # ---- update --------------------------------------------------------

    def update(self, dt: float) -> None:
        if self.state != RUNNING:
            return

        # Fill ATB bars. Enemy first so a simultaneous fill lets the player
        # see the enemy's hit land before opening the menu.
        if self.enemy.alive and not self.enemy.atb_ready:
            self.enemy.atb = min(config.ATB_MAX, self.enemy.atb + self.enemy.speed * dt)
        if self.hero.alive and not self.hero.atb_ready:
            self.hero.atb = min(config.ATB_MAX, self.hero.atb + self.hero.speed * dt)

        # Resolve enemy turn immediately when ready.
        if self.enemy.atb_ready and self.enemy.alive:
            self._enemy_attack()
            if self._check_end():
                return

        # Open hero menu when ready.
        if self.hero.atb_ready and self.hero.alive:
            self.state = HERO_MENU

    # ---- actions -------------------------------------------------------

    def _hero_attack(self) -> None:
        dmg = _roll_damage(self.hero, self.enemy)
        self.enemy.take_damage(dmg)
        self.hero.atb = 0.0
        if self._check_end():
            return
        self.state = RUNNING

    def _enemy_attack(self) -> None:
        dmg = _roll_damage(self.enemy, self.hero)
        self.hero.take_damage(dmg)
        self.enemy.atb = 0.0

    def _check_end(self) -> bool:
        if not self.enemy.alive:
            self.state = OVER
            self.outcome = "win"
            return True
        if not self.hero.alive:
            self.state = OVER
            self.outcome = "lose"
            return True
        return False

    # ---- draw ----------------------------------------------------------

    def _ensure_fonts(self) -> None:
        if self._font_small is None:
            self._font_small = pygame.font.Font(None, 22)
        if self._font_large is None:
            self._font_large = pygame.font.Font(None, 56)

    def draw(self, surface: pygame.Surface) -> None:
        self._ensure_fonts()
        surface.fill(config.BG)

        # Enemy: upper-left.
        self._draw_combatant(
            surface,
            self.enemy,
            box=pygame.Rect(60, 60, 160, 120),
            color=config.ENEMY,
            bars_below=True,
        )

        # Hero: lower-right.
        self._draw_combatant(
            surface,
            self.hero,
            box=pygame.Rect(config.SCREEN_W - 60 - 160, config.SCREEN_H - 60 - 120 - 60, 160, 120),
            color=config.HERO,
            bars_below=True,
        )

        if self.state == HERO_MENU:
            self._draw_menu(surface)

        if self.state == OVER:
            self._draw_over(surface)

    def _draw_combatant(
        self,
        surface: pygame.Surface,
        c: Combatant,
        box: pygame.Rect,
        color: tuple[int, int, int],
        bars_below: bool,
    ) -> None:
        assert self._font_small is not None
        # Body rectangle. Dim if dead.
        body_color = color if c.alive else tuple(v // 3 for v in color)
        pygame.draw.rect(surface, body_color, box)

        # Name centered above the body.
        name_surf = self._font_small.render(c.name, True, config.TEXT)
        surface.blit(name_surf, name_surf.get_rect(midbottom=(box.centerx, box.top - 4)))

        # Bars below the body: HP then ATB.
        bar_x = box.left
        bar_w = box.width
        bar_h = 10
        gap = 4

        y = box.bottom + 8 if bars_below else box.top - 8 - (bar_h * 2 + gap)

        # HP bar.
        hp_ratio = c.hp / c.max_hp if c.max_hp else 0
        pygame.draw.rect(surface, config.HP_EMPTY, (bar_x, y, bar_w, bar_h))
        pygame.draw.rect(surface, config.HP_FILL, (bar_x, y, int(bar_w * hp_ratio), bar_h))
        hp_text = self._font_small.render(f"HP {c.hp}/{c.max_hp}", True, config.TEXT)
        surface.blit(hp_text, (bar_x, y + bar_h + 2))

        # ATB bar.
        y2 = y + bar_h + 2 + hp_text.get_height() + gap
        atb_ratio = c.atb / config.ATB_MAX
        pygame.draw.rect(surface, config.ATB_EMPTY, (bar_x, y2, bar_w, bar_h))
        pygame.draw.rect(surface, config.ATB_FILL, (bar_x, y2, int(bar_w * atb_ratio), bar_h))
        atb_text = self._font_small.render("ATB", True, config.TEXT)
        surface.blit(atb_text, (bar_x, y2 + bar_h + 2))

    def _draw_menu(self, surface: pygame.Surface) -> None:
        assert self._font_small is not None
        rect = pygame.Rect(40, config.SCREEN_H - 110, 200, 70)
        pygame.draw.rect(surface, config.MENU_BG, rect)
        pygame.draw.rect(surface, config.MENU_BORDER, rect, 2)

        cursor = self._font_small.render(">", True, config.CURSOR)
        label = self._font_small.render("Attack", True, config.TEXT)
        surface.blit(cursor, (rect.left + 16, rect.top + 22))
        surface.blit(label, (rect.left + 36, rect.top + 22))

        hint = self._font_small.render("Enter to confirm", True, config.TEXT)
        surface.blit(hint, (rect.left + 16, rect.bottom - hint.get_height() - 6))

    def _draw_over(self, surface: pygame.Surface) -> None:
        assert self._font_large is not None
        assert self._font_small is not None

        # Dim overlay.
        overlay = pygame.Surface((config.SCREEN_W, config.SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        surface.blit(overlay, (0, 0))

        text = "WIN" if self.outcome == "win" else "LOSE"
        big = self._font_large.render(text, True, config.TEXT)
        surface.blit(big, big.get_rect(center=(config.SCREEN_W // 2, config.SCREEN_H // 2 - 20)))

        hint = self._font_small.render("Press any key to quit", True, config.TEXT)
        surface.blit(hint, hint.get_rect(center=(config.SCREEN_W // 2, config.SCREEN_H // 2 + 30)))
