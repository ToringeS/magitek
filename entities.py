"""Combatant data for the M3 battle. No pygame imports — pure data."""

from dataclasses import dataclass

import config


@dataclass
class Combatant:
    name: str
    hp: int
    max_hp: int
    attack: int
    defense: int
    speed: int
    mp: int = 0
    max_mp: int = 0
    atb: float = 0.0
    # Visual-only smoothing targets for HP and ATB bars. Battle math reads
    # `hp` / `atb`; rendering reads these so the bars can interpolate.
    display_hp: float = 0.0
    display_atb: float = 0.0

    @property
    def alive(self) -> bool:
        return self.hp > 0

    @property
    def atb_ready(self) -> bool:
        return self.atb >= config.ATB_MAX

    def take_damage(self, amount: int) -> int:
        """Reduce HP, clamped at 0. Returns the damage actually applied."""
        applied = min(self.hp, max(0, amount))
        self.hp -= applied
        return applied

    def spend_mp(self, amount: int) -> bool:
        """Deduct MP if possible. Returns True on success, False if insufficient."""
        if amount < 0 or self.mp < amount:
            return False
        self.mp -= amount
        return True


def _from_stats(stats: dict) -> Combatant:
    mp = stats.get("mp", 0)
    hp = stats["hp"]
    return Combatant(
        name=stats["name"],
        hp=hp,
        max_hp=hp,
        mp=mp,
        max_mp=mp,
        attack=stats["attack"],
        defense=stats["defense"],
        speed=stats["speed"],
        display_hp=float(hp),
        display_atb=0.0,
    )


def make_party() -> list[Combatant]:
    """Return the hero party in display order (index 0 = top slot)."""
    return [_from_stats(s) for s in config.HERO_STATS_LIST]


def make_enemies() -> list[Combatant]:
    """Return the enemy party in display order (index 0 = top slot)."""
    return [_from_stats(s) for s in config.ENEMY_STATS_LIST]
