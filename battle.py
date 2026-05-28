"""BattleScene: ATB timing, two-level action menu, damage, win/lose.

Three sub-states:
- RUNNING: ATB bars fill. Enemy acts the moment its bar fills; if the hero's
  bar fills we switch to HERO_MENU.
- HERO_MENU: both bars paused (Wait mode). Player picks Attack or opens the
  Magic submenu to cast Fire (or backs out without spending a turn).
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

# Main menu rows
MAIN_MENU = ("Attack", "Magic")
MENU_ATTACK = 0
MENU_MAGIC = 1


def _roll_damage(attacker: Combatant, defender: Combatant) -> int:
    variance = random.uniform(*config.DAMAGE_VARIANCE)
    return max(1, round((attacker.attack - defender.defense) * variance))


def _spell_damage(spell: dict, defender: Combatant) -> int:
    if spell.get("ignores_defense"):
        return int(spell["power"])
    return max(1, int(spell["power"]) - defender.defense)


class BattleScene:
    def __init__(self) -> None:
        self.hero = make_hero()
        self.enemy = make_enemy()
        self.state = RUNNING
        self.outcome: str | None = None  # "win" or "lose" once OVER

        # Menu cursors. Reset each time the menu opens so the player always
        # starts on Attack.
        self.menu_index = MENU_ATTACK
        self.submenu_open = False
        self.submenu_index = 0  # 0..len(SPELLS): last index is "Back"

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
            if self.submenu_open:
                self._handle_submenu_key(event.key)
            else:
                self._handle_main_menu_key(event.key)
        elif self.state == OVER:
            # Any key quits.
            self.done = True

    def _handle_main_menu_key(self, key: int) -> None:
        if key in (pygame.K_UP, pygame.K_DOWN):
            self.menu_index = (self.menu_index + (1 if key == pygame.K_DOWN else -1)) % len(MAIN_MENU)
        elif key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
            if self.menu_index == MENU_ATTACK:
                self._hero_attack()
            elif self.menu_index == MENU_MAGIC:
                self._open_submenu()

    def _handle_submenu_key(self, key: int) -> None:
        last = len(config.SPELLS)  # index of the "Back" row
        if key in (pygame.K_UP, pygame.K_DOWN):
            step = 1 if key == pygame.K_DOWN else -1
            self.submenu_index = self._next_submenu_index(self.submenu_index, step)
        elif key == pygame.K_ESCAPE:
            self._close_submenu()
        elif key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
            if self.submenu_index == last:
                self._close_submenu()
            else:
                spell = config.SPELLS[self.submenu_index]
                if self._can_cast(spell):
                    self._hero_cast(spell)

    def _can_cast(self, spell: dict) -> bool:
        return self.hero.mp >= spell["mp_cost"]

    def _next_submenu_index(self, start: int, step: int) -> int:
        """Move cursor, wrapping, skipping spells the hero cannot afford.

        "Back" is always selectable. Falls back to "Back" if nothing else is
        selectable.
        """
        last = len(config.SPELLS)
        total = last + 1
        idx = start
        for _ in range(total):
            idx = (idx + step) % total
            if idx == last:
                return idx
            if self._can_cast(config.SPELLS[idx]):
                return idx
        return last  # only Back is reachable

    def _open_submenu(self) -> None:
        self.submenu_open = True
        # Start on the first affordable spell; fall back to Back.
        self.submenu_index = self._next_submenu_index(-1, 1)

    def _close_submenu(self) -> None:
        self.submenu_open = False

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
            self.menu_index = MENU_ATTACK
            self.submenu_open = False
            self.state = HERO_MENU

    # ---- actions -------------------------------------------------------

    def _hero_attack(self) -> None:
        dmg = _roll_damage(self.hero, self.enemy)
        self.enemy.take_damage(dmg)
        self._end_hero_turn()

    def _hero_cast(self, spell: dict) -> None:
        # Guarded by the cursor-skip in the submenu, but defend in code too.
        if not self.hero.spend_mp(spell["mp_cost"]):
            return
        dmg = _spell_damage(spell, self.enemy)
        self.enemy.take_damage(dmg)
        self._end_hero_turn()

    def _end_hero_turn(self) -> None:
        self.hero.atb = 0.0
        self.submenu_open = False
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

        # Bars below the body: HP, then optional MP, then ATB.
        bar_x = box.left
        bar_w = box.width
        bar_h = 10
        gap = 4

        # Compute starting y. With MP we need extra vertical room when bars_below.
        bars_block_h = bar_h * 2 + gap  # HP bar+label + ATB bar+label approx
        y = box.bottom + 8 if bars_below else box.top - 8 - bars_block_h

        # HP bar.
        hp_ratio = c.hp / c.max_hp if c.max_hp else 0
        pygame.draw.rect(surface, config.HP_EMPTY, (bar_x, y, bar_w, bar_h))
        pygame.draw.rect(surface, config.HP_FILL, (bar_x, y, int(bar_w * hp_ratio), bar_h))
        hp_text = self._font_small.render(f"HP {c.hp}/{c.max_hp}", True, config.TEXT)
        surface.blit(hp_text, (bar_x, y + bar_h + 2))

        y = y + bar_h + 2 + hp_text.get_height() + gap

        # MP bar (only if this combatant has MP).
        if c.max_mp > 0:
            mp_ratio = c.mp / c.max_mp
            pygame.draw.rect(surface, config.MP_EMPTY, (bar_x, y, bar_w, bar_h))
            pygame.draw.rect(surface, config.MP_FILL, (bar_x, y, int(bar_w * mp_ratio), bar_h))
            mp_text = self._font_small.render(f"MP {c.mp}/{c.max_mp}", True, config.TEXT)
            surface.blit(mp_text, (bar_x, y + bar_h + 2))
            y = y + bar_h + 2 + mp_text.get_height() + gap

        # ATB bar.
        atb_ratio = c.atb / config.ATB_MAX
        pygame.draw.rect(surface, config.ATB_EMPTY, (bar_x, y, bar_w, bar_h))
        pygame.draw.rect(surface, config.ATB_FILL, (bar_x, y, int(bar_w * atb_ratio), bar_h))
        atb_text = self._font_small.render("ATB", True, config.TEXT)
        surface.blit(atb_text, (bar_x, y + bar_h + 2))

    def _draw_menu(self, surface: pygame.Surface) -> None:
        assert self._font_small is not None
        rect = pygame.Rect(40, config.SCREEN_H - 150, 220, 110)
        pygame.draw.rect(surface, config.MENU_BG, rect)
        pygame.draw.rect(surface, config.MENU_BORDER, rect, 2)

        if self.submenu_open:
            self._draw_submenu_rows(surface, rect)
            hint_text = "Enter • Esc back"
        else:
            self._draw_main_menu_rows(surface, rect)
            hint_text = "↑↓ • Enter"

        hint = self._font_small.render(hint_text, True, config.TEXT_DIM)
        surface.blit(hint, (rect.left + 16, rect.bottom - hint.get_height() - 6))

    def _draw_main_menu_rows(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        assert self._font_small is not None
        row_h = self._font_small.get_height() + 6
        top = rect.top + 12
        for i, label in enumerate(MAIN_MENU):
            y = top + i * row_h
            if i == self.menu_index:
                cursor = self._font_small.render(">", True, config.CURSOR)
                surface.blit(cursor, (rect.left + 16, y))
            text = self._font_small.render(label, True, config.TEXT)
            surface.blit(text, (rect.left + 36, y))

    def _draw_submenu_rows(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        assert self._font_small is not None
        row_h = self._font_small.get_height() + 6
        top = rect.top + 12

        for i, spell in enumerate(config.SPELLS):
            y = top + i * row_h
            affordable = self._can_cast(spell)
            color = config.TEXT if affordable else config.TEXT_DIM
            if i == self.submenu_index:
                cursor = self._font_small.render(">", True, config.CURSOR)
                surface.blit(cursor, (rect.left + 16, y))
            name = self._font_small.render(spell["name"], True, color)
            surface.blit(name, (rect.left + 36, y))
            cost = self._font_small.render(f"{spell['mp_cost']} MP", True, color)
            surface.blit(cost, (rect.right - cost.get_width() - 16, y))

        # Back row.
        back_i = len(config.SPELLS)
        y = top + back_i * row_h
        if self.submenu_index == back_i:
            cursor = self._font_small.render(">", True, config.CURSOR)
            surface.blit(cursor, (rect.left + 16, y))
        back = self._font_small.render("Back", True, config.TEXT)
        surface.blit(back, (rect.left + 36, y))

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
