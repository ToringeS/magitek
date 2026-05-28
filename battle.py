"""BattleScene: 2v2 ATB combat with target selection.

Sub-states:
- RUNNING: ATB bars fill. Any combatant whose bar hits ATB_MAX is appended to a
  shared FIFO ready-queue. While idle, pop the next actor.
- HERO_MENU: the active hero (queue head, if a hero) owns the menu. ATB paused.
- TARGETING: pending action waits for a target choice. Cancel returns to the
  prior menu without spending the turn (or MP). ATB paused.
- ACTION: lunge animation plays; ATB paused, input ignored. Damage resolves at
  the contact point of the lunge.
- DEATHWAIT: an action wiped a side. Wait for in-flight death fades, then OVER.
- OVER: battle resolved. Any keydown signals exit.

Per-combatant body drawing still routes through `_draw_combatant` (the M2
refactor goal); we just call it once per combatant in each party so a later
sprite milestone only swaps the body draw.
"""

import math
import random

import pygame

import config
from effects import Action, DamageNumber, DeathFade, HitReaction
from entities import Combatant, make_enemies, make_party


# Sub-states
RUNNING = "running"
HERO_MENU = "hero_menu"
TARGETING = "targeting"
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
        self.heroes = make_party()
        self.enemies = make_enemies()
        self.state = RUNNING
        self.outcome: str | None = None

        # Menu state — meaningful only while HERO_MENU/TARGETING. Reset on entry.
        self.menu_index = MENU_ATTACK
        self.submenu_open = False
        self.submenu_index = 0
        self.active_hero: Combatant | None = None

        # Pending action between menu pick and target confirmation.
        self.pending_kind: str | None = None       # "attack" | "fire"
        self.pending_spell: dict | None = None
        self.target_enemy: Combatant | None = None
        self.target_from_submenu = False           # cancel destination flag

        # Shared FIFO of combatants whose bars filled. Heroes and enemies mix.
        self._ready_queue: list[Combatant] = []

        # Slot layout: enemies left column (top/bottom), heroes right column.
        # Bob phases are spread so the four bodies don't sway in lockstep.
        self._slots: dict[int, _Slot] = {}
        for i, e in enumerate(self.enemies):
            y = config.SLOT_TOP_Y if i == 0 else config.SLOT_BOTTOM_Y
            self._slots[id(e)] = _Slot(
                box=pygame.Rect(config.ENEMY_COL_X, y, config.BODY_W, config.BODY_H),
                color=config.ENEMY_COLORS[i % len(config.ENEMY_COLORS)],
                bob_phase=math.pi if i == 0 else math.pi * 0.5,
            )
        for i, h in enumerate(self.heroes):
            y = config.SLOT_TOP_Y if i == 0 else config.SLOT_BOTTOM_Y
            self._slots[id(h)] = _Slot(
                box=pygame.Rect(config.HERO_COL_X, y, config.BODY_W, config.BODY_H),
                color=config.HERO_COLORS[i % len(config.HERO_COLORS)],
                bob_phase=0.0 if i == 0 else math.pi * 1.5,
            )

        # Animation state.
        self.action: Action | None = None
        self.hit_reaction: HitReaction | None = None
        self.damage_numbers: list[DamageNumber] = []
        self.death_fades: list[DeathFade] = []
        self.pending_outcome: str | None = None

        # Idle-bob phase clock.
        self._clock = 0.0

        # Whether the user has requested to leave the OVER screen.
        self.done = False

        # Lazy fonts / background.
        self._font_small: pygame.font.Font | None = None
        self._font_large: pygame.font.Font | None = None
        self._font_damage: pygame.font.Font | None = None
        self._bg_surface: pygame.Surface | None = None

    def _slot_for(self, c: Combatant) -> _Slot:
        return self._slots[id(c)]

    @property
    def combatants(self) -> list[Combatant]:
        return self.heroes + self.enemies

    def _in_queue(self, c: Combatant) -> bool:
        """Identity check — Combatants compare by value via @dataclass, so
        prefer `is` over `in` for queue membership."""
        return any(x is c for x in self._ready_queue)

    # ---- input ---------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return

        if self.state == HERO_MENU:
            if self.submenu_open:
                self._handle_submenu_key(event.key)
            else:
                self._handle_main_menu_key(event.key)
        elif self.state == TARGETING:
            self._handle_target_key(event.key)
        elif self.state == OVER:
            # Any key quits.
            self.done = True
        # RUNNING / ACTION / DEATHWAIT — input ignored on purpose.

    def _handle_main_menu_key(self, key: int) -> None:
        if key in (pygame.K_UP, pygame.K_DOWN):
            step = 1 if key == pygame.K_DOWN else -1
            self.menu_index = (self.menu_index + step) % len(MAIN_MENU)
        elif key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
            if self.menu_index == MENU_ATTACK:
                self._enter_targeting(kind="attack", spell=None, from_submenu=False)
            elif self.menu_index == MENU_MAGIC:
                self._open_submenu()

    def _handle_submenu_key(self, key: int) -> None:
        last = len(config.SPELLS)  # index of "Back"
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
                    self._enter_targeting(kind="fire", spell=spell, from_submenu=True)

    def _handle_target_key(self, key: int) -> None:
        if key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
            step = 1 if key in (pygame.K_DOWN, pygame.K_RIGHT) else -1
            self._cycle_target(step)
        elif key == pygame.K_ESCAPE:
            self._cancel_targeting()
        elif key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
            self._confirm_target()

    def _can_cast(self, spell: dict) -> bool:
        return self.active_hero is not None and self.active_hero.mp >= spell["mp_cost"]

    def _next_submenu_index(self, start: int, step: int) -> int:
        """Move cursor, wrapping, skipping spells the active hero cannot afford.

        "Back" is always selectable. Falls back to "Back" if nothing else is.
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
        self.submenu_index = self._next_submenu_index(-1, 1)

    def _close_submenu(self) -> None:
        self.submenu_open = False

    # ---- targeting -----------------------------------------------------

    def _enter_targeting(self, kind: str, spell: dict | None, from_submenu: bool) -> None:
        self.pending_kind = kind
        self.pending_spell = spell
        self.target_from_submenu = from_submenu
        # Default to first living enemy (top slot wins ties).
        self.target_enemy = next((e for e in self.enemies if e.alive), None)
        if self.target_enemy is None:
            # No living enemies — shouldn't be reachable mid-battle.
            self._cancel_targeting()
            return
        self.state = TARGETING

    def _cycle_target(self, step: int) -> None:
        alive = [e for e in self.enemies if e.alive]
        if not alive:
            return
        if self.target_enemy not in alive:
            self.target_enemy = alive[0]
            return
        i = alive.index(self.target_enemy)
        self.target_enemy = alive[(i + step) % len(alive)]

    def _cancel_targeting(self) -> None:
        # Don't spend the turn — return to the prior menu.
        self.pending_kind = None
        self.pending_spell = None
        self.target_enemy = None
        self.submenu_open = self.target_from_submenu
        self.state = HERO_MENU

    def _confirm_target(self) -> None:
        if self.active_hero is None or self.target_enemy is None:
            return
        if not self.target_enemy.alive:
            # ATB is paused while targeting so this is unreachable in practice,
            # but snap to a living target if we're ever wrong.
            self._cycle_target(1)
            if self.target_enemy is None or not self.target_enemy.alive:
                self._cancel_targeting()
                return
        if self.pending_kind == "attack":
            self._begin_hero_attack(self.active_hero, self.target_enemy)
        elif self.pending_kind == "fire":
            assert self.pending_spell is not None
            self._begin_hero_cast(self.active_hero, self.target_enemy, self.pending_spell)
        # active_hero stays set for the lunge; cleared in _finish_action.
        self.pending_kind = None
        self.pending_spell = None
        self.target_enemy = None

    # ---- update --------------------------------------------------------

    def update(self, dt: float) -> None:
        self._clock += dt
        self._tick_smoothing(dt)
        self._tick_overlays(dt)

        if self.state == ACTION:
            self._update_action(dt)
            return

        if self.state == DEATHWAIT:
            # All in-flight death fades have been ticked by _tick_overlays.
            # Once the list empties, show Win/Lose.
            if not self.death_fades:
                self._goto_over()
            return

        if self.state in (HERO_MENU, TARGETING, OVER):
            return

        # RUNNING — fill bars, then dispatch the next ready actor (if any).
        self._fill_atb(dt)
        self._dispatch_next()

    def _fill_atb(self, dt: float) -> None:
        for c in self.combatants:
            if not c.alive:
                continue
            if self._in_queue(c):
                continue
            if c.atb_ready:
                # Defensive — a full bar that's not in the queue gets queued.
                self._ready_queue.append(c)
                continue
            c.atb = min(config.ATB_MAX, c.atb + c.speed * dt)
            if c.atb_ready:
                self._ready_queue.append(c)

    def _dispatch_next(self) -> None:
        while self._ready_queue:
            actor = self._ready_queue[0]
            if not actor.alive:
                # Dead actor slipped through — drop and look at the next.
                self._ready_queue.pop(0)
                continue
            self._ready_queue.pop(0)
            if actor in self.heroes:
                self._open_hero_menu(actor)
            else:
                self._begin_enemy_attack(actor)
            return

    def _open_hero_menu(self, hero: Combatant) -> None:
        self.active_hero = hero
        self.menu_index = MENU_ATTACK
        self.submenu_open = False
        self.state = HERO_MENU

    def _tick_smoothing(self, dt: float) -> None:
        """Move display_hp / display_atb toward their truth values."""
        k = 1.0 - math.exp(-config.BAR_INTERP_RATE * dt)
        for c in self.combatants:
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
        for df in self.death_fades:
            df.tick(dt)
        self.death_fades = [df for df in self.death_fades if not df.done]

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

    def _begin_hero_attack(self, hero: Combatant, target: Combatant) -> None:
        dmg = _roll_damage(hero, target)
        self.action = Action(actor=hero, target=target, damage=dmg, is_fire=False)
        self.submenu_open = False
        self.state = ACTION

    def _begin_hero_cast(self, hero: Combatant, target: Combatant, spell: dict) -> None:
        # Guarded by the cursor-skip in the submenu, but defend in code too.
        if not hero.spend_mp(spell["mp_cost"]):
            return
        dmg = _spell_damage(spell, target)
        self.action = Action(actor=hero, target=target, damage=dmg, is_fire=True)
        self.submenu_open = False
        self.state = ACTION

    def _begin_enemy_attack(self, enemy: Combatant) -> None:
        living_heroes = [h for h in self.heroes if h.alive]
        if not living_heroes:
            # Battle is already lost; reset the bar and let the wipe check
            # transition us out next frame.
            enemy.atb = 0.0
            return
        target = random.choice(living_heroes)
        dmg = _roll_damage(enemy, target)
        self.action = Action(actor=enemy, target=target, damage=dmg, is_fire=False)
        self.state = ACTION

    def _finish_action(self) -> None:
        assert self.action is not None
        actor = self.action.actor
        target = self.action.target
        actor.atb = 0.0
        self.action = None
        self.active_hero = None

        if not target.alive:
            self.death_fades.append(DeathFade(target=target))
            # A dead combatant must leave both the queue and the turn rotation.
            self._ready_queue = [c for c in self._ready_queue if c is not target]

        outcome = self._check_outcome()
        if outcome is not None:
            # Spec: don't finish queued menus when a side is wiped mid-turn.
            self._ready_queue.clear()
            self.pending_outcome = outcome
            self.state = DEATHWAIT
            return

        self.state = RUNNING

    def _check_outcome(self) -> str | None:
        if not any(e.alive for e in self.enemies):
            return "win"
        if not any(h.alive for h in self.heroes):
            return "lose"
        return None

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
        for y in range(config.SCREEN_H):
            r = y / max(1, config.SCREEN_H - 1)
            color = tuple(
                int(config.BG_TOP[i] * (1.0 - r) + config.BG_BOTTOM[i] * r)
                for i in range(3)
            )
            pygame.draw.line(s, color, (0, y), (config.SCREEN_W, y))
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

        # Bodies first (in column order), then bars, then markers/cursors,
        # then floating numbers, then menu, then over screen.
        for c in self.combatants:
            self._draw_combatant(surface, c)

        for c in self.combatants:
            self._draw_bars(surface, c)

        if self.state in (HERO_MENU, TARGETING) and self.active_hero is not None:
            self._draw_active_hero_marker(surface, self.active_hero)

        if self.state == TARGETING and self.target_enemy is not None:
            self._draw_target_cursor(surface, self.target_enemy)

        self._draw_damage_numbers(surface)

        if self.state == HERO_MENU:
            self._draw_menu(surface)

        if self.state == OVER:
            self._draw_over(surface)

    def _draw_combatant(self, surface: pygame.Surface, c: Combatant) -> None:
        """Render one combatant's body and name.

        This is the single surface that touches body pixels. All animation —
        idle bob, lunge, shake, hit flash, death fade/sink — is applied here,
        so a later milestone can swap the body draw for a sprite blit and leave
        the animation math untouched.
        """
        assert self._font_small is not None
        slot = self._slot_for(c)
        ox, oy = self._combatant_offset(c, slot)
        body_rect = slot.box.move(ox, oy)

        body_color = slot.color if c.alive else tuple(v // 3 for v in slot.color)

        fade = self._fade_for(c)
        if fade is not None:
            alpha = fade.alpha
            if alpha > 0:
                body_surf = pygame.Surface(body_rect.size, pygame.SRCALPHA)
                body_surf.fill((*body_color, alpha))
                surface.blit(body_surf, body_rect.topleft)
        elif c.alive:
            pygame.draw.rect(surface, body_color, body_rect)
        # Dead + no active fade ⇒ left play; draw nothing.

        if self.hit_reaction is not None and self.hit_reaction.target is c:
            a = self.hit_reaction.flash_alpha
            if a > 0:
                flash = pygame.Surface(body_rect.size, pygame.SRCALPHA)
                flash.fill((*config.HIT_FLASH_COLOR, int(255 * a)))
                surface.blit(flash, body_rect.topleft)

        if c.alive or fade is not None:
            name_surf = self._font_small.render(c.name, True, config.TEXT)
            if fade is not None:
                name_surf.set_alpha(fade.alpha)
            surface.blit(
                name_surf,
                name_surf.get_rect(midbottom=(body_rect.centerx, body_rect.top - 4)),
            )

    def _fade_for(self, c: Combatant) -> DeathFade | None:
        for df in self.death_fades:
            if df.target is c:
                return df
        return None

    def _combatant_offset(self, c: Combatant, slot: _Slot) -> tuple[int, int]:
        ox, oy = 0, 0

        acting = self.action is not None and self.action.actor is c
        being_hit = self.hit_reaction is not None and self.hit_reaction.target is c
        fade = self._fade_for(c)

        # Idle bob — suppressed while acting, while taking a hit, or while dying.
        if c.alive and not acting and not being_hit and fade is None:
            bob = math.sin(self._clock * config.IDLE_BOB_HZ * 2.0 * math.pi + slot.bob_phase)
            oy += int(bob * config.IDLE_BOB_AMP)

        # Lunge toward the target.
        if acting:
            assert self.action is not None
            target_slot = self._slot_for(self.action.target)
            r = self.action.offset_ratio()
            dx = target_slot.box.centerx - slot.box.centerx
            dy = target_slot.box.centery - slot.box.centery
            ox += int(dx * config.LUNGE_DISTANCE_RATIO * r)
            oy += int(dy * config.LUNGE_DISTANCE_RATIO * r)

        # Hit shake.
        if being_hit:
            assert self.hit_reaction is not None
            ox += self.hit_reaction.shake_x
            oy += self.hit_reaction.shake_y

        # Death sink.
        if fade is not None:
            oy += fade.sink_offset

        return ox, oy

    def _draw_bars(self, surface: pygame.Surface, c: Combatant) -> None:
        """Bars stay anchored at the home position. Hidden once the death fade
        finishes — the combatant has left play.
        """
        if not c.alive and self._fade_for(c) is None:
            return
        assert self._font_small is not None
        slot = self._slot_for(c)
        bar_x = slot.box.left
        bar_w = slot.box.width
        bar_h = 8
        gap = 2

        y = slot.box.bottom + 6

        # HP — smoothed.
        hp_ratio = max(0.0, c.display_hp) / c.max_hp if c.max_hp else 0.0
        pygame.draw.rect(surface, config.HP_EMPTY, (bar_x, y, bar_w, bar_h))
        pygame.draw.rect(surface, config.HP_FILL, (bar_x, y, int(bar_w * hp_ratio), bar_h))
        hp_text = self._font_small.render(f"HP {max(0, c.hp)}/{c.max_hp}", True, config.TEXT)
        surface.blit(hp_text, (bar_x, y + bar_h + 1))
        y += bar_h + 1 + hp_text.get_height() + gap

        # MP — snaps; spec only smooths HP and ATB.
        if c.max_mp > 0:
            mp_ratio = c.mp / c.max_mp
            pygame.draw.rect(surface, config.MP_EMPTY, (bar_x, y, bar_w, bar_h))
            pygame.draw.rect(surface, config.MP_FILL, (bar_x, y, int(bar_w * mp_ratio), bar_h))
            mp_text = self._font_small.render(f"MP {c.mp}/{c.max_mp}", True, config.TEXT)
            surface.blit(mp_text, (bar_x, y + bar_h + 1))
            y += bar_h + 1 + mp_text.get_height() + gap

        # ATB — smoothed.
        atb_ratio = max(0.0, c.display_atb) / config.ATB_MAX
        pygame.draw.rect(surface, config.ATB_EMPTY, (bar_x, y, bar_w, bar_h))
        pygame.draw.rect(surface, config.ATB_FILL, (bar_x, y, int(bar_w * atb_ratio), bar_h))
        atb_text = self._font_small.render("ATB", True, config.TEXT)
        surface.blit(atb_text, (bar_x, y + bar_h + 1))

    def _draw_active_hero_marker(self, surface: pygame.Surface, hero: Combatant) -> None:
        """Right-pointing chevron just left of the active hero's body."""
        slot = self._slot_for(hero)
        cx = slot.box.left - 12
        cy = slot.box.centery
        pygame.draw.polygon(
            surface,
            config.ACTIVE_HERO_MARKER,
            [(cx, cy - 6), (cx + 8, cy), (cx, cy + 6)],
        )

    def _draw_target_cursor(self, surface: pygame.Surface, target: Combatant) -> None:
        """Downward triangle floating just above the targeted enemy."""
        slot = self._slot_for(target)
        cx = slot.box.centerx
        top = slot.box.top - 24
        pygame.draw.polygon(
            surface,
            config.TARGET_CURSOR,
            [(cx - 8, top), (cx + 8, top), (cx, top + 12)],
        )

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
        rect = pygame.Rect(
            (config.SCREEN_W - 220) // 2,
            config.SCREEN_H - 130,
            220,
            110,
        )
        pygame.draw.rect(surface, config.MENU_BG, rect)
        pygame.draw.rect(surface, config.MENU_BORDER, rect, 2)

        if self.submenu_open:
            self._draw_submenu_rows(surface, rect)
            hint_text = "Enter • Esc back"
        else:
            self._draw_main_menu_rows(surface, rect)
            hint_text = "↑↓ • Enter"

        # Active hero header — needed now that two heroes can hold a turn.
        if self.active_hero is not None:
            title = self._font_small.render(self.active_hero.name, True, config.TEXT)
            surface.blit(title, (rect.left + 8, rect.top - title.get_height() - 2))

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

        overlay = pygame.Surface((config.SCREEN_W, config.SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        surface.blit(overlay, (0, 0))

        text = "WIN" if self.outcome == "win" else "LOSE"
        big = self._font_large.render(text, True, config.TEXT)
        surface.blit(big, big.get_rect(center=(config.SCREEN_W // 2, config.SCREEN_H // 2 - 20)))

        hint = self._font_small.render("Press any key to quit", True, config.TEXT)
        surface.blit(hint, hint.get_rect(center=(config.SCREEN_W // 2, config.SCREEN_H // 2 + 30)))
