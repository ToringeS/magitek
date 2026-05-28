# Milestone 1 — Magic

Builds on M0. Adds a second menu action and the first resource mechanic: **MP**. One
spell, **Fire**. Everything from M0 stays as-is unless stated below.

## Stack
- Unchanged. Python 3.11+, pygame, no new dependencies.

## What's new
1. The hero gains **MP**: `max_mp = 30`, starts full. Displayed next to HP.
2. The battle menu grows from one option to two: `Attack` / `Magic`.
3. Selecting `Magic` opens a **submenu** listing spells. M1 has exactly one: `Fire`.
   - Selecting `Fire`: deal **fixed 25 damage** to the enemy, **ignoring defense**.
     Costs **10 MP**. Resets the hero's ATB bar to 0, same as Attack.
   - A `Back` option (or Esc) returns to the main menu without spending a turn.
4. If the hero has **less than 10 MP**, `Fire` is shown but **unselectable** (greyed
   out / skipped by the cursor). The hero can still choose `Attack`.
5. The enemy is unchanged: no MP, no magic, auto-attacks on a full bar.

## Data changes
- `Combatant` gains `mp` and `max_mp`. The enemy can leave these at 0.
- Spells live as plain data (e.g. a dataclass or dict): `name`, `mp_cost`, `power`,
  `ignores_defense`. Keep it a small list so M2+ can add entries, but only `Fire`
  exists now.

## Stats
| | HP | MP | attack | defense | speed |
|---|---|---|---|---|---|
| Hero | 100 | 30 | 20 | 5 | 12 |
| Enemy | 60 | — | 12 | 3 | 9 |

**Fire**: power 25, cost 10 MP, ignores defense.

## Done criteria
- [ ] Hero shows MP alongside HP; starts at 30/30.
- [ ] Full ATB bar shows an `Attack` / `Magic` menu.
- [ ] `Magic` → submenu with `Fire` and a way back to the main menu.
- [ ] `Fire` deals 25 damage ignoring defense, costs 10 MP, ends the turn.
- [ ] With MP < 10, `Fire` is present but cannot be selected; `Attack` still works.
- [ ] Backing out of the Magic submenu does not consume the turn.
- [ ] No crashes across a win using Fire and a win using only Attack.

## Explicitly DEFERRED — out of scope for M1
Items · multiple spells · elemental weaknesses/resistances · party · multiple enemies
· sprites/animation · sound · status effects · levels/XP/equipment · overworld · tile
maps · NPCs · dialogue · save/load.
