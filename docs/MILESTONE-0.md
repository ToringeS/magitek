# Milestone 0 — One Battle, Start to Finish

A single ATB battle: one hero vs one enemy, **Attack only**. Colored rectangles and
text labels — no sprites, no sound. When this runs and a battle can be won and lost,
M0 is done.

## Stack
- Python 3.11+, pygame.
- No other dependencies.

## The loop
1. Battle starts. Hero and enemy both visible with HP shown.
2. Each combatant has an **ATB bar** that fills from 0 → 100 over time, at a rate set
   by a `speed` stat. Hero is slightly faster than the enemy.
3. When a combatant's bar is full:
   - **Hero**: pause the fill, show an action menu with a single option, `Attack`.
     On select, deal damage to the enemy, reset the hero's bar to 0, resume.
   - **Enemy**: immediately attack the hero, reset its bar to 0. No menu, no AI.
4. Damage: `damage = max(1, round((attacker.attack - defender.defense) * variance))`
   where `variance` is a random float in `[0.8, 1.2]`.
5. HP can't go below 0. When a combatant hits 0 HP the battle ends.
6. Show a **Win** screen (enemy dies) or **Lose** screen (hero dies). Any key quits.

## Stats (hardcode these in config)
| | HP | attack | defense | speed |
|---|---|---|---|---|
| Hero | 100 | 20 | 5 | 12 |
| Enemy | 60 | 12 | 3 | 9 |

(`speed` = ATB points added per second.)

## Suggested file layout
```
main.py        # entry point, pygame init, top-level game loop, scene switching
battle.py      # BattleScene: ATB timing, menu, damage, win/lose
entities.py    # Combatant dataclass (name, hp, max_hp, attack, defense, speed, atb)
config.py      # screen size, FPS, colors, the stat table above
```

## Done criteria (M0 is finished when all are true)
- [ ] `python main.py` opens a window showing hero and enemy with HP and ATB bars.
- [ ] Bars fill over time; hero fills faster.
- [ ] Hero's full bar shows an Attack menu; selecting it damages the enemy.
- [ ] Enemy attacks automatically when its bar fills.
- [ ] Reaching 0 HP ends the battle with a Win or Lose screen.
- [ ] No crashes across a full win and a full loss.

## Explicitly DEFERRED — out of scope for M0, say no until it ships
Party members · multiple enemies · sprites/animation · sound · magic · items ·
status effects · levels/XP/equipment · overworld · tile maps · NPCs · dialogue ·
save/load · real FF6 damage formulas.
