"""Combatant data for the M1 battle. No pygame imports — pure data."""

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
    return Combatant(
        name=stats["name"],
        hp=stats["hp"],
        max_hp=stats["hp"],
        mp=mp,
        max_mp=mp,
        attack=stats["attack"],
        defense=stats["defense"],
        speed=stats["speed"],
    )


def make_hero() -> Combatant:
    return _from_stats(config.HERO_STATS)


def make_enemy() -> Combatant:
    return _from_stats(config.ENEMY_STATS)
