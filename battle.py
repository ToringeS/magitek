"""BattleScene: ATB timing, two-level action menu, damage, animations, win/lose.

Sub-states:
- RUNNING: ATB bars fill. Enemy queues an action the moment its bar fills; if
  the hero's bar fills we switch to HERO_MENU.
- HERO_MENU: both bars paused. Player picks Attack or opens the Magic submenu
  to cast Fire (or backs out without spending a turn).
- ACTION: a lunge animation is playing. ATB filling is paused; input ignored.
  Damage resolves at the contact point of the lunge.
- DEATHWAIT: the action killed a combatant; play their fade/sink, then go OVER.
- OVER: battle resolved; show Win/Lose. Any keydown signals exit.

M2 refactor goal: all per-combatant body drawing goes through `_draw_combatant`.
Animation offsets (idle bob, lunge, shake, death sink) and color treatments
(flash, fade) are applied there, so a future sprite milestone only needs to
change the line that draws the body itself.
"""

import math
import random

import pygame

import config
from effects import Action, DamageNumber, DeathFade, HitReaction
from entities import Combatant, make_enemy, make_hero


# Sub-states
RUNNING = "running"
HERO_MENU = "hero_menu"
ACTION = "action"
DEATHWAIT = "deathwait"
OVER = "over"

# Main menu rows
MAIN_MENU = ("Attack", "Magic")
MENU_ATTACK = 0
MENU_MAGIC = 1


class _Slot:
    """A combatant's home position + visual identity. Stable for the battle;
    only the per-frame offsets (computed elsewhere) change.
    """

    __slots__ = ("box", "color", "bob_phase")

    def __init__(self, box: pygame.Rect, color: tuple[int, int, int], bob_phase: float) -> None:
        self.box = box
        self.color = color
        self.bob_phase = bob_phase


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

        # Slots — pick once. Enemy is offset by half a cycle so the two
        # combatants don't bob in lockstep.
        self._slots: dict[int, _Slot] = {
            id(self.enemy): _Slot(
                pygame.Rect(60, 60, 160, 120),
                config.ENEMY,
                bob_phase=math.pi,
            ),
            id(self.hero): _Slot(
                pygame.Rect(
                    config.SCREEN_W - 60 - 160,
                    config.SCREEN_H - 60 - 120 - 60,
                    160,
                    120,
                ),
                config.HERO,
                bob_phase=0.0,
            ),
        }

        # Animation state.
        self.action: Action | None = None
        self.hit_reaction: HitReaction | None = None
        self.damage_numbers: list[DamageNumber] = []
        self.death_fade: DeathFade | None = None
        self.pending_outcome: str | None = None  # set when entering DEATHWAIT

        # Time accumulator for idle-bob phase.
        self._clock = 0.0

        # Whether the user has requested to leave the OVER screen.
        self.done = False

        # Fonts / cached background initialized lazily so headless imports
        # don't need a display.
        self._font_small: pygame.font.Font | None = None
        self._font_large: pygame.font.Font | None = None
        self._font_damage: pygame.font.Font | None = None
        self._bg_surface: pygame.Surface | None = None

    def _slot_for(self, c: Combatant) -> _Slot:
        return self._slots[id(c)]

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
        # RUNNING / ACTION / DEATHWAIT — input is ignored on purpose.

    def _handle_main_menu_key(self, key: int) -> None:
        if key in (pygame.K_UP, pygame.K_DOWN):
            self.menu_index = (self.menu_index + (1 if key == pygame.K_DOWN else -1)) % len(MAIN_MENU)
        elif key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
            if self.menu_index == MENU_ATTACK:
                self._begin_hero_attack()
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
                    self._begin_hero_cast(spell)

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
        self._clock += dt
        self._tick_smoothing(dt)
        self._tick_overlays(dt)

        if self.state == ACTION:
            self._update_action(dt)
            return

        if self.state == DEATHWAIT:
            assert self.death_fade is not None
            self.death_fade.tick(dt)
            if self.death_fade.done:
                self._goto_over()
            return

        if self.state != RUNNING:
            return

        # Fill ATB bars. Enemy first so a tied ready fires the enemy turn
        # first — matches M0/M1 behaviour.
        if self.enemy.alive and not self.enemy.atb_ready:
            self.enemy.atb = min(config.ATB_MAX, self.enemy.atb + self.enemy.speed * dt)
        if self.hero.alive and not self.hero.atb_ready:
            self.hero.atb = min(config.ATB_MAX, self.hero.atb + self.hero.speed * dt)

        if self.enemy.atb_ready and self.enemy.alive:
            self._begin_enemy_attack()
            return

        if self.hero.atb_ready and self.hero.alive:
            self.menu_index = MENU_ATTACK
            self.submenu_open = False
            self.state = HERO_MENU

    def _tick_smoothing(self, dt: float) -> None:
        """Move display_hp / display_atb toward their truth values."""
        k = 1.0 - math.exp(-config.BAR_INTERP_RATE * dt)
        for c in (self.hero, self.enemy):
            c.display_hp += (c.hp - c.display_hp) * k
            c.display_atb += (c.atb - c.display_atb) * k

    def _tick_overlays(self, dt: float) -> None:
        if self.hit_reaction is not None:
            self.hit_reaction.tick(dt)
            if self.hit_reaction.done:
                self.hit_reaction = None
        for dn in self.damage_numbers:
            dn.tick(dt)
        self.damage_numbers = [dn for dn in self.damage_numbers if not dn.done]

    def _update_action(self, dt: float) -> None:
        assert self.action is not None
        self.action.tick(dt)
        if self.action.at_contact and not self.action.contact_applied:
            self.action.target.take_damage(self.action.damage)
            self._spawn_hit_reaction(self.action.target)
            self._spawn_damage_number(self.action)
            self.action.contact_applied = True
        if self.action.done:
            self._finish_action()

    # ---- actions -------------------------------------------------------

    def _begin_hero_attack(self) -> None:
        dmg = _roll_damage(self.hero, self.enemy)
        self.action = Action(actor=self.hero, target=self.enemy, damage=dmg, is_fire=False)
        self.submenu_open = False
        self.state = ACTION

    def _begin_hero_cast(self, spell: dict) -> None:
        # Guarded by the cursor-skip in the submenu, but defend in code too.
        if not self.hero.spend_mp(spell["mp_cost"]):
            return
        dmg = _spell_damage(spell, self.enemy)
        self.action = Action(actor=self.hero, target=self.enemy, damage=dmg, is_fire=True)
        self.submenu_open = False
        self.state = ACTION

    def _begin_enemy_attack(self) -> None:
        dmg = _roll_damage(self.enemy, self.hero)
        self.action = Action(actor=self.enemy, target=self.hero, damage=dmg, is_fire=False)
        self.state = ACTION

    def _finish_action(self) -> None:
        assert self.action is not None
        actor = self.action.actor
        target = self.action.target
        actor.atb = 0.0
        self.action = None

        if not target.alive:
            self.death_fade = DeathFade(target=target)
            self.pending_outcome = "win" if target is self.enemy else "lose"
            self.state = DEATHWAIT
            return

        self.state = RUNNING

    def _spawn_hit_reaction(self, target: Combatant) -> None:
        # One action plays at a time, so a single slot is enough.
        self.hit_reaction = HitReaction(target=target)

    def _spawn_damage_number(self, action: Action) -> None:
        slot = self._slot_for(action.target)
        color = config.DAMAGE_COLOR_FIRE if action.is_fire else config.DAMAGE_COLOR_ATTACK
        self.damage_numbers.append(
            DamageNumber(
                value=action.damage,
                x=float(slot.box.centerx),
                y=float(slot.box.top - 10),
                color=color,
            )
        )

    def _goto_over(self) -> None:
        self.state = OVER
        self.outcome = self.pending_outcome

    # ---- draw ----------------------------------------------------------

    def _ensure_fonts(self) -> None:
        if self._font_small is None:
            self._font_small = pygame.font.Font(None, 22)
        if self._font_large is None:
            self._font_large = pygame.font.Font(None, 56)
        if self._font_damage is None:
            self._font_damage = pygame.font.Font(None, 32)

    def _ensure_background(self) -> None:
        if self._bg_surface is not None:
            return
        s = pygame.Surface((config.SCREEN_W, config.SCREEN_H))
        # Vertical gradient.
        for y in range(config.SCREEN_H):
            r = y / max(1, config.SCREEN_H - 1)
            color = tuple(
                int(config.BG_TOP[i] * (1.0 - r) + config.BG_BOTTOM[i] * r)
                for i in range(3)
            )
            pygame.draw.line(s, color, (0, y), (config.SCREEN_W, y))
        # Floor band.
        pygame.draw.rect(
            s,
            config.BG_FLOOR,
            pygame.Rect(
                0,
                config.BG_HORIZON,
                config.SCREEN_W,
                config.SCREEN_H - config.BG_HORIZON,
            ),
        )
        # Horizon highlight.
        pygame.draw.line(
            s,
            tuple(min(255, v + 24) for v in config.BG_FLOOR),
            (0, config.BG_HORIZON),
            (config.SCREEN_W, config.BG_HORIZON),
        )
        self._bg_surface = s

    def draw(self, surface: pygame.Surface) -> None:
        self._ensure_fonts()
        self._ensure_background()
        assert self._bg_surface is not None
        surface.blit(self._bg_surface, (0, 0))

        # Bodies first (in their home order), then bars at the home position,
        # then floating numbers over everything.
        self._draw_combatant(surface, self.enemy)
        self._draw_combatant(surface, self.hero)

        self._draw_bars(surface, self.enemy)
        self._draw_bars(surface, self.hero)

        self._draw_damage_numbers(surface)

        if self.state == HERO_MENU:
            self._draw_menu(surface)

        if self.state == OVER:
            self._draw_over(surface)

    def _draw_combatant(self, surface: pygame.Surface, c: Combatant) -> None:
        """Render one combatant's body and name.

        This is the single surface that touches body pixels. All animation
        — idle bob, lunge, shake, hit flash, death fade/sink — is applied
        here, so a later milestone can swap the body draw for a sprite blit
        and leave the animation math untouched.
        """
        assert self._font_small is not None
        slot = self._slot_for(c)
        ox, oy = self._combatant_offset(c, slot)
        body_rect = slot.box.move(ox, oy)

        # Body color: dim once defeated.
        body_color = slot.color if c.alive else tuple(v // 3 for v in slot.color)

        dying = self.death_fade is not None and self.death_fade.target is c
        if dying:
            # Render the body onto an alpha surface so the fade reads cleanly.
            alpha = self.death_fade.alpha  # type: ignore[union-attr]
            if alpha > 0:
                body_surf = pygame.Surface(body_rect.size, pygame.SRCALPHA)
                body_surf.fill((*body_color, alpha))
                surface.blit(body_surf, body_rect.topleft)
        else:
            pygame.draw.rect(surface, body_color, body_rect)

        # Hit flash overlay.
        if self.hit_reaction is not None and self.hit_reaction.target is c:
            a = self.hit_reaction.flash_alpha
            if a > 0:
                flash = pygame.Surface(body_rect.size, pygame.SRCALPHA)
                flash.fill((*config.HIT_FLASH_COLOR, int(255 * a)))
                surface.blit(flash, body_rect.topleft)

        # Name centered above the body (also follows the body's offset).
        name_surf = self._font_small.render(c.name, True, config.TEXT)
        if dying:
            name_surf.set_alpha(self.death_fade.alpha)  # type: ignore[union-attr]
        surface.blit(
            name_surf,
            name_surf.get_rect(midbottom=(body_rect.centerx, body_rect.top - 4)),
        )

    def _combatant_offset(self, c: Combatant, slot: _Slot) -> tuple[int, int]:
        ox, oy = 0, 0

        # Idle bob — suppressed while acting, while taking a hit, or while dying.
        acting = self.action is not None and self.action.actor is c
        being_hit = self.hit_reaction is not None and self.hit_reaction.target is c
        dying = self.death_fade is not None and self.death_fade.target is c
        if c.alive and not acting and not being_hit and not dying:
            bob = math.sin(self._clock * config.IDLE_BOB_HZ * 2.0 * math.pi + slot.bob_phase)
            oy += int(bob * config.IDLE_BOB_AMP)

        # Lunge toward the target.
        if acting:
            target_slot = self._slot_for(self.action.target)  # type: ignore[union-attr]
            r = self.action.offset_ratio()  # type: ignore[union-attr]
            dx = target_slot.box.centerx - slot.box.centerx
            dy = target_slot.box.centery - slot.box.centery
            ox += int(dx * config.LUNGE_DISTANCE_RATIO * r)
            oy += int(dy * config.LUNGE_DISTANCE_RATIO * r)

        # Hit shake.
        if being_hit:
            ox += self.hit_reaction.shake_x  # type: ignore[union-attr]
            oy += self.hit_reaction.shake_y  # type: ignore[union-attr]

        # Death sink.
        if dying:
            oy += self.death_fade.sink_offset  # type: ignore[union-attr]

        return ox, oy

    def _draw_bars(self, surface: pygame.Surface, c: Combatant) -> None:
        """Bars stay anchored at the home position — they don't follow lunge
        or shake, so the player can read them while the body moves.
        """
        assert self._font_small is not None
        slot = self._slot_for(c)
        bar_x = slot.box.left
        bar_w = slot.box.width
        bar_h = 10
        gap = 4

        y = slot.box.bottom + 8

        # HP — smoothed.
        hp_ratio = max(0.0, c.display_hp) / c.max_hp if c.max_hp else 0.0
        pygame.draw.rect(surface, config.HP_EMPTY, (bar_x, y, bar_w, bar_h))
        pygame.draw.rect(surface, config.HP_FILL, (bar_x, y, int(bar_w * hp_ratio), bar_h))
        hp_text = self._font_small.render(f"HP {max(0, c.hp)}/{c.max_hp}", True, config.TEXT)
        surface.blit(hp_text, (bar_x, y + bar_h + 2))
        y += bar_h + 2 + hp_text.get_height() + gap

        # MP — snaps; spec only smooths HP and ATB.
        if c.max_mp > 0:
            mp_ratio = c.mp / c.max_mp
            pygame.draw.rect(surface, config.MP_EMPTY, (bar_x, y, bar_w, bar_h))
            pygame.draw.rect(surface, config.MP_FILL, (bar_x, y, int(bar_w * mp_ratio), bar_h))
            mp_text = self._font_small.render(f"MP {c.mp}/{c.max_mp}", True, config.TEXT)
            surface.blit(mp_text, (bar_x, y + bar_h + 2))
            y += bar_h + 2 + mp_text.get_height() + gap

        # ATB — smoothed.
        atb_ratio = max(0.0, c.display_atb) / config.ATB_MAX
        pygame.draw.rect(surface, config.ATB_EMPTY, (bar_x, y, bar_w, bar_h))
        pygame.draw.rect(surface, config.ATB_FILL, (bar_x, y, int(bar_w * atb_ratio), bar_h))
        atb_text = self._font_small.render("ATB", True, config.TEXT)
        surface.blit(atb_text, (bar_x, y + bar_h + 2))

    def _draw_damage_numbers(self, surface: pygame.Surface) -> None:
        assert self._font_damage is not None
        for dn in self.damage_numbers:
            text = self._font_damage.render(str(dn.value), True, dn.color)
            a = dn.current_alpha()
            if a < 255:
                text.set_alpha(a)
            rect = text.get_rect(center=(int(dn.x), int(dn.current_y())))
            surface.blit(text, rect)

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
