"""Combatant data for the M0 battle. No pygame imports — pure data."""

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


def _from_stats(stats: dict) -> Combatant:
    return Combatant(
        name=stats["name"],
        hp=stats["hp"],
        max_hp=stats["hp"],
        attack=stats["attack"],
        defense=stats["defense"],
        speed=stats["speed"],
    )


def make_hero() -> Combatant:
    return _from_stats(config.HERO_STATS)


def make_enemy() -> Combatant:
    return _from_stats(config.ENEMY_STATS)
