"""Animation state used by M2's BattleScene.

Each effect is a small dataclass with a `tick(dt)` and a `done` flag. They hold
no pygame state — they describe *what* is happening; BattleScene's draw code
turns that into pixels. Splitting these out keeps the scene focused on state
transitions, and lines up with the M2 refactor goal: animation logic is
independent of how a combatant's body is rendered.
"""

from dataclasses import dataclass
import random

import config
from entities import Combatant


@dataclass
class Action:
    """A combatant lunging toward its target. Damage is precomputed when the
    action begins and applied at the *contact* point (start of the hold).
    """

    actor: Combatant
    target: Combatant
    damage: int
    is_fire: bool = False
    t: float = 0.0
    contact_applied: bool = False

    @property
    def _lunge_total(self) -> float:
        return config.LUNGE_OUT + config.LUNGE_HOLD + config.LUNGE_BACK

    @property
    def total(self) -> float:
        """Total time the scene stays in ACTION. We extend past the lunge so
        the hit reaction (flash + shake) plays before ATB resumes.
        """
        return max(
            self._lunge_total,
            config.LUNGE_OUT + config.HIT_SHAKE_DURATION,
        )

    @property
    def done(self) -> bool:
        return self.t >= self.total

    @property
    def at_contact(self) -> bool:
        return self.t >= config.LUNGE_OUT

    def offset_ratio(self) -> float:
        """How far the actor has moved toward the target, in [0, 1].

        Ramps 0→1 over LUNGE_OUT, holds at 1 over LUNGE_HOLD, ramps 1→0 over
        LUNGE_BACK, then stays at 0 while the hit reaction finishes.
        """
        if self.t < config.LUNGE_OUT:
            return self.t / config.LUNGE_OUT
        held_end = config.LUNGE_OUT + config.LUNGE_HOLD
        if self.t < held_end:
            return 1.0
        if self.t < self._lunge_total:
            return 1.0 - (self.t - held_end) / config.LUNGE_BACK
        return 0.0

    def tick(self, dt: float) -> None:
        self.t += dt


@dataclass
class HitReaction:
    """Flash + shake on a target that just took damage."""

    target: Combatant
    t: float = 0.0
    shake_x: int = 0
    shake_y: int = 0

    @property
    def done(self) -> bool:
        return self.t >= max(config.HIT_FLASH_DURATION, config.HIT_SHAKE_DURATION)

    @property
    def flash_alpha(self) -> float:
        if self.t >= config.HIT_FLASH_DURATION:
            return 0.0
        return 1.0 - self.t / config.HIT_FLASH_DURATION

    def tick(self, dt: float) -> None:
        self.t += dt
        if self.t < config.HIT_SHAKE_DURATION:
            # Random jitter, amplitude tapering to zero — readable, not nauseating.
            amp = int(config.HIT_SHAKE_AMPLITUDE * (1.0 - self.t / config.HIT_SHAKE_DURATION))
            self.shake_x = random.randint(-amp, amp) if amp > 0 else 0
            self.shake_y = random.randint(-amp, amp) if amp > 0 else 0
        else:
            self.shake_x = 0
            self.shake_y = 0


@dataclass
class DamageNumber:
    """A damage value rising and fading above the target."""

    value: int
    x: float
    y: float
    color: tuple[int, int, int]
    t: float = 0.0

    @property
    def done(self) -> bool:
        return self.t >= config.DAMAGE_NUMBER_DURATION

    def current_y(self) -> float:
        r = min(1.0, self.t / config.DAMAGE_NUMBER_DURATION)
        return self.y - config.DAMAGE_NUMBER_RISE * r

    def current_alpha(self) -> int:
        r = min(1.0, self.t / config.DAMAGE_NUMBER_DURATION)
        # Hold opaque for the first half, then fade.
        if r < 0.5:
            return 255
        return max(0, int(255 * (1.0 - (r - 0.5) * 2.0)))

    def tick(self, dt: float) -> None:
        self.t += dt


@dataclass
class DeathFade:
    """Fade-out and sink for a defeated combatant. Plays before the OVER screen."""

    target: Combatant
    t: float = 0.0

    @property
    def done(self) -> bool:
        return self.t >= config.DEATH_FADE_DURATION

    @property
    def alpha(self) -> int:
        r = min(1.0, self.t / config.DEATH_FADE_DURATION)
        return max(0, int(255 * (1.0 - r)))

    @property
    def sink_offset(self) -> int:
        r = min(1.0, self.t / config.DEATH_FADE_DURATION)
        return int(config.DEATH_SINK * r)

    def tick(self, dt: float) -> None:
        self.t += dt
